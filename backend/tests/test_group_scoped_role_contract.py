import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class GroupScopedRoleContractTests(unittest.TestCase):
    def test_each_role_can_belong_to_only_one_group(self):
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

    def test_user_role_assignment_derives_group_membership(self):
        source = (REPO_ROOT / 'backend' / 'app' / 'api' / 'iam_users.py').read_text(encoding='utf-8')
        self.assertIn("detail='Solo se permite un rol por grupo para cada usuario'", source)
        self.assertIn('db.execute(delete(GroupMember).where(GroupMember.user_id == user.id))', source)
        self.assertIn('db.add_all(GroupMember(user_id=user.id, group_id=group.id) for group in groups)', source)
        self.assertIn("detail='Cada rol asignado al usuario debe pertenecer a un grupo activo'", source)

    def test_group_membership_does_not_grant_every_group_role(self):
        service = (REPO_ROOT / 'backend' / 'app' / 'services' / 'iam_service.py').read_text(encoding='utf-8')
        self.assertIn('.join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)', service)
        self.assertIn('.join(GroupRole, GroupRole.role_id == Role.id)', service)
        self.assertNotIn('group_role_permissions =', service)
        self.assertIn("sources[code].add(f'Grupo {group_name} → Rol {role_name}')", service)

    def test_database_guard_rejects_two_roles_in_same_group(self):
        migration = (
            REPO_ROOT
            / 'backend'
            / 'alembic'
            / 'versions'
            / '20260820_0002_group_scoped_roles.py'
        ).read_text(encoding='utf-8')
        self.assertIn('trg_user_role_one_per_group', migration)
        self.assertIn("RAISE EXCEPTION 'A user can only have one role per group'", migration)

    def test_user_access_ui_uses_one_role_selector_per_group(self):
        frontend = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        self.assertIn('<h3>Acceso por grupo</h3>', frontend)
        self.assertIn('const setGroupRole = (group, rawRoleId) => {', frontend)
        self.assertIn('body: JSON.stringify({ role_ids: draftRoleIds })', frontend)
        self.assertIn('Sin rol / sin acceso', frontend)
        self.assertNotIn('<h3>Roles directos</h3>', frontend)

    def test_group_member_editor_is_read_only(self):
        frontend = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        backend = (REPO_ROOT / 'backend' / 'app' / 'api' / 'iam_group_assignments.py').read_text(encoding='utf-8')
        self.assertIn('Solo lectura. La membresía se obtiene al asignar un rol de este grupo', frontend)
        self.assertIn('disabled render={(user)', frontend)
        self.assertIn("detail='Los miembros del grupo se administran asignando un rol del grupo al usuario'", backend)


if __name__ == '__main__':
    unittest.main()
