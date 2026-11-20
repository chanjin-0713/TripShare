import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tripshare.models import (  # noqa: E402
    CATEGORIES, Expense, MAX_PARTICIPANTS, Trip, ValidationError, demo_trip, load_trip,
    parse_amount, save_trip,
)


class ParticipantTests(unittest.TestCase):
    def test_add_and_trim(self):
        t = Trip()
        self.assertEqual(t.add_participant("  가상  민수 "), "가상 민수")

    def test_empty_and_too_long(self):
        t = Trip()
        with self.assertRaises(ValidationError):
            t.add_participant("   ")
        with self.assertRaises(ValidationError):
            t.add_participant("가" * 13)

    def test_duplicate_case_insensitive(self):
        t = Trip()
        t.add_participant("Tom")
        with self.assertRaises(ValidationError):
            t.add_participant("tom")

    def test_max_ten(self):
        t = Trip()
        for i in range(MAX_PARTICIPANTS):
            t.add_participant(f"가상{i}")
        with self.assertRaises(ValidationError):
            t.add_participant("초과")

    def test_remove_min_two(self):
        t = Trip(participants=["가", "나"])
        with self.assertRaises(ValidationError):
            t.remove_participant("가")
        t.add_participant("다")
        t.remove_participant("가")
        self.assertEqual(t.participants, ["나", "다"])

    def test_remove_blocked_by_expense(self):
        t = Trip(participants=["가", "나", "다"],
                 expenses=[Expense("식사", 30000, "가", ["가", "나"])])
        with self.assertRaises(ValidationError):
            t.remove_participant("가")   # 결제자
        with self.assertRaises(ValidationError):
            t.remove_participant("나")   # 분담자
        t.remove_participant("다")       # 연결 없음 -> 삭제 가능 (3->2명)

    def test_rename_updates_expenses(self):
        t = Trip(participants=["가", "나"], expenses=[Expense("택시", 1000, "가", ["가", "나"])])
        t.rename_participant("가", "다")
        self.assertEqual(t.expenses[0].payer, "다")
        self.assertEqual(t.expenses[0].participants, ["다", "나"])
        with self.assertRaises(ValidationError):
            t.rename_participant("다", "나")
        t.rename_participant("다", "다")  # 자기 자신으로의 변경은 허용


class ExpenseTests(unittest.TestCase):
    def setUp(self):
        self.t = Trip(name="테스트", budget=100000, participants=["가", "나", "다"])

    def test_add_valid(self):
        e = self.t.add_expense("  점심  식사 ", "35,000", "가", "식비")
        self.assertEqual((e.title, e.amount, e.payer, e.category), ("점심 식사", 35000, "가", "식비"))
        self.assertEqual(self.t.total_spent, 35000)

    def test_amount_rules(self):
        for bad in ("0", "-100", "1.5", "", "abc", "10000000001"):
            with self.assertRaises(ValidationError, msg=bad):
                self.t.add_expense("x", bad, "가", "식비")
        for bad in (0, -1, True, 1.5):
            with self.assertRaises(ValidationError, msg=str(bad)):
                self.t.add_expense("x", bad, "가", "식비")
        self.t.add_expense("x", "1", "가", "식비")  # 1원은 허용
        self.assertEqual(len(self.t.expenses), 1)

    def test_title_payer_category_rules(self):
        with self.assertRaises(ValidationError):
            self.t.add_expense("  ", 1000, "가", "식비")
        with self.assertRaises(ValidationError):
            self.t.add_expense("가" * 31, 1000, "가", "식비")
        with self.assertRaises(ValidationError):
            self.t.add_expense("x", 1000, "없는사람", "식비")
        with self.assertRaises(ValidationError):
            self.t.add_expense("x", 1000, "가", "없는카테고리")
        self.assertEqual(self.t.expenses, [])

    def test_all_six_categories(self):
        self.assertEqual(CATEGORIES, ["숙박비", "식비", "교통비", "관광 및 입장료", "쇼핑", "기타"])
        for c in CATEGORIES:
            self.t.add_expense("x", 1000, "나", c)
        self.assertEqual(len(self.t.expenses), 6)

    def test_update_and_failed_update_keeps_original(self):
        self.t.add_expense("택시", 10000, "가", "교통비")
        self.t.update_expense(0, "버스", "2,500", "나", "교통비")
        e = self.t.expenses[0]
        self.assertEqual((e.title, e.amount, e.payer), ("버스", 2500, "나"))
        with self.assertRaises(ValidationError):
            self.t.update_expense(0, "망함", "0", "다", "기타")
        self.assertEqual((e.title, e.amount, e.payer), ("버스", 2500, "나"))
        with self.assertRaises(ValidationError):
            self.t.update_expense(5, "x", 1000, "가", "기타")

    def test_remove(self):
        self.t.add_expense("a", 1000, "가", "기타")
        self.t.add_expense("b", 2000, "나", "기타")
        self.assertEqual(self.t.remove_expense(0).title, "a")
        self.assertEqual([e.title for e in self.t.expenses], ["b"])
        with self.assertRaises(ValidationError):
            self.t.remove_expense(3)

    def test_payer_cannot_be_removed_but_unrelated_can(self):
        self.t.add_expense("a", 1000, "가", "기타")
        with self.assertRaises(ValidationError):
            self.t.remove_participant("가")
        self.t.remove_participant("다")

    def test_persistence_with_category_and_old_files(self):
        self.t.add_expense("호텔", 90000, "나", "숙박비")
        again = Trip.from_dict(self.t.to_dict())
        self.assertEqual(again.expenses[0].category, "숙박비")
        old = {"name": "옛", "participants": ["가", "나"],
               "expenses": [{"title": "t", "amount": 5, "payer": "가", "participants": []}]}
        self.assertEqual(Trip.from_dict(old).expenses[0].category, "기타")
        bad = dict(old, expenses=[{"title": "t", "amount": 0, "payer": "가"}])
        with self.assertRaises(ValidationError):
            Trip.from_dict(bad)

    def test_demo_has_expenses(self):
        d = demo_trip()
        self.assertTrue(d.expenses and d.total_spent <= d.budget)


class BasicInfoTests(unittest.TestCase):
    def test_parse_amount(self):
        self.assertEqual(parse_amount("1,200,000원"), 1200000)
        self.assertEqual(parse_amount(" 0 "), 0)
        for bad in ("", "-5", "1.5", "abc", "１２"):
            with self.assertRaises(ValidationError, msg=bad):
                parse_amount(bad)

    def test_set_basic_info_atomic(self):
        t = Trip(name="원래", budget=5)
        with self.assertRaises(ValidationError):
            t.set_basic_info("새이름", "잘못")
        self.assertEqual((t.name, t.budget), ("원래", 5))
        t.set_basic_info(" 부산  여행 ", "300,000")
        self.assertEqual((t.name, t.budget), ("부산 여행", 300000))

    def test_budget_limits(self):
        with self.assertRaises(ValidationError):
            Trip.validate_budget("99999999999999")
        with self.assertRaises(ValidationError):
            Trip.validate_trip_name("")
        with self.assertRaises(ValidationError):
            Trip.validate_trip_name("가" * 31)

    def test_setup_problems(self):
        self.assertEqual(len(Trip().setup_problems()), 2)
        self.assertEqual(demo_trip().setup_problems(), [])


class PersistenceTests(unittest.TestCase):
    def test_roundtrip_including_blank_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sub" / "trip.json"
            trip = demo_trip()
            trip.expenses.append(Expense("숙소", 100000, "가상민수", ["가상민수", "가상지은"]))
            save_trip(trip, p)
            self.assertEqual(load_trip(p).to_dict(), trip.to_dict())
            save_trip(Trip(), p)
            self.assertEqual(load_trip(p).name, "")

    def test_corrupt_and_missing(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "trip.json"
            with self.assertRaises(FileNotFoundError):
                load_trip(p)
            p.write_text("{깨진", encoding="utf-8")
            with self.assertRaises(ValidationError):
                load_trip(p)
            for bad in ([], {"name": 5}, {"name": "a", "budget": -1},
                        {"name": "a", "participants": ["x", "x"]},
                        {"name": "a", "participants": ["x"],
                         "expenses": [{"amount": 1, "payer": "없음", "participants": []}]}):
                p.write_text(json.dumps(bad), encoding="utf-8")
                with self.assertRaises(ValidationError, msg=str(bad)):
                    load_trip(p)


if __name__ == "__main__":
    unittest.main()
