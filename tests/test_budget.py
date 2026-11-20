import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tripshare.budget import CAUTION, OK, OVER, UNSET, evaluate  # noqa: E402


class BudgetTests(unittest.TestCase):
    def test_unset_budget_has_no_percent(self):
        for spent in (0, 50000):
            s = evaluate(0, spent)
            self.assertEqual((s.level, s.percent, s.bar_ratio), (UNSET, None, 0.0))
            self.assertTrue(s.is_unset)
            self.assertEqual(s.percent_text, "예산 미설정")

    def test_ok_below_80_percent(self):
        s = evaluate(1000, 799)
        self.assertEqual((s.level, s.remaining, s.percent), (OK, 201, 79.9))
        self.assertEqual(evaluate(1000, 0).level, OK)
        self.assertEqual(evaluate(1000, 0).percent_text, "0.0%")

    def test_caution_from_exactly_80_percent(self):
        self.assertEqual(evaluate(1000, 800).level, CAUTION)
        self.assertEqual(evaluate(1_200_000, 960_000).level, CAUTION)
        self.assertEqual(evaluate(1_200_000, 959_999).level, OK)

    def test_exactly_100_percent_is_caution_not_over(self):
        s = evaluate(1000, 1000)
        self.assertEqual((s.level, s.remaining, s.over_amount, s.bar_ratio), (CAUTION, 0, 0, 1.0))
        self.assertIn("모두 사용", s.message)

    def test_over_100_percent(self):
        s = evaluate(1000, 1001)
        self.assertEqual((s.level, s.remaining, s.over_amount, s.bar_ratio), (OVER, -1, 1, 1.0))
        self.assertIn("1원 초과", s.message)
        self.assertEqual(evaluate(1_200_000, 5_312_500).over_amount, 4_112_500)

    def test_percent_uses_integer_math(self):
        self.assertEqual(evaluate(3, 1).percent, 33.3)
        self.assertEqual(evaluate(10_000_000_000, 9_999_999_999).percent, 99.9)


if __name__ == "__main__":
    unittest.main()
