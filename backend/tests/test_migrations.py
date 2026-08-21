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

        self.assertEqual(script.get_heads(), ['20260821_0008'])
        revisions = {revision.revision: revision.down_revision for revision in script.walk_revisions()}
        self.assertEqual(revisions['20260821_0008'], '20260821_0007')
        self.assertEqual(revisions['20260821_0007'], '20260821_0006')
        self.assertEqual(revisions['20260821_0006'], '20260821_0005')
        self.assertEqual(revisions['20260821_0005'], '20260821_0004')
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
        self.assertIn('trg_group_role_user_cardinality', migration)
        self.assertIn('enforce_group_role_user_cardinality', migration)
        self.assertIn('Grouping this role would give a user multiple roles in the same group', migration)

    def test_activity_period_migration_backfills_and_guards_open_periods(self):
        backend_dir = Path(__file__).resolve().parents[1]
        migration = (
            backend_dir / 'alembic' / 'versions' / '20260821_0005_activity_periods.py'
        ).read_text(encoding='utf-8')

        self.assertIn("down_revision = '20260821_0004'", migration)
        for table in ('user_activity_periods', 'area_activity_periods', 'role_activity_periods', 'group_activity_periods'):
            self.assertIn(table, migration)
        self.assertIn('active_until IS NULL OR active_until >= active_from', migration)
        self.assertIn("postgresql_where=sa.text('active_until IS NULL')", migration)
        self.assertIn("CASE WHEN active THEN NULL ELSE created_at END", migration)

    def test_period_snapshot_migration_adds_json_and_backfills_relations(self):
        backend_dir = Path(__file__).resolve().parents[1]
        migration = (
            backend_dir / 'alembic' / 'versions' / '20260821_0006_period_snapshot_values.py'
        ).read_text(encoding='utf-8')
        self.assertIn("down_revision = '20260821_0005'", migration)
        self.assertIn("sa.Column('values', sa.JSON(), nullable=True)", migration)
        self.assertIn("'identity_document': row['identity_document']", migration)
        self.assertIn("'assigned_roles': [dict(item) for item in assigned]", migration)
        self.assertIn("'group': dict(group) if group else None", migration)

    def test_period_audit_migration_records_actor_time_and_changes(self):
        backend_dir = Path(__file__).resolve().parents[1]
        migration = (
            backend_dir / 'alembic' / 'versions' / '20260821_0007_period_audit_metadata.py'
        ).read_text(encoding='utf-8')
        self.assertIn("down_revision = '20260821_0006'", migration)
        for column in ('event_at', 'actor_user_id', 'actor_identifier', 'change_type', 'changed_fields', 'changes'):
            self.assertIn(column, migration)
        self.assertIn("actor_identifier='SYSTEM:MIGRATION_BACKFILL'", migration)

    def test_period_timestamps_are_timezone_aware(self):
        backend_dir = Path(__file__).resolve().parents[1]
        migration = (
            backend_dir / 'alembic' / 'versions' / '20260821_0008_normalize_period_timestamps.py'
        ).read_text(encoding='utf-8')
        self.assertIn("down_revision = '20260821_0007'", migration)
        self.assertIn("type_=sa.DateTime(timezone=True)", migration)
        self.assertIn("AT TIME ZONE \\'UTC\\'", migration)


if __name__ == '__main__':
    unittest.main()
