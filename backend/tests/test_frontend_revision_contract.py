import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class FrontendRevisionContractTests(unittest.TestCase):
    def test_correction_form_is_modular_and_authoritative(self):
        form_source = (REPO_ROOT / 'frontend' / 'src' / 'expense-form.jsx').read_text(encoding='utf-8')
        self.assertIn('export function resolveRequestType(draft)', form_source)
        self.assertIn('draft.status === "QUOTATION_VOTING"', form_source)
        self.assertIn('(draft.quotation_options || []).length >= 2', form_source)
        self.assertIn('const effectiveRequestType = draft ? inferredDraftType : requestType;', form_source)
        self.assertIn('request_type: effectiveRequestType', form_source)
        self.assertIn('effectiveRequestType === "MULTI_QUOTE"', form_source)
        self.assertIn('effectiveRequestType === "SIMPLE"', form_source)
        self.assertIn('Tipo de solicitud:', form_source)
        self.assertIn('Múltiples cotizaciones', form_source)

    def test_multi_quote_correction_restores_existing_options(self):
        form_source = (REPO_ROOT / 'frontend' / 'src' / 'expense-form.jsx').read_text(encoding='utf-8')
        self.assertIn('restoredQuoteOptions(draft)', form_source)
        self.assertIn('existing_attachment', form_source)
        self.assertIn('Soporte existente conservado', form_source)
        self.assertIn('!draft && quoteOptions.length > 2', form_source)

    def test_legacy_main_uses_modular_expense_form_at_build_time(self):
        vite_config = (REPO_ROOT / 'frontend' / 'vite.config.js').read_text(encoding='utf-8')
        self.assertIn('import ExpenseForm from "./expense-form.jsx";', vite_config)
        self.assertIn('function ExpenseForm({', vite_config)
        self.assertIn('function ClosurePanel(', vite_config)
        self.assertIn('modular-expense-form', vite_config)
        self.assertIn('key={revision ? revision.request_id', vite_config)

    def test_type_selector_is_creation_only(self):
        form_source = (REPO_ROOT / 'frontend' / 'src' / 'expense-form.jsx').read_text(encoding='utf-8')
        self.assertIn('{!draft && (', form_source)
        self.assertIn('request-type-tabs', form_source)
        self.assertIn('El tipo no cambia durante una corrección.', form_source)


if __name__ == '__main__':
    unittest.main()
