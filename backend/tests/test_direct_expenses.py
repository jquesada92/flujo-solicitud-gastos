import os
import tempfile
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
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.application import create_app
from app.core.database import Base, get_db
from app.core.rate_limit import clear_rate_limits
from app.core.security import create_token, hash_password
from app.models.entities import (
    Approval,
    ApprovalPolicy,
    DirectExpense,
    Expense,
    ExpenseArea,
    ExpenseStatus,
    ExpenseSubcategory,
    QuotationVote,
    QuotationVotingInvitation,
    User,
    UserRole,
)
from app.models.iam import (
    Permission,
    Role,
    RolePermission,
    SystemAccount,
    UserRoleAssignment,
)


PDF = b'%PDF-1.4\n% direct expense test\n'


class DirectExpenseTests(unittest.TestCase):
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
        self.upload_directory = tempfile.TemporaryDirectory()
        self.upload_path = Path(self.upload_directory.name)
        self.upload_patch = patch(
            'app.services.document_service.upload_dir',
            return_value=self.upload_path,
        )
        self.upload_patch.start()

        with self.Session() as db:
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(table.delete())
            db.commit()

            permissions = {
                code: Permission(code=code, name=name, active=True)
                for code, name in (
                    ('requests:read', 'Consultar solicitudes'),
                    ('requests:create', 'Crear solicitudes'),
                    ('requests:approve', 'Aprobar solicitudes'),
                    ('config:manage', 'Administrar configuración'),
                )
            }
            db.add_all(permissions.values())
            db.flush()

            area = ExpenseArea(code='ADMINISTRATION', name='Administración', active=True)
            db.add(area)
            db.flush()
            db.add(
                ExpenseSubcategory(
                    area_id=area.id,
                    code='SERVICES',
                    name='Servicios',
                    active=True,
                )
            )

            requester = self._new_user(
                db,
                'requester@example.com',
                analytics_id='requester-analytics',
            )
            outsider = self._new_user(db, 'outsider@example.com')
            system = self._new_user(db, 'system@example.com')
            approver = self._new_user(db, 'approver@example.com')
            requester_role = Role(code='requester', name='Solicitante', active=True)
            approver_role = Role(code='approver', name='Aprobador', active=True)
            db.add_all([requester_role, approver_role])
            db.flush()
            db.add_all([
                RolePermission(
                    role_id=requester_role.id,
                    permission_id=permissions['requests:create'].id,
                ),
                RolePermission(
                    role_id=approver_role.id,
                    permission_id=permissions['requests:approve'].id,
                ),
                UserRoleAssignment(user_id=requester.id, role_id=requester_role.id),
                UserRoleAssignment(user_id=approver.id, role_id=approver_role.id),
                SystemAccount(user_id=system.id, account_type='TECHNICAL_ADMIN'),
            ])
            db.commit()

            self.requester_id = requester.id
            self.outsider_id = outsider.id
            self.system_id = system.id
            self.approver_role_id = approver_role.id
            self.requester_token = create_token(requester)
            self.outsider_token = create_token(outsider)
            self.system_token = create_token(system)

    def tearDown(self):
        self.upload_patch.stop()
        self.upload_directory.cleanup()

    @staticmethod
    def _new_user(
        db,
        email: str,
        *,
        analytics_id: str | None = None,
    ) -> User:
        user = User(
            name=email.split('@')[0],
            email=email,
            analytics_id=analytics_id,
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
        db.flush()
        return user

    @staticmethod
    def _auth(token: str) -> dict[str, str]:
        return {'Authorization': f'Bearer {token}'}

    def _add_policy(
        self,
        *,
        name: str = 'Registro directo',
        expense_area: str = 'ADMINISTRATION',
        minimum: str = '0',
        maximum: str | None = '500',
        mode: str = 'NO_APPROVAL',
        active: bool = True,
        role_ids: list[int] | None = None,
    ) -> int:
        with self.Session() as db:
            policy = ApprovalPolicy(
                name=name,
                expense_type=expense_area,
                min_amount=Decimal(minimum),
                max_amount=Decimal(maximum) if maximum is not None else None,
                approval_mode=mode,
                approver_profile_codes=[],
                approver_role_ids=role_ids or [],
                approver_group_ids=[],
                active=active,
            )
            db.add(policy)
            db.commit()
            db.refresh(policy)
            return policy.id

    def _post_direct(
        self,
        *,
        token: str | None = None,
        amount: str = '125.50',
        expense_area: str = 'ADMINISTRATION',
        filename: str = 'invoice.pdf',
        content: bytes = PDF,
        content_type: str = 'application/pdf',
    ):
        return self.client.post(
            '/api/direct-expenses',
            headers=self._auth(token or self.requester_token),
            data={
                'expense_area': expense_area,
                'supplier': 'Proveedor de prueba',
                'item_description': 'Mantenimiento preventivo',
                'amount': amount,
            },
            files={'invoice': (filename, content, content_type)},
        )

    def _simple_request_payload(self, *, amount: str = '125.50') -> dict:
        return {
            'title': 'Solicitud ordinaria',
            'description': 'No debe crearse dentro de una banda directa',
            'expense_area': 'ADMINISTRATION',
            'expense_category': 'SERVICES',
            'urgency': 'NORMAL',
            'request_type': 'SIMPLE',
            'amount': amount,
            'supplier': 'Proveedor de prueba',
            'item_url': 'https://example.com/support',
        }

    def test_policy_api_accepts_targetless_no_approval_and_preserves_no_overlap(self):
        payload = {
            'name': 'Sin aprobación hasta cien',
            'expense_type': 'ADMINISTRATION',
            'min_amount': '0',
            'max_amount': '100',
            'approval_mode': 'NO_APPROVAL',
            'approver_role_ids': [],
            'approver_group_ids': [],
            'active': True,
        }
        created = self.client.post(
            '/api/rules/policies',
            headers=self._auth(self.system_token),
            json=payload,
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()['approval_mode'], 'NO_APPROVAL')
        self.assertEqual(created.json()['approver_role_ids'], [])

        adjacent = self.client.post(
            '/api/rules/policies',
            headers=self._auth(self.system_token),
            json={**payload, 'name': 'Banda adyacente', 'min_amount': '100', 'max_amount': '200'},
        )
        self.assertEqual(adjacent.status_code, 201, adjacent.text)

        overlapping = self.client.post(
            '/api/rules/policies',
            headers=self._auth(self.system_token),
            json={**payload, 'name': 'Banda solapada', 'min_amount': '50', 'max_amount': '150'},
        )
        self.assertEqual(overlapping.status_code, 409, overlapping.text)

        normal_without_target = self.client.post(
            '/api/rules/policies',
            headers=self._auth(self.system_token),
            json={**payload, 'name': 'Mayoría inválida', 'approval_mode': 'MAJORITY'},
        )
        self.assertEqual(normal_without_target.status_code, 422, normal_without_target.text)

        direct_with_target = self.client.post(
            '/api/rules/policies',
            headers=self._auth(self.system_token),
            json={**payload, 'name': 'Directa inválida', 'approver_role_ids': [self.approver_role_id]},
        )
        self.assertEqual(direct_with_target.status_code, 422, direct_with_target.text)

        boolean_target = self.client.post(
            '/api/rules/policies',
            headers=self._auth(self.system_token),
            json={**payload, 'name': 'Target booleano', 'approval_mode': 'ANY', 'approver_role_ids': [True]},
        )
        self.assertEqual(boolean_target.status_code, 422, boolean_target.text)

    def test_eligible_policies_only_exposes_active_valid_no_approval_bands(self):
        eligible_id = self._add_policy(name='Directa activa', maximum='100')
        self._add_policy(name='Directa inactiva', minimum='100', maximum='200', active=False)
        self._add_policy(
            name='Con aprobación',
            minimum='100',
            maximum='200',
            mode='ANY',
            role_ids=[self.approver_role_id],
        )
        self._add_policy(
            name='Directa corrupta',
            minimum='200',
            maximum='300',
            role_ids=['not-an-id'],
        )

        response = self.client.get(
            '/api/direct-expenses/eligible-policies',
            headers=self._auth(self.requester_token),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), [{
            'id': eligible_id,
            'name': 'Directa activa',
            'expense_area': 'ADMINISTRATION',
            'min_amount': '0.00',
            'max_amount': '100.00',
            'approval_mode': 'NO_APPROVAL',
        }])

        denied = self.client.get(
            '/api/direct-expenses/eligible-policies',
            headers=self._auth(self.outsider_token),
        )
        self.assertEqual(denied.status_code, 403, denied.text)

    def test_direct_creation_is_independent_from_every_request_workflow_table(self):
        policy_id = self._add_policy()

        response = self._post_direct()

        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertTrue(body['record_id'])
        self.assertEqual(body['display_id'], f"GD-{body['record_id']}")
        self.assertEqual(body['expense_area'], 'ADMINISTRATION')
        self.assertEqual(Decimal(body['amount']), Decimal('125.50'))
        self.assertEqual(body['approval_policy_id'], policy_id)
        self.assertEqual(body['requester_user_id'], self.requester_id)
        self.assertEqual(body['requester_analytics_id'], 'requester-analytics')
        self.assertEqual(body['invoice']['download_url'], f"/api/direct-expenses/{body['record_id']}/invoice")

        with self.Session() as db:
            record = db.scalar(select(DirectExpense))
            self.assertIsNotNone(record)
            self.assertEqual(db.scalar(select(func.count(Expense.id))), 0)
            self.assertEqual(db.scalar(select(func.count(Approval.id))), 0)
            self.assertEqual(db.scalar(select(func.count(QuotationVotingInvitation.id))), 0)
            self.assertEqual(db.scalar(select(func.count(QuotationVote.id))), 0)
            invoice_path = self.upload_path / record.invoice_stored_name
        self.assertTrue(invoice_path.is_file())
        self.assertEqual(invoice_path.read_bytes(), PDF)

    def test_amount_band_uses_exclusive_minimum_and_inclusive_maximum(self):
        self._add_policy(minimum='100', maximum='200')

        excluded = self._post_direct(amount='100')
        self.assertEqual(excluded.status_code, 422, excluded.text)

        included = self._post_direct(amount='200')
        self.assertEqual(included.status_code, 201, included.text)
        with self.Session() as db:
            self.assertEqual(db.scalar(select(func.count(DirectExpense.id))), 1)
            self.assertEqual(db.scalar(select(func.count(Expense.id))), 0)

    def test_area_policy_precedes_all_policy_even_when_all_is_no_approval(self):
        self._add_policy(
            name='Fallback directo',
            expense_area='ALL',
            maximum='500',
        )
        self._add_policy(
            name='Área con aprobación',
            maximum='500',
            mode='ANY',
            role_ids=[self.approver_role_id],
        )

        response = self._post_direct(amount='125')

        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn('no coinciden', response.json()['detail'])
        with self.Session() as db:
            self.assertEqual(db.scalar(select(func.count(DirectExpense.id))), 0)
            self.assertEqual(db.scalar(select(func.count(Expense.id))), 0)

    def test_create_requires_permission_and_valid_private_invoice(self):
        self._add_policy()

        denied = self._post_direct(token=self.outsider_token)
        self.assertEqual(denied.status_code, 403, denied.text)

        invalid_signature = self._post_direct(content=b'not a pdf')
        self.assertEqual(invalid_signature.status_code, 415, invalid_signature.text)

        invalid_extension = self._post_direct(filename='invoice.txt')
        self.assertEqual(invalid_extension.status_code, 415, invalid_extension.text)

        with self.Session() as db:
            self.assertEqual(db.scalar(select(func.count(DirectExpense.id))), 0)
            self.assertEqual(db.scalar(select(func.count(Expense.id))), 0)
        self.assertEqual(list(self.upload_path.iterdir()), [])

    def test_failed_database_commit_removes_written_invoice_and_row(self):
        self._add_policy()

        with patch.object(Session, 'commit', side_effect=RuntimeError('forced commit failure')):
            with self.assertRaises(RuntimeError):
                self._post_direct()

        with self.Session() as db:
            self.assertEqual(db.scalar(select(func.count(DirectExpense.id))), 0)
            self.assertEqual(db.scalar(select(func.count(Expense.id))), 0)
        self.assertEqual(list(self.upload_path.iterdir()), [])

    def test_owner_and_system_have_private_list_and_download_access(self):
        self._add_policy()
        created = self._post_direct()
        self.assertEqual(created.status_code, 201, created.text)
        record_id = created.json()['record_id']

        owner_list = self.client.get(
            '/api/direct-expenses',
            headers=self._auth(self.requester_token),
        )
        self.assertEqual(owner_list.status_code, 200, owner_list.text)
        self.assertEqual([item['record_id'] for item in owner_list.json()], [record_id])

        outsider_list = self.client.get(
            '/api/direct-expenses',
            headers=self._auth(self.outsider_token),
        )
        self.assertEqual(outsider_list.status_code, 200, outsider_list.text)
        self.assertEqual(outsider_list.json(), [])

        outsider_download = self.client.get(
            f'/api/direct-expenses/{record_id}/invoice',
            headers=self._auth(self.outsider_token),
        )
        self.assertEqual(outsider_download.status_code, 403, outsider_download.text)

        system_list = self.client.get(
            '/api/direct-expenses',
            headers=self._auth(self.system_token),
        )
        self.assertEqual(system_list.status_code, 200, system_list.text)
        self.assertEqual([item['record_id'] for item in system_list.json()], [record_id])

        owner_download = self.client.get(
            f'/api/direct-expenses/{record_id}/invoice',
            headers=self._auth(self.requester_token),
        )
        self.assertEqual(owner_download.status_code, 200, owner_download.text)
        self.assertEqual(owner_download.content, PDF)

        system_download = self.client.get(
            f'/api/direct-expenses/{record_id}/invoice',
            headers=self._auth(self.system_token),
        )
        self.assertEqual(system_download.status_code, 200, system_download.text)
        self.assertEqual(system_download.content, PDF)

    def test_no_approval_band_rejects_simple_and_multi_quote_request_creation(self):
        self._add_policy(maximum='500')

        simple = self.client.post(
            '/api/expenses',
            headers=self._auth(self.requester_token),
            json=self._simple_request_payload(amount='125'),
        )
        self.assertEqual(simple.status_code, 422, simple.text)
        self.assertIn('/api/direct-expenses', simple.json()['detail'])

        multi_payload = {
            'title': 'Comparación ordinaria',
            'description': 'Tampoco debe crear una solicitud',
            'expense_area': 'ADMINISTRATION',
            'expense_category': 'SERVICES',
            'urgency': 'NORMAL',
            'request_type': 'MULTI_QUOTE',
            'quotation_options': [
                {
                    'supplier': 'Proveedor uno',
                    'amount': '100',
                    'item_url': 'https://example.com/one',
                },
                {
                    'supplier': 'Proveedor dos',
                    'amount': '450',
                    'item_url': 'https://example.com/two',
                },
            ],
        }
        multiple = self.client.post(
            '/api/expenses',
            headers=self._auth(self.requester_token),
            json=multi_payload,
        )
        self.assertEqual(multiple.status_code, 422, multiple.text)
        self.assertIn('/api/direct-expenses', multiple.json()['detail'])

        with self.Session() as db:
            self.assertEqual(db.scalar(select(func.count(Expense.id))), 0)
            self.assertEqual(db.scalar(select(func.count(DirectExpense.id))), 0)

    def test_correction_into_no_approval_band_is_rejected_without_mutation(self):
        self._add_policy(maximum='500')
        with self.Session() as db:
            expense = Expense(
                request_id='existing-request',
                flow_id='existing-flow',
                display_id='ADM-2026-EXISTING',
                request_type='SIMPLE',
                title='Título original',
                description='Descripción original',
                expense_area='ADMINISTRATION',
                expense_category='SERVICES',
                urgency='NORMAL',
                amount=Decimal('900'),
                supplier='Proveedor original',
                item_url='https://example.com/original',
                requested_by='requester@example.com',
                requester_analytics_id='requester-analytics',
                status=ExpenseStatus.NEEDS_REVISION,
            )
            db.add(expense)
            db.commit()

        response = self.client.put(
            '/api/expenses/existing-request/resubmit',
            headers=self._auth(self.requester_token),
            json=self._simple_request_payload(amount='200'),
        )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn('/api/direct-expenses', response.json()['detail'])
        with self.Session() as db:
            stored = db.scalar(select(Expense).where(Expense.request_id == 'existing-request'))
            self.assertEqual(stored.title, 'Título original')
            self.assertEqual(stored.amount, Decimal('900'))
            self.assertEqual(stored.status, ExpenseStatus.NEEDS_REVISION)
            self.assertEqual(db.scalar(select(func.count(Expense.id))), 1)
            self.assertEqual(db.scalar(select(func.count(DirectExpense.id))), 0)

    def test_forward_migration_creates_independent_direct_expense_table(self):
        migration = (
            Path(__file__).resolve().parents[1]
            / 'alembic'
            / 'versions'
            / '20260828_0013_direct_expenses.py'
        ).read_text(encoding='utf-8')
        self.assertIn("revision = '20260828_0013'", migration)
        self.assertIn("down_revision = '20260827_0012'", migration)
        self.assertIn("'direct_expenses'", migration)
        self.assertIn("_fk('users', 'id')", migration)
        self.assertNotIn("_fk('expenses', 'id')", migration)


if __name__ == '__main__':
    unittest.main()
