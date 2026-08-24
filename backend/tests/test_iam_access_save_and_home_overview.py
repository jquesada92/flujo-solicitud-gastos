import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class IamAccessSaveAndHomeOverviewTests(unittest.TestCase):
    def test_user_access_is_staged_and_saved_once_for_single_role(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        self.assertIn('const [draftRoleIds, setDraftRoleIds] = useState([]);', source)
        self.assertIn('const selectedRoleId = draftRoleIds[0] || "";', source)
        self.assertIn('const setRole = (rawRoleId) => {', source)
        self.assertIn('setDraftRoleIds(nextRoleId ? [nextRoleId] : []);', source)
        self.assertIn('const saveAccess = async () => {', source)
        self.assertIn('body: JSON.stringify({ role_ids: draftRoleIds })', source)
        self.assertIn('<h3>Rol</h3>', source)
        self.assertIn('`Miembro — ${selectedRoleGroup.name}`', source)
        self.assertIn('Sin grupo — Rol global', source)
        self.assertIn('Sin rol / sin acceso', source)
        self.assertIn('Guardar cambios', source)
        self.assertNotIn('const setGroupRole = (group, rawRoleId) => {', source)
        self.assertNotIn('const toggleGlobalRole = (roleId, checked)', source)
        self.assertNotIn('Acceso por grupo', source)
        self.assertNotIn('Roles globales', source)
        self.assertNotIn('const updateAssignment = async', source)
        self.assertNotIn('<h3>Roles directos</h3>', source)
        self.assertNotIn('Permisos individuales', source)
        self.assertNotIn('<h3>Cargos</h3>', source)
        self.assertNotIn('["positions", "Cargos"]', source)

    def test_group_roles_and_permissions_are_saved_atomically_and_members_are_derived(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'iam-admin.jsx').read_text(encoding='utf-8')
        api = (REPO_ROOT / 'backend' / 'app' / 'api' / 'iam_group_assignments.py').read_text(encoding='utf-8')
        self.assertIn('permission_codes: draftPermissionCodes,', source)
        self.assertIn('role_ids: draftRoleIds,', source)
        self.assertIn('member_ids: draftMemberIds,', source)
        self.assertIn("@router.patch('/groups/{group_id}', response_model=GroupOut)", api)
        self.assertIn('GroupPermission(group_id=group.id, permission_id=permission.id)', api)
        self.assertIn('select(GroupRole).where(GroupRole.group_id == group.id)', api)
        self.assertIn('db.delete(assignment)', api)
        self.assertIn("db.execute(delete(GroupMember).where(GroupMember.group_id == group.id))", api)
        self.assertIn('the freshly derived membership is authoritative', api)
        self.assertIn('Solo lectura. La membresía se obtiene al asignar un rol de este grupo', source)
        self.assertIn('Un grupo puede existir sin roles', source)
        self.assertNotIn('Promise.all(changes)', source)

    def test_permissions_are_resolved_through_grouped_or_global_roles_only(self):
        service = (REPO_ROOT / 'backend' / 'app' / 'services' / 'iam_service.py').read_text(encoding='utf-8')
        policy = (REPO_ROOT / 'backend' / 'app' / 'api' / 'iam_access_policy.py').read_text(encoding='utf-8')
        self.assertIn('.join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)', service)
        self.assertIn('.join(GroupRole, GroupRole.role_id == Role.id)', service)
        self.assertIn('.join(GroupPermission, GroupPermission.group_id == UserGroup.id)', service)
        self.assertIn('~exists(select(GroupRole.id).where(GroupRole.role_id == Role.id))', service)
        self.assertIn("sources[code].add(f'Rol global {role_name}')", service)
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
