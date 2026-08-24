from datetime import datetime
import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.audit_context import set_audit_actor
from app.models.activity_periods import (
    AreaActivityPeriod,
    GroupActivityPeriod,
    RoleActivityPeriod,
    UserActivityPeriod,
)
from app.models.entities import ExpenseArea, User, UserRole
from app.models.iam import GroupPermission, GroupRole, Permission, Role, RolePermission, UserGroup


class ActivityPeriodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine('sqlite+pysqlite:///:memory:')
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine, expire_on_commit=False)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

    def _user(self, email='period@example.com', *, active=True):
        return User(
            name='Period User', email=email, password_hash='not-used',
            role=UserRole.VIEWER, title='SIN_ASIGNAR', active=active,
        )

    def test_creation_adds_one_period_with_parent_creation_timestamp(self):
        with self.Session() as db:
            records = [
                (self._user(), UserActivityPeriod, 'user_id'),
                (ExpenseArea(code='OPS', name='Operations', active=True), AreaActivityPeriod, 'area_id'),
                (Role(code='reviewer', name='Reviewer', active=True), RoleActivityPeriod, 'role_id'),
                (UserGroup(code='finance', name='Finance', active=True), GroupActivityPeriod, 'group_id'),
            ]
            for entity, _, _ in records:
                db.add(entity)
            db.commit()

            for entity, period_model, foreign_key in records:
                period = db.scalar(select(period_model).where(getattr(period_model, foreign_key) == entity.id))
                self.assertIsNotNone(period)
                self.assertEqual(period.active_from, entity.created_at)
                self.assertIsNone(period.active_until)
                self.assertEqual(period.values['active'], entity.active)
                self.assertEqual(period.change_type, 'CREATE')
                self.assertEqual(period.actor_identifier, 'SYSTEM')

    def test_inactive_creation_has_an_open_version_marked_inactive(self):
        with self.Session() as db:
            user = self._user(active=False)
            db.add(user)
            db.commit()
            period = db.scalar(select(UserActivityPeriod).where(UserActivityPeriod.user_id == user.id))
            self.assertEqual(period.active_from, user.created_at)
            self.assertIsNone(period.active_until)
            self.assertFalse(period.values['active'])
            self.assertEqual(period.values['email'], user.email)

    def test_deactivation_closes_and_reactivation_opens_a_new_period(self):
        with self.Session() as db:
            area = ExpenseArea(code='LEGAL', name='Legal', active=True)
            db.add(area)
            db.commit()

            area.active = False
            db.commit()
            periods = list(db.scalars(select(AreaActivityPeriod).where(AreaActivityPeriod.area_id == area.id)))
            self.assertEqual(len(periods), 2)
            self.assertIsNotNone(periods[0].active_until)
            self.assertGreaterEqual(periods[0].active_until, periods[0].active_from)
            self.assertFalse(periods[1].values['active'])

            area.active = True
            db.commit()
            periods = list(db.scalars(
                select(AreaActivityPeriod)
                .where(AreaActivityPeriod.area_id == area.id)
                .order_by(AreaActivityPeriod.id)
            ))
            self.assertEqual(len(periods), 3)
            self.assertTrue(periods[2].values['active'])
            self.assertIsNone(periods[2].active_until)

    def test_non_active_field_modification_creates_a_new_snapshot(self):
        with self.Session() as db:
            group = UserGroup(code='audit', name='Audit', active=True)
            db.add(group)
            db.commit()
            group.active = True
            group.description = 'Updated without a state transition'
            db.commit()
            count = len(list(db.scalars(select(GroupActivityPeriod).where(GroupActivityPeriod.group_id == group.id))))
            periods = list(db.scalars(select(GroupActivityPeriod).where(GroupActivityPeriod.group_id == group.id).order_by(GroupActivityPeriod.id)))
            self.assertEqual(len(periods), 2)
            self.assertIsNotNone(periods[0].active_until)
            self.assertEqual(periods[1].values['description'], 'Updated without a state transition')

    def test_role_group_relationship_change_creates_a_new_role_snapshot(self):
        with self.Session() as db:
            role = Role(code='secretary', name='Secretary', active=True)
            group = UserGroup(code='board', name='Board', active=True)
            db.add_all([role, group])
            db.commit()
            db.add(GroupRole(group_id=group.id, role_id=role.id))
            db.commit()
            periods = list(db.scalars(select(RoleActivityPeriod).where(RoleActivityPeriod.role_id == role.id).order_by(RoleActivityPeriod.id)))
            self.assertEqual(len(periods), 2)
            self.assertIsNone(periods[0].values['group'])
            self.assertEqual(periods[1].values['group']['code'], 'board')
            self.assertEqual(periods[1].change_type, 'RELATION_UPDATE')
            self.assertIn('group', periods[1].changed_fields)

            assignment = db.scalar(select(GroupRole).where(GroupRole.role_id == role.id))
            db.delete(assignment)
            db.commit()
            periods = list(db.scalars(
                select(RoleActivityPeriod)
                .where(RoleActivityPeriod.role_id == role.id)
                .order_by(RoleActivityPeriod.id)
            ))
            self.assertEqual(len(periods), 3)
            self.assertIsNone(periods[-1].values['group'])
            self.assertIn('group', periods[-1].changed_fields)

    def test_role_and_group_permission_changes_are_versioned(self):
        with self.Session() as db:
            permission = Permission(code='requests:create', name='Create requests', active=True)
            role = Role(code='requester', name='Requester', active=True)
            group = UserGroup(code='operations', name='Operations', active=True)
            db.add_all([permission, role, group])
            db.commit()

            db.add_all([
                RolePermission(role_id=role.id, permission_id=permission.id),
                GroupPermission(group_id=group.id, permission_id=permission.id),
            ])
            db.commit()

            role_periods = list(db.scalars(
                select(RoleActivityPeriod)
                .where(RoleActivityPeriod.role_id == role.id)
                .order_by(RoleActivityPeriod.id)
            ))
            group_periods = list(db.scalars(
                select(GroupActivityPeriod)
                .where(GroupActivityPeriod.group_id == group.id)
                .order_by(GroupActivityPeriod.id)
            ))
            self.assertEqual(len(role_periods), 2)
            self.assertEqual(len(group_periods), 2)
            self.assertEqual(role_periods[-1].values['permission_codes'], ['requests:create'])
            self.assertEqual(group_periods[-1].values['permission_codes'], ['requests:create'])
            self.assertIn('permission_codes', role_periods[-1].changed_fields)
            self.assertIn('permission_codes', group_periods[-1].changed_fields)

    def test_group_metadata_and_permission_change_share_one_final_snapshot(self):
        with self.Session() as db:
            permission = Permission(code='areas:manage', name='Manage areas', active=True)
            group = UserGroup(code='directors', name='Directors', active=True)
            db.add_all([permission, group])
            db.commit()

            group.description = 'Approves and supervises requests'
            db.add(GroupPermission(group_id=group.id, permission_id=permission.id))
            db.commit()

            periods = list(db.scalars(
                select(GroupActivityPeriod)
                .where(GroupActivityPeriod.group_id == group.id)
                .order_by(GroupActivityPeriod.id)
            ))
            self.assertEqual(len(periods), 2)
            self.assertEqual(periods[-1].change_type, 'UPDATE')
            self.assertEqual(periods[-1].values['description'], 'Approves and supervises requests')
            self.assertEqual(periods[-1].values['permission_codes'], ['areas:manage'])
            self.assertIn('description', periods[-1].changed_fields)
            self.assertIn('permission_codes', periods[-1].changed_fields)

    def test_revision_records_actor_timestamp_and_before_after_changes(self):
        with self.Session() as db:
            actor = self._user('auditor@example.com')
            area = ExpenseArea(code='HR', name='Human Resources', active=True)
            db.add_all([actor, area])
            db.commit()
            set_audit_actor(
                db,
                user_id=actor.id,
                identifier=actor.email,
                identity_document=actor.identity_document,
            )
            area.name = 'People Operations'
            db.commit()
            revision = db.scalar(
                select(AreaActivityPeriod)
                .where(AreaActivityPeriod.area_id == area.id, AreaActivityPeriod.active_until.is_(None))
            )
            self.assertEqual(revision.actor_user_id, actor.id)
            self.assertEqual(revision.actor_identifier, actor.email)
            self.assertEqual(revision.change_type, 'UPDATE')
            self.assertEqual(revision.changed_fields, ['name'])
            self.assertEqual(revision.changes['name']['before'], 'Human Resources')
            self.assertEqual(revision.changes['name']['after'], 'People Operations')
            self.assertEqual(revision.event_at, revision.active_from)

    def test_database_rejects_two_open_periods_for_same_entity(self):
        with self.Session() as db:
            role = Role(code='buyer', name='Buyer', active=True)
            db.add(role)
            db.commit()
            db.add(RoleActivityPeriod(role_id=role.id, active_from=datetime.utcnow()))
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()


if __name__ == '__main__':
    unittest.main()
