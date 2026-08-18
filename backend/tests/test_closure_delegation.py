import os
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
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
from app.models.closure import ExpenseClosureDelegation
from app.models.entities import Expense, ExpenseStatus, User, UserRole
from app.models.iam import Permission, SystemAccount, UserPermission


PDF = b'%PDF-1.4\n% closure test\n'


class ClosureDelegationTests(unittest.TestCase):
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

            close_permission = Permission(code='requests:close', name='Cerrar legacy', active=True)
            db.add(close_permission)
            db.flush()

            requester = self._user(db, 'requester@example.com')
            delegate = self._user(db, 'delegate@example.com')
            outsider = self._user(db, 'legacy-closer@example.com')
            admin = self._user(db, 'admin@example.com')
            db.flush()

            db.add(UserPermission(user_id=outsider.id, permission_id=close_permission.id))
            db.add(SystemAccount(user_id=admin.id, account_type='TECHNICAL_ADMIN'))

            expense = Expense(
                request_id='closure-request',
                flow_id='closure-flow',
                display_id='ADM-2026-CLOSURE-001',
                request_type='SIMPLE',
                title='Solicitud para cierre',
                description='Prueba de delegación de cierre',
                expense_type='ADMINISTRATION',
                expense_subcategory='SERVICES',
                urgency='NORMAL',
                amount=Decimal('100.00'),
                supplier='Proveedor',
                requested_by=requester.email,
                status=ExpenseStatus.APPROVED,
            )
            db.add(expense)
            db.commit()

            self.requester_id = requester.id
            self.delegate_id = delegate.id
            self.outsider_id = outsider.id
            self.admin_id = admin.id
            self.expense_id = expense.id
            self.requester_token = create_token(requester)
            self.delegate_token = create_token(delegate)
            self.outsider_token = create_token(outsider)
            self.admin_token = create_token(admin)

    def _user(self, db, email: str) -> User:
        user = User(
            name=email.split('@')[0],
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

    def auth(self, token: str) -> dict[str, str]:
        return {'Authorization': f'Bearer {token}'}

    def close(self, token: str):
        with patch('app.api.financial_actions.write_document', return_value=Path('/tmp/test-invoice.pdf')):
            return self.client.post(
                '/api/expenses/closure-request/close',
                headers=self.auth(token),
                files={'invoice': ('invoice.pdf', PDF, 'application/pdf')},
                data={'notes': 'Factura registrada'},
            )

    def test_requester_has_closure_and_delegation_capabilities_without_global_close_permission(self):
        response = self.client.get('/api/expenses', headers=self.auth(self.requester_token))
        self.assertEqual(response.status_code, 200, response.text)
        item = next(row for row in response.json() if row['request_id'] == 'closure-request')
        self.assertTrue(item['can_close'])
        self.assertTrue(item['can_delegate_close'])

    def test_global_close_permission_does_not_authorize_somebody_elses_request(self):
        response = self.client.get('/api/expenses', headers=self.auth(self.outsider_token))
        self.assertEqual(response.status_code, 200, response.text)
        item = next(row for row in response.json() if row['request_id'] == 'closure-request')
        self.assertFalse(item['can_close'])
        self.assertFalse(item['can_delegate_close'])

        denied = self.close(self.outsider_token)
        self.assertEqual(denied.status_code, 403, denied.text)
        self.assertIn('delegado por el solicitante', denied.json()['detail'])

    def test_requester_can_delegate_and_delegate_can_close(self):
        delegated = self.client.put(
            '/api/expenses/closure-request/closure-delegation',
            headers=self.auth(self.requester_token),
            json={'delegate_user_id': self.delegate_id},
        )
        self.assertEqual(delegated.status_code, 200, delegated.text)
        self.assertEqual(delegated.json()['delegation']['delegate']['id'], self.delegate_id)

        delegate_view = self.client.get('/api/expenses', headers=self.auth(self.delegate_token))
        item = next(row for row in delegate_view.json() if row['request_id'] == 'closure-request')
        self.assertTrue(item['can_close'])
        self.assertFalse(item['can_delegate_close'])

        dashboard = self.client.get('/api/expenses/dashboard', headers=self.auth(self.delegate_token))
        pending = {row['request_id']: row['actions'] for row in dashboard.json()['pending_items']}
        self.assertEqual(pending['closure-request'], ['CLOSE_REQUEST'])

        closed = self.close(self.delegate_token)
        self.assertEqual(closed.status_code, 200, closed.text)
        self.assertEqual(closed.json()['status'], 'CLOSED')

        with self.Session() as db:
            stored = db.get(Expense, self.expense_id)
            self.assertEqual(stored.closed_by, 'delegate@example.com')

    def test_requester_can_revoke_delegation_and_delegate_loses_authority(self):
        create = self.client.put(
            '/api/expenses/closure-request/closure-delegation',
            headers=self.auth(self.requester_token),
            json={'delegate_user_id': self.delegate_id},
        )
        self.assertEqual(create.status_code, 200, create.text)

        revoke = self.client.delete(
            '/api/expenses/closure-request/closure-delegation',
            headers=self.auth(self.requester_token),
        )
        self.assertEqual(revoke.status_code, 200, revoke.text)
        self.assertIsNone(revoke.json()['delegation'])

        denied = self.close(self.delegate_token)
        self.assertEqual(denied.status_code, 403, denied.text)

        with self.Session() as db:
            delegation = db.scalar(select(ExpenseClosureDelegation).where(
                ExpenseClosureDelegation.expense_id == self.expense_id
            ))
            self.assertIsNotNone(delegation.revoked_at)
            self.assertEqual(delegation.revoked_by_user_id, self.requester_id)

    def test_only_requester_can_create_delegation(self):
        denied = self.client.put(
            '/api/expenses/closure-request/closure-delegation',
            headers=self.auth(self.outsider_token),
            json={'delegate_user_id': self.delegate_id},
        )
        self.assertEqual(denied.status_code, 403, denied.text)

    def test_system_administrator_can_close_without_global_close_permission(self):
        response = self.client.get('/api/expenses', headers=self.auth(self.admin_token))
        item = next(row for row in response.json() if row['request_id'] == 'closure-request')
        self.assertTrue(item['can_close'])
        self.assertFalse(item['can_delegate_close'])

        closed = self.close(self.admin_token)
        self.assertEqual(closed.status_code, 200, closed.text)
        self.assertEqual(closed.json()['status'], 'CLOSED')


if __name__ == '__main__':
    unittest.main()
