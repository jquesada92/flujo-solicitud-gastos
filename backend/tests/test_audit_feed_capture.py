import os
import unittest

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('SECRET_KEY', 'unit-test-secret-key-at-least-32-characters')
os.environ.setdefault('ANALYTICS_HASH_KEY', 'unit-test-analytics-key-at-least-32-characters')
os.environ.setdefault('ENVIRONMENT', 'test')

from sqlalchemy import create_engine, delete, func, select, update
from sqlalchemy.orm import sessionmaker

import app.models.audit_capture  # noqa: F401
from app.core.audit_context import set_audit_actor
from app.core.database import Base
from app.models.audit_capture import prepare_entity_revision, record_entity_revision
from app.models.audit_feed import AuditChangeFeed
from app.models.entities import ExpenseArea, User, UserRole
from app.models.iam import Permission, Position, Role, RolePermission, UserGroup, UserRoleAssignment


class AuditFeedCaptureTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    @staticmethod
    def _user(email='person@example.com'):
        return User(
            name='Persona Auditada',
            first_name='Persona',
            last_name='Auditada',
            email=email,
            password_hash='not-a-secret-in-tests',
            role=UserRole.VIEWER,
            title='SIN_ASIGNAR',
            active=True,
            must_change_password=False,
        )

    def test_entity_create_and_update_append_precomputed_delta(self):
        with self.Session() as db:
            area = ExpenseArea(code='OPS', name='Operaciones', active=True)
            db.add(area)
            db.commit()

            area.name = 'Operaciones generales'
            db.commit()

            events = list(db.scalars(
                select(AuditChangeFeed)
                .where(
                    AuditChangeFeed.entity_type == 'AREA',
                    AuditChangeFeed.entity_id == str(area.id),
                )
                .order_by(AuditChangeFeed.event_sequence)
            ))

        self.assertEqual([item.change_type for item in events], ['CREATE', 'UPDATE'])
        self.assertEqual(events[-1].changes['name'], {
            'before': 'Operaciones',
            'after': 'Operaciones generales',
        })

    def test_role_permission_changes_are_coalesced_into_role_revision(self):
        with self.Session() as db:
            permission = Permission(code='requests:read', name='Consultar', active=True)
            role = Role(code='reader', name='Lector', active=True)
            db.add_all([permission, role])
            db.commit()

            db.add(RolePermission(role_id=role.id, permission_id=permission.id))
            db.commit()

            event = db.scalar(
                select(AuditChangeFeed)
                .where(
                    AuditChangeFeed.entity_type == 'ROLE',
                    AuditChangeFeed.entity_id == str(role.id),
                    AuditChangeFeed.event_type == 'ROLE_PERMISSIONS_UPDATED',
                )
                .order_by(AuditChangeFeed.event_sequence.desc())
            )

        self.assertIsNotNone(event)
        self.assertEqual(event.changes['permission_codes']['before'], [])
        self.assertEqual(event.changes['permission_codes']['after'], ['requests:read'])

    def test_core_delete_bridge_records_pure_user_role_removal(self):
        with self.Session() as db:
            user = self._user()
            role = Role(code='temporary', name='Temporal', active=True)
            db.add_all([user, role])
            db.flush()
            db.add(UserRoleAssignment(user_id=user.id, role_id=role.id))
            db.commit()

            set_audit_actor(
                db,
                user_id=user.id,
                identifier=user.email,
                label=user.full_name,
            )
            db.execute(delete(UserRoleAssignment).where(
                UserRoleAssignment.user_id == user.id,
            ))
            record_entity_revision(
                db,
                User,
                user.id,
                event_type='USER_ROLES_UPDATED',
            )
            db.commit()

            event = db.scalar(
                select(AuditChangeFeed)
                .where(
                    AuditChangeFeed.entity_type == 'USER',
                    AuditChangeFeed.entity_id == str(user.id),
                    AuditChangeFeed.event_type == 'USER_ROLES_UPDATED',
                )
                .order_by(AuditChangeFeed.event_sequence.desc())
            )

        self.assertEqual([item['name'] for item in event.changes['assigned_roles']['before']], ['Temporal'])
        self.assertEqual(event.changes['assigned_roles']['after'], [])
        self.assertEqual(event.actor_label, 'Persona Auditada')

    def test_prepared_core_change_keeps_before_state_without_feed_baseline(self):
        with self.Session() as db:
            inserted = db.execute(Position.__table__.insert().values(
                code='legacy-position',
                name='Cargo anterior',
                description=None,
                active=True,
            ))
            position_id = inserted.inserted_primary_key[0]
            db.commit()

            prepare_entity_revision(db, Position, position_id)
            db.execute(
                update(Position)
                .where(Position.id == position_id)
                .values(name='Cargo actual')
            )
            record_entity_revision(db, Position, position_id)
            db.commit()

            event = db.scalar(select(AuditChangeFeed).where(
                AuditChangeFeed.entity_type == 'POSITION',
                AuditChangeFeed.entity_id == str(position_id),
            ))

        self.assertEqual(event.change_type, 'UPDATE')
        self.assertEqual(event.changes['name'], {
            'before': 'Cargo anterior',
            'after': 'Cargo actual',
        })

    def test_rollback_removes_business_change_and_feed_event(self):
        with self.Session() as db:
            group = UserGroup(code='finance', name='Finanzas', active=True)
            db.add(group)
            db.flush()
            db.rollback()

        with self.Session() as db:
            self.assertEqual(db.scalar(select(func.count(UserGroup.id))), 0)
            self.assertEqual(db.scalar(select(func.count(AuditChangeFeed.event_sequence))), 0)

    def test_noop_update_does_not_append_event(self):
        with self.Session() as db:
            role = Role(code='same', name='Sin cambios', active=True)
            db.add(role)
            db.commit()
            original_count = db.scalar(select(func.count(AuditChangeFeed.event_sequence)))

            role.name = 'Sin cambios'
            db.commit()
            next_count = db.scalar(select(func.count(AuditChangeFeed.event_sequence)))

        self.assertEqual(next_count, original_count)


if __name__ == '__main__':
    unittest.main()
