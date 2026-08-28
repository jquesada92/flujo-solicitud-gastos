import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND = REPO_ROOT / "frontend"


class FrontendMutationProcessingTests(unittest.TestCase):
    def test_request_governor_blocks_every_api_mutation_but_not_activity_sync(self):
        source = (FRONTEND / "src" / "request-governor.js").read_text(encoding="utf-8")
        main = (FRONTEND / "src" / "main.jsx").read_text(encoding="utf-8")

        self.assertIn('const MUTATION_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);', source)
        self.assertIn('const BACKGROUND_MUTATION_PATHS = new Set(["/api/auth/activity"]);', source)
        self.assertIn('const blockForMutation = shouldBlockForMutation(url, method, init);', source)
        self.assertIn('if (blockForMutation) beginBlockingMutation();', source)
        self.assertIn('if (blockForMutation) endBlockingMutation();', source)
        self.assertIn('activeBlockingMutations = Math.max(0, activeBlockingMutations - 1);', source)
        self.assertIn('appMutationOverlay: false', main)

    def test_processing_overlay_is_modal_accessible_and_keyboard_blocking(self):
        source = (FRONTEND / "src" / "request-governor.js").read_text(encoding="utf-8")
        css = (FRONTEND / "src" / "action-state.css").read_text(encoding="utf-8")
        index = (FRONTEND / "index.html").read_text(encoding="utf-8")

        self.assertLess(index.index('/src/request-governor.js'), index.index('/src/main.jsx'))
        self.assertLess(index.index('/src/request-governor.js'), index.index('/src/iam-admin.jsx'))
        self.assertLess(index.index('/src/request-governor.js'), index.index('/src/classification-admin.js'))
        for fragment in (
            'overlay.setAttribute("role", "alertdialog")',
            'overlay.setAttribute("aria-modal", "true")',
            'document.body.setAttribute("aria-busy", "true")',
            'element.setAttribute("inert", "")',
            'element.removeAttribute("inert")',
            'overlay.focus({ preventScroll: true })',
            'Procesando…',
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)

        for fragment in (
            '.app-processing-overlay {',
            'position: fixed;',
            'inset: 0;',
            'z-index: 2147483646;',
            'safe-area-inset-bottom',
            '.app-processing-overlay[hidden]',
            '@media (max-width: 440px)',
            '@media (prefers-reduced-motion: no-preference)',
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, css)


if __name__ == "__main__":
    unittest.main()
