import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class FrontendConfigurationAccessTests(unittest.TestCase):
    def test_vite_bridge_uses_system_account_for_technical_configuration(self):
        vite = (REPO_ROOT / 'frontend' / 'vite.config.js').read_text(encoding='utf-8')
        self.assertIn('isSystemAdmin = user.is_system_account === true', vite)
        self.assertIn('(user.permission_codes || []).includes("areas:manage")', vite)
        self.assertIn('canConfigure = isSystemAdmin', vite)
        self.assertIn('canAccessOrganization = isSystemAdmin', vite)
        self.assertIn('data-system-admin={isSystemAdmin ? "true" : "false"}', vite)

    def test_area_menu_is_independent_from_technical_configuration(self):
        vite = (REPO_ROOT / 'frontend' / 'vite.config.js').read_text(encoding='utf-8')
        self.assertIn('canManageAreas && <button onClick={() => navigateTo("categories")}', vite)
        self.assertIn('tab === "categories" && canManageAreas ?', vite)

    def test_access_console_is_injected_only_for_system_admin_menu(self):
        vite = (REPO_ROOT / 'frontend' / 'vite.config.js').read_text(encoding='utf-8')
        self.assertIn('protectAccessMenuInjection', vite)
        self.assertIn('menu.dataset.systemAdmin !== "true"', vite)
        self.assertIn('existing?.remove()', vite)
        self.assertIn('iam-admin access menu extraction expected 1 injection guard', vite)

    def test_access_menu_bridge_is_whitespace_tolerant_and_fail_fast(self):
        vite = (REPO_ROOT / 'frontend' / 'vite.config.js').read_text(encoding='utf-8')
        function = vite.split('function protectAccessMenuInjection(source) {', 1)[1].split(
            '\n}\n\nfunction modularExpenseFormPlugin()', 1
        )[0]
        self.assertIn('\\s*', function)
        self.assertIn('source.matchAll(pattern)', function)
        self.assertIn('matches.length !== 1', function)
        self.assertNotIn('replaceRequired(', function)
        self.assertNotIn('system-only access menu injection', function)

    def test_area_api_uses_dedicated_permission(self):
        source = (REPO_ROOT / 'backend' / 'app' / 'api' / 'areas.py').read_text(encoding='utf-8')
        self.assertIn("require_permission('areas:manage')", source)
        self.assertIn("has_permission(db, user.id, 'areas:manage')", source)
        self.assertNotIn("require_permission('config:manage')", source)


if __name__ == '__main__':
    unittest.main()
