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
    Expense,
    ExpenseArea,
    ExpenseAttachment,
    ExpenseStatus,
    ExpenseSubcategory,
    User,
    UserRole,
)
from app.models.iam import (
    GroupPermission,
    GroupRole,
    Permission,
    Role,
    RolePermission,
    UserGroup,
    UserRoleAssignment,
)


class RequestFlowCreationTests(unittest.TestCase):
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

            self.read_permission = Permission(code='requests:read', name='Consultar solicitudes', active=True)
            self.create_permission = Permission(code='requests:create', name='Crear solicitudes', active=True)
            self.approve_permission = Permission(code='requests:approve', name='Aprobar solicitudes', active=True)
            db.add_all([self.read_permission, self.create_permission, self.approve_permission])
            db.flush()

            area = ExpenseArea(code='ADMINISTRATION', name='Administración', active=True)
            db.add(area)
            db.flush()
            db.add(ExpenseSubcategory(area_id=area.id, code='SERVICES', name='Servicios', active=True))

            self.requester = self._new_user(db, 'requester@example.com')
            db.flush()
            requester_role = Role(code='requester', name='Solicitante', active=True)
            db.add(requester_role)
            db.flush()
            db.add(RolePermission(role_id=requester_role.id, permission_id=self.create_permission.id))
            db.add(UserRoleAssignment(user_id=self.requester.id, role_id=requester_role.id))
            db.commit()

            self.requester_token = create_token(self.requester)

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

    def _auth(self) -> dict[str, str]:
        return {'Authorization': f'Bearer {self.requester_token}'}

    def _payload(self, *, quotation_pending: bool = False) -> dict:
        return {
            'title': 'Reparación de la bomba',
            'description': 'Cambio preventivo solicitado',
            'expense_area': 'ADMINISTRATION',
            'expense_category': 'SERVICES',
            'urgency': 'NORMAL',
            'request_type': 'SIMPLE',
            'amount': '125.50',
            'supplier': 'Proveedor de prueba',
            'item_url': None if quotation_pending else 'https://example.com/cotizacion',
            'quotation_pending': quotation_pending,
        }

    def _add_iam_approvers(self):
        with self.Session() as db:
            approve = db.scalar(select(Permission).where(Permission.code == 'requests:approve'))

            own_group = UserGroup(code='operations', name='Operaciones', active=True)
            inherited_group = UserGroup(code='board', name='Junta Directiva', active=True)
            own_role = Role(code='president', name='Presidente', active=True)
            inherited_role = Role(code='treasurer', name='Tesorero', active=True)
            global_role = Role(code='global-approver', name='Aprobador global', active=True)
            own_user = self._new_user(db, 'president@example.com')
            inherited_user = self._new_user(db, 'treasurer@example.com')
            global_user = self._new_user(db, 'global@example.com')
            db.add_all([own_group, inherited_group, own_role, inherited_role, global_role])
            db.flush()

            db.add_all([
                GroupRole(group_id=own_group.id, role_id=own_role.id),
                GroupRole(group_id=inherited_group.id, role_id=inherited_role.id),
                RolePermission(role_id=own_role.id, permission_id=approve.id),
                GroupPermission(group_id=inherited_group.id, permission_id=approve.id),
                RolePermission(role_id=global_role.id, permission_id=approve.id),
                UserRoleAssignment(user_id=own_user.id, role_id=own_role.id),
                UserRoleAssignment(user_id=inherited_user.id, role_id=inherited_role.id),
                UserRoleAssignment(user_id=global_user.id, role_id=global_role.id),
            ])
            db.commit()

    def test_simple_request_uses_iam_approvers_without_an_amount_policy(self):
        self._add_iam_approvers()

        with patch('app.services.approval_engine.send_approval_request'):
            response = self.client.post('/api/expenses', json=self._payload(), headers=self._auth())

        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()['status'], 'PENDING_APPROVAL')
        with self.Session() as db:
            approvers = set(db.scalars(select(Approval.approver_email)).all())
            modes = set(db.scalars(select(Approval.approval_mode)).all())
        self.assertEqual(
            approvers,
            {'president@example.com', 'treasurer@example.com', 'global@example.com'},
        )
        self.assertEqual(modes, {'MAJORITY'})

    def test_notification_failure_does_not_report_a_committed_flow_as_creation_failure(self):
        self._add_iam_approvers()

        with (
            patch('app.services.approval_engine.send_approval_request', side_effect=RuntimeError('smtp unavailable')),
            patch('app.services.approval_engine.logger.exception'),
        ):
            response = self.client.post('/api/expenses', json=self._payload(), headers=self._auth())

        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()['status'], 'PENDING_APPROVAL')
        with self.Session() as db:
            self.assertEqual(db.scalar(select(func.count(Expense.id))), 1)
            self.assertEqual(db.scalar(select(func.count(Approval.id))), 3)

    def test_request_with_url_is_not_persisted_when_no_flow_can_start(self):
        response = self.client.post('/api/expenses', json=self._payload(), headers=self._auth())

        self.assertEqual(response.status_code, 422, response.text)
        with self.Session() as db:
            self.assertEqual(db.scalar(select(func.count(Expense.id))), 0)

    def test_simple_resubmit_rolls_back_when_no_flow_can_start(self):
        with self.Session() as db:
            expense = Expense(
                request_id='request-to-correct',
                flow_id='original-flow',
                display_id='ADM-2026-CORRECT',
                request_type='SIMPLE',
                title='Título original',
                description='Descripción original',
                expense_area='ADMINISTRATION',
                expense_category='SERVICES',
                urgency='NORMAL',
                amount=Decimal('900.00'),
                supplier='Proveedor original',
                item_url='https://example.com/original',
                requested_by=self.requester.email,
                status=ExpenseStatus.NEEDS_REVISION,
            )
            db.add(expense)
            db.commit()

        response = self.client.put(
            '/api/expenses/request-to-correct/resubmit',
            json=self._payload(),
            headers=self._auth(),
        )

        self.assertEqual(response.status_code, 422, response.text)
        with self.Session() as db:
            stored = db.scalar(
                select(Expense).where(Expense.request_id == 'request-to-correct')
            )
            self.assertEqual(stored.flow_id, 'original-flow')
            self.assertEqual(stored.title, 'Título original')
            self.assertEqual(stored.amount, Decimal('900.00'))
            self.assertEqual(stored.status, ExpenseStatus.NEEDS_REVISION)
            self.assertEqual(db.scalar(select(func.count(Approval.id))), 0)

    def test_request_with_upload_is_removed_when_no_flow_can_start(self):
        created = self.client.post(
            '/api/expenses',
            json=self._payload(quotation_pending=True),
            headers=self._auth(),
        )
        self.assertEqual(created.status_code, 201, created.text)

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)

            def write_test_document(stored_name: str, content: bytes) -> Path:
                path = temporary_path / stored_name
                path.write_bytes(content)
                return path

            with patch('app.api.document_actions.write_document', side_effect=write_test_document):
                uploaded = self.client.post(
                    f"/api/expenses/{created.json()['request_id']}/attachments",
                    files={'file': ('quotation.pdf', b'%PDF-1.7\n', 'application/pdf')},
                    headers=self._auth(),
                )

            self.assertEqual(uploaded.status_code, 422, uploaded.text)
            self.assertEqual(list(temporary_path.iterdir()), [])

        with self.Session() as db:
            self.assertEqual(db.scalar(select(func.count(Expense.id))), 0)
            self.assertEqual(db.scalar(select(func.count(ExpenseAttachment.id))), 0)


if __name__ == '__main__':
    unittest.main()
