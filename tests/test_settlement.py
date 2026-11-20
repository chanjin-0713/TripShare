import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tripshare.models import CATEGORIES, Trip, ValidationError, demo_trip  # noqa: E402
from tripshare.settlement import Transfer, calculate  # noqa: E402


def make_trip(names, expenses):
    t = Trip(name="t", participants=list(names))
    for title, amount, payer in expenses:
        t.add_expense(title, amount, payer, "기타")
    return t


class SpecExampleTests(unittest.TestCase):
    """요구사항 문서의 예시와 정확히 일치해야 한다."""

    def setUp(self):
        self.s = calculate(make_trip(
            ["민수", "지연", "현우"],
            [("숙박비", 180000, "민수"), ("식비", 90000, "지연"), ("교통비", 30000, "현우")]))

    def test_totals(self):
        self.assertEqual(self.s.total, 300000)
        self.assertEqual(self.s.base_share, 100000)
        self.assertEqual(self.s.remainder, 0)

    def test_balances(self):
        got = {b.name: (b.paid, b.share, b.diff) for b in self.s.balances}
        self.assertEqual(got, {"민수": (180000, 100000, 80000),
                               "지연": (90000, 100000, -10000),
                               "현우": (30000, 100000, -70000)})
        self.assertEqual([b.status for b in self.s.balances], ["받을 돈", "보낼 돈", "보낼 돈"])

    def test_transfers(self):
        self.assertEqual(self.s.transfers, [Transfer("지연", "민수", 10000), Transfer("현우", "민수", 70000)])
        self.assertEqual(self.s.transfers[0].sentence(), "지연님이 민수님에게 10,000원을 보내세요.")


class EdgeCaseTests(unittest.TestCase):
    def test_remainder_is_exact(self):
        s = calculate(make_trip(["가", "나", "다"], [("a", 100000, "가")]))
        self.assertEqual((s.base_share, s.remainder), (33333, 1))
        self.assertEqual([b.share for b in s.balances], [33334, 33333, 33333])
        self.assertEqual(sum(b.share for b in s.balances), 100000)
        self.assertEqual(sum(b.diff for b in s.balances), 0)

    def test_no_expenses(self):
        s = calculate(make_trip(["가", "나"], []))
        self.assertEqual((s.total, s.transfers), (0, []))
        self.assertTrue(all(b.status == "정산 완료" for b in s.balances))

    def test_already_even(self):
        s = calculate(make_trip(["가", "나"], [("a", 1000, "가"), ("b", 1000, "나")]))
        self.assertEqual(s.transfers, [])

    def test_one_person_paid_everything(self):
        s = calculate(make_trip(["가", "나", "다", "라"], [("a", 40000, "가")]))
        self.assertEqual(s.transfers, [Transfer("나", "가", 10000), Transfer("다", "가", 10000),
                                       Transfer("라", "가", 10000)])

    def test_needs_two_participants(self):
        with self.assertRaises(ValidationError):
            calculate(Trip(participants=["가"]))

    def test_demo_data(self):
        s = calculate(demo_trip())
        self.assertEqual(s.total, 654500)
        self.assertEqual(sum(b.diff for b in s.balances), 0)


class PropertyTests(unittest.TestCase):
    def test_random_trips_settle_exactly(self):
        rnd = random.Random(2024)
        for _ in range(500):
            n = rnd.randint(2, 10)
            names = [f"p{i}" for i in range(n)]
            t = make_trip(names, [(f"e{k}", rnd.randint(1, 500000), rnd.choice(names))
                                  for k in range(rnd.randint(0, 15))])
            s = calculate(t)
            self.assertEqual(sum(b.share for b in s.balances), s.total)
            self.assertEqual(sum(b.diff for b in s.balances), 0)
            self.assertLessEqual(max(b.share for b in s.balances) - min(b.share for b in s.balances), 1)
            self.assertLessEqual(len(s.transfers), n - 1)
            net = {b.name: b.diff for b in s.balances}
            for tr in s.transfers:
                self.assertGreater(tr.amount, 0)
                self.assertNotEqual(tr.sender, tr.receiver)
                net[tr.sender] += tr.amount
                net[tr.receiver] -= tr.amount
            self.assertTrue(all(v == 0 for v in net.values()), net)  # 송금 후 모두 0원


if __name__ == "__main__":
    unittest.main()
