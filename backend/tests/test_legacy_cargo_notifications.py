import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('SECRET_KEY', 'unit-test-secret-key-at-least-32-characters')
os.environ.setdefault('ANALYTICS_HASH_KEY', 'unit-test-analytics-key-at-least-32-characters')
os.environ.setdefault('ENVIRONMENT', 'test')
os.environ.setdefault('EMAIL_MODE', 'console')

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.application import create_app
from app.core.database import Base, get_db
from app.core.security import create_token, hash_password
from app.models.entities import AccessProfile, User, UserRole
from app.models.iam import (
    Permission,
    Position,
    PositionRole,
    Role,
    RolePermission,
    SystemAccount,
    UserPosition,
)


class LegacyCargoNotificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            'sqlite://',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool,
        )
        cls.Session = sessionmaker(bind=cls.engine, autocommit=False, autoflush=False)
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
        with self.Session() as db:
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(table.delete())
            db.commit()

            read = Permission(code='requests:read', name='Consultar solicitudes', active=True)
            approve = Permission(code='requests:approve', name='Aprobar solicitudes', active=True)
            config = Permission(code='config:manage', name='Administrar configuración', active=True)
            db.add_all([read, approve, config])
            db.flush()

            approver_role = Role(code='approver', name='Aprobador', active=True, system_managed=False)
            db.add(approver_role)
            db.flush()
            db.add(RolePermission(role_id=approver_role.id, permission_id=approve.id))

            vocal = Position(code='legacy-vocero', name='Vocal', active=True)
            treasurer = Position(code='legacy-tesorero', name='Tesorero', active=True)
            db.add_all([vocal, treasurer])
            db.flush()
            db.add(PositionRole(position_id=treasurer.id, role_id=approver_role.id))

            db.add_all([
                AccessProfile(
                    code='VOCERO', name='Vocal', can_request=False, can_approve=False,
                    can_view=True, can_configure=False, active=True,
                ),
                AccessProfile(
                    code='TESORERO', name='Tesorero', can_request=False, can_approve=True,
                    can_view=True, can_configure=False, active=True,
                ),
            ])

            admin = self._user(db, 'admin@example.com', 'ADMIN-LEGACY', UserRole.ADMIN, 'ADMIN_SISTEMA')
            member = self._user(db, 'member@example.com', 'MEMBER-LEGACY', UserRole.VIEWER, 'VOCERO')
            db.flush()
            db.add(SystemAccount(user_id=admin.id, account_type='TECHNICAL_ADMIN'))
            db.add(UserPosition(user_id=member.id, position_id=vocal.id))
            db.commit()

            self.admin_token = create_token(admin)
            self.member_id = member.id
            self.vocal_id = vocal.id
            self.treasurer_id = treasurer.id

    def _user(self, db, email, document, role, title):
        user = User(
            name=email.split('@')[0],
            first_name='Test',
            last_name='User',
            identity_document=document,
            email=email,
            password_hash=hash_password('Test-password-123!'),
            role=role,
            title=title,
            active=True,
            can_request=False,
            can_approve=False,
            can_view=True,
            can_configure=role == UserRole.ADMIN,
            must_change_password=False,
            last_activity_at=datetime.now(timezone.utc),
        )
        db.add(user)
        return user

    def auth(self):
        return {'Authorization': f'Bearer {self.admin_token}'}

    @staticmethod
    def _apply_without_audit(_db, user, changes, _actor):
        if 'title' in changes:
            user.title = changes['title']
        if 'active' in changes:
            user.active = changes['active']

    def test_assignment_screen_updates_canonical_position_and_sends_email(self):
        with patch(
            'app.api.legacy_position_notifications._apply_user_changes',
            side_effect=self._apply_without_audit,
        ), patch(
            'app.api.legacy_position_notifications.send_user_access_updated'
        ) as notification:
            response = self.client.patch(
                '/api/users/bulk',
                headers=self.auth(),
                json={'users': [{'id': self.member_id, 'title': 'TESORERO'}]},
            )

        self.assertEqual(response.status_code, 200, response.text)
        notification.assert_called_once()
        _, positions, permissions = notification.call_args.args
        self.assertEqual(positions, ['Tesorero'])
        self.assertIn(('Consultar solicitudes', 'requests:read'), permissions)
        self.assertIn(('Aprobar solicitudes', 'requests:approve'), permissions)

        with self.Session() as db:
            user = db.get(User, self.member_id)
            position_ids = set(db.scalars(
                select(UserPosition.position_id).where(UserPosition.user_id == self.member_id)
            ).all())
            self.assertEqual(user.title, 'TESORERO')
            self.assertEqual(position_ids, {self.treasurer_id})

    def test_email_failure_rolls_back_legacy_and_canonical_cargo(self):
        with patch(
            'app.api.legacy_position_notifications._apply_user_changes',
            side_effect=self._apply_without_audit,
        ), patch(
            'app.api.legacy_position_notifications.send_user_access_updated',
            side_effect=RuntimeError('mail unavailable'),
        ):
            response = self.client.patch(
                '/api/users/bulk',
                headers=self.auth(),
                json={'users': [{'id': self.member_id, 'title': 'TESORERO'}]},
            )

        self.assertEqual(response.status_code, 502, response.text)
        with self.Session() as db:
            user = db.get(User, self.member_id)
            position_ids = set(db.scalars(
                select(UserPosition.position_id).where(UserPosition.user_id == self.member_id)
            ).all())
            self.assertEqual(user.title, 'VOCERO')
            self.assertEqual(position_ids, {self.vocal_id})

    def test_same_cargo_does_not_send_duplicate_email(self):
        with patch(
            'app.api.legacy_position_notifications._apply_user_changes',
            side_effect=self._apply_without_audit,
        ), patch(
            'app.api.legacy_position_notifications.send_user_access_updated'
        ) as notification:
            response = self.client.patch(
                '/api/users/bulk',
                headers=self.auth(),
                json={'users': [{'id': self.member_id, 'title': 'VOCERO'}]},
            )

        self.assertEqual(response.status_code, 200, response.text)
        notification.assert_not_called()


if __name__ == '__main__':
    unittest.main()
