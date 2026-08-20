import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class RequestCreatePermissionVisibilityTests(unittest.TestCase):
    def test_request_form_uses_effective_requests_create_permission(self):
        vite = (REPO_ROOT / 'frontend' / 'vite.config.js').read_text(encoding='utf-8')
        self.assertIn('canCreate = permissionCodes.includes("requests:create")', vite)
        self.assertIn('request creation capability', vite)

    def test_backend_create_endpoint_requires_requests_create(self):
        source = (REPO_ROOT / 'backend' / 'app' / 'api' / 'request_actions.py').read_text(encoding='utf-8')
        self.assertIn("user: User = Depends(require_permission('requests:create'))", source)

    def test_correction_form_remains_available_for_resource_authorized_revision(self):
        vite = (REPO_ROOT / 'frontend' / 'vite.config.js').read_text(encoding='utf-8')
        self.assertIn('{(canCreate || revision) && (', vite)


if __name__ == '__main__':
    unittest.main()
