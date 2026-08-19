import os
import unittest
from datetime import datetime, timezone
from decimal import Decimal

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
from app.models.entities import Expense, ExpenseStatus, User, UserRole
from app.models.iam import Permission
from app.services.iam_service import users_with_permission


class UniversalTrackingTests(unittest.TestCase):
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

            db.add(Permission(code='requests:read', name='Consultar solicitudes', active=True))
            self.requester = self._new_user(db, 'requester@example.com', UserRole.REQUESTER)
            self.viewer = self._new_user(db, 'viewer@example.com', UserRole.VIEWER)
            db.flush()

            db.add_all([
                self._expense('REQ-OWN', 'ADM-2026-00000000001', self.requester.email, 'Solicitud propia'),
                self._expense('REQ-OTHER', 'ADM-2026-00000000002', self.viewer.email, 'Solicitud de otro usuario'),
            ])
            db.commit()

            self.requester_id = self.requester.id
            self.viewer_id = self.viewer.id
            self.requester_token = create_token(self.requester)
            self.viewer_token = create_token(self.viewer)

    def _new_user(self, db, email: str, role: UserRole) -> User:
        user = User(
            name=email.split('@')[0],
            email=email,
            password_hash=hash_password('Test-password-123!'),
            role=role,
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

    def _expense(self, request_id: str, display_id: str, requested_by: str, title: str) -> Expense:
        return Expense(
            request_id=request_id,
            flow_id=f'FLOW-{request_id}',
            display_id=display_id,
            request_type='SIMPLE',
            title=title,
            description='Seguimiento compartido',
            expense_type='ADMINISTRATION',
            expense_subcategory='SERVICES',
            urgency='NORMAL',
            amount=Decimal('100.00'),
            supplier='Proveedor',
            requested_by=requested_by,
            status=ExpenseStatus.SUBMITTED,
        )

    def auth(self, token: str) -> dict[str, str]:
        return {'Authorization': f'Bearer {token}'}

    def test_active_user_receives_read_as_product_baseline(self):
        response = self.client.get('/api/iam/me/permissions', headers=self.auth(self.requester_token))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['permission_codes'], ['requests:read'])
        self.assertIn(
            'Acceso base del producto para usuarios activos',
            response.json()['sources']['requests:read'],
        )

        me = self.client.get('/api/auth/me', headers=self.auth(self.requester_token))
        self.assertEqual(me.status_code, 200, me.text)
        self.assertTrue(me.json()['can_view'])
        self.assertFalse(me.json()['can_request'])
        self.assertFalse(me.json()['can_approve'])
        self.assertFalse(me.json()['can_close'])

    def test_requester_can_track_requests_created_by_other_users(self):
        response = self.client.get('/api/expenses', headers=self.auth(self.requester_token))
        self.assertEqual(response.status_code, 200, response.text)
        request_ids = {item['request_id'] for item in response.json()}
        self.assertEqual(request_ids, {'REQ-OWN', 'REQ-OTHER'})

    def test_every_active_user_can_open_dashboard(self):
        response = self.client.get('/api/expenses/dashboard', headers=self.auth(self.viewer_token))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['in_process'], 2)
        self.assertEqual(response.json()['pending_my_action'], 0)
        self.assertEqual(response.json()['last_31_days']['created'], 2)

    def test_read_baseline_population_contains_all_active_users(self):
        with self.Session() as db:
            users = users_with_permission(db, 'requests:read')
        self.assertEqual({user.id for user in users}, {self.requester_id, self.viewer_id})

    def test_read_baseline_does_not_grant_closure_of_somebody_elses_request(self):
        with self.Session() as db:
            expense = db.scalar(select(Expense).where(Expense.request_id == 'REQ-OWN'))
            expense.status = ExpenseStatus.APPROVED
            db.commit()

        response = self.client.post(
            '/api/expenses/REQ-OWN/close',
            headers=self.auth(self.viewer_token),
            files={'invoice': ('invoice.pdf', b'%PDF-1.7\n', 'application/pdf')},
        )
        self.assertEqual(response.status_code, 403, response.text)


if __name__ == '__main__':
    unittest.main()
