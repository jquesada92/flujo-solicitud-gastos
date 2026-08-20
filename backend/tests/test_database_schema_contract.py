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

    def test_only_clean_initial_alembic_baseline_exists(self):
        revisions = sorted(path.name for path in VERSIONS_DIR.glob('*.py'))
        self.assertEqual(revisions, ['20260820_0001_initial_schema.py'])

        baseline = (VERSIONS_DIR / revisions[0]).read_text(encoding='utf-8')
        self.assertIn("revision = '20260820_0001'", baseline)
        self.assertIn('down_revision = None', baseline)
        self.assertIn("existing_tables - {'alembic_version'}", baseline)
        self.assertIn('Fresh baseline requires an empty application schema', baseline)

    def test_alembic_version_table_uses_application_schema(self):
        env_source = (REPO_ROOT / 'backend' / 'alembic' / 'env.py').read_text(encoding='utf-8')
        self.assertIn('version_table_schema=database_schema', env_source)
        self.assertIn("config.attributes['database_schema'] = database_schema", env_source)
        self.assertIn('CREATE SCHEMA IF NOT EXISTS', env_source)
        self.assertIn('SET search_path TO', env_source)

    def test_env_examples_declare_administracion(self):
        backend_env = (REPO_ROOT / 'backend' / '.env.example').read_text(encoding='utf-8')
        preview_env = (REPO_ROOT / 'backend' / '.env.preview.example').read_text(encoding='utf-8')
        self.assertIn('DATABASE_SCHEMA=administracion', backend_env)
        self.assertIn('DATABASE_SCHEMA=administracion', preview_env)
        self.assertIn('ph_torre_delta', backend_env)


if __name__ == '__main__':
    unittest.main()
