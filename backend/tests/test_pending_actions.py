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
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.application import create_app
from app.core.database import Base, get_db
from app.core.security import create_token, hash_password
from app.models.entities import (
    Approval,
    ApprovalStatus,
    Expense,
    ExpenseStatus,
    QuotationOption,
    QuotationVotingInvitation,
    User,
    UserRole,
)
from app.models.iam import Permission, UserPermission


class PendingActionTests(unittest.TestCase):
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

            permissions = {}
            for code in ('requests:read', 'requests:create', 'requests:approve', 'requests:close'):
                permission = Permission(code=code, name=code, active=True)
                db.add(permission)
                permissions[code] = permission
            db.flush()

            self.requester = self._user(db, 'requester@example.com')
            self.approver = self._user(db, 'approver@example.com')
            self.reviewer_two = self._user(db, 'reviewer-two@example.com')
            self.closer = self._user(db, 'closer@example.com')
            db.flush()
            self._grant(db, self.requester, permissions['requests:create'])
            self._grant(db, self.approver, permissions['requests:approve'])
            self._grant(db, self.reviewer_two, permissions['requests:approve'])
            self._grant(db, self.closer, permissions['requests:close'])
            db.commit()

            self.requester_token = create_token(self.requester)
            self.approver_token = create_token(self.approver)
            self.reviewer_two_token = create_token(self.reviewer_two)
            self.closer_token = create_token(self.closer)

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

    def _grant(self, db, user: User, permission: Permission) -> None:
        db.add(UserPermission(user_id=user.id, permission_id=permission.id))

    def _expense(self, db, request_id: str, status: ExpenseStatus, requested_by: str) -> Expense:
        expense = Expense(
            request_id=request_id,
            flow_id=f'FLOW-{request_id}',
            display_id=f'ADM-{request_id}',
            request_type='SIMPLE',
            title=f'Solicitud {request_id}',
            description='Acción contextual de prueba',
            expense_type='ADMINISTRATION',
            expense_subcategory='SERVICES',
            urgency='NORMAL',
            amount=Decimal('100.00'),
            supplier='Proveedor',
            requested_by=requested_by,
            status=status,
        )
        db.add(expense)
        db.flush()
        return expense

    def auth(self, token: str) -> dict[str, str]:
        return {'Authorization': f'Bearer {token}'}

    def test_pending_approval_opens_contextual_action_and_can_be_decided(self):
        with self.Session() as db:
            expense = self._expense(db, 'REQ-APPROVE', ExpenseStatus.PENDING_APPROVAL, self.requester.email)
            db.add(Approval(
                expense_id=expense.id,
                flow_id=expense.flow_id,
                approver_email=self.approver.email,
                approver_role='requests:approve',
                step=1,
                approval_mode='ANY',
                token='approval-token',
                status=ApprovalStatus.PENDING,
            ))
            db.commit()

        dashboard = self.client.get('/api/expenses/dashboard', headers=self.auth(self.approver_token))
        self.assertEqual(dashboard.status_code, 200, dashboard.text)
        item = next(row for row in dashboard.json()['pending_items'] if row['request_id'] == 'REQ-APPROVE')
        self.assertEqual(item['actions'], ['APPROVAL_DECISION'])

        detail = self.client.get('/api/expenses/REQ-APPROVE/my-actions', headers=self.auth(self.approver_token))
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual([action['code'] for action in detail.json()['actions']], ['APPROVAL_DECISION'])

        decision = self.client.post(
            '/api/expenses/REQ-APPROVE/approval-decision',
            headers=self.auth(self.approver_token),
            json={'decision': 'APPROVED', 'comment': 'Aprobado desde Inicio'},
        )
        self.assertEqual(decision.status_code, 200, decision.text)
        self.assertEqual(decision.json()['status'], 'APPROVED')

        refreshed = self.client.get('/api/expenses/REQ-APPROVE/my-actions', headers=self.auth(self.approver_token))
        self.assertEqual(refreshed.status_code, 200, refreshed.text)
        self.assertEqual(refreshed.json()['actions'], [])

    def test_single_revision_request_interrupts_majority_and_hands_task_to_requester(self):
        with self.Session() as db:
            expense = self._expense(db, 'REQ-REVIEW', ExpenseStatus.PENDING_APPROVAL, self.requester.email)
            db.add_all([
                Approval(
                    expense_id=expense.id,
                    flow_id=expense.flow_id,
                    approver_email=self.approver.email,
                    approver_role='requests:approve',
                    step=1,
                    approval_mode='MAJORITY',
                    token='review-token-one',
                    status=ApprovalStatus.PENDING,
                ),
                Approval(
                    expense_id=expense.id,
                    flow_id=expense.flow_id,
                    approver_email=self.reviewer_two.email,
                    approver_role='requests:approve',
                    step=2,
                    approval_mode='MAJORITY',
                    token='review-token-two',
                    status=ApprovalStatus.PENDING,
                ),
            ])
            db.commit()

        missing_comment = self.client.post(
            '/api/expenses/REQ-REVIEW/approval-decision',
            headers=self.auth(self.approver_token),
            json={'decision': 'REVISION_REQUESTED', 'comment': '  '},
        )
        self.assertEqual(missing_comment.status_code, 409, missing_comment.text)
        self.assertIn('Debes indicar qué debe corregir', missing_comment.json()['detail'])

        decision = self.client.post(
            '/api/expenses/REQ-REVIEW/approval-decision',
            headers=self.auth(self.approver_token),
            json={
                'decision': 'REVISION_REQUESTED',
                'comment': 'La cotización no coincide con el alcance solicitado.',
            },
        )
        self.assertEqual(decision.status_code, 200, decision.text)
        self.assertEqual(decision.json()['status'], 'NEEDS_REVISION')

        with self.Session() as db:
            expense = db.scalar(select(Expense).where(Expense.request_id == 'REQ-REVIEW'))
            approvals = list(db.scalars(
                select(Approval).where(Approval.expense_id == expense.id).order_by(Approval.step)
            ).all())
            self.assertEqual(expense.status, ExpenseStatus.NEEDS_REVISION)
            self.assertEqual(approvals[0].status, ApprovalStatus.REVISION_REQUESTED)
            self.assertEqual(approvals[0].comment, 'La cotización no coincide con el alcance solicitado.')
            self.assertEqual(approvals[1].status, ApprovalStatus.EXPIRED)

        requester_dashboard = self.client.get(
            '/api/expenses/dashboard',
            headers=self.auth(self.requester_token),
        )
        requester_items = {
            item['request_id']: item['actions']
            for item in requester_dashboard.json()['pending_items']
        }
        self.assertEqual(requester_items['REQ-REVIEW'], ['CORRECT_REQUEST'])

        other_reviewer = self.client.get(
            '/api/expenses/REQ-REVIEW/my-actions',
            headers=self.auth(self.reviewer_two_token),
        )
        self.assertEqual(other_reviewer.status_code, 200, other_reviewer.text)
        self.assertEqual(other_reviewer.json()['actions'], [])

    def test_quotation_invitation_is_reported_as_vote_action(self):
        with self.Session() as db:
            expense = self._expense(db, 'REQ-VOTE', ExpenseStatus.QUOTATION_VOTING, self.requester.email)
            expense.request_type = 'MULTI_QUOTE'
            db.add_all([
                QuotationOption(expense_id=expense.id, option_number=1, supplier='Proveedor A', amount=Decimal('90.00')),
                QuotationOption(expense_id=expense.id, option_number=2, supplier='Proveedor B', amount=Decimal('95.00')),
                QuotationVotingInvitation(expense_id=expense.id, voter_user_id=self.approver.id, token='vote-token'),
            ])
            db.commit()

        detail = self.client.get('/api/expenses/REQ-VOTE/my-actions', headers=self.auth(self.approver_token))
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual([action['code'] for action in detail.json()['actions']], ['QUOTATION_VOTE'])
        self.assertEqual(len(detail.json()['request']['quotation_options']), 2)

    def test_requester_revision_and_closer_actions_are_user_specific(self):
        with self.Session() as db:
            self._expense(db, 'REQ-REVISION', ExpenseStatus.NEEDS_REVISION, self.requester.email)
            self._expense(db, 'REQ-CLOSE', ExpenseStatus.APPROVED, self.requester.email)
            db.commit()

        requester = self.client.get('/api/expenses/dashboard', headers=self.auth(self.requester_token))
        requester_items = {item['request_id']: item['actions'] for item in requester.json()['pending_items']}
        self.assertEqual(requester_items['REQ-REVISION'], ['CORRECT_REQUEST'])
        self.assertNotIn('REQ-CLOSE', requester_items)

        closer = self.client.get('/api/expenses/dashboard', headers=self.auth(self.closer_token))
        closer_items = {item['request_id']: item['actions'] for item in closer.json()['pending_items']}
        self.assertEqual(closer_items['REQ-CLOSE'], ['CLOSE_REQUEST'])
        self.assertNotIn('REQ-REVISION', closer_items)


if __name__ == '__main__':
    unittest.main()
