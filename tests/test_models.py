import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tripshare.models import (  # noqa: E402
    Expense, MAX_PARTICIPANTS, Trip, ValidationError, demo_trip, load_trip,
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
