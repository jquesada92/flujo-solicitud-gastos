import os
import unittest
from datetime import datetime, timezone
from decimal import Decimal

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('SECRET_KEY', 'unit-test-secret-key-at-least-32-characters')
os.environ.setdefault('ANALYTICS_HASH_KEY', 'unit-test-analytics-key-at-least-32-characters')
os.environ.setdefault('ENVIRONMENT', 'test')
os.environ.setdefault('EMAIL_MODE', 'console')

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.application import create_app
from app.core.database import Base, get_db
from app.core.security import create_token, hash_password
from app.models.entities import (
    Expense,
    ExpenseArea,
    ExpenseAttachment,
    ExpenseStatus,
    ExpenseSubcategory,
    QuotationOption,
    QuotationVote,
    QuotationVotingInvitation,
    User,
    UserRole,
)
from app.models.iam import Permission, SystemAccount, UserPermission


class MultiQuoteRevisionTests(unittest.TestCase):
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

            read = Permission(code='requests:read', name='Consultar', active=True)
            create = Permission(code='requests:create', name='Crear', active=True)
            approve = Permission(code='requests:approve', name='Aprobar', active=True)
            close = Permission(code='requests:close', name='Cerrar', active=True)
            config = Permission(code='config:manage', name='Configurar', active=True)
            db.add_all([read, create, approve, close, config])
            db.flush()

            area = ExpenseArea(code='ADMINISTRATION', name='Administración', active=True)
            db.add(area)
            db.flush()
            db.add(ExpenseSubcategory(
                area_id=area.id,
                code='EQUIPMENT',
                name='Equipos',
                active=True,
            ))

            admin = self._user(db, 'admin@example.com')
            approver = self._user(db, 'approver@example.com')
            db.flush()
            db.add(SystemAccount(user_id=admin.id, account_type='TECHNICAL_ADMIN'))
            db.add(UserPermission(user_id=approver.id, permission_id=approve.id))
            db.flush()

            expense = Expense(
                request_id='multi-revision-test',
                flow_id='flow-before-revision',
                display_id='ADM-2026-00000000001',
                request_type='MULTI_QUOTE',
                title='Compra original',
                description='Solicitud con múltiples cotizaciones',
                expense_type='ADMINISTRATION',
                expense_subcategory='EQUIPMENT',
                urgency='NORMAL',
                amount=None,
                supplier=None,
                item_url=None,
                requested_by=admin.email,
                status=ExpenseStatus.QUOTATION_VOTING,
            )
            db.add(expense)
            db.flush()

            option_one = QuotationOption(
                expense_id=expense.id,
                option_number=1,
                supplier='Proveedor A',
                amount=Decimal('100.00'),
                item_url=None,
                notes='Archivo existente',
            )
            option_two = QuotationOption(
                expense_id=expense.id,
                option_number=2,
                supplier='Proveedor B',
                amount=Decimal('110.00'),
                item_url='https://example.com/quote-b',
                notes=None,
            )
            db.add_all([option_one, option_two])
            db.flush()

            attachment = ExpenseAttachment(
                expense_id=expense.id,
                quotation_option_id=option_one.id,
                original_name='quote-a.pdf',
                stored_name='quote-a-existing.pdf',
                content_type='application/pdf',
                size=100,
                document_type='QUOTATION_OPTION',
            )
            old_invitation = QuotationVotingInvitation(
                expense_id=expense.id,
                voter_user_id=approver.id,
                token='old-voting-token',
            )
            old_vote = QuotationVote(
                expense_id=expense.id,
                quotation_option_id=option_two.id,
                voter_user_id=approver.id,
                voter_email=approver.email,
                voter_role='requests:approve',
            )
            db.add_all([attachment, old_invitation, old_vote])
            db.commit()

            self.admin_id = admin.id
            self.approver_id = approver.id
            self.approver_email = approver.email
            self.expense_id = expense.id
            self.option_one_id = option_one.id
            self.token = create_token(admin)
            self.approver_token = create_token(approver)

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

    def auth(self, token: str | None = None):
        return {'Authorization': f'Bearer {token or self.token}'}

    def multi_payload(self):
        return {
            'title': 'Compra corregida',
            'description': 'Se corrigieron las cotizaciones sin cambiar el tipo de solicitud',
            'expense_type': 'ADMINISTRATION',
            'expense_subcategory': 'EQUIPMENT',
            'urgency': 'HIGH',
            'request_type': 'MULTI_QUOTE',
            'amount': None,
            'supplier': None,
            'item_url': None,
            'quotation_options': [
                {
                    'supplier': 'Proveedor A corregido',
                    'amount': '105.00',
                    'item_url': None,
                    'attachment_pending': True,
                    'notes': 'Mantiene el archivo existente',
                },
                {
                    'supplier': 'Proveedor B corregido',
                    'amount': '115.00',
                    'item_url': 'https://example.com/quote-b-updated',
                    'notes': 'URL actualizada',
                },
            ],
        }

    def test_multi_quote_revision_preserves_type_options_support_and_restarts_voting(self):
        response = self.client.put(
            '/api/expenses/multi-revision-test/resubmit',
            headers=self.auth(),
            json=self.multi_payload(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload['request_type'], 'MULTI_QUOTE')
        self.assertEqual(payload['status'], 'QUOTATION_VOTING')
        self.assertEqual(len(payload['quotation_options']), 2)
        self.assertEqual(payload['quotation_options'][0]['supplier'], 'Proveedor A corregido')
        self.assertNotEqual(payload['flow_id'], 'flow-before-revision')

        with self.Session() as db:
            stored = db.get(Expense, self.expense_id)
            self.assertEqual(stored.request_type, 'MULTI_QUOTE')
            self.assertEqual(stored.status, ExpenseStatus.QUOTATION_VOTING)
            self.assertIsNone(stored.amount)
            self.assertIsNone(stored.supplier)
            self.assertIsNone(stored.selected_quotation_id)

            attachment = db.scalar(select(ExpenseAttachment).where(
                ExpenseAttachment.quotation_option_id == self.option_one_id,
            ))
            self.assertIsNotNone(attachment)

            vote_count = db.scalar(select(func.count(QuotationVote.id)).where(
                QuotationVote.expense_id == self.expense_id,
            ))
            self.assertEqual(vote_count, 0)

            invitations = list(db.scalars(select(QuotationVotingInvitation).where(
                QuotationVotingInvitation.expense_id == self.expense_id,
            )).all())
            self.assertEqual(len(invitations), 1)
            self.assertNotEqual(invitations[0].token, 'old-voting-token')

    def test_non_owner_approver_cannot_correct_somebody_elses_request(self):
        response = self.client.put(
            '/api/expenses/multi-revision-test/resubmit',
            headers=self.auth(self.approver_token),
            json=self.multi_payload(),
        )
        self.assertEqual(response.status_code, 403, response.text)
        self.assertIn('Solo el solicitante original o el Administrador del sistema', response.json()['detail'])
        self.assertIn('Enviar a revisión', response.json()['detail'])

    def test_original_requester_can_correct_without_global_create_permission(self):
        with self.Session() as db:
            expense = db.get(Expense, self.expense_id)
            expense.requested_by = self.approver_email
            db.commit()

        response = self.client.put(
            '/api/expenses/multi-revision-test/resubmit',
            headers=self.auth(self.approver_token),
            json=self.multi_payload(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['status'], 'QUOTATION_VOTING')

    def test_legacy_simple_flag_is_inferred_as_multi_quote_from_durable_evidence(self):
        with self.Session() as db:
            expense = db.get(Expense, self.expense_id)
            expense.request_type = 'SIMPLE'
            db.commit()

        response = self.client.put(
            '/api/expenses/multi-revision-test/resubmit',
            headers=self.auth(),
            json=self.multi_payload(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload['request_type'], 'MULTI_QUOTE')
        self.assertEqual(payload['status'], 'QUOTATION_VOTING')

        with self.Session() as db:
            stored = db.get(Expense, self.expense_id)
            self.assertEqual(stored.request_type, 'MULTI_QUOTE')

    def test_revision_cannot_change_multi_quote_into_simple(self):
        payload = {
            'title': 'Intento de conversión',
            'description': 'No debe cambiar el tipo original',
            'expense_type': 'ADMINISTRATION',
            'expense_subcategory': 'EQUIPMENT',
            'urgency': 'NORMAL',
            'request_type': 'SIMPLE',
            'amount': '10.00',
            'supplier': 'Proveedor simple',
            'item_url': 'https://example.com/simple',
            'quotation_options': [],
        }
        response = self.client.put(
            '/api/expenses/multi-revision-test/resubmit',
            headers=self.auth(),
            json=payload,
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertIn('no puede cambiar el tipo original', response.json()['detail'])


if __name__ == '__main__':
    unittest.main()
