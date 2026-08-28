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
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.application import create_app
from app.core.database import Base, get_db
from app.core.security import create_token, hash_password
from app.models.entities import (
    Approval,
    ApprovalPolicy,
    Expense,
    ExpenseArea,
    ExpenseStatus,
    ExpenseSubcategory,
    QuotationVotingInvitation,
    User,
    UserRole,
)
from app.models.iam import (
    GroupPermission,
    GroupRole,
    Permission,
    Role,
    RolePermission,
    SystemAccount,
    UserGroup,
    UserRoleAssignment,
)
from app.services.approval_policy_service import find_applicable_policy, minimum_votes_for_mode


PDF = b'%PDF-1.7\n% scoped approval rule test\n'


class ScopedApprovalRuleTests(unittest.TestCase):
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

            permissions = {
                code: Permission(code=code, name=code, active=True)
                for code in (
                    'requests:read',
                    'requests:create',
                    'requests:approve',
                    'config:manage',
                )
            }
            db.add_all(permissions.values())
            db.flush()

            area = ExpenseArea(code='ADMINISTRATION', name='Administración', active=True)
            other_area = ExpenseArea(code='OPERATIONS', name='Operaciones', active=True)
            db.add_all([area, other_area])
            db.flush()
            db.add_all([
                ExpenseSubcategory(area_id=area.id, code='SERVICES', name='Servicios', active=True),
                ExpenseSubcategory(area_id=other_area.id, code='SUPPLIES', name='Insumos', active=True),
            ])

            requester = self._user(db, 'requester@example.com')
            admin = self._user(db, 'admin@example.com')
            db.flush()
            requester_role = Role(code='requester', name='Solicitante', active=True)
            db.add(requester_role)
            db.flush()
            db.add_all([
                RolePermission(role_id=requester_role.id, permission_id=permissions['requests:create'].id),
                UserRoleAssignment(user_id=requester.id, role_id=requester_role.id),
                SystemAccount(user_id=admin.id, account_type='TECHNICAL_ADMIN'),
            ])

            board = UserGroup(code='board', name='Junta Directiva', active=True)
            db.add(board)
            db.flush()
            db.add(GroupPermission(
                group_id=board.id,
                permission_id=permissions['requests:approve'].id,
            ))

            board_users = []
            board_roles = []
            for index in range(1, 6):
                role = Role(code=f'board-role-{index}', name=f'Rol Junta {index}', active=True)
                member = self._user(db, f'board{index}@example.com')
                db.add_all([role, member])
                db.flush()
                db.add_all([
                    GroupRole(group_id=board.id, role_id=role.id),
                    UserRoleAssignment(user_id=member.id, role_id=role.id),
                ])
                board_roles.append(role)
                board_users.append(member)

            outsider_role = Role(code='outside-approver', name='Aprobador externo', active=True)
            outsider = self._user(db, 'outside@example.com')
            db.add_all([outsider_role, outsider])
            db.flush()
            db.add_all([
                RolePermission(
                    role_id=outsider_role.id,
                    permission_id=permissions['requests:approve'].id,
                ),
                UserRoleAssignment(user_id=outsider.id, role_id=outsider_role.id),
            ])
            db.commit()

            self.requester_token = create_token(requester)
            self.admin_token = create_token(admin)
            self.board_tokens = [create_token(member) for member in board_users]
            self.outsider_token = create_token(outsider)
            self.board_id = board.id
            self.first_board_role_id = board_roles[0].id

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

    @staticmethod
    def _auth(token: str) -> dict[str, str]:
        return {'Authorization': f'Bearer {token}'}

    def _policy(self, minimum, maximum, *, mode='MAJORITY', area='ADMINISTRATION'):
        return self.client.post(
            '/api/rules/policies',
            headers=self._auth(self.admin_token),
            json={
                'name': f'Regla {area} {minimum}-{maximum}',
                'expense_type': area,
                'min_amount': str(minimum),
                'max_amount': None if maximum is None else str(maximum),
                'approval_mode': mode,
                # Selecting both proves that a user reached twice is invited once.
                'approver_role_ids': [self.first_board_role_id],
                'approver_group_ids': [self.board_id],
                'active': True,
            },
        )

    @staticmethod
    def _multi_payload(amounts=('150.00', '300.00')) -> dict:
        return {
            'title': 'Compra con varias opciones',
            'description': 'Comparación regida por monto máximo',
            'expense_area': 'ADMINISTRATION',
            'expense_category': 'SERVICES',
            'urgency': 'NORMAL',
            'request_type': 'MULTI_QUOTE',
            'quotation_options': [
                {
                    'supplier': f'Proveedor {index}',
                    'amount': amount,
                    'item_url': f'https://example.com/quote-{index}',
                }
                for index, amount in enumerate(amounts, 1)
            ],
        }

    def _create_multi(self, amounts=('150.00', '300.00')):
        with patch('app.api.request_actions.send_quotation_vote_request'):
            return self.client.post(
                '/api/expenses',
                headers=self._auth(self.requester_token),
                json=self._multi_payload(amounts),
            )

    def _create_simple(self, amount='300.00'):
        with patch('app.services.approval_engine.send_approval_request'):
            return self.client.post(
                '/api/expenses',
                headers=self._auth(self.requester_token),
                json={
                    'title': 'Compra sencilla configurada',
                    'description': 'Prueba de audiencia por Grupo',
                    'expense_area': 'ADMINISTRATION',
                    'expense_category': 'SERVICES',
                    'urgency': 'NORMAL',
                    'request_type': 'SIMPLE',
                    'amount': amount,
                    'supplier': 'Proveedor simple',
                    'item_url': 'https://example.com/simple-quote',
                },
            )

    def _vote(self, request_id: str, token: str, option_id: int):
        return self.client.post(
            f'/api/expenses/{request_id}/quotation-vote',
            headers=self._auth(token),
            json={'quotation_option_id': option_id},
        )

    def test_adjacent_ranges_are_valid_and_boundary_matches_only_lower_band(self):
        first = self._policy('0', '200')
        second = self._policy('200', '500')
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(second.status_code, 201, second.text)

        overlap = self._policy('199', '300')
        self.assertEqual(overlap.status_code, 409, overlap.text)

        with self.Session() as db:
            at_boundary = find_applicable_policy(
                db, 'ADMINISTRATION', Decimal(first.json()['max_amount'])
            )
            above_boundary = find_applicable_policy(db, 'ADMINISTRATION', Decimal('200.01'))
            self.assertEqual(at_boundary.id, first.json()['id'])
            self.assertEqual(above_boundary.id, second.json()['id'])

    def test_maximum_quote_selects_policy_and_group_expands_all_roles_once(self):
        policy = self._policy('200', '500')
        self.assertEqual(policy.status_code, 201, policy.text)

        created = self._create_multi()
        self.assertEqual(created.status_code, 201, created.text)
        payload = created.json()
        self.assertEqual(payload['approval_policy_id'], policy.json()['id'])
        self.assertEqual(payload['policy_evaluation_amount'], '300.00')
        self.assertEqual(payload['minimum_votes_required'], 3)

        with self.Session() as db:
            expense = db.scalar(select(Expense).where(Expense.request_id == payload['request_id']))
            invited_emails = set(db.scalars(
                select(User.email)
                .join(QuotationVotingInvitation, QuotationVotingInvitation.voter_user_id == User.id)
                .where(QuotationVotingInvitation.expense_id == expense.id)
            ).all())
            invitation_count = db.scalar(select(func.count(QuotationVotingInvitation.id)).where(
                QuotationVotingInvitation.expense_id == expense.id,
            ))
        self.assertEqual(invitation_count, 5)
        self.assertEqual(invited_emails, {f'board{index}@example.com' for index in range(1, 6)})
        self.assertEqual(minimum_votes_for_mode('ANY', 15), 1)
        self.assertEqual(minimum_votes_for_mode('MAJORITY', 15), 8)
        self.assertEqual(minimum_votes_for_mode('ALL', 15), 15)

    def test_simple_policy_uses_the_same_group_targets_and_mode(self):
        policy = self._policy('200', '500', mode='ALL')
        self.assertEqual(policy.status_code, 201, policy.text)

        created = self._create_simple()
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()['approval_policy_id'], policy.json()['id'])
        self.assertEqual(created.json()['minimum_votes_required'], 5)
        with self.Session() as db:
            approvers = set(db.scalars(select(Approval.approver_email)).all())
            modes = set(db.scalars(select(Approval.approval_mode)).all())
        self.assertEqual(approvers, {f'board{index}@example.com' for index in range(1, 6)})
        self.assertEqual(modes, {'ALL'})

    def test_policy_quorum_enables_requester_close_but_keeps_remaining_votes_open(self):
        self.assertEqual(self._policy('200', '500').status_code, 201)
        created = self._create_multi()
        self.assertEqual(created.status_code, 201, created.text)
        request_id = created.json()['request_id']
        first_option, second_option = [item['id'] for item in created.json()['quotation_options']]

        for token in self.board_tokens[:3]:
            response = self._vote(request_id, token, first_option)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['status'], 'QUOTATION_VOTING')

        requester_view = self.client.get('/api/expenses', headers=self._auth(self.requester_token))
        item = next(row for row in requester_view.json() if row['request_id'] == request_id)
        self.assertTrue(item['quotation_quorum_reached'])
        self.assertTrue(item['can_close'])
        self.assertEqual(item['quotation_vote_count'], 3)

        dashboard = self.client.get(
            '/api/expenses/dashboard', headers=self._auth(self.requester_token)
        )
        pending = {row['request_id']: row['actions'] for row in dashboard.json()['pending_items']}
        self.assertIn('CLOSE_REQUEST', pending[request_id])
        detail = self.client.get(
            f'/api/expenses/{request_id}/my-actions',
            headers=self._auth(self.requester_token),
        )
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()['request']['minimum_votes_required'], 3)
        self.assertTrue(detail.json()['request']['quotation_quorum_reached'])

        remaining_view = self.client.get('/api/expenses', headers=self._auth(self.board_tokens[3]))
        remaining_item = next(row for row in remaining_view.json() if row['request_id'] == request_id)
        self.assertTrue(remaining_item['can_vote'])
        fourth_vote = self._vote(request_id, self.board_tokens[3], second_option)
        self.assertEqual(fourth_vote.status_code, 200, fourth_vote.text)
        self.assertEqual(fourth_vote.json()['status'], 'QUOTATION_VOTING')

        with tempfile.TemporaryDirectory() as temporary_directory:
            invoice_path = Path(temporary_directory) / 'invoice.pdf'
            invoice_path.write_bytes(PDF)
            with patch('app.api.financial_actions.write_document', return_value=invoice_path):
                closed = self.client.post(
                    f'/api/expenses/{request_id}/close',
                    headers=self._auth(self.requester_token),
                    files={'invoice': ('invoice.pdf', PDF, 'application/pdf')},
                    data={'notes': 'Cierre por quórum'},
                )
        self.assertEqual(closed.status_code, 200, closed.text)
        self.assertEqual(closed.json()['status'], 'CLOSED')
        self.assertEqual(closed.json()['selected_quotation_id'], first_option)

        late_vote = self._vote(request_id, self.board_tokens[4], first_option)
        self.assertEqual(late_vote.status_code, 409, late_vote.text)

    def test_quorum_tie_does_not_enable_close_and_later_vote_recalculates_leader(self):
        self.assertEqual(self._policy('200', '500').status_code, 201)
        created = self._create_multi(('250.00', '300.00', '400.00'))
        self.assertEqual(created.status_code, 201, created.text)
        request_id = created.json()['request_id']
        options = [item['id'] for item in created.json()['quotation_options']]

        for token, option_id in zip(self.board_tokens[:3], options):
            response = self._vote(request_id, token, option_id)
            self.assertEqual(response.status_code, 200, response.text)

        tied_view = self.client.get('/api/expenses', headers=self._auth(self.requester_token))
        tied = next(row for row in tied_view.json() if row['request_id'] == request_id)
        self.assertTrue(tied['quotation_quorum_reached'])
        self.assertFalse(tied['can_close'])

        later = self._vote(request_id, self.board_tokens[3], options[0])
        self.assertEqual(later.status_code, 200, later.text)
        resolved_view = self.client.get('/api/expenses', headers=self._auth(self.requester_token))
        resolved = next(row for row in resolved_view.json() if row['request_id'] == request_id)
        self.assertTrue(resolved['can_close'])

    def test_without_policy_every_eligible_user_must_vote_before_ordinary_close(self):
        created = self._create_multi(('50.00', '100.00'))
        self.assertEqual(created.status_code, 201, created.text)
        payload = created.json()
        request_id = payload['request_id']
        option_id = payload['quotation_options'][0]['id']
        self.assertIsNone(payload['approval_policy_id'])
        # In the non-production test policy the technical account also has the
        # active approval permission. Production excludes it by policy.
        self.assertEqual(payload['minimum_votes_required'], 7)

        for token in self.board_tokens:
            response = self._vote(request_id, token, option_id)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['status'], 'QUOTATION_VOTING')

        before_all = self.client.get('/api/expenses', headers=self._auth(self.requester_token))
        item = next(row for row in before_all.json() if row['request_id'] == request_id)
        self.assertFalse(item['can_close'])

        outsider_vote = self._vote(request_id, self.outsider_token, option_id)
        self.assertEqual(outsider_vote.status_code, 200, outsider_vote.text)
        self.assertEqual(outsider_vote.json()['status'], 'QUOTATION_VOTING')

        premature_close = self.client.post(
            f'/api/expenses/{request_id}/close',
            headers=self._auth(self.requester_token),
            files={'invoice': ('invoice.pdf', PDF, 'application/pdf')},
            data={'notes': 'Intento sin regla antes de todos los votos'},
        )
        self.assertEqual(premature_close.status_code, 409, premature_close.text)
        with self.Session() as db:
            still_open = db.scalar(
                select(Expense).where(Expense.request_id == request_id)
            )
            self.assertEqual(still_open.status, ExpenseStatus.QUOTATION_VOTING)
            self.assertIsNone(still_open.selected_quotation_id)

        final_vote = self._vote(request_id, self.admin_token, option_id)
        self.assertEqual(final_vote.status_code, 200, final_vote.text)
        self.assertEqual(final_vote.json()['status'], 'APPROVED')


if __name__ == '__main__':
    unittest.main()
