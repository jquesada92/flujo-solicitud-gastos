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
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.application import create_app
from app.core.database import Base, get_db
from app.core.rate_limit import clear_rate_limits
from app.core.security import create_token, hash_password
from app.models.entities import (
    Expense,
    ExpenseAttachment,
    ExpenseStatus,
    QuotationOption,
    QuotationVote,
    QuotationVoteEvent,
    QuotationVotingInvitation,
    User,
    UserRole,
)
from app.models.iam import Permission, Role, RolePermission, UserRoleAssignment


PDF = b'%PDF-1.7\nquotation-voting-test\n'


class MultiQuoteOpenVotingTests(unittest.TestCase):
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
        with self.Session() as db:
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(table.delete())
            db.commit()

            read = Permission(code='requests:read', name='Consultar solicitudes', active=True)
            approve = Permission(code='requests:approve', name='Aprobar solicitudes', active=True)
            db.add_all([read, approve])
            db.flush()

            requester = self._user(db, 'requester@example.com')
            voter_one = self._user(db, 'voter-one@example.com')
            voter_two = self._user(db, 'voter-two@example.com')
            db.flush()
            self._grant(db, requester, read, 'requester-read')
            self._grant(db, voter_one, read, 'voter-one-read')
            self._grant(db, voter_two, read, 'voter-two-read')
            self._grant(db, voter_one, approve, 'voter-one')
            self._grant(db, voter_two, approve, 'voter-two')

            expense = Expense(
                request_id='multi-open-voting',
                flow_id='FLOW-MULTI-OPEN-VOTING',
                display_id='ADM-2026-0000000001',
                request_type='MULTI_QUOTE',
                title='Compra con cotizaciones',
                description='Comprueba empate, cambio de voto y cierre con factura.',
                expense_type='ADMINISTRATION',
                expense_subcategory='SERVICES',
                urgency='NORMAL',
                requested_by=requester.email,
                status=ExpenseStatus.QUOTATION_VOTING,
            )
            db.add(expense)
            db.flush()
            option_one = QuotationOption(
                expense_id=expense.id,
                option_number=1,
                supplier='Proveedor A',
                amount=Decimal('90.00'),
                item_url='https://example.test/quote-a',
            )
            option_two = QuotationOption(
                expense_id=expense.id,
                option_number=2,
                supplier='Proveedor B',
                amount=Decimal('95.00'),
                item_url='https://example.test/quote-b',
            )
            db.add_all([option_one, option_two])
            db.flush()
            db.add_all([
                QuotationVotingInvitation(
                    expense_id=expense.id,
                    voter_user_id=voter_one.id,
                    token='multi-voter-one',
                ),
                QuotationVotingInvitation(
                    expense_id=expense.id,
                    voter_user_id=voter_two.id,
                    token='multi-voter-two',
                ),
            ])
            db.commit()

            self.expense_id = expense.id
            self.option_one_id = option_one.id
            self.option_two_id = option_two.id
            self.requester_token = create_token(requester)
            self.voter_one_token = create_token(voter_one)
            self.voter_two_token = create_token(voter_two)

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

    def _grant(self, db, user: User, permission: Permission, code: str) -> None:
        role = Role(code=code, name=code, active=True, system_managed=False)
        db.add(role)
        db.flush()
        db.add_all([
            RolePermission(role_id=role.id, permission_id=permission.id),
            UserRoleAssignment(user_id=user.id, role_id=role.id),
        ])

    @staticmethod
    def auth(token: str) -> dict[str, str]:
        return {'Authorization': f'Bearer {token}'}

    def vote(self, token: str, option_id: int):
        return self.client.post(
            '/api/expenses/multi-open-voting/quotation-vote',
            headers=self.auth(token),
            json={'quotation_option_id': option_id},
        )

    def close(self):
        with patch(
            'app.api.financial_actions.write_document',
            return_value=Path('test-invoice-does-not-touch-disk.pdf'),
        ):
            return self.client.post(
                '/api/expenses/multi-open-voting/close',
                headers=self.auth(self.requester_token),
                files={'invoice': ('invoice.pdf', PDF, 'application/pdf')},
                data={'notes': 'Factura de la opción ganadora'},
            )

    def test_tie_stays_open_until_a_voter_changes_vote_then_invoice_closes(self):
        tracking = self.client.get('/api/expenses', headers=self.auth(self.requester_token))
        self.assertEqual(tracking.status_code, 200, tracking.text)
        row = next(item for item in tracking.json() if item['request_id'] == 'multi-open-voting')
        self.assertEqual(Decimal(row['tracking_amount']), Decimal('95.00'))

        first = self.vote(self.voter_one_token, self.option_one_id)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()['status'], 'QUOTATION_VOTING')
        self.assertIsNone(first.json()['selected_quotation_id'])

        tracking = self.client.get('/api/expenses', headers=self.auth(self.requester_token))
        row = next(item for item in tracking.json() if item['request_id'] == 'multi-open-voting')
        self.assertEqual(Decimal(row['tracking_amount']), Decimal('90.00'))

        incomplete = self.close()
        self.assertEqual(incomplete.status_code, 409, incomplete.text)
        self.assertIn('todos los participantes', incomplete.json()['detail'])

        tied = self.vote(self.voter_two_token, self.option_two_id)
        self.assertEqual(tied.status_code, 200, tied.text)
        self.assertEqual(tied.json()['status'], 'QUOTATION_VOTING')
        self.assertIsNone(tied.json()['selected_quotation_id'])

        tracking = self.client.get('/api/expenses', headers=self.auth(self.requester_token))
        row = next(item for item in tracking.json() if item['request_id'] == 'multi-open-voting')
        self.assertEqual(Decimal(row['tracking_amount']), Decimal('95.00'))

        dashboard = self.client.get(
            '/api/expenses/dashboard',
            headers=self.auth(self.voter_one_token),
        )
        self.assertEqual(dashboard.status_code, 200, dashboard.text)
        pending = next(
            item for item in dashboard.json()['pending_items']
            if item['request_id'] == 'multi-open-voting'
        )
        self.assertEqual(pending['actions'], ['QUOTATION_VOTE'])

        detail = self.client.get(
            '/api/expenses/multi-open-voting/my-actions',
            headers=self.auth(self.voter_one_token),
        )
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual([item['code'] for item in detail.json()['actions']], ['QUOTATION_VOTE'])
        self.assertEqual(detail.json()['actions'][0]['label'], 'Votar o cambiar voto')
        self.assertTrue(detail.json()['request']['quotation_is_complete'])
        self.assertTrue(detail.json()['request']['quotation_has_tie'])
        self.assertEqual(detail.json()['request']['current_quotation_option_id'], self.option_one_id)

        blocked = self.close()
        self.assertEqual(blocked.status_code, 409, blocked.text)
        self.assertIn('empatada', blocked.json()['detail'])

        changed = self.vote(self.voter_two_token, self.option_one_id)
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()['status'], 'QUOTATION_VOTING')
        self.assertEqual(changed.json()['selected_quotation_id'], self.option_one_id)

        tracking = self.client.get('/api/expenses', headers=self.auth(self.requester_token))
        row = next(item for item in tracking.json() if item['request_id'] == 'multi-open-voting')
        self.assertEqual(Decimal(row['tracking_amount']), Decimal('90.00'))

        closed = self.close()
        self.assertEqual(closed.status_code, 200, closed.text)
        self.assertEqual(closed.json()['status'], 'CLOSED')
        self.assertEqual(closed.json()['selected_quotation_id'], self.option_one_id)

        rejected_after_close = self.vote(self.voter_one_token, self.option_two_id)
        self.assertEqual(rejected_after_close.status_code, 409, rejected_after_close.text)

        with self.Session() as db:
            expense = db.get(Expense, self.expense_id)
            self.assertEqual(expense.status, ExpenseStatus.CLOSED)
            self.assertEqual(db.scalar(select(func.count(QuotationVote.id))), 2)
            self.assertEqual(db.scalar(select(func.count(QuotationVoteEvent.id))), 3)
            self.assertEqual(db.scalar(select(func.count(ExpenseAttachment.id)).where(
                ExpenseAttachment.document_type == 'INVOICE'
            )), 1)

    def test_email_invitation_reopens_with_current_vote_and_allows_change(self):
        first = self.client.post(
            '/api/expenses/quotation-vote-email/multi-voter-one',
            json={'quotation_option_id': self.option_one_id},
        )
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()['status'], 'QUOTATION_VOTING')

        reopened = self.client.get(
            '/api/expenses/quotation-vote-email/multi-voter-one',
        )
        self.assertEqual(reopened.status_code, 200, reopened.text)
        self.assertEqual(reopened.json()['current_option_id'], self.option_one_id)

        changed = self.client.post(
            '/api/expenses/quotation-vote-email/multi-voter-one',
            json={'quotation_option_id': self.option_two_id},
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()['status'], 'QUOTATION_VOTING')

        with self.Session() as db:
            vote = db.scalar(select(QuotationVote).where(
                QuotationVote.expense_id == self.expense_id,
                QuotationVote.voter_user_id == db.scalar(select(User.id).where(
                    User.email == 'voter-one@example.com',
                )),
            ))
            self.assertEqual(vote.quotation_option_id, self.option_two_id)
            self.assertEqual(db.scalar(select(func.count(QuotationVote.id))), 1)
            self.assertEqual(db.scalar(select(func.count(QuotationVoteEvent.id))), 2)

    def test_provisional_winner_can_return_to_tie_and_loses_close_capability(self):
        self.assertEqual(self.vote(self.voter_one_token, self.option_one_id).status_code, 200)
        leader = self.vote(self.voter_two_token, self.option_one_id)
        self.assertEqual(leader.status_code, 200, leader.text)
        self.assertEqual(leader.json()['status'], 'QUOTATION_VOTING')
        self.assertEqual(leader.json()['selected_quotation_id'], self.option_one_id)

        tracking = self.client.get('/api/expenses', headers=self.auth(self.requester_token))
        self.assertEqual(tracking.status_code, 200, tracking.text)
        row = next(item for item in tracking.json() if item['request_id'] == 'multi-open-voting')
        self.assertTrue(row['can_close'])

        tied_again = self.vote(self.voter_two_token, self.option_two_id)
        self.assertEqual(tied_again.status_code, 200, tied_again.text)
        self.assertIsNone(tied_again.json()['selected_quotation_id'])

        tracking = self.client.get('/api/expenses', headers=self.auth(self.requester_token))
        row = next(item for item in tracking.json() if item['request_id'] == 'multi-open-voting')
        self.assertFalse(row['can_close'])

        with self.Session() as db:
            expense = db.get(Expense, self.expense_id)
            self.assertEqual(expense.status, ExpenseStatus.QUOTATION_VOTING)
            self.assertIsNone(expense.selected_quotation_id)
            self.assertEqual(db.scalar(select(func.count(ExpenseAttachment.id)).where(
                ExpenseAttachment.document_type == 'INVOICE'
            )), 0)

    def test_legacy_approved_multi_quote_cannot_bypass_live_vote_validation(self):
        with self.Session() as db:
            expense = db.get(Expense, self.expense_id)
            expense.status = ExpenseStatus.APPROVED
            expense.selected_quotation_id = self.option_one_id
            db.commit()

        blocked = self.close()
        self.assertEqual(blocked.status_code, 409, blocked.text)
        self.assertIn('ya no está abierta', blocked.json()['detail'])

        with self.Session() as db:
            self.assertEqual(db.scalar(select(func.count(ExpenseAttachment.id))), 0)


if __name__ == '__main__':
    unittest.main()
