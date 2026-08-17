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


if __name__ == '__main__':
    unittest.main()
