import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class ContainerPortabilityTests(unittest.TestCase):
    def test_shell_scripts_are_forced_to_lf_by_git(self):
        attributes = (REPO_ROOT / '.gitattributes').read_text(encoding='utf-8')
        self.assertIn('*.sh text eol=lf', attributes)

    def test_backend_image_normalizes_windows_crlf(self):
        dockerfile = (REPO_ROOT / 'backend' / 'Dockerfile').read_text(encoding='utf-8')
        self.assertIn("sed -i 's/\\r$//'", dockerfile)
        self.assertIn('chmod +x /app/scripts/*.sh', dockerfile)

    def test_compose_waits_for_backend_health_before_frontend(self):
        compose = (REPO_ROOT / 'docker-compose.yml').read_text(encoding='utf-8')
        self.assertIn('condition: service_healthy', compose)
        self.assertIn('/api/health', compose)

    def test_compose_email_links_use_reachable_frontend_port(self):
        compose = (REPO_ROOT / 'docker-compose.yml').read_text(encoding='utf-8')
        root_env_example = (REPO_ROOT / '.env.example').read_text(encoding='utf-8')

        self.assertIn('127.0.0.1:3000:80', compose)
        self.assertIn('PUBLIC_URL: ${LOCAL_PUBLIC_URL:-http://localhost:3000}', compose)
        self.assertIn('LOCAL_PUBLIC_URL=http://localhost:3000', root_env_example)
        self.assertIn(
            'LOCAL_CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173',
            root_env_example,
        )


if __name__ == '__main__':
    unittest.main()
