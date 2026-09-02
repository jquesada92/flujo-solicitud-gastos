import os
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('SECRET_KEY', 'unit-test-secret-key-at-least-32-characters')
os.environ.setdefault('ANALYTICS_HASH_KEY', 'unit-test-analytics-key-at-least-32-characters')
os.environ.setdefault('ENVIRONMENT', 'test')

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.audit import (
    APP_TIME_ZONE,
    AUDIT_PAGE_SIZE,
    _date_range_bounds,
    list_audit_events,
)
from app.application import create_app
from app.core.audit_context import set_audit_actor
from app.core.database import Base, get_db
from app.core.rate_limit import clear_rate_limits
from app.core.security import create_token
from app.models.audit_feed import AuditChangeFeed
from app.models.entities import ApprovalPolicy, User, UserRole
from app.models.iam import Permission, Role, SystemAccount, UserRoleAssignment


class AuditApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            'sqlite://',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool,
        )
        cls.Session = sessionmaker(bind=cls.engine, expire_on_commit=False)
        Base.metadata.create_all(cls.engine)
        cls.app = create_app()

        def override_get_db():
            with cls.Session() as db:
                yield db

        cls.app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(cls.app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.app.dependency_overrides.clear()
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def setUp(self):
        clear_rate_limits()
        with self.Session() as db:
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(table.delete())
            db.commit()

            db.add_all([
                Permission(code='requests:read', name='Consultar solicitudes', active=True),
                Permission(code='config:manage', name='Administrar configuración', active=True),
            ])
            self.admin = User(
                name='Sys Admin',
                first_name='Sys',
                last_name='Admin',
                email='admin@example.com',
                password_hash='not-used',
                role=UserRole.ADMIN,
                title='ADMIN_SISTEMA',
                active=True,
                must_change_password=False,
                last_activity_at=datetime.now(timezone.utc),
            )
            self.target = User(
                name='Usuario Auditada',
                first_name='Usuario',
                last_name='Auditada',
                identity_document='8-888-8888',
                phone='6000-1234',
                email='persona.auditada@example.com',
                password_hash='not-used',
                role=UserRole.VIEWER,
                title='SIN_ASIGNAR',
                active=True,
                must_change_password=False,
                last_activity_at=datetime.now(timezone.utc),
            )
            db.add_all([self.admin, self.target])
            db.flush()
            db.add(SystemAccount(user_id=self.admin.id, account_type='TECHNICAL_ADMIN'))
            self.old_role = Role(code='old-role', name='Rol anterior', active=True)
            self.new_role = Role(code='new-role', name='Rol actual', active=True)
            db.add_all([self.old_role, self.new_role])
            db.flush()
            db.add(UserRoleAssignment(user_id=self.target.id, role_id=self.old_role.id))
            db.commit()

            self.admin_id = self.admin.id
            self.target_id = self.target.id
            self.old_role_id = self.old_role.id
            self.new_role_id = self.new_role.id
            self.admin_token = create_token(self.admin)

    def auth(self):
        return {'Authorization': f'Bearer {self.admin_token}'}

    def add_feed_event(
        self,
        event_id: str,
        occurred_at: datetime,
        *,
        kind: str = 'USER',
    ):
        with self.Session() as db:
            db.add(AuditChangeFeed(
                event_id=event_id,
                occurred_at=occurred_at,
                kind=kind,
                entity_type='USER',
                entity_id=str(self.target_id),
                event_type='USER_UPDATED',
                change_type='UPDATE',
                subject=event_id,
                actor_user_id=self.admin_id,
                actor_identifier='admin@example.com',
                actor_label='Sys Admin',
                changed_fields=['name'],
                changes={'name': {'before': 'Antes', 'after': event_id}},
                snapshot={'name': event_id},
                event_context={},
                search_text=event_id,
                source_type='TEST',
                source_id=event_id,
                visible=True,
            ))
            db.commit()

    def test_user_role_change_exposes_previous_and_current_roles(self):
        with self.Session() as db:
            set_audit_actor(
                db,
                user_id=self.admin_id,
                identifier='admin@example.com',
                identity_document=None,
                label='Sys Admin',
            )
            db.execute(delete(UserRoleAssignment).where(
                UserRoleAssignment.user_id == self.target_id
            ))
            db.add(UserRoleAssignment(user_id=self.target_id, role_id=self.new_role_id))
            db.commit()

        response = self.client.get(
            '/api/audit/events',
            params={'kind': 'USER'},
            headers=self.auth(),
        )

        self.assertEqual(response.status_code, 200, response.text)
        matching = [
            item for item in response.json()['items']
            if item['event_type'] == 'USER_ROLES_UPDATED'
            and item['subject'] == 'Usuario Auditada'
            and any(
                role.get('name') == 'Rol actual'
                for role in item['changes']['assigned_roles']['after']
            )
        ]
        self.assertEqual(len(matching), 1, response.json())
        event = matching[0]
        self.assertEqual(event['change_type'], 'UPDATE')
        self.assertEqual(event['actor'], 'Sys Admin')
        self.assertEqual(
            [role['name'] for role in event['changes']['assigned_roles']['before']],
            ['Rol anterior'],
        )
        self.assertEqual(
            [role['name'] for role in event['changes']['assigned_roles']['after']],
            ['Rol actual'],
        )

    def test_audit_response_masks_personal_identifiers(self):
        response = self.client.get(
            '/api/audit/events',
            params={'kind': 'USER'},
            headers=self.auth(),
        )

        self.assertEqual(response.status_code, 200, response.text)
        serialized = response.text
        self.assertNotIn('persona.auditada@example.com', serialized)
        self.assertNotIn('8-888-8888', serialized)
        self.assertNotIn('6000-1234', serialized)
        self.assertIn('p***@example.com', serialized)
        self.assertIn('****8888', serialized)
        self.assertIn('****1234', serialized)

    def test_deleted_rule_is_labeled_and_keeps_previous_values(self):
        with self.Session() as db:
            set_audit_actor(
                db,
                user_id=self.admin_id,
                identifier='admin@example.com',
                label='Sys Admin',
            )
            policy = ApprovalPolicy(
                name='Regla temporal',
                expense_type='ALL',
                min_amount=0,
                max_amount=100,
                approval_mode='ANY',
                approver_profile_codes=[],
                approver_role_ids=[self.old_role_id],
                approver_group_ids=[],
                active=True,
            )
            db.add(policy)
            db.commit()
            db.delete(policy)
            db.commit()

        response = self.client.get(
            '/api/audit/events',
            params={'kind': 'RULE'},
            headers=self.auth(),
        )

        self.assertEqual(response.status_code, 200, response.text)
        event = response.json()['items'][0]
        self.assertEqual(event['change_type'], 'DELETE')
        self.assertEqual(event['changes']['name'], {
            'before': 'Regla temporal',
            'after': None,
        })
        self.assertEqual(event['changes']['active'], {
            'before': True,
            'after': None,
        })

    def test_listing_executes_one_feed_query(self):
        statements = []

        def count_statement(*_):
            statements.append(1)

        event.listen(self.engine, 'before_cursor_execute', count_statement)
        try:
            with self.Session() as db:
                result = list_audit_events(
                    kind='ALL',
                    limit=AUDIT_PAGE_SIZE,
                    cursor=None,
                    q=None,
                    date_from=None,
                    date_to=None,
                    db=db,
                )
        finally:
            event.remove(self.engine, 'before_cursor_execute', count_statement)

        self.assertGreater(len(result['items']), 0)
        self.assertEqual(len(statements), 1)

    def test_default_keyset_pagination_returns_ten_then_two_without_duplicates(self):
        occurred_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        expected_ids = {f'TEST:FLOW:{index:02d}' for index in range(12)}
        for event_id in expected_ids:
            self.add_feed_event(event_id, occurred_at, kind='FLOW')

        first_response = self.client.get(
            '/api/audit/events',
            params={'kind': 'FLOW'},
            headers=self.auth(),
        )

        self.assertEqual(first_response.status_code, 200, first_response.text)
        first_page = first_response.json()
        first_ids = [item['event_id'] for item in first_page['items']]
        self.assertEqual(len(first_ids), AUDIT_PAGE_SIZE)
        self.assertTrue(first_page['has_more'])
        self.assertIsNotNone(first_page['next_cursor'])

        second_response = self.client.get(
            '/api/audit/events',
            params={
                'kind': 'FLOW',
                'cursor': first_page['next_cursor'],
            },
            headers=self.auth(),
        )

        self.assertEqual(second_response.status_code, 200, second_response.text)
        second_page = second_response.json()
        second_ids = [item['event_id'] for item in second_page['items']]
        self.assertEqual(len(second_ids), 2)
        self.assertFalse(second_page['has_more'])
        self.assertIsNone(second_page['next_cursor'])
        self.assertTrue(set(first_ids).isdisjoint(second_ids))
        self.assertEqual(set(first_ids + second_ids), expected_ids)

    def test_default_range_is_seven_inclusive_application_dates(self):
        fixed_now = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
        with patch('app.api.audit.APP_TIME_ZONE', 'America/Panama'):
            range_start, range_end, current = _date_range_bounds(
                None,
                None,
                now=fixed_now,
            )

        self.assertEqual(range_start, datetime(2026, 8, 26, 5, 0, tzinfo=timezone.utc))
        self.assertEqual(range_end, datetime(2026, 9, 2, 5, 0, tzinfo=timezone.utc))
        self.assertEqual(current, fixed_now)

    def test_custom_range_can_retrieve_events_older_than_45_days(self):
        now = datetime.now(timezone.utc)
        recent_id = 'TEST:RECENT'
        historical_id = 'TEST:HISTORICAL'
        self.add_feed_event(recent_id, now - timedelta(days=2))
        historical_at = now - timedelta(days=60)
        self.add_feed_event(historical_id, historical_at)

        default_response = self.client.get('/api/audit/events', headers=self.auth())
        self.assertEqual(default_response.status_code, 200, default_response.text)
        default_ids = {item['event_id'] for item in default_response.json()['items']}
        self.assertIn(recent_id, default_ids)
        self.assertNotIn(historical_id, default_ids)

        historical_date = historical_at.astimezone(ZoneInfo(APP_TIME_ZONE)).date()
        custom_response = self.client.get(
            '/api/audit/events',
            params={
                'date_from': historical_date.isoformat(),
                'date_to': historical_date.isoformat(),
            },
            headers=self.auth(),
        )
        self.assertEqual(custom_response.status_code, 200, custom_response.text)
        custom_ids = {item['event_id'] for item in custom_response.json()['items']}
        self.assertIn(historical_id, custom_ids)
        self.assertNotIn(recent_id, custom_ids)

    def test_custom_dates_include_both_calendar_days(self):
        selected_date = (
            datetime.now(ZoneInfo(APP_TIME_ZONE)) - timedelta(days=20)
        ).date()
        range_start, range_end, _ = _date_range_bounds(selected_date, selected_date)
        start_id = 'TEST:RANGE_START'
        end_id = 'TEST:RANGE_END'
        outside_id = 'TEST:NEXT_DAY'
        self.add_feed_event(start_id, range_start)
        self.add_feed_event(end_id, range_end - timedelta(microseconds=1))
        self.add_feed_event(outside_id, range_end)

        response = self.client.get(
            '/api/audit/events',
            params={
                'kind': 'USER',
                'date_from': selected_date.isoformat(),
                'date_to': selected_date.isoformat(),
            },
            headers=self.auth(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        event_ids = {item['event_id'] for item in response.json()['items']}
        self.assertIn(start_id, event_ids)
        self.assertIn(end_id, event_ids)
        self.assertNotIn(outside_id, event_ids)

    def test_date_range_requires_both_dates_in_order(self):
        partial = self.client.get(
            '/api/audit/events',
            params={'date_from': date.today().isoformat()},
            headers=self.auth(),
        )
        self.assertEqual(partial.status_code, 422, partial.text)

        reversed_range = self.client.get(
            '/api/audit/events',
            params={'date_from': '2026-09-01', 'date_to': '2026-08-31'},
            headers=self.auth(),
        )
        self.assertEqual(reversed_range.status_code, 422, reversed_range.text)

    def test_invalid_cursor_returns_validation_error(self):
        response = self.client.get(
            '/api/audit/events',
            params={'cursor': 'invalid'},
            headers=self.auth(),
        )
        self.assertEqual(response.status_code, 422, response.text)


if __name__ == '__main__':
    unittest.main()
