import unittest
from pathlib import Path

from app.models.entities import Expense
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

        dumped = payload.model_dump(mode='json')
        self.assertEqual(dumped['expense_area'], 'ADMINISTRATION')
        self.assertEqual(dumped['expense_category'], 'EQUIPMENT')
        self.assertNotIn('expense_type', dumped)
        self.assertNotIn('expense_subcategory', dumped)

    def test_legacy_input_is_temporarily_accepted_but_not_serialized(self):
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
        dumped = payload.model_dump(mode='json')
        self.assertIn('expense_area', dumped)
        self.assertIn('expense_category', dumped)
        self.assertNotIn('expense_type', dumped)
        self.assertNotIn('expense_subcategory', dumped)

    def test_response_models_expose_only_canonical_names(self):
        for model in (ExpenseOut, InvoiceOut):
            fields = model.model_fields
            self.assertIn('expense_area', fields)
            self.assertIn('expense_category', fields)
            self.assertNotIn('expense_type', fields)
            self.assertNotIn('expense_subcategory', fields)

    def test_orm_and_physical_column_names_are_canonical(self):
        self.assertIn('expense_area', Expense.__table__.columns)
        self.assertIn('expense_category', Expense.__table__.columns)
        self.assertNotIn('expense_type', Expense.__table__.columns)
        self.assertNotIn('expense_subcategory', Expense.__table__.columns)
        self.assertTrue(hasattr(Expense, 'expense_area'))
        self.assertTrue(hasattr(Expense, 'expense_category'))
        # Transitional query aliases are allowed internally while remaining
        # backend consumers move to the canonical names.
        self.assertTrue(hasattr(Expense, 'expense_type'))
        self.assertTrue(hasattr(Expense, 'expense_subcategory'))

    def test_frontend_sends_canonical_wire_payload(self):
        source = (REPO_ROOT / 'frontend' / 'src' / 'domain-normalization.js').read_text(encoding='utf-8')
        self.assertIn("normalized.expense_area = normalized.expense_type", source)
        self.assertIn("normalized.expense_category = normalized.expense_subcategory", source)
        self.assertIn('delete normalized.expense_type', source)
        self.assertIn('delete normalized.expense_subcategory', source)

    def test_pending_action_payload_uses_canonical_attributes(self):
        source = (REPO_ROOT / 'backend' / 'app' / 'api' / 'my_actions.py').read_text(encoding='utf-8')
        self.assertIn("'expense_area': expense.expense_area", source)
        self.assertIn("'expense_category': expense.expense_category", source)
        self.assertNotIn("'expense_type':", source)
        self.assertNotIn("'expense_subcategory':", source)

    def test_clean_baseline_creates_canonical_columns_directly(self):
        migration = (
            REPO_ROOT
            / 'backend'
            / 'alembic'
            / 'versions'
            / '20260820_0001_initial_schema.py'
        ).read_text(encoding='utf-8')
        self.assertIn("sa.Column('expense_area', sa.String(80), nullable=False, index=True)", migration)
        self.assertIn("sa.Column('expense_category', sa.String(80), nullable=True)", migration)
        self.assertNotIn("new_column_name='expense_area'", migration)
        self.assertNotIn("new_column_name='expense_category'", migration)
        self.assertIn('no legacy table migration, data copy, rename, backfill', migration)


if __name__ == '__main__':
    unittest.main()
