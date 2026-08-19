import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
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
from app.models.iam import Permission, Position, PositionRole, Role, RolePermission, SystemAccount
from app.services import email_service


class UserAccessNotificationTests(unittest.TestCase):
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
            config = Permission(code='config:manage', name='Administración técnica', active=True)
            db.add_all([read, approve, config])
            db.flush()

            approver_role = Role(code='approver', name='Aprobador', active=True, system_managed=False)
            db.add(approver_role)
            db.flush()
            db.add(RolePermission(role_id=approver_role.id, permission_id=approve.id))

            vocal = Position(code='vocal', name='Vocal', active=True)
            treasurer = Position(code='treasurer', name='Tesorero', active=True)
            db.add_all([vocal, treasurer])
            db.flush()
            db.add(PositionRole(position_id=treasurer.id, role_id=approver_role.id))

            admin = self._new_user(db, 'admin@example.com', 'ADMIN-1')
            member = self._new_user(db, 'member@example.com', 'MEMBER-1')
            db.flush()
            db.add(SystemAccount(user_id=admin.id, account_type='TECHNICAL_ADMIN'))
            db.commit()

            self.admin_id = admin.id
            self.member_id = member.id
            self.vocal_id = vocal.id
            self.treasurer_id = treasurer.id
            self.admin_token = create_token(admin)

    def _new_user(self, db, email: str, identity_document: str) -> User:
        user = User(
            name=email.split('@')[0],
            first_name='Test',
            last_name='User',
            identity_document=identity_document,
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

    def test_invitation_contains_position_and_effective_permissions(self):
        with patch('app.api.iam_users.send_user_invitation') as invitation:
            response = self.client.post(
                '/api/iam/users',
                headers=self.auth(),
                json={
                    'identity_document': 'NEW-100',
                    'first_name': 'Ana',
                    'last_name': 'Pérez',
                    'email': 'ana@example.com',
                    'active': True,
                    'position_ids': [self.treasurer_id],
                },
            )
        self.assertEqual(response.status_code, 201, response.text)
        invitation.assert_called_once()
        _, temporary_password, positions, permissions = invitation.call_args.args
        self.assertTrue(temporary_password)
        self.assertEqual(positions, ['Tesorero'])
        self.assertIn(('Consultar solicitudes', 'requests:read'), permissions)
        self.assertIn(('Aprobar solicitudes', 'requests:approve'), permissions)

    def test_real_position_change_sends_updated_effective_permissions(self):
        first = self.client.patch(
            f'/api/iam/users/{self.member_id}',
            headers=self.auth(),
            json={'position_ids': [self.vocal_id]},
        )
        self.assertEqual(first.status_code, 200, first.text)

        with patch('app.api.iam_users.send_user_access_updated') as notification:
            response = self.client.patch(
                f'/api/iam/users/{self.member_id}',
                headers=self.auth(),
                json={'position_ids': [self.treasurer_id]},
            )
        self.assertEqual(response.status_code, 200, response.text)
        notification.assert_called_once()
        _, positions, permissions = notification.call_args.args
        self.assertEqual(positions, ['Tesorero'])
        self.assertIn(('Consultar solicitudes', 'requests:read'), permissions)
        self.assertIn(('Aprobar solicitudes', 'requests:approve'), permissions)

    def test_saving_same_position_does_not_send_duplicate_notification(self):
        with patch('app.api.iam_users.send_user_access_updated'):
            first = self.client.patch(
                f'/api/iam/users/{self.member_id}',
                headers=self.auth(),
                json={'position_ids': [self.treasurer_id]},
            )
        self.assertEqual(first.status_code, 200, first.text)

        with patch('app.api.iam_users.send_user_access_updated') as notification:
            response = self.client.patch(
                f'/api/iam/users/{self.member_id}',
                headers=self.auth(),
                json={'position_ids': [self.treasurer_id]},
            )
        self.assertEqual(response.status_code, 200, response.text)
        notification.assert_not_called()

    def test_position_change_rolls_back_when_required_notification_fails(self):
        with patch('app.api.iam_users.send_user_access_updated', side_effect=RuntimeError('mail unavailable')):
            response = self.client.patch(
                f'/api/iam/users/{self.member_id}',
                headers=self.auth(),
                json={'position_ids': [self.treasurer_id]},
            )
        self.assertEqual(response.status_code, 502, response.text)
        with self.Session() as db:
            position_ids = set(db.scalars(
                select(Position.id)
                .join_from(Position, __import__('app.models.iam', fromlist=['UserPosition']).UserPosition,
                           __import__('app.models.iam', fromlist=['UserPosition']).UserPosition.position_id == Position.id)
                .where(__import__('app.models.iam', fromlist=['UserPosition']).UserPosition.user_id == self.member_id)
            ).all())
        self.assertEqual(position_ids, set())

    def test_email_templates_render_cargo_and_permission_details(self):
        user = SimpleNamespace(name='Ana Pérez', email='ana@example.com')
        with patch('app.services.email_service._send') as send:
            email_service.send_user_invitation(
                user,
                'Temp-123!',
                ['Tesorero'],
                [('Consultar solicitudes', 'requests:read'), ('Aprobar solicitudes', 'requests:approve')],
            )
        _, _, text_body, html_body = send.call_args.args
        self.assertIn('Tesorero', text_body)
        self.assertIn('requests:approve', text_body)
        self.assertIn('Tesorero', html_body)
        self.assertIn('requests:approve', html_body)

        with patch('app.services.email_service._send') as send:
            email_service.send_user_access_updated(
                user,
                ['Vicepresidente'],
                [('Consultar solicitudes', 'requests:read')],
            )
        _, subject, text_body, html_body = send.call_args.args
        self.assertIn('Actualización de cargo y permisos', subject)
        self.assertIn('Vicepresidente', text_body)
        self.assertIn('requests:read', html_body)


if __name__ == '__main__':
    unittest.main()
