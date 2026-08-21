import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class UserTrackingScreenTests(unittest.TestCase):
    def test_home_no_longer_loads_team_tracking_data(self):
        compatibility = (REPO_ROOT / 'frontend' / 'src' / 'organization-overview.jsx').read_text(encoding='utf-8')
        self.assertIn('return null;', compatibility)
        self.assertNotIn('/api/organization/groups', compatibility)

    def test_tracking_screen_is_loaded_as_a_dedicated_authenticated_view(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'user-tracking.jsx').read_text(encoding='utf-8')
        index = (REPO_ROOT / 'frontend' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('const TRACKING_HASH = "#user-tracking"', source)
        self.assertIn('button.textContent = "Seguimiento"', source)
        self.assertIn('/api/organization/groups', source)
        self.assertIn('Seguimiento de usuarios', source)
        self.assertIn('Solo usuarios con acciones pendientes', source)
        self.assertIn('Usuario, grupo o rol', source)
        self.assertIn('/src/user-tracking.jsx', index)

    def test_tracking_endpoint_is_read_only_and_available_to_active_users(self):
        source = (REPO_ROOT / 'backend' / 'app' / 'api' / 'organization_overview.py').read_text(encoding='utf-8')
        self.assertIn("@router.get('/groups')", source)
        self.assertIn("require_permission('requests:read')", source)
        self.assertIn('pending_actions_by_expense(db, member)', source)
        self.assertIn('_group_role_names', source)
        self.assertIn('GroupRole.group_id == group_id', source)
        self.assertNotIn('@router.post', source)
        self.assertNotIn('@router.patch', source)
        self.assertNotIn('@router.delete', source)


if __name__ == '__main__':
    unittest.main()
