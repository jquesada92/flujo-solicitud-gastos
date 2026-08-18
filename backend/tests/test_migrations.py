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

        self.assertEqual(script.get_heads(), ['20260818_0004'])
        revisions = {revision.revision: revision.down_revision for revision in script.walk_revisions()}
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
        self.assertIn('Runtime authorization does not read legacy profile names', migration)


if __name__ == '__main__':
    unittest.main()
