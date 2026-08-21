import os
import unittest
from datetime import datetime, timezone

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('SECRET_KEY', 'unit-test-secret-key-at-least-32-characters')
os.environ.setdefault('ANALYTICS_HASH_KEY', 'unit-test-analytics-key-at-least-32-characters')
os.environ.setdefault('ENVIRONMENT', 'test')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.security import hash_password
from app.models.entities import User, UserRole
from app.models.iam import (
    GroupMember,
    GroupRole,
    Permission,
    Position,
    PositionRole,
    Role,
    RolePermission,
    UserGroup,
    UserPosition,
    UserRoleAssignment,
)
from app.services.iam_service import (
    effective_permission_codes,
    permission_sources,
    users_with_permission,
)


class PositionRoleIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            'sqlite://',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool,
        )
        cls.Session = sessionmaker(bind=cls.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(cls.engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def setUp(self):
        with self.Session() as db:
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(table.delete())
            db.commit()

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
        db.flush()
        return user

    def _approver_role(self, db) -> Role:
        permission = Permission(
            code='requests:approve',
            name='Aprobar solicitudes',
            active=True,
        )
        read = Permission(
            code='requests:read',
            name='Consultar solicitudes',
            active=True,
        )
        role = Role(
            code='approver',
            name='Aprobador',
            active=True,
            system_managed=False,
        )
        db.add_all([permission, read, role])
        db.flush()
        db.add(RolePermission(role_id=role.id, permission_id=permission.id))
        db.flush()
        return role

    def test_position_role_relation_does_not_grant_permission(self):
        with self.Session() as db:
            role = self._approver_role(db)
            user = self._user(db, 'treasurer@example.com')
            position = Position(code='treasurer', name='Tesorero', active=True)
            db.add(position)
            db.flush()
            db.add_all([
                UserPosition(user_id=user.id, position_id=position.id),
                PositionRole(position_id=position.id, role_id=role.id),
            ])
            db.commit()

            self.assertNotIn('requests:approve', effective_permission_codes(db, user.id))
            self.assertNotIn('requests:approve', permission_sources(db, user.id))
            self.assertEqual(users_with_permission(db, 'requests:approve'), [])

    def test_group_membership_without_explicit_user_role_does_not_grant_permission(self):
        with self.Session() as db:
            role = self._approver_role(db)
            user = self._user(db, 'member@example.com')
            group = UserGroup(code='board', name='Junta Directiva', active=True)
            db.add(group)
            db.flush()
            db.add_all([
                GroupMember(group_id=group.id, user_id=user.id),
                GroupRole(group_id=group.id, role_id=role.id),
            ])
            db.commit()

            self.assertNotIn('requests:approve', effective_permission_codes(db, user.id))
            self.assertEqual(users_with_permission(db, 'requests:approve'), [])

    def test_explicit_role_inside_group_is_the_authorization_source(self):
        with self.Session() as db:
            role = self._approver_role(db)
            user = self._user(db, 'approver@example.com')
            group = UserGroup(code='board', name='Junta Directiva', active=True)
            db.add(group)
            db.flush()
            db.add_all([
                GroupRole(group_id=group.id, role_id=role.id),
                GroupMember(group_id=group.id, user_id=user.id),
                UserRoleAssignment(user_id=user.id, role_id=role.id),
            ])
            db.commit()

            self.assertIn('requests:approve', effective_permission_codes(db, user.id))
            self.assertIn(
                'Grupo Junta Directiva → Rol Aprobador',
                permission_sources(db, user.id)['requests:approve'],
            )
            eligible = users_with_permission(db, 'requests:approve')
            self.assertEqual([item.id for item in eligible], [user.id])

    def test_explicit_global_role_is_an_authorization_source(self):
        with self.Session() as db:
            role = self._approver_role(db)
            user = self._user(db, 'global-approver@example.com')
            db.add(UserRoleAssignment(user_id=user.id, role_id=role.id))
            db.commit()

            self.assertIn('requests:approve', effective_permission_codes(db, user.id))
            self.assertIn(
                'Rol global Aprobador',
                permission_sources(db, user.id)['requests:approve'],
            )
            eligible = users_with_permission(db, 'requests:approve')
            self.assertEqual([item.id for item in eligible], [user.id])


if __name__ == '__main__':
    unittest.main()
