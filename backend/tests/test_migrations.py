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

        self.assertEqual(script.get_heads(), ['20260818_0005'])
        revisions = {revision.revision: revision.down_revision for revision in script.walk_revisions()}
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


if __name__ == '__main__':
    unittest.main()
