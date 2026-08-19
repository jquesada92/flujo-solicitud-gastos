import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class PendingActionDelegationContractTests(unittest.TestCase):
    def test_my_actions_exposes_request_scoped_closure_delegation_capability(self):
        source = (REPO_ROOT / 'backend' / 'app' / 'api' / 'my_actions.py').read_text(encoding='utf-8')
        self.assertIn('from app.services.closure_service import can_delegate_closure', source)
        self.assertIn("'can_delegate_close': can_delegate_closure(expense, user)", source)
        self.assertIn("'request': _request_payload(expense, user)", source)


if __name__ == '__main__':
    unittest.main()
