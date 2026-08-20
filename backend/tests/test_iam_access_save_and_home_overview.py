import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class IamAccessSaveAndHomeOverviewTests(unittest.TestCase):
    def test_user_access_is_staged_and_saved_once_per_role_set(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        self.assertIn('const [draftRoleIds, setDraftRoleIds] = useState([]);', source)
        self.assertIn('const setGroupRole = (group, rawRoleId) => {', source)
        self.assertIn('const saveAccess = async () => {', source)
        self.assertIn('body: JSON.stringify({ role_ids: draftRoleIds })', source)
        self.assertIn('Acceso por grupo', source)
        self.assertIn('Sin rol / sin acceso', source)
        self.assertIn('Guardar cambios', source)
        self.assertNotIn('const updateAssignment = async', source)
        self.assertNotIn('<h3>Roles directos</h3>', source)
        self.assertNotIn('Permisos individuales', source)
        self.assertNotIn('<h3>Cargos</h3>', source)
        self.assertNotIn('["positions", "Cargos"]', source)

    def test_group_role_catalog_is_saved_atomically_and_members_are_derived(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        api = (REPO_ROOT / 'backend' / 'app' / 'api' / 'iam_group_assignments.py').read_text(encoding='utf-8')
        self.assertIn('body: JSON.stringify({ role_ids: draftRoleIds, member_ids: draftMemberIds })', source)
        self.assertIn("@router.patch('/groups/{group_id}')", api)
        self.assertIn('db.execute(delete(GroupRole)', api)
        self.assertIn('Los miembros del grupo se administran asignando un rol del grupo al usuario', api)
        self.assertIn('Solo lectura. La membresía se obtiene al asignar un rol de este grupo', source)
        self.assertNotIn('Promise.all(changes)', source)

    def test_permissions_are_resolved_only_through_group_scoped_user_roles(self):
        service = (REPO_ROOT / 'backend' / 'app' / 'services' / 'iam_service.py').read_text(encoding='utf-8')
        policy = (REPO_ROOT / 'backend' / 'app' / 'api' / 'iam_access_policy.py').read_text(encoding='utf-8')
        self.assertIn('.join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)', service)
        self.assertIn('.join(GroupRole, GroupRole.role_id == Role.id)', service)
        self.assertNotIn('UserPermission', service)
        self.assertNotIn('PositionRole', service)
        self.assertIn('Los permisos no se asignan directamente a usuarios', policy)
        self.assertIn('La membresía de grupo se obtiene al asignar al usuario un rol de ese grupo', policy)
        self.assertIn('Los cargos pertenecen al organigrama y no otorgan acceso', policy)

    def test_tracking_shows_group_specific_member_roles_and_pending_counts(self):
        frontend = (REPO_ROOT / 'frontend' / 'src' / 'user-tracking.jsx').read_text(encoding='utf-8')
        backend = (REPO_ROOT / 'backend' / 'app' / 'api' / 'organization_overview.py').read_text(encoding='utf-8')
        self.assertIn('/api/organization/groups', frontend)
        self.assertIn('member.roles.map', frontend)
        self.assertIn('member.pending_actions', frontend)
        self.assertIn("@router.get('/groups')", backend)
        self.assertIn('pending_actions_by_expense(db, member)', backend)
        self.assertIn('_group_role_names', backend)
        self.assertIn('GroupRole.group_id == group_id', backend)

    def test_canonical_dashboard_counts_actual_actions(self):
        source = (REPO_ROOT / 'backend' / 'app' / 'api' / 'dashboard.py').read_text(encoding='utf-8')
        self.assertIn('pending = pending_actions_by_expense(db, user)', source)
        self.assertIn("'pending_my_action': sum(len(actions) for actions in pending.values())", source)
        self.assertIn("'actions': pending.get(item.id, [])", source)


if __name__ == '__main__':
    unittest.main()
