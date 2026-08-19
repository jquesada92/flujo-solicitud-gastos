import unittest
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


class MigrationTopologyTests(unittest.TestCase):
    def test_alembic_has_single_head_and_expected_chain(self):
        backend_dir = Path(__file__).resolve().parents[1]
        config = Config(str(backend_dir / 'alembic.ini'))
        config.set_main_option('script_location', str(backend_dir / 'alembic'))
        script = ScriptDirectory.from_config(config)

        self.assertEqual(script.get_heads(), ['20260819_0008'])
        revisions = {revision.revision: revision.down_revision for revision in script.walk_revisions()}
        self.assertEqual(revisions['20260819_0008'], '20260819_0007')
        self.assertEqual(revisions['20260819_0007'], '20260818_0006')
        self.assertEqual(revisions['20260818_0006'], '20260818_0005')
        self.assertEqual(revisions['20260818_0005'], '20260818_0004')
        self.assertEqual(revisions['20260818_0004'], '20260817_0003')
        self.assertEqual(revisions['20260817_0003'], '20260817_0002')
        self.assertEqual(revisions['20260817_0002'], '20260817_0001')
        self.assertEqual(revisions['20260817_0001'], '20260817_0000')
        self.assertIsNone(revisions['20260817_0000'])

    def test_position_role_migration_contains_legacy_compatibility_import(self):
        backend_dir = Path(__file__).resolve().parents[1]
        migration = (
            backend_dir
            / 'alembic'
            / 'versions'
            / '20260818_0004_position_role_inheritance.py'
        ).read_text(encoding='utf-8')

        self.assertIn("'position_roles'", migration)
        self.assertIn('access_profiles', migration)
        self.assertIn("('can_approve', 'requests:approve')", migration)
        self.assertIn('user_positions', migration)
        self.assertIn('authorization does not read legacy profile names', migration)

    def test_closure_delegation_migration_is_auditable_and_single_active(self):
        backend_dir = Path(__file__).resolve().parents[1]
        migration = (
            backend_dir
            / 'alembic'
            / 'versions'
            / '20260818_0005_closure_delegation.py'
        ).read_text(encoding='utf-8')

        self.assertIn('expense_closure_delegations', migration)
        self.assertIn('delegate_user_id', migration)
        self.assertIn('delegated_by_user_id', migration)
        self.assertIn('revoked_at', migration)
        self.assertIn('uq_expense_closure_delegation_active', migration)
        self.assertIn('revoked_at IS NULL', migration)
        self.assertIn("WHERE code = 'requests:close'", migration)
        self.assertIn("SET active = FALSE", migration)
        self.assertIn('Retirado como autoridad runtime', migration)

    def test_area_management_migration_separates_technical_configuration(self):
        backend_dir = Path(__file__).resolve().parents[1]
        migration = (
            backend_dir
            / 'alembic'
            / 'versions'
            / '20260818_0006_area_management_permission.py'
        ).read_text(encoding='utf-8')

        self.assertIn("'areas:manage'", migration)
        self.assertIn("'area-manager'", migration)
        self.assertIn("'Gestor de áreas'", migration)
        self.assertIn('system_accounts', migration)
        self.assertIn('intentionally NOT assigned to any', migration)
        self.assertNotIn("'JUNTA_DIRECTIVA'", migration)
        self.assertNotIn("'ADMINISTRACION'", migration)

    def test_configuration_read_migration_is_database_driven_and_read_only(self):
        backend_dir = Path(__file__).resolve().parents[1]
        migration = (
            backend_dir
            / 'alembic'
            / 'versions'
            / '20260819_0007_configuration_read_access.py'
        ).read_text(encoding='utf-8')

        self.assertIn("'config:read'", migration)
        self.assertIn("'configuration-viewer'", migration)
        self.assertIn("'Visor de configuración'", migration)
        self.assertIn("'requests:approve'", migration)
        self.assertIn('user_role_assignments', migration)
        self.assertIn('position_roles', migration)
        self.assertIn('group_roles', migration)
        self.assertIn('structural bootstrap', migration)
        self.assertIn('bootstrap only', migration)
        for organizational_name in ('PRESIDENTE', 'VICEPRESIDENTE', 'TESORERO', 'VOCERO'):
            self.assertNotIn(organizational_name, migration)

    def test_expense_area_category_migration_renames_without_rewriting_data(self):
        backend_dir = Path(__file__).resolve().parents[1]
        migration = (
            backend_dir
            / 'alembic'
            / 'versions'
            / '20260819_0008_expense_area_category_columns.py'
        ).read_text(encoding='utf-8')

        self.assertIn("revision = '20260819_0008'", migration)
        self.assertIn("down_revision = '20260819_0007'", migration)
        self.assertIn("op.alter_column('expenses', 'expense_type', new_column_name='expense_area')", migration)
        self.assertIn("op.alter_column('expenses', 'expense_subcategory', new_column_name='expense_category')", migration)
        self.assertIn('ix_expenses_expense_area', migration)
        self.assertIn("op.alter_column('expenses', 'expense_category', new_column_name='expense_subcategory')", migration)
        self.assertIn("op.alter_column('expenses', 'expense_area', new_column_name='expense_type')", migration)


if __name__ == '__main__':
    unittest.main()
