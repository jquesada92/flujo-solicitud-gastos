import os
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import jwt
from fastapi import HTTPException
from pydantic import ValidationError

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('SECRET_KEY', 'unit-test-secret-key-at-least-32-characters')
os.environ.setdefault('ANALYTICS_HASH_KEY', 'unit-test-analytics-key-at-least-32-characters')

from app.api import auth
from app.api.approvals import _ensure_link_is_current
from app.api.expenses import _validate_file_content
from app.core.config import Settings, get_settings
from app.core.rate_limit import (
    READ_POLICY,
    SENSITIVE_POLICY,
    UPLOAD_POLICY,
    WRITE_POLICY,
    clear_rate_limits,
    consume_user_request,
    policy_for_request,
)
from app.core.security import create_token, hash_password, session_is_idle, verify_password
from app.models.entities import ApprovalStatus, ExpenseStatus
from app.services import email_service
from app.services.approval_engine import apply_decision


class SecurityControlTests(unittest.TestCase):
    def tearDown(self):
        auth._login_attempts.clear()
        clear_rate_limits()

    def test_jwt_contains_session_version(self):
        token = create_token(SimpleNamespace(id=7, session_version=3))
        payload = jwt.decode(token, get_settings().secret_key, algorithms=['HS256'])
        self.assertEqual(payload['sv'], 3)

    def test_new_passwords_use_argon2(self):
        encoded = hash_password('A-secure-test-password!')
        self.assertTrue(encoded.startswith('$argon2'))
        self.assertTrue(verify_password('A-secure-test-password!', encoded))
        self.assertFalse(verify_password('wrong-password', encoded))

    def test_login_rate_limit_blocks_after_maximum(self):
        key = '127.0.0.1:user@example.com'
        for _ in range(auth.LOGIN_MAX_ATTEMPTS):
            auth._record_login_failure(key)
        with self.assertRaises(HTTPException) as raised:
            auth._check_login_limit(key)
        self.assertEqual(raised.exception.status_code, 429)

    def test_rejects_spoofed_file_type(self):
        with self.assertRaises(HTTPException) as raised:
            _validate_file_content(b'<script>alert(1)</script>', 'image/png')
        self.assertEqual(raised.exception.status_code, 415)

    def test_accepts_pdf_signature(self):
        self.assertEqual(_validate_file_content(b'%PDF-1.7\n', 'application/pdf'), '.pdf')

    def test_pending_approval_does_not_expire_by_age(self):
        approval = SimpleNamespace(
            status=ApprovalStatus.PENDING,
            created_at=datetime.now(timezone.utc) - timedelta(days=365),
            expense=SimpleNamespace(status=ExpenseStatus.PENDING_APPROVAL),
        )
        _ensure_link_is_current(approval)

    def test_answered_approval_cannot_be_submitted_again(self):
        approval = SimpleNamespace(status=ApprovalStatus.APPROVED)
        with self.assertRaises(ValueError):
            apply_decision(unittest.mock.MagicMock(), approval, ApprovalStatus.APPROVED, None)

    def test_session_expires_after_thirty_idle_minutes(self):
        now = datetime.now(timezone.utc)
        self.assertFalse(session_is_idle(now - timedelta(minutes=29), now))
        self.assertTrue(session_is_idle(now - timedelta(minutes=30), now))

    def test_authenticated_user_rate_limit(self):
        for index in range(SENSITIVE_POLICY.limit):
            allowed, remaining, _ = consume_user_request('user-7', SENSITIVE_POLICY, now=index / 100)
            self.assertTrue(allowed)
            self.assertEqual(remaining, SENSITIVE_POLICY.limit - index - 1)
        allowed, remaining, retry_after = consume_user_request('user-7', SENSITIVE_POLICY, now=1)
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)
        self.assertGreaterEqual(retry_after, 1)

    def test_rate_limit_isolated_by_user(self):
        for _ in range(WRITE_POLICY.limit):
            consume_user_request('user-1', WRITE_POLICY, now=0)
        allowed, _, _ = consume_user_request('user-2', WRITE_POLICY, now=0)
        self.assertTrue(allowed)

    def test_request_policies_match_risk(self):
        self.assertEqual(policy_for_request('GET', '/api/expenses'), READ_POLICY)
        self.assertEqual(policy_for_request('POST', '/api/expenses'), WRITE_POLICY)
        self.assertEqual(policy_for_request('POST', '/api/expenses/x/attachments'), UPLOAD_POLICY)
        self.assertEqual(policy_for_request('POST', '/api/approvals/token'), SENSITIVE_POLICY)
        self.assertEqual(policy_for_request('POST', '/api/iam/groups'), SENSITIVE_POLICY)

    def test_brevo_email_uses_https_api(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.status = 201
        with (
            patch.object(email_service, 'BREVO_API_KEY', 'test-api-key'),
            patch.object(email_service, 'EMAIL_FROM', 'verified@example.com'),
            patch.object(email_service, 'urlopen', return_value=response) as send,
        ):
            email_service._send_brevo('recipient@example.com', 'Subject', 'Text', '<p>HTML</p>')
        request = send.call_args.args[0]
        payload = request.data.decode('utf-8')
        self.assertEqual(request.full_url, 'https://api.brevo.com/v3/smtp/email')
        self.assertIn('verified@example.com', payload)
        self.assertNotIn('test-api-key', payload)

    def test_production_settings_reject_development_secrets(self):
        with self.assertRaises(ValidationError):
            Settings(
                database_url='postgresql://example/db',
                environment='production',
                secret_key='development-only-change-me',
                analytics_hash_key='',
                admin_password='Admin123!',
                cors_allowed_origins='http://localhost:3000',
            )


if __name__ == '__main__':
    unittest.main()
