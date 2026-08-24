import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class AccessNavigationBridgeTests(unittest.TestCase):
    def test_bridge_is_loaded_before_main_app(self):
        index = (REPO_ROOT / 'frontend' / 'index.html').read_text(encoding='utf-8')
        bridge = '/src/access-navigation-bridge.js'
        main = '/src/main.jsx'
        self.assertIn(bridge, index)
        self.assertIn(main, index)
        self.assertLess(index.index(bridge), index.index(main))

    def test_topbar_navigation_closes_access_console(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'access-navigation-bridge.js').read_text(encoding='utf-8')
        self.assertIn('window.location.hash !== ACCESS_HASH', source)
        self.assertIn('target?.closest(".topbar button")', source)
        self.assertIn('button.dataset.iamAccess === "true"', source)
        self.assertIn('button.closest(".config-menu-items")', source)
        self.assertIn('document.getElementById("iam-admin-root")', source)
        self.assertIn('iamRoot?.querySelectorAll(\'[data-unsaved="true"]\')', source)
        self.assertIn('window.confirm("Hay cambios sin guardar.', source)
        self.assertIn('event.stopImmediatePropagation()', source)
        self.assertIn('marker.dataset.unsaved = "false"', source)
        self.assertIn('window.location.hash = ""', source)
        self.assertIn('document.addEventListener("click", leaveAccessConsoleOnTopbarNavigation, true)', source)


if __name__ == '__main__':
    unittest.main()
