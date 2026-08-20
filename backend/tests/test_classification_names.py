import unittest

from app.schemas.area import CategoryCreate


class ClassificationNameTests(unittest.TestCase):
    def test_category_name_allows_slash_separator(self):
        payload = CategoryCreate(name='Servicios/Consultoría')
        self.assertEqual(payload.name, 'Servicios / Consultoría')

    def test_category_name_normalizes_spaces_around_slash(self):
        payload = CategoryCreate(name='Servicios   /   Consultoría')
        self.assertEqual(payload.name, 'Servicios / Consultoría')


if __name__ == '__main__':
    unittest.main()
