import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class HomeDashboardPersonalTests(unittest.TestCase):
    def test_request_metrics_are_scoped_to_logged_in_requester(self):
        source = (REPO_ROOT / 'backend' / 'app' / 'api' / 'dashboard.py').read_text(encoding='utf-8')
        self.assertIn("requester_filter = func.lower(Expense.requested_by) == user.email.lower()", source)
        self.assertGreaterEqual(source.count('requester_filter,'), 4)
        self.assertIn('Personal Home dashboard', source)

    def test_pending_actions_still_use_user_assignment_resolver(self):
        source = (REPO_ROOT / 'backend' / 'app' / 'api' / 'dashboard.py').read_text(encoding='utf-8')
        self.assertIn('pending = pending_actions_by_expense(db, user)', source)
        self.assertIn("'pending_my_action': sum(len(actions) for actions in pending.values())", source)


if __name__ == '__main__':
    unittest.main()
