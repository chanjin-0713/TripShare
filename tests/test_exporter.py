import csv
import io
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tripshare import exporter  # noqa: E402
from tripshare.models import Trip, ValidationError, demo_trip  # noqa: E402

NOW = datetime(2026, 11, 20, 10, 30)


def spec_trip():
    t = Trip(name="제주 예시", budget=400000, participants=["민수", "지연", "현우"])
    t.add_expense("숙소", 180000, "민수", "숙박비")
    t.add_expense("저녁", 90000, "지연", "식비")
    t.add_expense("버스", 30000, "현우", "교통비")
    return t


def read_csv_sections(path):
    text = Path(path).read_bytes().decode("utf-8-sig")
    sections, cur = {}, None
    for row in csv.reader(io.StringIO(text, newline="")):
        if not row:
            cur = None
        elif cur is None:
            cur = sections.setdefault(row[0], [])
        else:
            cur.append(row)
    return sections


class TxtTests(unittest.TestCase):
    def test_contains_all_required_items(self):
        txt = exporter.build_txt(spec_trip(), NOW)
        for needle in ("제주 예시", "민수, 지연, 현우", "전체 여행 경비 : 300,000원", "여행 예산      : 400,000원",
                       "남은 예산 100,000원", "1인당 부담액   : 100,000원",
                       "180,000원", "+80,000원", "-70,000원",
                       "1. 지연님이 민수님에게 10,000원을 보내세요.",
                       "2. 현우님이 민수님에게 70,000원을 보내세요.",
                       "[지출 내역]", "2026-11-20 10:30"):
            self.assertIn(needle, txt)

    def test_columns_aligned(self):
        lines = exporter.build_txt(spec_trip(), NOW).splitlines()
        rows = [l for l in lines if l.startswith(("민수", "지연", "현우"))]
        widths = {exporter._width(r) for r in rows}
        self.assertEqual(len(widths), 1, rows)  # 전각 문자 폭까지 맞춰 모든 행의 표시 폭이 같다

    def test_budget_unset_over_and_remainder(self):
        t = spec_trip()
        t.budget = 0
        self.assertIn("예산 미설정", exporter.build_txt(t, NOW))
        t.budget = 100000
        self.assertIn("200,000원 초과", exporter.build_txt(t, NOW))
        t.add_expense("x", 1, "민수", "기타")
        self.assertIn("나누어떨어지지 않는 1원", exporter.build_txt(t, NOW))

    def test_no_expenses_and_too_few_participants(self):
        txt = exporter.build_txt(Trip(name="빈", participants=["가", "나"]), NOW)
        self.assertIn("등록된 지출이 없어", txt)
        with self.assertRaises(ValidationError):
            exporter.build_txt(Trip(name="x", participants=["가"]), NOW)


class CsvTests(unittest.TestCase):
    def test_sections_are_separated(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.csv"
            exporter.save_csv(spec_trip(), p)
            self.assertEqual(p.read_bytes()[:3], b"\xef\xbb\xbf")  # UTF-8 BOM
            s = read_csv_sections(p)
            self.assertEqual(list(s), ["[여행 정보]", "[지출 내역]", "[참가자별 정산]", "[송금 결과]"])
            self.assertEqual(s["[지출 내역]"][0], ["번호", "항목", "카테고리", "결제한 사람", "금액(원)"])
            self.assertEqual(s["[지출 내역]"][1:], [["1", "숙소", "숙박비", "민수", "180000"],
                                                  ["2", "저녁", "식비", "지연", "90000"],
                                                  ["3", "버스", "교통비", "현우", "30000"]])
            self.assertEqual(s["[참가자별 정산]"][1], ["민수", "180000", "100000", "80000", "받을 돈"])
            self.assertEqual(s["[송금 결과]"][1:], [["1", "지연", "민수", "10000"], ["2", "현우", "민수", "70000"]])
            info = dict(s["[여행 정보]"][1:])
            self.assertEqual((info["여행 이름"], info["전체 여행 경비(원)"], info["여행 예산(원)"]),
                             ("제주 예시", "300000", "400000"))

    def test_korean_survives_roundtrip_and_crlf(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "k.csv"
            exporter.save_csv(demo_trip(), p)
            raw = p.read_bytes()
            self.assertIn("가상민수".encode("utf-8"), raw)
            self.assertNotIn(b"\r\r\n", raw)

    def test_formula_injection_is_neutralized(self):
        t = Trip(name="t", participants=["가", "나"])
        t.add_expense("=1+1", 1000, "가", "기타")
        t.add_expense("-cmd", 1000, "나", "기타")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "i.csv"
            exporter.save_csv(t, p)
            rows = read_csv_sections(p)["[지출 내역]"][1:]
            self.assertEqual([r[1] for r in rows], ["'=1+1", "'-cmd"])
            diffs = [r[3] for r in read_csv_sections(p)["[참가자별 정산]"][1:]]
            self.assertEqual(diffs, ["0", "0"])  # 숫자 열은 그대로(음수 숫자가 변형되지 않음)

    def test_negative_numbers_stay_numeric(self):
        s = spec_trip()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "n.csv"
            exporter.save_csv(s, p)
            rows = read_csv_sections(p)["[참가자별 정산]"][1:]
            self.assertEqual([r[3] for r in rows], ["80000", "-10000", "-70000"])

    def test_empty_transfers_section_still_present(self):
        t = Trip(name="t", participants=["가", "나"])
        t.add_expense("a", 1000, "가", "기타")
        t.add_expense("b", 1000, "나", "기타")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "e.csv"
            exporter.save_csv(t, p)
            self.assertEqual(read_csv_sections(p)["[송금 결과]"], [["순서", "보내는 사람", "받는 사람", "금액(원)"]])


class FileTests(unittest.TestCase):
    def test_txt_file_has_bom_and_crlf(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.txt"
            exporter.save_txt(spec_trip(), p, NOW)
            raw = p.read_bytes()
            self.assertEqual(raw[:3], b"\xef\xbb\xbf")
            self.assertIn(b"\r\n", raw)
            self.assertNotIn(b"\r\r\n", raw)
            self.assertIn("지연님이 민수님에게", raw.decode("utf-8-sig"))

    def test_filenames(self):
        self.assertEqual(exporter.safe_filename('제주: 3/4일?*'), "제주 34일")
        self.assertEqual(exporter.safe_filename("  ...  "), "여행")
        t = Trip(name='a<b>"c')
        self.assertEqual(exporter.default_filename(t, "csv", NOW), "TripShare_abc_20261120.csv")


if __name__ == "__main__":
    unittest.main()
