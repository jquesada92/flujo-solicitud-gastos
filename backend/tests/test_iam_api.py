import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('SECRET_KEY', 'unit-test-secret-key-at-least-32-characters')
os.environ.setdefault('ANALYTICS_HASH_KEY', 'unit-test-analytics-key-at-least-32-characters')
os.environ.setdefault('ENVIRONMENT', 'test')

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import auth
from app.application import create_app
from app.core.database import Base, get_db
from app.core.security import create_token, hash_password
from app.models.entities import User, UserRole
from app.models.iam import (
    Permission,
    Role,
    RolePermission,
    SystemAccount,
    UserPermission,
    UserRoleAssignment,
)
from app.services.iam_service import users_with_permission


ALL_PRODUCT_PERMISSIONS = {
    'requests:read',
    'requests:create',
    'requests:approve',
    'requests:close',
    'areas:manage',
    'config:manage',
}


class IamApiTests(unittest.TestCase):
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
        auth._login_attempts.clear()
        with self.Session() as db:
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(table.delete())
            db.commit()

            permissions = {
                code: Permission(code=code, name=code, active=True)
                for code in ALL_PRODUCT_PERMISSIONS
            }
            db.add_all(permissions.values())
            db.flush()

            system_role = Role(
                code='system-administrator',
                name='Administrador del sistema',
                active=True,
                system_managed=True,
            )
            db.add(system_role)
            db.flush()
            db.add_all([
                RolePermission(role_id=system_role.id, permission_id=permissions['config:manage'].id),
                RolePermission(role_id=system_role.id, permission_id=permissions['requests:read'].id),
            ])

            self.admin = self._new_user(db, 'admin@example.com')
            self.normal_user = self._new_user(db, 'member@example.com')
            db.flush()
            db.add(SystemAccount(user_id=self.admin.id, account_type='TECHNICAL_ADMIN'))
            db.add(UserRoleAssignment(user_id=self.admin.id, role_id=system_role.id))
            db.commit()

            self.admin_id = self.admin.id
            self.normal_user_id = self.normal_user.id
            self.admin_token = create_token(self.admin)
            self.user_token = create_token(self.normal_user)

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

    def auth(self, token: str) -> dict[str, str]:
        return {'Authorization': f'Bearer {token}'}

    def test_system_admin_has_all_active_permissions_outside_production(self):
        response = self.client.get('/api/iam/me/permissions', headers=self.auth(self.admin_token))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()['permission_codes']), ALL_PRODUCT_PERMISSIONS)
        for sources in response.json()['sources'].values():
            self.assertIn('Acceso de prueba de cuenta técnica (no producción)', sources)

    def test_login_returns_system_account_identity_and_full_non_production_capability_view(self):
        response = self.client.post(
            '/api/auth/login',
            json={'email': 'admin@example.com', 'password': 'Test-password-123!'},
        )
        self.assertEqual(response.status_code, 200, response.text)
        user = response.json()['user']
        self.assertEqual(set(user['permission_codes']), ALL_PRODUCT_PERMISSIONS)
        self.assertTrue(user['is_system_account'])
        self.assertTrue(user['can_request'])
        self.assertTrue(user['can_approve'])
        self.assertTrue(user['can_view'])
        self.assertTrue(user['can_configure'])
        self.assertTrue(user['can_close'])

    def test_normal_user_me_is_not_system_account(self):
        response = self.client.get('/api/auth/me', headers=self.auth(self.user_token))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()['is_system_account'])

    def test_system_account_can_join_approval_population_outside_production(self):
        with self.Session() as db:
            users = users_with_permission(db, 'requests:approve')
        self.assertIn(self.admin_id, {user.id for user in users})

    def test_system_account_is_restricted_in_production_but_can_manage_areas(self):
        with self.Session() as db:
            close_permission = db.scalar(select(Permission).where(Permission.code == 'requests:close'))
            db.add(UserPermission(user_id=self.admin_id, permission_id=close_permission.id))
            db.commit()

        production = SimpleNamespace(is_production_environment=True)
        with patch('app.services.iam_service.get_settings', return_value=production):
            effective = self.client.get('/api/iam/me/permissions', headers=self.auth(self.admin_token))
            self.assertEqual(
                set(effective.json()['permission_codes']),
                {'areas:manage', 'config:manage', 'requests:read'},
            )
            self.assertNotIn('requests:close', effective.json()['permission_codes'])

            with self.Session() as db:
                approvers = users_with_permission(db, 'requests:approve')
            self.assertNotIn(self.admin_id, {user.id for user in approvers})

    def test_user_without_config_cannot_administer_iam(self):
        response = self.client.get('/api/iam/roles', headers=self.auth(self.user_token))
        self.assertEqual(response.status_code, 403)

    def test_stale_config_manage_assignment_is_ignored_for_non_system_user(self):
        with self.Session() as db:
            permission = db.scalar(select(Permission).where(Permission.code == 'config:manage'))
            db.add(UserPermission(user_id=self.normal_user_id, permission_id=permission.id))
            db.commit()

        response = self.client.get('/api/iam/roles', headers=self.auth(self.user_token))
        self.assertEqual(response.status_code, 403)
        effective = self.client.get(
            f'/api/iam/users/{self.normal_user_id}/effective-permissions',
            headers=self.auth(self.admin_token),
        )
        self.assertNotIn('config:manage', effective.json()['permission_codes'])

    def test_area_manage_can_be_assigned_to_ordinary_user(self):
        grant = self.client.put(
            f'/api/iam/users/{self.normal_user_id}/permissions/areas:manage',
            headers=self.auth(self.admin_token),
        )
        self.assertEqual(grant.status_code, 200, grant.text)

        create_area = self.client.post(
            '/api/areas',
            headers=self.auth(self.user_token),
            json={'name': 'Operaciones'},
        )
        self.assertEqual(create_area.status_code, 201, create_area.text)
        self.assertEqual(create_area.json()['name'], 'Operaciones')

        iam_denied = self.client.get('/api/iam/roles', headers=self.auth(self.user_token))
        self.assertEqual(iam_denied.status_code, 403)

    def test_group_role_assignment_changes_effective_permissions_immediately(self):
        role = self.client.post(
            '/api/iam/roles',
            headers=self.auth(self.admin_token),
            json={
                'name': 'Aprobador',
                'description': 'Decide solicitudes',
                'permission_codes': ['requests:read', 'requests:approve'],
                'active': True,
            },
        )
        self.assertEqual(role.status_code, 201, role.text)
        role_id = role.json()['id']

        group = self.client.post(
            '/api/iam/groups',
            headers=self.auth(self.admin_token),
            json={'name': 'Comité de aprobación', 'active': True},
        )
        self.assertEqual(group.status_code, 201, group.text)
        group_id = group.json()['id']

        assigned_role = self.client.put(
            f'/api/iam/groups/{group_id}/roles/{role_id}',
            headers=self.auth(self.admin_token),
        )
        self.assertEqual(assigned_role.status_code, 200, assigned_role.text)

        member = self.client.put(
            f'/api/iam/groups/{group_id}/members/{self.normal_user_id}',
            headers=self.auth(self.admin_token),
        )
        self.assertEqual(member.status_code, 200, member.text)

        effective = self.client.get(
            f'/api/iam/users/{self.normal_user_id}/effective-permissions',
            headers=self.auth(self.admin_token),
        )
        self.assertEqual(effective.status_code, 200, effective.text)
        self.assertEqual(
            set(effective.json()['permission_codes']),
            {'requests:read', 'requests:approve'},
        )
        sources = effective.json()['sources']['requests:approve']
        self.assertTrue(any('Comité de aprobación' in source for source in sources))

    def test_direct_permission_is_additive(self):
        grant = self.client.put(
            f'/api/iam/users/{self.normal_user_id}/permissions/requests:create',
            headers=self.auth(self.admin_token),
        )
        self.assertEqual(grant.status_code, 200, grant.text)

        effective = self.client.get(
            f'/api/iam/users/{self.normal_user_id}/effective-permissions',
            headers=self.auth(self.admin_token),
        )
        self.assertIn('requests:create', effective.json()['permission_codes'])
        self.assertIn('Asignación directa', effective.json()['sources']['requests:create'])

    def test_system_managed_role_cannot_be_edited_from_ui(self):
        with self.Session() as db:
            role_id = db.scalar(select(Role.id).where(Role.code == 'system-administrator'))
        response = self.client.patch(
            f'/api/iam/roles/{role_id}',
            headers=self.auth(self.admin_token),
            json={'name': 'Super Admin'},
        )
        self.assertEqual(response.status_code, 409)


if __name__ == '__main__':
    unittest.main()
