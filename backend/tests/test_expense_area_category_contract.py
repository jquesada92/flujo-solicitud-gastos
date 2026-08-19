import unittest
from pathlib import Path

from app.schemas.expense import ExpenseCreate, ExpenseOut, InvoiceOut


REPO_ROOT = Path(__file__).resolve().parents[2]


class ExpenseAreaCategoryContractTests(unittest.TestCase):
    def test_create_contract_uses_canonical_public_names(self):
        fields = ExpenseCreate.model_fields
        self.assertIn('expense_area', fields)
        self.assertIn('expense_category', fields)
        self.assertNotIn('expense_type', fields)
        self.assertNotIn('expense_subcategory', fields)

        payload = ExpenseCreate(
            title='Compra de equipo',
            description='Compra requerida para operación',
            expense_area='ADMINISTRATION',
            expense_category='EQUIPMENT',
            amount=100,
            supplier='Proveedor',
            item_url='https://example.com/quote',
        )
        self.assertEqual(payload.expense_area, 'ADMINISTRATION')
        self.assertEqual(payload.expense_category, 'EQUIPMENT')

        # Persistence compatibility remains internal only; the ORM still uses
        # the legacy attribute names until its dedicated migration/refactor.
        dumped = payload.model_dump(mode='json')
        self.assertEqual(dumped['expense_type'], 'ADMINISTRATION')
        self.assertEqual(dumped['expense_subcategory'], 'EQUIPMENT')
        self.assertNotIn('expense_area', dumped)
        self.assertNotIn('expense_category', dumped)

    def test_legacy_input_is_temporarily_accepted_but_not_canonical(self):
        payload = ExpenseCreate(
            title='Compra de equipo',
            description='Compra requerida para operación',
            expense_type='ADMINISTRATION',
            expense_subcategory='EQUIPMENT',
            amount=100,
            supplier='Proveedor',
            item_url='https://example.com/quote',
        )
        self.assertEqual(payload.expense_area, 'ADMINISTRATION')
        self.assertEqual(payload.expense_category, 'EQUIPMENT')

    def test_response_models_expose_only_canonical_names(self):
        for model in (ExpenseOut, InvoiceOut):
            fields = model.model_fields
            self.assertIn('expense_area', fields)
            self.assertIn('expense_category', fields)
            self.assertNotIn('expense_type', fields)
            self.assertNotIn('expense_subcategory', fields)

    def test_frontend_sends_canonical_wire_payload(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'domain-normalization.js').read_text(encoding='utf-8')
        self.assertIn("normalized.expense_area = normalized.expense_type", source)
        self.assertIn("normalized.expense_category = normalized.expense_subcategory", source)
        self.assertIn('delete normalized.expense_type', source)
        self.assertIn('delete normalized.expense_subcategory', source)

    def test_pending_action_payload_is_canonical(self):
        source = (REPO_ROOT / 'backend' / 'app' / 'api' / 'my_actions.py').read_text(encoding='utf-8')
        self.assertIn("'expense_area': expense.expense_type", source)
        self.assertIn("'expense_category': expense.expense_subcategory", source)
        self.assertNotIn("'expense_type': expense.expense_type", source)
        self.assertNotIn("'expense_subcategory': expense.expense_subcategory", source)


if __name__ == '__main__':
    unittest.main()
