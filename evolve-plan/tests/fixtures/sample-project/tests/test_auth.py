import unittest

from src.auth import authenticate


class AuthenticationTests(unittest.TestCase):
    def test_valid_password_authenticates(self) -> None:
        self.assertTrue(authenticate("demo", "correct-horse"))


if __name__ == "__main__":
    unittest.main()
