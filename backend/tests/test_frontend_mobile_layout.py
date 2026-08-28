import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND = REPO_ROOT / "frontend" / "src"


class FrontendMobileLayoutTests(unittest.TestCase):
    def test_mobile_layer_is_loaded_after_legacy_styles(self):
        source = (FRONTEND / "main.jsx").read_text(encoding="utf-8")
        self.assertIn('import "./mobile-layout.css";', source)
        self.assertLess(source.index('import "./styles.css";'), source.index('import "./mobile-layout.css";'))

    def test_expense_rows_keep_semantic_labels_on_mobile(self):
        source = (FRONTEND / "main.jsx").read_text(encoding="utf-8")
        labels = set(re.findall(r'data-label="([^"]+)"', source))
        self.assertTrue(
            {"Solicitud", "Inicio", "Actualización", "Categoría", "Soportes", "Factura", "Monto", "Estado", "Avance", "Acciones"}.issubset(labels)
        )

    def test_mobile_css_protects_viewport_and_touch_targets(self):
        source = (FRONTEND / "mobile-layout.css").read_text(encoding="utf-8")
        required = (
            "@media (max-width: 720px)",
            "min-width: 0",
            "overflow-x: clip",
            ".table-wrap:has(.expenses-table)",
            ".expenses-table tbody",
            "content: attr(data-label)",
            "min-height: 44px",
            "100dvh",
            "safe-area-inset-bottom",
        )
        for fragment in required:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)

    def test_component_overlays_share_mobile_height_contract(self):
        tracking = (FRONTEND / "user-tracking.css").read_text(encoding="utf-8")
        dashboard = (FRONTEND / "home-dashboard.css").read_text(encoding="utf-8")
        iam = (FRONTEND / "iam-responsive.css").read_text(encoding="utf-8")
        self.assertIn("var(--mobile-topbar-offset,117px)", tracking)
        self.assertIn("100dvh", dashboard)
        self.assertIn("safe-area-inset-bottom", dashboard)
        self.assertIn("var(--mobile-topbar-offset, 117px)", iam)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr))", iam)


if __name__ == "__main__":
    unittest.main()
