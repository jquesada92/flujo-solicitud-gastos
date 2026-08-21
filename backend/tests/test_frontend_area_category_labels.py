import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class FrontendAreaCategoryLabelTests(unittest.TestCase):
    def test_expense_form_uses_area_then_category_labels(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'expense-form.jsx').read_text(encoding='utf-8')
        area_index = source.index('          Área\n          <select')
        category_index = source.index('          Categoría\n          <select')
        self.assertLess(area_index, category_index)

    def test_legacy_terminology_adapter_preserves_canonical_expense_form(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'domain-normalization.js').read_text(encoding='utf-8')
        self.assertIn("element?.closest?.('#expense-form, [data-canonical-classification-settings=", source)
        self.assertIn('isCanonicalTerminologyNode(node) ? userTerminology(text) : productTerminology(text)', source)
        self.assertIn('terminologyForNode(node, node.nodeValue)', source)
        self.assertIn('terminologyForNode(element, value)', source)


if __name__ == '__main__':
    unittest.main()
