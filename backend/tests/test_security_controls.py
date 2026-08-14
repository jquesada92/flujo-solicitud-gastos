import os
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import jwt
from fastapi import HTTPException

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('SECRET_KEY', 'unit-test-secret-key-at-least-32-characters')

from app.api import auth
from app.api.expenses import _validate_file_content
from app.services import email_service
from app.core.rate_limit import (
    READ_POLICY,
    SENSITIVE_POLICY,
    UPLOAD_POLICY,
    WRITE_POLICY,
    clear_rate_limits,
    consume_user_request,
    policy_for_request,
)
from app.core.security import SECRET_KEY, create_token, session_is_idle
from app.main import validate_runtime_security


class SecurityControlTests(unittest.TestCase):
    def tearDown(self):
        auth._login_attempts.clear()
        clear_rate_limits()

    def test_jwt_contains_session_version(self):
        token = create_token(SimpleNamespace(id=7, session_version=3))
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        self.assertEqual(payload['sv'], 3)

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

    def test_production_rejects_development_secrets(self):
        values = {
            'ENVIRONMENT': 'production',
            'SECRET_KEY': 'development-only-change-me',
            'ANALYTICS_HASH_KEY': '',
            'ADMIN_PASSWORD': 'Admin123!',
            'CORS_ALLOWED_ORIGINS': 'http://localhost:3000',
        }
        with patch.dict(os.environ, values, clear=False):
            with self.assertRaises(RuntimeError):
                validate_runtime_security()


if __name__ == '__main__':
    unittest.main()
