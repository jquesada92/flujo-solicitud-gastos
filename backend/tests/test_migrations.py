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

        self.assertEqual(script.get_heads(), ['20260817_0003'])
        revisions = {revision.revision: revision.down_revision for revision in script.walk_revisions()}
        self.assertEqual(revisions['20260817_0003'], '20260817_0002')
        self.assertEqual(revisions['20260817_0002'], '20260817_0001')
        self.assertEqual(revisions['20260817_0001'], '20260817_0000')
        self.assertIsNone(revisions['20260817_0000'])


if __name__ == '__main__':
    unittest.main()
