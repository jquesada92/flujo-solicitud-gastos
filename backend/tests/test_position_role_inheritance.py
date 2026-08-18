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
)
from app.services.iam_service import (
    effective_permission_codes,
    permission_sources,
    users_with_permission,
)


class PositionRoleInheritanceTests(unittest.TestCase):
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

    def test_user_inherits_approve_from_position_role(self):
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

            self.assertIn('requests:approve', effective_permission_codes(db, user.id))
            self.assertIn(
                'Cargo Tesorero → Aprobador',
                permission_sources(db, user.id)['requests:approve'],
            )
            eligible = users_with_permission(db, 'requests:approve')
            self.assertEqual([item.id for item in eligible], [user.id])

    def test_group_and_position_inheritance_are_both_valid_sources(self):
        with self.Session() as db:
            role = self._approver_role(db)
            president = self._user(db, 'president@example.com')
            vice = self._user(db, 'vice@example.com')

            position = Position(code='president', name='Presidente', active=True)
            group = UserGroup(code='board', name='Junta Directiva', active=True)
            db.add_all([position, group])
            db.flush()
            db.add_all([
                UserPosition(user_id=president.id, position_id=position.id),
                PositionRole(position_id=position.id, role_id=role.id),
                GroupMember(group_id=group.id, user_id=vice.id),
                GroupRole(group_id=group.id, role_id=role.id),
            ])
            db.commit()

            eligible = users_with_permission(db, 'requests:approve')
            self.assertEqual({item.id for item in eligible}, {president.id, vice.id})
            self.assertIn(
                'Grupo Junta Directiva → Aprobador',
                permission_sources(db, vice.id)['requests:approve'],
            )

    def test_inactive_position_does_not_grant_permission(self):
        with self.Session() as db:
            role = self._approver_role(db)
            user = self._user(db, 'inactive-position@example.com')
            position = Position(code='treasurer', name='Tesorero', active=False)
            db.add(position)
            db.flush()
            db.add_all([
                UserPosition(user_id=user.id, position_id=position.id),
                PositionRole(position_id=position.id, role_id=role.id),
            ])
            db.commit()

            self.assertNotIn('requests:approve', effective_permission_codes(db, user.id))
            self.assertEqual(users_with_permission(db, 'requests:approve'), [])


if __name__ == '__main__':
    unittest.main()
