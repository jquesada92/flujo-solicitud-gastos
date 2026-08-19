import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('SECRET_KEY', 'unit-test-secret-key-at-least-32-characters')
os.environ.setdefault('ANALYTICS_HASH_KEY', 'unit-test-analytics-key-at-least-32-characters')
os.environ.setdefault('ENVIRONMENT', 'test')

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.application import create_app
from app.core.database import Base, get_db
from app.core.security import create_token, hash_password
from app.models.entities import User, UserRole
from app.models.iam import Permission, Position, SystemAccount, UserPermission, UserPosition


class IamUserNotificationTests(unittest.TestCase):
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

            permissions = {
                'config:manage': Permission(
                    code='config:manage',
                    name='Administrar configuración',
                    active=True,
                ),
                'requests:read': Permission(
                    code='requests:read',
                    name='Consultar solicitudes',
                    active=True,
                ),
            }
            db.add_all(permissions.values())
            db.flush()

            admin = self._new_user(db, 'admin@example.com', 'Admin')
            member = self._new_user(db, 'member@example.com', 'Miembro')
            db.flush()
            db.add(SystemAccount(user_id=admin.id, account_type='TECHNICAL_ADMIN'))
            db.add(UserPermission(user_id=member.id, permission_id=permissions['requests:read'].id))

            analyst = Position(code='analista', name='Analista', active=True)
            treasurer = Position(code='tesorero', name='Tesorero', active=True)
            db.add_all([analyst, treasurer])
            db.flush()
            db.add(UserPosition(user_id=member.id, position_id=analyst.id))
            db.commit()

            self.admin_id = admin.id
            self.member_id = member.id
            self.analyst_id = analyst.id
            self.treasurer_id = treasurer.id
            self.admin_token = create_token(admin)

    def _new_user(self, db, email: str, name: str) -> User:
        user = User(
            name=name,
            email=email,
            password_hash=hash_password('Test-password-123!'),
            role=UserRole.VIEWER,
            title='SIN_ASIGNAR',
            active=True,
            can_request=False,
            can_approve=False,
            can_view=False,
            can_configure=False,
            must_change_password=False,
            last_activity_at=datetime.now(timezone.utc),
        )
        db.add(user)
        return user

    def auth(self) -> dict[str, str]:
        return {'Authorization': f'Bearer {self.admin_token}'}

    def test_creation_invitation_receives_database_position_and_effective_permissions(self):
        with patch('app.api.iam_users.send_user_invitation') as invitation:
            response = self.client.post(
                '/api/iam/users',
                headers=self.auth(),
                json={
                    'identity_document': '8-999-1234',
                    'first_name': 'Ana',
                    'last_name': 'Pérez',
                    'email': 'ana@example.com',
                    'active': True,
                    'position_ids': [self.treasurer_id],
                    'direct_permission_codes': ['requests:read'],
                },
            )

        self.assertEqual(response.status_code, 201, response.text)
        invitation.assert_called_once()
        kwargs = invitation.call_args.kwargs
        self.assertEqual(kwargs['positions'], ['Tesorero'])
        self.assertEqual(
            kwargs['permissions'],
            ['Consultar solicitudes (requests:read)'],
        )

    def test_position_change_sends_current_effective_permissions(self):
        with patch('app.api.iam_users.send_user_access_update') as notification:
            response = self.client.patch(
                f'/api/iam/users/{self.member_id}',
                headers=self.auth(),
                json={'position_ids': [self.treasurer_id]},
            )

        self.assertEqual(response.status_code, 200, response.text)
        notification.assert_called_once()
        kwargs = notification.call_args.kwargs
        self.assertEqual(kwargs['previous_positions'], ['Analista'])
        self.assertEqual(kwargs['positions'], ['Tesorero'])
        self.assertEqual(
            kwargs['permissions'],
            ['Consultar solicitudes (requests:read)'],
        )

    def test_email_failure_does_not_rollback_position_change(self):
        with patch(
            'app.api.iam_users.send_user_access_update',
            side_effect=RuntimeError('email provider unavailable'),
        ):
            response = self.client.patch(
                f'/api/iam/users/{self.member_id}',
                headers=self.auth(),
                json={'position_ids': [self.treasurer_id]},
            )

        self.assertEqual(response.status_code, 200, response.text)
        with self.Session() as db:
            position_ids = set(db.scalars(
                select(UserPosition.position_id).where(UserPosition.user_id == self.member_id)
            ).all())
        self.assertEqual(position_ids, {self.treasurer_id})


if __name__ == '__main__':
    unittest.main()
