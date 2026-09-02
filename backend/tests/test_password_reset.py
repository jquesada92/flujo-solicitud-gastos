import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import jwt

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('SECRET_KEY', 'unit-test-secret-key-at-least-32-characters')
os.environ.setdefault('ANALYTICS_HASH_KEY', 'unit-test-analytics-key-at-least-32-characters')
os.environ.setdefault('ENVIRONMENT', 'test')
os.environ.setdefault('EMAIL_MODE', 'console')

from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import auth as auth_api
from app.api.auth import INVALID_PASSWORD_RESET_DETAIL
from app.application import create_app
from app.core.config import Settings, get_settings
from app.core.database import Base, get_db
from app.core.rate_limit import PASSWORD_RESET_POLICY, clear_rate_limits, password_reset_subject, policy_for_request
from app.core.security import create_password_reset_token, create_token, hash_password, verify_password
from app.models.audit_feed import AuditChangeFeed
from app.models.entities import User, UserRole
from app.models.iam import Permission, SystemAccount
from app.services import email_service


class PasswordResetTests(unittest.TestCase):
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
        clear_rate_limits()
        auth_api._login_attempts.clear()
        with self.Session() as db:
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(table.delete())
            db.commit()

            db.add(Permission(code='config:manage', name='Administración técnica', active=True))
            admin = self._new_user(db, 'admin@example.com', 'ADMIN-RESET')
            member = self._new_user(db, 'member@example.com', 'MEMBER-RESET')
            db.flush()
            db.add(SystemAccount(user_id=admin.id, account_type='TECHNICAL_ADMIN'))
            db.commit()
            db.refresh(admin)
            db.refresh(member)

            self.admin_id = admin.id
            self.member_id = member.id
            self.admin_token = create_token(admin)
            self.member_token = create_token(member)
            self.original_password_hash = member.password_hash
            self.original_session_version = member.session_version

    def tearDown(self):
        clear_rate_limits()
        auth_api._login_attempts.clear()

    @staticmethod
    def _new_user(db, email: str, identity_document: str) -> User:
        user = User(
            name=email.split('@')[0],
            first_name='Test',
            last_name='User',
            identity_document=identity_document,
            email=email,
            password_hash=hash_password('Original-password-123!'),
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

    def auth(self, token: str | None = None) -> dict[str, str]:
        return {'Authorization': f'Bearer {token or self.admin_token}'}

    def issue_link(self) -> tuple[object, str]:
        with patch('app.api.users.send_password_reset_link') as send:
            response = self.client.post(
                f'/api/users/{self.member_id}/regenerate-password',
                headers=self.auth(),
            )
        self.assertEqual(response.status_code, 200, response.text)
        send.assert_called_once()
        reset_token = send.call_args.args[1]
        self.assertNotIn(reset_token, response.text)
        return response, reset_token

    def test_issue_link_preserves_password_and_sessions_and_audits_without_secrets(self):
        _, token = self.issue_link()
        claims = jwt.decode(token, get_settings().secret_key, algorithms=['HS256'])
        self.assertEqual(claims['purpose'], 'password-reset')
        self.assertEqual(claims['sub'], str(self.member_id))
        self.assertEqual(claims['prv'], 1)
        self.assertTrue(claims['jti'])
        self.assertIn('exp', claims)
        self.assertNotIn('sv', claims)

        with self.Session() as db:
            member = db.get(User, self.member_id)
            event = db.scalar(select(AuditChangeFeed).where(
                AuditChangeFeed.event_type == 'USER_PASSWORD_RESET_LINK_ISSUED'
            ))
            self.assertEqual(member.password_hash, self.original_password_hash)
            self.assertEqual(member.session_version, self.original_session_version)
            self.assertFalse(member.must_change_password)
            self.assertEqual(member.password_reset_version, 1)
            self.assertIsNotNone(event)
            audit_json = json.dumps({
                'changed_fields': event.changed_fields,
                'changes': event.changes,
            })
        self.assertNotIn(token, audit_json)
        self.assertNotIn(self.original_password_hash, audit_json)
        self.assertNotIn('password_hash', audit_json)

        current_session = self.client.get('/api/auth/me', headers=self.auth(self.member_token))
        self.assertEqual(current_session.status_code, 200, current_session.text)
        reset_token_is_not_a_session = self.client.get('/api/auth/me', headers=self.auth(token))
        self.assertEqual(reset_token_is_not_a_session.status_code, 401, reset_token_is_not_a_session.text)

    def test_new_link_invalidates_old_and_consumption_revokes_sessions(self):
        _, first_token = self.issue_link()
        _, second_token = self.issue_link()

        stale = self.client.post('/api/auth/reset-password', json={
            'token': first_token,
            'new_password': 'New-password-123!',
        })
        self.assertEqual(stale.status_code, 400, stale.text)
        self.assertEqual(stale.json()['detail'], INVALID_PASSWORD_RESET_DETAIL)

        with patch('app.api.auth.send_password_reset_completed') as completed:
            reset = self.client.post('/api/auth/reset-password', json={
                'token': second_token,
                'new_password': 'New-password-123!',
            })
        self.assertEqual(reset.status_code, 200, reset.text)
        completed.assert_called_once()
        self.assertEqual(reset.json(), {'message': 'Contraseña restablecida. Ya puedes iniciar sesión.'})
        self.assertNotIn('access_token', reset.json())

        with self.Session() as db:
            member = db.get(User, self.member_id)
            event = db.scalar(select(AuditChangeFeed).where(
                AuditChangeFeed.event_type == 'USER_PASSWORD_RESET_COMPLETED'
            ))
            self.assertTrue(verify_password('New-password-123!', member.password_hash))
            self.assertFalse(verify_password('Original-password-123!', member.password_hash))
            self.assertFalse(member.must_change_password)
            self.assertEqual(member.password_reset_version, 3)
            self.assertEqual(member.session_version, self.original_session_version + 1)
            self.assertIsNotNone(event)
            audit_json = json.dumps({
                'changed_fields': event.changed_fields,
                'changes': event.changes,
            })
        self.assertNotIn(second_token, audit_json)
        self.assertNotIn('password_hash', audit_json)

        revoked = self.client.get('/api/auth/me', headers=self.auth(self.member_token))
        self.assertEqual(revoked.status_code, 401, revoked.text)

        reused = self.client.post('/api/auth/reset-password', json={
            'token': second_token,
            'new_password': 'Another-password-123!',
        })
        self.assertEqual(reused.status_code, 400, reused.text)
        self.assertEqual(reused.json()['detail'], INVALID_PASSWORD_RESET_DETAIL)

    def test_authenticated_password_change_invalidates_an_outstanding_reset_link(self):
        _, reset_token = self.issue_link()

        changed = self.client.post(
            '/api/auth/change-password',
            headers=self.auth(self.member_token),
            json={
                'current_password': 'Original-password-123!',
                'new_password': 'Changed-password-123!',
            },
        )
        self.assertEqual(changed.status_code, 200, changed.text)

        stale = self.client.post('/api/auth/reset-password', json={
            'token': reset_token,
            'new_password': 'Reset-password-123!',
        })
        self.assertEqual(stale.status_code, 400, stale.text)
        self.assertEqual(stale.json()['detail'], INVALID_PASSWORD_RESET_DETAIL)

        with self.Session() as db:
            member = db.get(User, self.member_id)
            self.assertEqual(member.password_reset_version, 2)
            self.assertTrue(verify_password('Changed-password-123!', member.password_hash))

    def test_tampered_expired_and_unknown_tokens_share_generic_error(self):
        _, token = self.issue_link()
        token_header, token_payload, token_signature = token.split('.')
        tampered_signature = f'{"a" if token_signature[0] != "a" else "b"}{token_signature[1:]}'
        tampered = f'{token_header}.{token_payload}.{tampered_signature}'
        expired = jwt.encode(
            {
                'purpose': 'password-reset',
                'sub': str(self.member_id),
                'prv': 1,
                'jti': 'expired-test-token',
                'exp': datetime.now(timezone.utc) - timedelta(seconds=1),
            },
            get_settings().secret_key,
            algorithm='HS256',
        )
        unknown = jwt.encode(
            {
                'purpose': 'password-reset',
                'sub': '999999',
                'prv': 1,
                'jti': 'unknown-user-token',
                'exp': datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            get_settings().secret_key,
            algorithm='HS256',
        )
        for candidate in ('x', tampered, expired, unknown, self.member_token):
            with self.subTest(candidate=candidate[:12]):
                response = self.client.post('/api/auth/reset-password', json={
                    'token': candidate,
                    'new_password': 'New-password-123!',
                })
                self.assertEqual(response.status_code, 400, response.text)
                self.assertEqual(response.json()['detail'], INVALID_PASSWORD_RESET_DETAIL)

    def test_email_failure_rolls_back_link_version_and_audit(self):
        _, previous_token = self.issue_link()
        with patch('app.api.users.send_password_reset_link', side_effect=RuntimeError('email unavailable')):
            response = self.client.post(
                f'/api/users/{self.member_id}/regenerate-password',
                headers=self.auth(),
            )
        self.assertEqual(response.status_code, 502, response.text)

        with self.Session() as db:
            member = db.get(User, self.member_id)
            events = list(db.scalars(select(AuditChangeFeed).where(
                AuditChangeFeed.event_type == 'USER_PASSWORD_RESET_LINK_ISSUED'
            )).all())
            self.assertEqual(member.password_reset_version, 1)
            self.assertEqual(member.password_hash, self.original_password_hash)
            self.assertEqual(member.session_version, self.original_session_version)
            self.assertEqual(len(events), 1)

        with patch('app.api.auth.send_password_reset_completed'):
            previous_link_still_works = self.client.post('/api/auth/reset-password', json={
                'token': previous_token,
                'new_password': 'New-password-123!',
            })
        self.assertEqual(previous_link_still_works.status_code, 200, previous_link_still_works.text)

    def test_inactive_and_system_accounts_cannot_receive_reset_links(self):
        with self.Session() as db:
            member = db.get(User, self.member_id)
            member.active = False
            db.commit()

        with patch('app.api.users.send_password_reset_link') as send:
            inactive = self.client.post(
                f'/api/users/{self.member_id}/regenerate-password',
                headers=self.auth(),
            )
            technical = self.client.post(
                f'/api/users/{self.admin_id}/regenerate-password',
                headers=self.auth(),
            )
        self.assertEqual(inactive.status_code, 409, inactive.text)
        self.assertEqual(technical.status_code, 403, technical.text)
        send.assert_not_called()

    def test_inactive_and_system_accounts_cannot_consume_signed_reset_tokens(self):
        with self.Session() as db:
            member = db.get(User, self.member_id)
            admin = db.get(User, self.admin_id)
            member.password_reset_version = 1
            admin.password_reset_version = 1
            member_token = create_password_reset_token(member)
            admin_token = create_password_reset_token(admin)
            member.active = False
            db.commit()

        for candidate in (member_token, admin_token):
            with self.subTest(candidate=candidate[:12]):
                response = self.client.post('/api/auth/reset-password', json={
                    'token': candidate,
                    'new_password': 'New-password-123!',
                })
                self.assertEqual(response.status_code, 400, response.text)
                self.assertEqual(response.json()['detail'], INVALID_PASSWORD_RESET_DETAIL)

    def test_ordinary_user_cannot_issue_reset_link(self):
        denied = self.client.post(
            f'/api/users/{self.member_id}/regenerate-password',
            headers=self.auth(self.member_token),
        )
        self.assertEqual(denied.status_code, 403, denied.text)

    def test_public_reset_endpoint_has_dedicated_rate_limit(self):
        self.assertEqual(
            policy_for_request('POST', '/api/auth/reset-password'),
            PASSWORD_RESET_POLICY,
        )
        payload = {'token': 'x' * 20, 'new_password': 'New-password-123!'}
        for attempt in range(PASSWORD_RESET_POLICY.limit):
            response = self.client.post(
                '/api/auth/reset-password',
                headers={'X-Forwarded-For': f'198.51.100.{attempt + 1}'},
                json=payload,
            )
            self.assertEqual(response.status_code, 400, response.text)
        blocked = self.client.post(
            '/api/auth/reset-password',
            headers={'X-Forwarded-For': '203.0.113.250'},
            json=payload,
        )
        self.assertEqual(blocked.status_code, 429, blocked.text)
        self.assertEqual(blocked.headers['X-RateLimit-Policy'], 'password-reset')

        login = self.client.post('/api/auth/login', json={
            'email': 'member@example.com',
            'password': 'Definitely-wrong-password!',
        })
        self.assertEqual(login.status_code, 401, login.text)

    def test_password_reset_token_expiration_setting_is_bounded(self):
        settings = Settings(database_url='sqlite://')
        self.assertEqual(settings.password_reset_token_expire_minutes, 30)
        for invalid in (4, 1441):
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                Settings(database_url='sqlite://', password_reset_token_expire_minutes=invalid)

    def test_email_and_active_state_changes_invalidate_outstanding_links(self):
        _, email_token = self.issue_link()
        changed_email = self.client.patch(
            f'/api/iam/users/{self.member_id}',
            headers=self.auth(),
            json={'email': 'member-updated@example.com'},
        )
        self.assertEqual(changed_email.status_code, 200, changed_email.text)
        stale_email = self.client.post('/api/auth/reset-password', json={
            'token': email_token,
            'new_password': 'New-password-123!',
        })
        self.assertEqual(stale_email.status_code, 400, stale_email.text)

        _, active_token = self.issue_link()
        inactivated = self.client.patch(
            f'/api/iam/users/{self.member_id}',
            headers=self.auth(),
            json={'active': False},
        )
        self.assertEqual(inactivated.status_code, 200, inactivated.text)
        stale_active = self.client.post('/api/auth/reset-password', json={
            'token': active_token,
            'new_password': 'New-password-123!',
        })
        self.assertEqual(stale_active.status_code, 400, stale_active.text)

    def test_confirmation_email_failure_does_not_undo_completed_reset(self):
        _, reset_token = self.issue_link()
        with (
            patch('app.api.auth.send_password_reset_completed', side_effect=RuntimeError('email unavailable')),
            self.assertLogs('app.api.auth', level='WARNING'),
        ):
            response = self.client.post('/api/auth/reset-password', json={
                'token': reset_token,
                'new_password': 'New-password-123!',
            })
        self.assertEqual(response.status_code, 200, response.text)
        with self.Session() as db:
            self.assertTrue(verify_password('New-password-123!', db.get(User, self.member_id).password_hash))

    def test_password_reset_subject_only_trusts_forwarding_from_private_proxy(self):
        self.assertEqual(
            password_reset_subject('127.0.0.1', '198.51.100.10, 203.0.113.20'),
            'password-reset-ip:203.0.113.20',
        )
        self.assertEqual(
            password_reset_subject('8.8.8.8', '203.0.113.20'),
            'password-reset-ip:8.8.8.8',
        )

    def test_reset_email_contains_one_time_link_and_no_temporary_password(self):
        user = SimpleNamespace(name='Ana Pérez', email='ana@example.com')
        with patch('app.services.email_service._send') as send:
            email_service.send_password_reset_link(user, 'signed.jwt.token')
        _, subject, text_body, html_body = send.call_args.args
        self.assertIn('Restablece tu contraseña', subject)
        self.assertIn('/reset-password#token=signed.jwt.token', text_body)
        self.assertIn('/reset-password#token=signed.jwt.token', html_body)
        self.assertNotIn('Contraseña temporal', text_body)
        self.assertNotIn('Contraseña temporal', html_body)

    def test_reset_completion_email_contains_no_token_or_password(self):
        user = SimpleNamespace(name='Ana Pérez', email='ana@example.com')
        with patch('app.services.email_service._send') as send:
            email_service.send_password_reset_completed(user)
        _, subject, text_body, html_body = send.call_args.args
        self.assertIn('Contraseña actualizada', subject)
        self.assertIn('sesiones anteriores fueron cerradas', text_body)
        self.assertNotIn('token', text_body.lower())
        self.assertNotIn('contraseña:', text_body.lower())
        self.assertNotIn('token', html_body.lower())


if __name__ == '__main__':
    unittest.main()
