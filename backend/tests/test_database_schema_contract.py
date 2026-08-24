import os
import unittest
from pathlib import Path

from pydantic import ValidationError

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('SECRET_KEY', 'unit-test-secret-key-at-least-32-characters')
os.environ.setdefault('ANALYTICS_HASH_KEY', 'unit-test-analytics-key-at-least-32-characters')
os.environ.setdefault('ENVIRONMENT', 'test')
os.environ.setdefault('EMAIL_MODE', 'console')

from app.core.config import Settings


REPO_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_DIR = REPO_ROOT / 'backend' / 'alembic' / 'versions'


class DatabaseSchemaContractTests(unittest.TestCase):
    def test_application_schema_defaults_to_administracion(self):
        settings = Settings(database_url='sqlite://')
        self.assertEqual(settings.database_schema, 'administracion')

    def test_system_schemas_are_rejected(self):
        for schema in ('public', 'pg_catalog', 'pg_temp', 'information_schema'):
            with self.subTest(schema=schema):
                with self.assertRaises(ValidationError):
                    Settings(database_url='sqlite://', database_schema=schema)

    def test_invalid_schema_identifier_is_rejected(self):
        for schema in ('administracion;drop schema public', '123schema', 'admin schema', ''):
            with self.subTest(schema=schema):
                with self.assertRaises(ValidationError):
                    Settings(database_url='sqlite://', database_schema=schema)

    def test_clean_initial_baseline_is_preserved_and_forward_migrations_are_linear(self):
        revisions = sorted(path.name for path in VERSIONS_DIR.glob('*.py'))
        self.assertEqual(
            revisions,
            [
                '20260820_0001_initial_schema.py',
                '20260820_0002_group_scoped_roles.py',
                '20260821_0003_single_user_position.py',
                '20260821_0004_allow_global_roles.py',
                '20260821_0005_activity_periods.py',
                '20260821_0006_period_snapshot_values.py',
                '20260821_0007_period_audit_metadata.py',
                '20260821_0008_normalize_period_timestamps.py',
                '20260824_0009_group_permission_inheritance.py',
            ],
        )

        baseline = (VERSIONS_DIR / '20260820_0001_initial_schema.py').read_text(encoding='utf-8')
        self.assertIn("revision = '20260820_0001'", baseline)
        self.assertIn('down_revision = None', baseline)
        self.assertIn("existing_tables - {'alembic_version'}", baseline)
        self.assertIn('Fresh baseline requires an empty application schema', baseline)

        group_roles = (VERSIONS_DIR / '20260820_0002_group_scoped_roles.py').read_text(encoding='utf-8')
        self.assertIn("revision = '20260820_0002'", group_roles)
        self.assertIn("down_revision = '20260820_0001'", group_roles)

        single_position = (VERSIONS_DIR / '20260821_0003_single_user_position.py').read_text(encoding='utf-8')
        self.assertIn("revision = '20260821_0003'", single_position)

        activity_periods = (VERSIONS_DIR / '20260821_0005_activity_periods.py').read_text(encoding='utf-8')
        self.assertIn("revision = '20260821_0005'", activity_periods)
        self.assertIn("down_revision = '20260821_0004'", activity_periods)

        snapshots = (VERSIONS_DIR / '20260821_0006_period_snapshot_values.py').read_text(encoding='utf-8')
        self.assertIn("revision = '20260821_0006'", snapshots)
        self.assertIn("down_revision = '20260821_0005'", snapshots)

        audit_metadata = (VERSIONS_DIR / '20260821_0007_period_audit_metadata.py').read_text(encoding='utf-8')
        self.assertIn("revision = '20260821_0007'", audit_metadata)
        self.assertIn("down_revision = '20260821_0006'", audit_metadata)

        timestamps = (VERSIONS_DIR / '20260821_0008_normalize_period_timestamps.py').read_text(encoding='utf-8')
        self.assertIn("revision = '20260821_0008'", timestamps)
        self.assertIn("down_revision = '20260821_0007'", timestamps)
        group_permissions = (VERSIONS_DIR / '20260824_0009_group_permission_inheritance.py').read_text(encoding='utf-8')
        self.assertIn("revision = '20260824_0009'", group_permissions)
        self.assertIn("down_revision = '20260821_0008'", group_permissions)
        self.assertIn("down_revision = '20260820_0002'", single_position)

        global_roles = (VERSIONS_DIR / '20260821_0004_allow_global_roles.py').read_text(encoding='utf-8')
        self.assertIn("revision = '20260821_0004'", global_roles)
        self.assertIn("down_revision = '20260821_0003'", global_roles)

    def test_alembic_version_table_uses_application_schema(self):
        env_source = (REPO_ROOT / 'backend' / 'alembic' / 'env.py').read_text(encoding='utf-8')
        self.assertIn('version_table_schema=database_schema', env_source)
        self.assertIn("config.attributes['database_schema'] = database_schema", env_source)
        self.assertIn('CREATE SCHEMA IF NOT EXISTS', env_source)
        self.assertNotIn("connect_args['options']", env_source)
        self.assertNotIn("options': '-csearch_path=", env_source)

    def test_runtime_engine_is_compatible_with_neon_pooler(self):
        database_source = (REPO_ROOT / 'backend' / 'app' / 'core' / 'database.py').read_text(encoding='utf-8')
        self.assertIn('MetaData(schema=APPLICATION_SCHEMA)', database_source)
        self.assertNotIn("connect_args['options']", database_source)
        self.assertNotIn("options': '-csearch_path=", database_source)

    def test_display_id_counter_uses_schema_qualified_model_table(self):
        expenses_source = (REPO_ROOT / 'backend' / 'app' / 'api' / 'expenses.py').read_text(encoding='utf-8')
        self.assertIn('counter_table = AreaCounter.__table__.fullname', expenses_source)
        self.assertIn('INSERT INTO {counter_table}', expenses_source)

    def test_postgresql_enums_inherit_application_schema(self):
        entities_source = (REPO_ROOT / 'backend' / 'app' / 'models' / 'entities.py').read_text(encoding='utf-8')
        self.assertEqual(entities_source.count('inherit_schema=True'), 3)

    def test_alembic_schema_setup_commits_before_migration_transaction(self):
        env_source = (REPO_ROOT / 'backend' / 'alembic' / 'env.py').read_text(encoding='utf-8')
        create_schema_position = env_source.index('CREATE SCHEMA IF NOT EXISTS')
        setup_commit_position = env_source.index('connection.commit()', create_schema_position)
        configure_position = env_source.index('context.configure(', setup_commit_position)
        begin_position = env_source.index('with context.begin_transaction():', configure_position)

        self.assertLess(create_schema_position, setup_commit_position)
        self.assertLess(setup_commit_position, configure_position)
        self.assertLess(configure_position, begin_position)
        self.assertNotIn('SET search_path TO', env_source)

    def test_render_declares_application_schema_explicitly(self):
        render_source = (REPO_ROOT / 'render.yaml').read_text(encoding='utf-8')
        self.assertIn('- key: DATABASE_SCHEMA', render_source)
        self.assertIn('value: administracion', render_source)

    def test_default_compose_uses_local_postgres_service(self):
        compose_source = (REPO_ROOT / 'docker-compose.yml').read_text(encoding='utf-8')
        self.assertIn('image: postgres:16-alpine', compose_source)
        self.assertIn('postgres_data:/var/lib/postgresql/data', compose_source)
        self.assertIn('@db:5432/${POSTGRES_DB:-ph_torre_delta}', compose_source)
        self.assertIn('DATABASE_SCHEMA: ${DATABASE_SCHEMA:-administracion}', compose_source)
        self.assertIn('condition: service_healthy', compose_source)

    def test_env_examples_declare_administracion(self):
        backend_env = (REPO_ROOT / 'backend' / '.env.example').read_text(encoding='utf-8')
        preview_env = (REPO_ROOT / 'backend' / '.env.preview.example').read_text(encoding='utf-8')
        self.assertIn('DATABASE_SCHEMA=administracion', backend_env)
        self.assertIn('DATABASE_SCHEMA=administracion', preview_env)
        self.assertIn('ph_torre_delta', backend_env)


if __name__ == '__main__':
    unittest.main()
