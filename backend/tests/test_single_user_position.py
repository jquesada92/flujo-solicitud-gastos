import os
import unittest

from pydantic import ValidationError

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('SECRET_KEY', 'unit-test-secret-key-at-least-32-characters')
os.environ.setdefault('ANALYTICS_HASH_KEY', 'unit-test-analytics-key-at-least-32-characters')
os.environ.setdefault('ENVIRONMENT', 'test')

from app.models.iam import UserPosition
from app.schemas.iam_user import IamUserCreate, IamUserUpdate


class SingleUserPositionTests(unittest.TestCase):
    def test_create_rejects_more_than_one_cargo(self):
        with self.assertRaises(ValidationError):
            IamUserCreate(
                identity_document='TEST-001',
                first_name='Ana',
                last_name='Pérez',
                email='ana@example.com',
                position_ids=[1, 2],
            )

    def test_update_rejects_more_than_one_cargo(self):
        with self.assertRaises(ValidationError):
            IamUserUpdate(position_ids=[1, 2])

    def test_database_model_has_unique_user_position_constraint(self):
        constraint_names = {
            constraint.name
            for constraint in UserPosition.__table__.constraints
            if constraint.name
        }
        self.assertIn('uq_user_position_user', constraint_names)
        self.assertNotIn('uq_user_position', constraint_names)


if __name__ == '__main__':
    unittest.main()
