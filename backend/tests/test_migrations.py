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

        self.assertEqual(script.get_heads(), ['20260821_0004'])
        revisions = {revision.revision: revision.down_revision for revision in script.walk_revisions()}
        self.assertEqual(revisions['20260821_0004'], '20260821_0003')
        self.assertEqual(revisions['20260821_0003'], '20260820_0002')
        self.assertEqual(revisions['20260820_0002'], '20260820_0001')
        self.assertIsNone(revisions['20260820_0001'])

    def test_initial_schema_remains_clean_fresh_install_baseline(self):
        backend_dir = Path(__file__).resolve().parents[1]
        baseline = (
            backend_dir
            / 'alembic'
            / 'versions'
            / '20260820_0001_initial_schema.py'
        ).read_text(encoding='utf-8')

        self.assertIn("revision = '20260820_0001'", baseline)
        self.assertIn('down_revision = None', baseline)
        self.assertIn("existing_tables - {'alembic_version'}", baseline)
        self.assertIn('Fresh baseline requires an empty application schema', baseline)

    def test_group_scoped_role_migration_enforces_role_group_cardinality(self):
        backend_dir = Path(__file__).resolve().parents[1]
        migration = (
            backend_dir
            / 'alembic'
            / 'versions'
            / '20260820_0002_group_scoped_roles.py'
        ).read_text(encoding='utf-8')

        self.assertIn("revision = '20260820_0002'", migration)
        self.assertIn("down_revision = '20260820_0001'", migration)
        self.assertIn("create_unique_constraint('uq_group_role_role', ['role_id'])", migration)
        self.assertIn('trg_user_role_one_per_group', migration)
        self.assertIn("RAISE EXCEPTION 'A user can only have one role per group'", migration)
        self.assertIn('INSERT INTO', migration)
        self.assertIn('group_members', migration)
        self.assertIn('user_role_assignments', migration)

    def test_single_position_migration_enforces_one_cargo_per_user(self):
        backend_dir = Path(__file__).resolve().parents[1]
        migration = (
            backend_dir
            / 'alembic'
            / 'versions'
            / '20260821_0003_single_user_position.py'
        ).read_text(encoding='utf-8')

        self.assertIn("revision = '20260821_0003'", migration)
        self.assertIn("down_revision = '20260820_0002'", migration)
        self.assertIn("GROUP BY user_id", migration)
        self.assertIn("drop_constraint('uq_user_position'", migration)
        self.assertIn("create_unique_constraint('uq_user_position_user', ['user_id'])", migration)

    def test_global_role_migration_allows_ungrouped_roles_without_relaxing_group_guard(self):
        backend_dir = Path(__file__).resolve().parents[1]
        migration = (
            backend_dir
            / 'alembic'
            / 'versions'
            / '20260821_0004_allow_global_roles.py'
        ).read_text(encoding='utf-8')

        self.assertIn("revision = '20260821_0004'", migration)
        self.assertIn("down_revision = '20260821_0003'", migration)
        self.assertIn('IF target_group_id IS NULL THEN', migration)
        self.assertIn('RETURN NEW;', migration)
        self.assertIn("RAISE EXCEPTION 'A user can only have one role per group'", migration)
        self.assertIn('CREATE OR REPLACE FUNCTION', migration)


if __name__ == '__main__':
    unittest.main()
