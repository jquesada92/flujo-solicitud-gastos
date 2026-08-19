from pathlib import Path
import unittest


class FrontendClassificationAdminContractTests(unittest.TestCase):
    def test_canonical_area_category_screen_uses_global_category_catalog(self):
        repo_root = Path(__file__).resolve().parents[2]
        script = (repo_root / 'frontend' / 'src' / 'classification-admin.js').read_text(encoding='utf-8')
        index = (repo_root / 'frontend' / 'index.html').read_text(encoding='utf-8')

        self.assertIn("Áreas y categorías", script)
        self.assertIn("/api/areas?include_inactive=true", script)
        self.assertIn("/api/areas/categories?include_inactive=true", script)
        self.assertIn("const path = isArea ? '/api/areas' : '/api/areas/categories';", script)
        self.assertIn("`/api/areas/${selectedAreaId}/categories/${category.id}`", script)
        self.assertIn("method: checkbox.checked ? 'POST' : 'DELETE'", script)
        self.assertIn("Crea cada categoría una sola vez", script)
        self.assertNotIn("/api/categories/subcategories", script)
        self.assertIn('/src/classification-admin.js', index)


if __name__ == '__main__':
    unittest.main()
