import os
import unittest
from datetime import datetime, timezone

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('SECRET_KEY', 'unit-test-secret-key-at-least-32-characters')
os.environ.setdefault('ANALYTICS_HASH_KEY', 'unit-test-analytics-key-at-least-32-characters')
os.environ.setdefault('ENVIRONMENT', 'test')
os.environ.setdefault('EMAIL_MODE', 'console')

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.application import create_app
from app.core.database import Base, get_db
from app.core.security import apply_effective_permissions_to_user, create_token, hash_password
from app.models.entities import User, UserRole
from app.models.iam import Permission, Position, PositionRole, Role, RolePermission, UserPosition
from app.services.iam_service import has_permission


class ConfigurationReadAccessTests(unittest.TestCase):
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

            requests_read = Permission(
                code='requests:read',
                name='Consultar solicitudes',
                description='Lectura base',
                active=True,
            )
            config_read = Permission(
                code='config:read',
                name='Consultar configuración',
                description='Acceso de solo lectura',
                active=True,
            )
            config_manage = Permission(
                code='config:manage',
                name='Administrar configuración',
                description='Acceso de escritura',
                active=True,
            )
            viewer_role = Role(
                code='configuration-viewer',
                name='Visor de configuración',
                description='Rol de lectura',
                active=True,
                system_managed=False,
            )
            viewer_position = Position(
                code='configuration-observer-seat',
                name='Cargo de observación',
                description='Cargo de prueba sin nombre organizacional especial',
                active=True,
            )
            db.add_all([requests_read, config_read, config_manage, viewer_role, viewer_position])
            db.flush()
            db.add(RolePermission(role_id=viewer_role.id, permission_id=config_read.id))
            db.add(PositionRole(position_id=viewer_position.id, role_id=viewer_role.id))

            self.viewer = User(
                name='Visor de configuración',
                first_name='Visor',
                last_name='Configuración',
                identity_document='CFG-READ-1',
                email='config-viewer@example.com',
                password_hash=hash_password('Test-password-123!'),
                role=UserRole.VIEWER,
                title='SIN_ASIGNAR',
                active=True,
                can_request=False,
                can_approve=False,
                can_view=True,
                can_configure=False,
                must_change_password=False,
                last_activity_at=datetime.now(timezone.utc),
            )
            db.add(self.viewer)
            db.flush()
            db.add(UserPosition(user_id=self.viewer.id, position_id=viewer_position.id))
            db.commit()
            self.viewer_token = create_token(self.viewer)
            self.viewer_id = self.viewer.id

    def auth(self) -> dict[str, str]:
        return {'Authorization': f'Bearer {self.viewer_token}'}

    def test_config_read_is_inherited_by_cargo_without_config_manage(self):
        with self.Session() as db:
            user = db.get(User, self.viewer_id)
            hydrated = apply_effective_permissions_to_user(db, user)
            self.assertTrue(hydrated.can_configure)
            self.assertTrue(has_permission(db, user.id, 'config:read'))
            self.assertFalse(has_permission(db, user.id, 'config:manage'))

    def test_configuration_gets_are_available_to_read_only_user(self):
        for path in (
            '/api/iam/permissions',
            '/api/iam/roles',
            '/api/iam/groups',
            '/api/iam/users',
            '/api/iam/positions',
            '/api/users',
            '/api/users/profiles?include_inactive=true',
            '/api/rules/policies',
        ):
            with self.subTest(path=path):
                response = self.client.get(path, headers=self.auth())
                self.assertEqual(response.status_code, 200, response.text)

    def test_configuration_mutations_remain_forbidden(self):
        attempts = (
            ('post', '/api/iam/roles', {'name': 'No permitido', 'description': None, 'permission_codes': [], 'active': True}),
            ('post', '/api/iam/groups', {'name': 'No permitido', 'description': None, 'active': True}),
            ('post', '/api/iam/positions', {'name': 'No permitido', 'description': None, 'active': True}),
            ('patch', f'/api/iam/users/{self.viewer_id}', {'active': False}),
        )
        for method, path, payload in attempts:
            with self.subTest(method=method, path=path):
                response = getattr(self.client, method)(path, headers=self.auth(), json=payload)
                self.assertEqual(response.status_code, 403, response.text)


if __name__ == '__main__':
    unittest.main()
