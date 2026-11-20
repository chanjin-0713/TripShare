import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tripshare.models import CATEGORIES, Trip, demo_trip  # noqa: E402
from tripshare.stats import compute  # noqa: E402


def trip_with(*items):
    t = Trip(name="t", participants=["가", "나", "다"])
    for title, amount, payer, cat in items:
        t.add_expense(title, amount, payer, cat)
    return t


class StatsTests(unittest.TestCase):
    def test_example(self):
        s = compute(trip_with(("호텔", 180000, "가", "숙박비"), ("저녁", 90000, "나", "식비"),
                              ("버스", 30000, "다", "교통비")))
        self.assertEqual((s.total, s.expense_count), (300000, 3))
        self.assertEqual([(p.name, p.amount, p.count) for p in s.payers],
                         [("가", 180000, 1), ("나", 90000, 1), ("다", 30000, 1)])
        by = {c.category: c for c in s.categories}
        self.assertEqual((by["숙박비"].amount, by["숙박비"].share_text), (180000, "60.0%"))
        self.assertEqual((by["식비"].amount, by["식비"].share_text), (90000, "30.0%"))
        self.assertEqual(by["교통비"].share_text, "10.0%")
        self.assertEqual((by["쇼핑"].amount, by["쇼핑"].share_text), (0, "0.0%"))

    def test_all_categories_listed_in_order(self):
        s = compute(Trip(participants=["가", "나"]))
        self.assertEqual([c.category for c in s.categories], CATEGORIES)
        self.assertEqual(s.total, 0)
        self.assertTrue(all(c.share_tenths == 0 for c in s.categories))

    def test_same_payer_and_category_accumulate(self):
        s = compute(trip_with(("a", 1000, "가", "식비"), ("b", 2500, "가", "식비")))
        self.assertEqual((s.payers[0].amount, s.payers[0].count), (3500, 2))
        self.assertEqual([c for c in s.categories if c.category == "식비"][0].count, 2)

    def test_shares_sum_to_exactly_100(self):
        s = compute(trip_with(("a", 1, "가", "식비"), ("b", 1, "나", "쇼핑"), ("c", 1, "다", "기타")))
        self.assertEqual(sum(c.share_tenths for c in s.categories), 1000)  # 33.3+33.3+33.3 이 아니라 100.0
        rnd = random.Random(7)
        for _ in range(300):
            t = trip_with(*[(f"e{i}", rnd.randint(1, 999999), rnd.choice("가나다"), rnd.choice(CATEGORIES))
                            for i in range(rnd.randint(1, 12))])
            s = compute(t)
            self.assertEqual(sum(c.share_tenths for c in s.categories), 1000)
            self.assertEqual(sum(c.amount for c in s.categories), s.total)
            self.assertEqual(sum(p.amount for p in s.payers), s.total)

    def test_demo(self):
        s = compute(demo_trip())
        self.assertEqual(s.total, 654500)


if __name__ == "__main__":
    unittest.main()
