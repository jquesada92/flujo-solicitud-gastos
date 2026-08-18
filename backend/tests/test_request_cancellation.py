import os
import unittest
from datetime import datetime, timezone
from decimal import Decimal

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('SECRET_KEY', 'unit-test-secret-key-at-least-32-characters')
os.environ.setdefault('ANALYTICS_HASH_KEY', 'unit-test-analytics-key-at-least-32-characters')
os.environ.setdefault('ENVIRONMENT', 'test')

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.application import create_app
from app.core.database import Base, get_db
from app.core.security import create_token, hash_password
from app.models.entities import Expense, ExpenseStatus, User, UserRole
from app.models.iam import Permission, SystemAccount, UserPermission


class RequestCancellationTests(unittest.TestCase):
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
            create = Permission(code='requests:create', name='Crear solicitudes', active=True)
            db.add_all([read, create])
            db.flush()

            self.requester = self._new_user(db, 'requester@example.com')
            self.other_creator = self._new_user(db, 'creator@example.com')
            self.system_admin = self._new_user(db, 'technical@example.com')
            db.flush()

            # Give another business user create permission deliberately. This must
            # not let them cancel a request they do not own.
            db.add(UserPermission(user_id=self.other_creator.id, permission_id=create.id))
            db.add(SystemAccount(user_id=self.system_admin.id, account_type='TECHNICAL_ADMIN'))

            db.add_all([
                self._expense('REQ-MULTI', self.requester.email, ExpenseStatus.QUOTATION_VOTING),
                self._expense('REQ-CLOSED', self.requester.email, ExpenseStatus.CLOSED),
            ])
            db.commit()

            self.requester_token = create_token(self.requester)
            self.other_creator_token = create_token(self.other_creator)
            self.system_admin_token = create_token(self.system_admin)

    def _new_user(self, db, email: str) -> User:
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

    def _expense(self, request_id: str, requested_by: str, status: ExpenseStatus) -> Expense:
        return Expense(
            request_id=request_id,
            flow_id=f'FLOW-{request_id}',
            display_id=f'ADM-{request_id}',
            request_type='MULTI_QUOTE' if status == ExpenseStatus.QUOTATION_VOTING else 'SIMPLE',
            title=f'Solicitud {request_id}',
            description='Prueba de cancelación',
            expense_type='ADMINISTRATION',
            expense_subcategory='SERVICES',
            urgency='NORMAL',
            amount=Decimal('100.00'),
            supplier='Proveedor',
            requested_by=requested_by,
            status=status,
        )

    def auth(self, token: str) -> dict[str, str]:
        return {'Authorization': f'Bearer {token}'}

    def test_tracking_marks_only_owned_open_request_as_cancellable_for_requester(self):
        response = self.client.get('/api/expenses', headers=self.auth(self.requester_token))
        self.assertEqual(response.status_code, 200, response.text)
        by_id = {item['request_id']: item for item in response.json()}
        self.assertTrue(by_id['REQ-MULTI']['can_cancel'])
        self.assertFalse(by_id['REQ-CLOSED']['can_cancel'])

    def test_business_user_with_create_permission_cannot_cancel_someone_elses_request(self):
        response = self.client.post(
            '/api/expenses/REQ-MULTI/cancel',
            headers=self.auth(self.other_creator_token),
            json={'reason': 'No corresponde'},
        )
        self.assertEqual(response.status_code, 403, response.text)
        self.assertIn('Solo el solicitante original o el Administrador del sistema', response.json()['detail'])

    def test_requester_can_cancel_own_multi_quote_while_voting_is_open(self):
        response = self.client.post(
            '/api/expenses/REQ-MULTI/cancel',
            headers=self.auth(self.requester_token),
            json={'reason': 'Solicitud creada por error'},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['status'], 'CANCELLED')
        self.assertEqual(response.json()['cancellation_reason'], 'Solicitud creada por error')

    def test_system_admin_can_cancel_any_open_request(self):
        listing = self.client.get('/api/expenses', headers=self.auth(self.system_admin_token))
        self.assertEqual(listing.status_code, 200, listing.text)
        by_id = {item['request_id']: item for item in listing.json()}
        self.assertTrue(by_id['REQ-MULTI']['can_cancel'])

        response = self.client.post(
            '/api/expenses/REQ-MULTI/cancel',
            headers=self.auth(self.system_admin_token),
            json={'reason': 'Cancelación administrativa'},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['status'], 'CANCELLED')
        self.assertEqual(response.json()['cancelled_by'], self.system_admin.email)

    def test_closed_request_cannot_be_cancelled_even_by_system_admin(self):
        response = self.client.post(
            '/api/expenses/REQ-CLOSED/cancel',
            headers=self.auth(self.system_admin_token),
            json={'reason': 'Intento de cancelación'},
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertIn('cerrada', response.json()['detail'].lower())


if __name__ == '__main__':
    unittest.main()
