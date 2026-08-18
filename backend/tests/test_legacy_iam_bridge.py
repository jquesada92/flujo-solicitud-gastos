import os
import unittest
from datetime import datetime, timezone

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('SECRET_KEY', 'unit-test-secret-key-at-least-32-characters')
os.environ.setdefault('ANALYTICS_HASH_KEY', 'unit-test-analytics-key-at-least-32-characters')
os.environ.setdefault('ENVIRONMENT', 'test')

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.security import hash_password
from app.models.entities import User, UserRole
from app.models.iam import Permission, UserPermission
from app.services.legacy_iam_bridge import register_legacy_iam_bridge


class LegacyIamBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        register_legacy_iam_bridge()
        cls.engine = create_engine(
            'sqlite://',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool,
        )
        cls.Session = sessionmaker(bind=cls.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(cls.engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def setUp(self):
        with self.Session() as db:
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(table.delete())
            db.add_all([
                Permission(code='requests:create', name='Crear solicitudes', active=True),
                Permission(code='requests:approve', name='Aprobar solicitudes', active=True),
                Permission(code='config:manage', name='Administrar configuración', active=True),
            ])
            db.commit()

    def _user(self, email: str, *, role=UserRole.VIEWER, can_approve=False) -> User:
        return User(
            name=email,
            email=email,
            password_hash=hash_password('Test-password-123!'),
            role=role,
            title='SIN_ASIGNAR',
            active=True,
            can_request=False,
            can_approve=can_approve,
            can_view=True,
            can_configure=False,
            must_change_password=False,
            last_activity_at=datetime.now(timezone.utc),
        )

    def test_new_legacy_approver_seeds_canonical_permission(self):
        with self.Session() as db:
            user = self._user('approver@example.com', can_approve=True)
            db.add(user)
            db.commit()
            code = db.scalar(
                select(Permission.code)
                .join(UserPermission, UserPermission.permission_id == Permission.id)
                .where(UserPermission.user_id == user.id)
            )
            self.assertEqual(code, 'requests:approve')

    def test_legacy_update_seeds_permission_when_flag_changes_true(self):
        with self.Session() as db:
            user = self._user('member@example.com')
            db.add(user)
            db.commit()
            self.assertIsNone(db.scalar(select(UserPermission.id).where(UserPermission.user_id == user.id)))

            user.can_approve = True
            db.commit()

            code = db.scalar(
                select(Permission.code)
                .join(UserPermission, UserPermission.permission_id == Permission.id)
                .where(UserPermission.user_id == user.id)
            )
            self.assertEqual(code, 'requests:approve')

    def test_bridge_is_additive_and_does_not_revoke_canonical_grant(self):
        with self.Session() as db:
            user = self._user('existing@example.com', can_approve=True)
            db.add(user)
            db.commit()
            user.can_approve = False
            db.commit()
            code = db.scalar(
                select(Permission.code)
                .join(UserPermission, UserPermission.permission_id == Permission.id)
                .where(UserPermission.user_id == user.id)
            )
            self.assertEqual(code, 'requests:approve')

    def test_technical_admin_is_not_seeded_from_legacy_flags(self):
        with self.Session() as db:
            admin = self._user('system@example.com', role=UserRole.ADMIN, can_approve=True)
            db.add(admin)
            db.commit()
            self.assertIsNone(db.scalar(select(UserPermission.id).where(UserPermission.user_id == admin.id)))


if __name__ == '__main__':
    unittest.main()
