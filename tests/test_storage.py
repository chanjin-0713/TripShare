import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tripshare import models, storage  # noqa: E402
from tripshare.models import Trip, backup_path, default_data_path, demo_trip, load_trip, save_trip  # noqa: E402


class SaveTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.path = self.dir / "TripShare" / "trip.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_creates_folder_and_leaves_no_temp_file(self):
        save_trip(demo_trip(), self.path)
        self.assertTrue(self.path.exists())
        self.assertEqual(sorted(p.name for p in self.path.parent.iterdir()), ["trip.json"])
        json.loads(self.path.read_text(encoding="utf-8"))  # 유효한 JSON

    def test_second_save_keeps_previous_version_as_backup(self):
        t = demo_trip()
        save_trip(t, self.path)
        t.name = "두번째"
        save_trip(t, self.path)
        self.assertEqual(load_trip(self.path).name, "두번째")
        self.assertEqual(load_trip(backup_path(self.path)).name, "제주도 3박4일 (예시)")

    def test_failed_replace_keeps_original_and_cleans_temp(self):
        t = demo_trip()
        save_trip(t, self.path)
        t.name = "저장 실패해야 함"
        with mock.patch("os.replace", side_effect=PermissionError("denied")):
            with self.assertRaises(OSError):
                save_trip(t, self.path)
        self.assertEqual(load_trip(self.path).name, "제주도 3박4일 (예시)")  # 기존 파일 그대로
        self.assertFalse(self.path.with_name("trip.json.tmp").exists())

    def test_failed_write_keeps_original(self):
        t = demo_trip()
        save_trip(t, self.path)
        with mock.patch("os.fsync", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                save_trip(t, self.path)
        self.assertEqual(load_trip(self.path).name, t.name)
        self.assertFalse(self.path.with_name("trip.json.tmp").exists())

    def test_corrupt_main_does_not_overwrite_good_backup(self):
        t = demo_trip()
        save_trip(t, self.path)
        t.name = "B"
        save_trip(t, self.path)               # main=B, bak=원본
        self.path.write_text("{깨짐", encoding="utf-8")
        t.name = "C"
        save_trip(t, self.path)               # 손상된 main은 백업으로 복사하지 않는다
        self.assertEqual(load_trip(backup_path(self.path)).name, "제주도 3박4일 (예시)")

    def test_unwritable_location_raises_oserror(self):
        blocker = self.dir / "file"
        blocker.write_text("x")
        with self.assertRaises(OSError):
            save_trip(demo_trip(), blocker / "sub" / "trip.json")  # 폴더를 만들 수 없는 위치


class DataPathTests(unittest.TestCase):
    def test_uses_appdata_trip_share_folder(self):
        with mock.patch.dict(os.environ, {"APPDATA": r"C:\Users\x\AppData\Roaming"}):
            p = default_data_path()
        self.assertEqual((p.parent.name, p.name), ("TripShare", "trip.json"))
        self.assertIn("AppData", str(p))

    def test_falls_back_to_home_without_appdata(self):
        env = {k: v for k, v in os.environ.items() if k != "APPDATA"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(default_data_path().parent.name, "TripShare")


class StartupTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "trip.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_file_starts_demo(self):
        r = storage.startup_load(self.path)
        self.assertEqual(r.status, storage.NEW)
        self.assertEqual(r.trip.name, demo_trip().name)

    def test_valid_file_loaded(self):
        t = demo_trip()
        t.add_expense("추가", 1000, "가상민수", "기타")
        save_trip(t, self.path)
        r = storage.startup_load(self.path)
        self.assertEqual(r.status, storage.LOADED)
        self.assertEqual(r.trip.to_dict(), t.to_dict())

    def test_corrupt_without_backup(self):
        for bad in ("{깨진 json", "", "[]", '{"name": 5}', '{"version": 99, "name": "x"}'):
            with self.subTest(bad=bad):
                self.path.write_text(bad, encoding="utf-8")
                r = storage.startup_load(self.path)
                self.assertEqual(r.status, storage.CORRUPT)
                self.assertIsNone(r.trip)
                self.assertTrue(r.corrupt_copy.exists())      # 손상 파일은 지우지 않고 보관
                self.assertFalse(self.path.exists())
                self.assertEqual(r.corrupt_copy.read_text(encoding="utf-8"), bad)
                self.assertIn("보관", r.message)
                r.corrupt_copy.unlink()

    def test_binary_garbage_is_corrupt_not_crash(self):
        self.path.write_bytes(b"\xff\xfe\x00\x81garbage")
        self.assertEqual(storage.startup_load(self.path).status, storage.CORRUPT)

    def test_corrupt_with_backup_recovers(self):
        t = demo_trip()
        save_trip(t, self.path)
        t.name = "최신"
        save_trip(t, self.path)
        self.path.write_text("{깨짐", encoding="utf-8")
        r = storage.startup_load(self.path)
        self.assertEqual(r.status, storage.RECOVERED)
        self.assertEqual(r.trip.name, "제주도 3박4일 (예시)")
        self.assertIn("복구", r.message)

    def test_utf8_bom_file_is_accepted(self):
        self.path.write_bytes(b"\xef\xbb\xbf" + json.dumps(Trip(name="비오엠").to_dict(), ensure_ascii=False).encode())
        self.assertEqual(storage.startup_load(self.path).trip.name, "비오엠")

    def test_persists_across_restart(self):
        t = Trip(name="재실행", budget=500000, participants=["가", "나"])
        t.add_expense("점심", 12000, "가", "식비")
        save_trip(t, self.path)
        again = storage.startup_load(self.path).trip
        self.assertEqual((again.name, again.budget, again.participants), ("재실행", 500000, ["가", "나"]))
        self.assertEqual(again.expenses[0].amount, 12000)


if __name__ == "__main__":
    unittest.main()
