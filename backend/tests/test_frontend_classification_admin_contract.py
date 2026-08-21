from pathlib import Path
import unittest


class FrontendClassificationAdminContractTests(unittest.TestCase):
    def test_canonical_area_category_screen_uses_global_category_catalog(self):
        repo_root = Path(__file__).resolve().parents[2]
        script = (repo_root / 'frontend' / 'src' / 'classification-admin.js').read_text(encoding='utf-8')
        normalizer = (repo_root / 'frontend' / 'src' / 'domain-normalization.js').read_text(encoding='utf-8')
        index = (repo_root / 'frontend' / 'index.html').read_text(encoding='utf-8')

        self.assertIn("Áreas y categorías", script)
        self.assertIn("node('h2', '', isArea ? 'Áreas' : 'Categorías')", script)
        self.assertIn("isArea ? 'Nombre del área' : 'Nombre de la categoría'", script)
        self.assertIn("isArea ? 'Crear área' : 'Crear categoría'", script)
        self.assertIn("request('/api/areas')", script)
        self.assertIn("/api/areas/categories?include_inactive=true", script)
        self.assertIn("`/api/areas/recovery?name=${encodeURIComponent(input.value.trim())}`", script)
        self.assertIn("recovery ? `/api/areas/${recovery.id}`", script)
        self.assertIn("Crea cada categoría una sola vez", script)
        self.assertNotIn("/api/categories/subcategories", script)
        self.assertIn('[data-canonical-classification-settings="true"]', normalizer)
        self.assertIn('isCanonicalTerminologyNode', normalizer)
        self.assertIn('/src/classification-admin.js', index)

    def test_category_assignment_is_staged_saved_per_row_and_active_only(self):
        repo_root = Path(__file__).resolve().parents[2]
        script = (repo_root / 'frontend' / 'src' / 'classification-admin.js').read_text(encoding='utf-8')

        self.assertIn("node('h2', '', 'Categorías por área')", script)
        self.assertIn("['Categoría', 'Asignada', 'Estado', 'Áreas asignadas', 'Acción']", script)
        self.assertIn('assignmentDrafts', script)
        self.assertIn('function visibleAssignmentCategories()', script)
        self.assertIn('return state.categories.filter((category) => category.active);', script)
        self.assertIn('visibleAssignmentCategories().forEach((category) => {', script)
        self.assertIn("checkbox.addEventListener('change', () => {", script)
        self.assertNotIn("checkbox.addEventListener('change', async", script)
        self.assertIn('async function saveAssignment(category)', script)
        self.assertIn("`/api/areas/${state.selectedAreaId}/categories/${category.id}`", script)
        self.assertIn("method: assigned ? 'POST' : 'DELETE'", script)
        self.assertIn("save.disabled = !assignmentChanged(category)", script)
        self.assertIn('Hay cambios de categorías sin guardar', script)
        self.assertNotIn('!category.active && !persisted', script)
        self.assertIn('No hay categorías activas disponibles para asignar.', script)
        self.assertIn('dirtyCount ? `${dirtyCount} cambio(s) sin guardar` : `${activeCategories.length} categoría(s)`', script)
        self.assertIn("dirtyMarker.dataset.unsaved = hasAssignmentChanges() ? 'true' : 'false'", script)


if __name__ == '__main__':
    unittest.main()
