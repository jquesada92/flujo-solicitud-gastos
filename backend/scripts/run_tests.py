"""Run the backend suite with a deterministic, local-only environment.

The normal Settings class loads ``backend/.env``. Development machines may
point that file at PostgreSQL or an external service, so invoking unittest
discovery directly is not an isolated test command. This runner disables the
dotenv source before application modules are imported and supplies safe SQLite
and console-email values for the whole process.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
TEST_ENVIRONMENT = {
    'ENVIRONMENT': 'development',
    'RENDER': 'false',
    'DATABASE_URL': 'sqlite+pysqlite:///:memory:',
    'DATABASE_SCHEMA': 'administracion',
    'SECRET_KEY': 'unit-test-secret-key-at-least-32-characters',
    'ANALYTICS_HASH_KEY': 'unit-test-analytics-key-different-32-chars',
    'PUBLIC_URL': 'http://localhost:5173',
    'CORS_ALLOWED_ORIGINS': 'http://localhost:3000,http://localhost:5173',
    'EMAIL_MODE': 'console',
    'EMAIL_FROM': 'noreply@example.test',
    'BREVO_API_KEY': '',
    'SMTP_USER': '',
    'SMTP_PASSWORD': '',
    'ADMIN_EMAIL': 'admin.test@example.test',
    'ADMIN_PASSWORD': 'unit-test-admin-password-only',
}


def configure_isolated_environment() -> None:
    os.environ.update(TEST_ENVIRONMENT)

    # Importing this module does not instantiate Settings. Mutating the model
    # configuration here prevents get_settings() from reading backend/.env when
    # application modules are imported later by unittest discovery.
    from app.core.config import Settings

    Settings.model_config['env_file'] = None


def main() -> int:
    os.chdir(BACKEND_ROOT)
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    configure_isolated_environment()

    suite = unittest.defaultTestLoader.discover(str(BACKEND_ROOT / 'tests'))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
