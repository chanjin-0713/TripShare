"""GUI 시나리오 테스트 (화면이 있는 환경에서만 실행). 대화상자는 가짜로 대체한다."""
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from tkinter import filedialog, messagebox
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tripshare import app as app_module  # noqa: E402
from tripshare.models import Trip, demo_trip, save_trip  # noqa: E402

try:
    _probe = tk.Tk()
    _probe.destroy()
    HAS_DISPLAY = True
except tk.TclError:
    HAS_DISPLAY = False


@unittest.skipUnless(HAS_DISPLAY, "화면(Tk)을 사용할 수 없는 환경")
class GuiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.log = []
        self.answer = True
        patches = [
            mock.patch.object(messagebox, "showwarning", lambda t, m, **k: self.log.append(("W", m))),
            mock.patch.object(messagebox, "showinfo", lambda t, m, **k: self.log.append(("I", m))),
            mock.patch.object(messagebox, "showerror", lambda t, m, **k: self.log.append(("E", m))),
            mock.patch.object(messagebox, "askyesno", lambda t, m, **k: (self.log.append(("Q", m)), self.answer)[1]),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.apps = []

    def tearDown(self):
        for root in self.apps:
            try:
                root.destroy()
            except tk.TclError:
                pass
        self.tmp.cleanup()

    def start(self, path=None):
        root = tk.Tk()
        self.apps.append(root)
        app = app_module.TripShareApp(root, path or self.dir / "trip.json")
        root.update()
        return app

    def add_expense(self, app, title, amount, payer, category="기타"):
        p = app.expense_page
        p.title_var.set(title)
        p.amount_var.set(str(amount))
        p.payer_var.set(payer)
        p.category_var.set(category)
        p.on_submit()

    # ---- 메인 화면 구성 ----
    def test_layout_top_bar_and_menu(self):
        app = self.start()
        self.assertEqual([label for _k, label in app_module.PAGES],
                         ["대시보드", "참가자 관리", "지출 내역", "자동 정산", "통계", "데이터 내보내기"])
        self.assertEqual(app.top_trip.cget("text"), demo_trip().name)
        for key, _label in app_module.PAGES:       # 모든 화면이 열린다
            app.show_page(key)
            app.root.update()
            self.assertEqual(app.current_page, key)
        app.dashboard_page.name_var.set("부산 여행")
        app.dashboard_page.on_save_info()
        self.assertEqual(app.top_trip.cget("text"), "부산 여행")

    def test_default_window_size(self):
        app = self.start()
        s = app_module.ui.SCALE
        w, h = app.root.winfo_width(), app.root.winfo_height()
        screen_w, screen_h = app.root.winfo_screenwidth(), app.root.winfo_screenheight()
        self.assertLessEqual(w, screen_w)
        self.assertLessEqual(h, screen_h)
        if screen_w >= 1100 * s and screen_h >= 800 * s:
            self.assertEqual((w, h), (int(1050 * s), int(700 * s)))

    # ---- 대시보드 ----
    def test_dashboard_numbers_and_levels(self):
        app = self.start()
        d = app.dashboard_page
        app.show_page("dashboard")
        v = {k: d.stat_values[k].cget("text") for k in d.stat_values}
        self.assertEqual((v["spent"], v["budget"], v["remaining"], v["people"]),
                         ("654,500원", "1,200,000원", "545,500원", "4명"))
        self.assertEqual(d.percent_label.cget("text"), "54.5%")
        recent = [d.tree.item(i, "values")[0] for i in d.tree.get_children()]
        self.assertEqual(recent[0], "기념품")          # 가장 최근 등록이 맨 위
        self.assertEqual(len(recent), 5)
        d.budget_var.set("700,000")
        d.on_save_info()                                  # 93.5% -> 주의
        self.assertEqual(d.status.level, "caution")
        d.budget_var.set("600,000")
        d.on_save_info()                                  # 초과
        self.assertEqual(d.status.level, "over")
        self.assertEqual(d.stat_titles["remaining"].cget("text"), "초과 금액")
        d.budget_var.set("0")
        d.on_save_info()
        self.assertEqual(d.stat_values["budget"].cget("text"), "예산 미설정")
        self.assertEqual(d.percent_label.cget("text"), "예산 미설정")
        d.budget_var.set("abc")
        d.on_save_info()
        self.assertEqual(self.log[-1][0], "W")

    # ---- 참가자 관리 ----
    def test_participants_add_duplicate_remove(self):
        app = self.start()
        p = app.participants_page
        p.new_name_var.set("가상민수")
        p.on_add()
        self.assertIn("이미", self.log[-1][1])
        for i in range(6):
            p.new_name_var.set(f"가상{i}")
            p.on_add()
        self.assertEqual(len(app.trip.participants), 10)
        self.assertIn("disabled", p.add_button.state())
        p.on_remove("가상0")                              # 연결된 지출 없음 -> 삭제됨
        self.assertEqual(len(app.trip.participants), 9)
        p.on_remove("가상민수")                           # 결제자 -> 삭제 차단
        self.assertIn("지출 내역에 연결", self.log[-1][1])
        self.assertIn("가상민수", app.trip.participants)

    # ---- 지출 내역 ----
    def test_expense_register_edit_delete(self):
        app = self.start()
        e = app.expense_page
        self.add_expense(app, "택시", 0, "가상서준")
        self.assertIn("1원 이상", self.log[-1][1])
        self.add_expense(app, "택시", "15,000", "가상서준", "교통비")
        self.assertEqual(len(app.trip.expenses), 6)
        e.tree.selection_set("5")
        e.on_edit()
        e.amount_var.set("18000")
        e.on_submit()
        self.assertEqual(app.trip.expenses[5].amount, 18000)
        e.tree.selection_set("0")
        e.on_delete()
        self.assertEqual(len(app.trip.expenses), 5)

    # ---- 자동 정산: 요구사항 예시 ----
    def test_settlement_example(self):
        app = self.start()
        app.trip = Trip(name="예시", budget=0, participants=["민수", "지연", "현우"])
        app.trip.add_expense("숙박비", 180000, "민수", "숙박비")
        app.trip.add_expense("식비", 90000, "지연", "식비")
        app.trip.add_expense("교통비", 30000, "현우", "교통비")
        app.refresh()
        app.show_page("result")
        r = app.result_page
        sentences = [r.transfer_tree.item(i, "values")[1] for i in r.transfer_tree.get_children()]
        self.assertEqual(sentences, ["지연님이 민수님에게 10,000원을 보내세요.", "현우님이 민수님에게 70,000원을 보내세요."])
        self.assertIn("300,000원", r.total_label.cget("text"))

    # ---- 통계 ----
    def test_stats_modes(self):
        app = self.start()
        s = app.stats_page
        app.show_page("stats")
        self.assertEqual(s.mode, "bar")
        self.assertEqual(len(s.payer_bars.rows), 4)
        self.assertEqual(len(s.category_bars.rows), 6)
        s.set_mode("donut")
        app.root.update()
        self.assertEqual(s.mode, "donut")
        self.assertTrue(s.donut_view.winfo_ismapped() and not s.bar_view.winfo_ismapped())

    # ---- 데이터 내보내기 ----
    def test_export_txt_csv_and_cancel(self):
        app = self.start()
        e = app.export_page
        for kind in ("txt", "csv"):
            out = self.dir / f"out.{kind}"
            with mock.patch.object(filedialog, "asksaveasfilename", lambda **k: str(out)):
                e.on_export(kind)
            self.assertEqual(out.read_bytes()[:3], b"\xef\xbb\xbf")
        self.assertIn("저장했습니다", e.save_label.cget("text"))
        gone = self.dir / "none.csv"
        with mock.patch.object(filedialog, "asksaveasfilename", lambda **k: ""):
            e.on_export("csv")
        self.assertFalse(gone.exists())
        app.trip = Trip(name="x", participants=["가"])
        e.on_export("txt")
        self.assertEqual(self.log[-1][0], "W")

    # ---- 시작 / 저장 ----
    def test_first_run_creates_file_and_persists(self):
        path = self.dir / "sub" / "trip.json"
        app = self.start(path)
        self.assertTrue(path.exists())
        app.dashboard_page.name_var.set("재실행")
        app.dashboard_page.on_save_info()
        app.on_close()
        app2 = self.start(path)
        self.assertEqual(app2.trip.name, "재실행")

    def test_corrupt_file_does_not_crash(self):
        path = self.dir / "trip.json"
        path.write_text("{깨짐", encoding="utf-8")
        self.answer = True
        app = self.start(path)
        self.assertEqual(app.trip.participants, [])        # 새 여행
        self.assertTrue(any(k == "Q" and "불러오지 못했" in m for k, m in self.log))
        self.assertTrue(list(self.dir.glob("trip.corrupt-*.json")))


if __name__ == "__main__":
    unittest.main()
