from __future__ import annotations

import unittest

from main import slugify


class CliTests(unittest.TestCase):
    def test_slugify_handles_accents(self) -> None:
        self.assertEqual(slugify("Côte de Beauté"), "cote-de-beaute")
        self.assertEqual(slugify("Île de Ré"), "ile-de-re")


if __name__ == "__main__":
    unittest.main()
