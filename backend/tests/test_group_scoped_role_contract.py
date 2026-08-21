import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class GroupScopedRoleContractTests(unittest.TestCase):
    def test_each_role_can_belong_to_at_most_one_group(self):
        model = (REPO_ROOT / 'backend' / 'app' / 'models' / 'iam.py').read_text(encoding='utf-8')
        migration = (
            REPO_ROOT
            / 'backend'
            / 'alembic'
            / 'versions'
            / '20260820_0002_group_scoped_roles.py'
        ).read_text(encoding='utf-8')
        self.assertIn("UniqueConstraint('role_id', name='uq_group_role_role')", model)
        self.assertIn("create_unique_constraint('uq_group_role_role', ['role_id'])", migration)

    def test_grouped_user_role_assignment_derives_group_membership(self):
        source = (REPO_ROOT / 'backend' / 'app' / 'api' / 'iam_users.py').read_text(encoding='utf-8')
        self.assertIn("detail='Solo se permite un rol por grupo para cada usuario'", source)
        self.assertIn('db.execute(delete(GroupMember).where(GroupMember.user_id == user.id))', source)
        self.assertIn('db.add_all(GroupMember(user_id=user.id, group_id=group.id) for group in groups)', source)
        self.assertIn('global roles remain ungrouped', source)

    def test_global_roles_are_allowed_without_group_membership(self):
        source = (REPO_ROOT / 'backend' / 'app' / 'api' / 'iam_users.py').read_text(encoding='utf-8')
        migration = (
            REPO_ROOT
            / 'backend'
            / 'alembic'
            / 'versions'
            / '20260821_0004_allow_global_roles.py'
        ).read_text(encoding='utf-8')
        self.assertIn('if role_id in group_by_role', source)
        self.assertNotIn('Cada rol asignado al usuario debe pertenecer a un grupo activo', source)
        self.assertIn('IF target_group_id IS NULL THEN', migration)
        self.assertIn('RETURN NEW;', migration)

    def test_group_membership_does_not_grant_every_group_role(self):
        service = (REPO_ROOT / 'backend' / 'app' / 'services' / 'iam_service.py').read_text(encoding='utf-8')
        self.assertIn('.join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)', service)
        self.assertIn('.join(GroupRole, GroupRole.role_id == Role.id)', service)
        self.assertNotIn('group_role_permissions =', service)
        self.assertIn("sources[code].add(f'Grupo {group_name} → Rol {role_name}')", service)

    def test_global_role_permissions_have_explicit_source(self):
        service = (REPO_ROOT / 'backend' / 'app' / 'services' / 'iam_service.py').read_text(encoding='utf-8')
        self.assertIn("sources[code].add(f'Rol global {role_name}')", service)
        self.assertIn('~exists(select(GroupRole.id).where(GroupRole.role_id == Role.id))', service)

    def test_database_guard_only_limits_grouped_roles(self):
        migration = (
            REPO_ROOT
            / 'backend'
            / 'alembic'
            / 'versions'
            / '20260821_0004_allow_global_roles.py'
        ).read_text(encoding='utf-8')
        self.assertIn('trg_user_role_one_per_group', (
            REPO_ROOT / 'backend' / 'alembic' / 'versions' / '20260820_0002_group_scoped_roles.py'
        ).read_text(encoding='utf-8'))
        self.assertIn("RAISE EXCEPTION 'A user can only have one role per group'", migration)
        self.assertIn('IF target_group_id IS NULL THEN', migration)

    def test_user_access_ui_supports_group_and_global_roles(self):
        frontend = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        self.assertIn('<h3>Acceso por grupo</h3>', frontend)
        self.assertIn('<h3>Roles globales</h3>', frontend)
        self.assertIn('const toggleGlobalRole = (roleId, checked)', frontend)
        self.assertIn('body: JSON.stringify({ role_ids: draftRoleIds })', frontend)
        self.assertIn('Sin rol / sin acceso', frontend)
        self.assertNotIn('<h3>Roles directos</h3>', frontend)

    def test_group_may_have_zero_roles_and_detaching_makes_role_global(self):
        backend = (REPO_ROOT / 'backend' / 'app' / 'api' / 'iam_group_assignments.py').read_text(encoding='utf-8')
        frontend = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        self.assertIn('A group may have zero roles and a role may have zero or one group', backend)
        self.assertIn("db.execute(delete(GroupMember).where(GroupMember.group_id == group.id))", backend)
        self.assertIn('Un grupo puede existir sin roles', frontend)
        self.assertIn('lo convierte en rol global', frontend)


if __name__ == '__main__':
    unittest.main()
