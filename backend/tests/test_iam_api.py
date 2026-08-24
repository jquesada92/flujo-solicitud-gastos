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
from app.core.rate_limit import clear_rate_limits
from app.core.security import create_token, hash_password
from app.models.entities import ExpenseArea, User, UserRole
from app.models.iam import (
    Permission,
    Role,
    RolePermission,
    SystemAccount,
    UserGroup,
    UserPermission,
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
        clear_rate_limits()
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

    def test_inactive_entities_are_hidden_and_recoverable_by_business_key(self):
        with self.Session() as db:
            role = Role(code='archived-role', name='Archived Role', active=False, system_managed=False)
            group = UserGroup(code='archived-group', name='Archived Group', active=False)
            area = ExpenseArea(code='ARCHIVED-AREA', name='Archived Area', active=False)
            user = self._new_user(db, 'archived@example.com')
            user.identity_document = 'ARCHIVED-001'
            user.active = False
            db.add_all([role, group, area])
            db.commit()
            recovered_ids = (role.id, group.id, user.id, area.id)

        headers = self.auth(self.admin_token)
        self.assertNotIn('Archived Role', [item['name'] for item in self.client.get('/api/iam/roles', headers=headers).json()])
        self.assertNotIn('Archived Group', [item['name'] for item in self.client.get('/api/iam/groups', headers=headers).json()])
        self.assertNotIn('archived@example.com', [item['email'] for item in self.client.get('/api/iam/users', headers=headers).json()])
        self.assertNotIn('archived@example.com', [item['email'] for item in self.client.get('/api/users', headers=headers).json()])
        self.assertNotIn('Archived Area', [item['name'] for item in self.client.get('/api/areas', headers=headers).json()])

        recovered_role = self.client.get('/api/iam/roles/recovery', params={'name': ' archived role '}, headers=headers)
        recovered_group = self.client.get('/api/iam/groups/recovery', params={'name': 'ARCHIVED GROUP'}, headers=headers)
        recovered_user = self.client.get('/api/iam/users/recovery', params={'identity_document': 'archived-001'}, headers=headers)
        recovered_person = self.client.get('/api/users/recovery', params={'identity_document': 'archived-001'}, headers=headers)
        recovered_area = self.client.get('/api/areas/recovery', params={'name': 'ARCHIVED AREA'}, headers=headers)
        for response in (recovered_role, recovered_group, recovered_user, recovered_person, recovered_area):
            self.assertEqual(response.status_code, 200, response.text)
            self.assertFalse(response.json()['active'])
        self.assertEqual(recovered_role.json()['id'], recovered_ids[0])
        self.assertEqual(recovered_group.json()['id'], recovered_ids[1])
        self.assertEqual(recovered_user.json()['id'], recovered_ids[2])
        self.assertEqual(recovered_area.json()['id'], recovered_ids[3])

    def _create_group_role(self, group_name: str, role_name: str, permission_codes: list[str]) -> tuple[int, int]:
        role = self.client.post(
            '/api/iam/roles',
            headers=self.auth(self.admin_token),
            json={
                'name': role_name,
                'description': f'Rol de {group_name}',
                'permission_codes': permission_codes,
                'active': True,
            },
        )
        self.assertEqual(role.status_code, 201, role.text)
        role_id = role.json()['id']

        group = self.client.post(
            '/api/iam/groups',
            headers=self.auth(self.admin_token),
            json={'name': group_name, 'active': True},
        )
        self.assertEqual(group.status_code, 201, group.text)
        group_id = group.json()['id']

        bind = self.client.patch(
            f'/api/iam/groups/{group_id}',
            headers=self.auth(self.admin_token),
            json={'role_ids': [role_id]},
        )
        self.assertEqual(bind.status_code, 200, bind.text)
        return group_id, role_id

    def _assign_roles(self, user_id: int, role_ids: list[int]):
        response = self.client.patch(
            f'/api/iam/users/{user_id}',
            headers=self.auth(self.admin_token),
            json={'role_ids': role_ids},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response

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

    def test_area_manage_is_assigned_through_role_scoped_to_group(self):
        group_id, role_id = self._create_group_role(
            'Administración',
            'Gestor de áreas',
            ['areas:manage'],
        )
        updated = self._assign_roles(self.normal_user_id, [role_id])
        self.assertEqual(updated.json()['group_ids'], [group_id])
        self.assertEqual(updated.json()['role_ids'], [role_id])

        create_area = self.client.post(
            '/api/areas',
            headers=self.auth(self.user_token),
            json={'name': 'Operaciones'},
        )
        self.assertEqual(create_area.status_code, 201, create_area.text)
        self.assertEqual(create_area.json()['name'], 'Operaciones')

        iam_denied = self.client.get('/api/iam/roles', headers=self.auth(self.user_token))
        self.assertEqual(iam_denied.status_code, 403)

    def test_group_scoped_role_changes_effective_permissions_immediately(self):
        group_id, role_id = self._create_group_role(
            'Comité de aprobación',
            'Aprobador',
            ['requests:read', 'requests:approve'],
        )
        updated = self._assign_roles(self.normal_user_id, [role_id])
        self.assertEqual(updated.json()['group_ids'], [group_id])

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
        self.assertIn('Grupo Comité de aprobación → Rol Aprobador', sources)

    def test_group_permissions_are_inherited_without_replacing_role_permissions(self):
        group_id, role_id = self._create_group_role(
            'Junta Directiva',
            'Presidente',
            ['requests:create', 'requests:approve'],
        )
        configured = self.client.patch(
            f'/api/iam/groups/{group_id}',
            headers=self.auth(self.admin_token),
            json={
                'permission_codes': ['areas:manage', 'requests:approve', 'config:manage'],
            },
        )
        self.assertEqual(configured.status_code, 200, configured.text)
        self.assertEqual(
            configured.json()['permission_codes'],
            ['areas:manage', 'config:manage', 'requests:approve'],
        )

        self._assign_roles(self.normal_user_id, [role_id])
        effective = self.client.get(
            f'/api/iam/users/{self.normal_user_id}/effective-permissions',
            headers=self.auth(self.admin_token),
        )
        self.assertEqual(
            set(effective.json()['permission_codes']),
            {'requests:read', 'requests:create', 'requests:approve', 'areas:manage'},
        )
        self.assertNotIn('config:manage', effective.json()['permission_codes'])
        self.assertIn(
            'Grupo Junta Directiva (heredado por Rol Presidente)',
            effective.json()['sources']['areas:manage'],
        )
        self.assertEqual(
            set(effective.json()['sources']['requests:approve']),
            {
                'Grupo Junta Directiva → Rol Presidente',
                'Grupo Junta Directiva (heredado por Rol Presidente)',
            },
        )

        roles = self.client.get('/api/iam/roles', headers=self.auth(self.admin_token)).json()
        role = next(item for item in roles if item['id'] == role_id)
        self.assertEqual(set(role['permission_codes']), {'requests:create', 'requests:approve'})
        with self.Session() as db:
            inherited_area_managers = users_with_permission(db, 'areas:manage')
        self.assertIn(self.normal_user_id, {user.id for user in inherited_area_managers})

        inactivated = self.client.patch(
            f'/api/iam/groups/{group_id}',
            headers=self.auth(self.admin_token),
            json={'active': False},
        )
        self.assertEqual(inactivated.status_code, 200, inactivated.text)
        inactive_effective = self.client.get(
            f'/api/iam/users/{self.normal_user_id}/effective-permissions',
            headers=self.auth(self.admin_token),
        ).json()
        self.assertEqual(set(inactive_effective['permission_codes']), {'requests:read'})
        with self.Session() as db:
            inactive_area_managers = users_with_permission(db, 'areas:manage')
        self.assertNotIn(self.normal_user_id, {user.id for user in inactive_area_managers})

        reactivated = self.client.patch(
            f'/api/iam/groups/{group_id}',
            headers=self.auth(self.admin_token),
            json={'active': True},
        )
        self.assertEqual(reactivated.status_code, 200, reactivated.text)

        removed = self.client.patch(
            f'/api/iam/groups/{group_id}',
            headers=self.auth(self.admin_token),
            json={'permission_codes': []},
        )
        self.assertEqual(removed.status_code, 200, removed.text)
        self.assertEqual(removed.json()['permission_codes'], [])
        effective_after = self.client.get(
            f'/api/iam/users/{self.normal_user_id}/effective-permissions',
            headers=self.auth(self.admin_token),
        ).json()
        self.assertEqual(
            set(effective_after['permission_codes']),
            {'requests:read', 'requests:create', 'requests:approve'},
        )

    def test_group_permission_patch_rejects_unknown_code_atomically(self):
        created = self.client.post(
            '/api/iam/groups',
            headers=self.auth(self.admin_token),
            json={
                'name': 'Operaciones sensibles',
                'description': 'Original',
                'permission_codes': ['areas:manage'],
                'active': True,
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        group_id = created.json()['id']
        self.assertEqual(created.json()['permission_codes'], ['areas:manage'])

        rejected = self.client.patch(
            f'/api/iam/groups/{group_id}',
            headers=self.auth(self.admin_token),
            json={
                'name': 'Nombre que debe revertirse',
                'permission_codes': ['does:not-exist'],
            },
        )
        self.assertEqual(rejected.status_code, 422, rejected.text)

        groups = self.client.get(
            '/api/iam/groups',
            headers=self.auth(self.admin_token),
        ).json()
        group = next(item for item in groups if item['id'] == group_id)
        self.assertEqual(group['name'], 'Operaciones sensibles')
        self.assertEqual(group['permission_codes'], ['areas:manage'])

    def test_user_cannot_have_two_roles_from_same_group(self):
        group_id, first_role_id = self._create_group_role(
            'Solicitudes',
            'Solicitante',
            ['requests:create'],
        )
        second_role = self.client.post(
            '/api/iam/roles',
            headers=self.auth(self.admin_token),
            json={
                'name': 'Revisor de solicitudes',
                'permission_codes': ['requests:approve'],
                'active': True,
            },
        )
        self.assertEqual(second_role.status_code, 201, second_role.text)
        second_role_id = second_role.json()['id']
        bind = self.client.patch(
            f'/api/iam/groups/{group_id}',
            headers=self.auth(self.admin_token),
            json={'role_ids': [first_role_id, second_role_id]},
        )
        self.assertEqual(bind.status_code, 200, bind.text)

        response = self.client.patch(
            f'/api/iam/users/{self.normal_user_id}',
            headers=self.auth(self.admin_token),
            json={'role_ids': [first_role_id, second_role_id]},
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn('Solo se permite un rol por grupo', response.text)

    def test_direct_permission_assignment_is_rejected(self):
        grant = self.client.put(
            f'/api/iam/users/{self.normal_user_id}/permissions/requests:create',
            headers=self.auth(self.admin_token),
        )
        self.assertEqual(grant.status_code, 409, grant.text)

        effective = self.client.get(
            f'/api/iam/users/{self.normal_user_id}/effective-permissions',
            headers=self.auth(self.admin_token),
        )
        self.assertNotIn('requests:create', effective.json()['permission_codes'])

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
