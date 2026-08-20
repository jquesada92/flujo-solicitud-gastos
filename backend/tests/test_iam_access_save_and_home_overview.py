import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class IamAccessSaveAndHomeOverviewTests(unittest.TestCase):
    def test_user_access_is_staged_and_saved_once(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        self.assertIn('const [draftGroupIds, setDraftGroupIds] = useState([]);', source)
        self.assertIn('const [draftRoleIds, setDraftRoleIds] = useState([]);', source)
        self.assertIn('const saveAccess = async () => {', source)
        self.assertIn('body: JSON.stringify({ group_ids: draftGroupIds, role_ids: draftRoleIds })', source)
        self.assertIn('Guardar cambios', source)
        self.assertNotIn('const updateAssignment = async', source)
        self.assertNotIn('Permisos individuales', source)
        self.assertNotIn('<h3>Cargos</h3>', source)
        self.assertNotIn('["positions", "Cargos"]', source)

    def test_group_assignments_are_saved_atomically(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        api = (REPO_ROOT / 'backend' / 'app' / 'api' / 'iam_group_assignments.py').read_text(encoding='utf-8')
        self.assertIn('body: JSON.stringify({ role_ids: draftRoleIds, member_ids: draftMemberIds })', source)
        self.assertIn("@router.patch('/groups/{group_id}')", api)
        self.assertIn('db.execute(delete(GroupRole)', api)
        self.assertIn('db.execute(delete(GroupMember)', api)
        self.assertNotIn('Promise.all(changes)', source)

    def test_permissions_are_resolved_only_through_roles_and_groups(self):
        service = (REPO_ROOT / 'backend' / 'app' / 'services' / 'iam_service.py').read_text(encoding='utf-8')
        policy = (REPO_ROOT / 'backend' / 'app' / 'api' / 'iam_access_policy.py').read_text(encoding='utf-8')
        self.assertIn('direct_role_permissions | group_role_permissions', service)
        self.assertNotIn('UserPermission', service)
        self.assertNotIn('PositionRole', service)
        self.assertIn('Los permisos no se asignan directamente a usuarios', policy)
        self.assertIn('Los cargos pertenecen al organigrama y no otorgan acceso', policy)

    def test_home_shows_groups_members_roles_and_pending_counts(self):
        frontend = (REPO_ROOT / 'frontend' / 'src' / 'organization-overview.jsx').read_text(encoding='utf-8')
        backend = (REPO_ROOT / 'backend' / 'app' / 'api' / 'organization_overview.py').read_text(encoding='utf-8')
        dashboard = (REPO_ROOT / 'frontend' / 'src' / 'home-dashboard.jsx').read_text(encoding='utf-8')
        self.assertIn('/api/organization/groups', frontend)
        self.assertIn('member.roles.map', frontend)
        self.assertIn('member.pending_actions', frontend)
        self.assertIn("@router.get('/groups')", backend)
        self.assertIn('pending_actions_by_expense(db, member)', backend)
        self.assertIn('_effective_role_names', backend)
        self.assertIn('<OrganizationOverview refreshKey={refreshKey} />', dashboard)

    def test_canonical_dashboard_counts_actual_actions(self):
        source = (REPO_ROOT / 'backend' / 'app' / 'api' / 'dashboard.py').read_text(encoding='utf-8')
        self.assertIn('pending = pending_actions_by_expense(db, user)', source)
        self.assertIn("'pending_my_action': sum(len(actions) for actions in pending.values())", source)
        self.assertIn("'actions': pending.get(item.id, [])", source)


if __name__ == '__main__':
    unittest.main()
