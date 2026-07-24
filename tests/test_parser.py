import unittest

from parser import parse_transaction


class ParserTests(unittest.TestCase):
    def test_parses_expense_message(self) -> None:
        self.assertEqual(parse_transaction("кофе 1000"), (1000.0, "кофе", "expense"))

    def test_parses_income_message_with_plus_sign(self) -> None:
        self.assertEqual(parse_transaction("+150000 зарплата"), (150000.0, "зарплата", "income"))

    def test_parses_income_message_with_keyword(self) -> None:
        self.assertEqual(parse_transaction("доход 25000 премия"), (25000.0, "премия", "income"))


if __name__ == "__main__":
    unittest.main()
