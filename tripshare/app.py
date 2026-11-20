"""TripShare 메인 창: 상단 바 + 좌측 메뉴 + 화면(대시보드/참가자 관리/지출 내역/자동 정산/통계/데이터 내보내기)."""
from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from . import storage, ui
from .dashboard_page import DashboardPage
from .expense_page import ExpensePage
from .export_page import ExportPage
from .models import Trip, default_data_path, demo_trip, save_trip
from .participants_page import ParticipantsPage
from .result_page import ResultPage
from .stats_page import StatsPage
from .ui import (
    C_ACCENT, C_ACCENT_SOFT, C_AMBER, C_AMBER_BG, C_BG, C_BORDER, C_MUTED, C_RED, C_RED_BG, C_SIDEBAR, C_TEXT,
    FONT, ScrollArea, avatar, link,
)

APP_TITLE = "TripShare - 여행 경비 자동 정산"
DEFAULT_SIZE = (1050, 700)  # 기본 창 크기(픽셀, 100% 배율 기준)
MIN_SIZE = (820, 560)       # 이보다 작아지면 내용은 스크롤로 사용
PAGES = [("dashboard", "대시보드"), ("participants", "참가자 관리"), ("expenses", "지출 내역"),
         ("result", "자동 정산"), ("stats", "통계"), ("export", "데이터 내보내기")]
HELP_TEXT = """TripShare는 여행 경비를 입력하면 누가 누구에게 얼마를 보내야 하는지 자동으로 계산해 줍니다.

1. 대시보드: 총 경비, 예산, 남은 예산, 예산 사용률과 최근 지출을 한눈에 봅니다. 여행 이름과 예산도 여기서 바꿉니다.
2. 참가자 관리: 참가자(2~10명)를 추가·삭제합니다.
3. 지출 내역: 지출 항목, 금액, 결제한 사람, 카테고리를 등록·수정·삭제합니다.
4. 자동 정산: 참가자별 결제액·부담액·정산 차액과 송금 목록을 확인합니다.
5. 통계: 참가자별·카테고리별 지출을 막대그래프(또는 원형 그래프)로 봅니다.
6. 데이터 내보내기: 정산 결과를 TXT 또는 CSV(Excel) 파일로 저장합니다.

입력한 내용은 바로 자동 저장되며, 인터넷 연결이 필요 없습니다.
실제 개인정보 대신 가상의 이름을 사용해 주세요."""
ABOUT_TEXT = """TripShare - 여행 경비 자동 정산

친구·가족과 함께한 여행의 공동 경비를 균등하게 나누어
누가 누구에게 얼마를 송금하면 되는지 계산해 주는 프로그램입니다.

모든 데이터는 이 컴퓨터에만 저장되며 외부로 전송되지 않습니다."""


class TripShareApp:
    def __init__(self, root: tk.Tk, data_path: Path | None = None) -> None:
        self.root = root
        self.data_path = Path(data_path) if data_path else default_data_path()
        self._save_error_shown = False
        self.startup = storage.startup_load(self.data_path)
        self.trip = self.startup.trip or Trip()

        ui.set_scale(max(1.0, root.winfo_fpixels("1i") / 96))
        root.title(APP_TITLE)
        self._set_window_size()
        root.configure(bg=C_BG)
        self._setup_style()
        self._build_menu()
        self._build_ui()
        self.refresh()
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._report_startup()

    # ---------- 창 크기 / 메뉴 ----------
    def _set_window_size(self) -> None:
        """기본 1050x700. 화면이 작으면 화면 안에 들어오도록 줄이고(내용은 스크롤), 최소 크기도 화면에 맞춘다."""
        s = ui.SCALE
        screen_w, screen_h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        max_w, max_h = screen_w - int(20 * s), screen_h - int(90 * s)  # 작업 표시줄/제목 표시줄 여유
        width = min(int(DEFAULT_SIZE[0] * s), max_w)
        height = min(int(DEFAULT_SIZE[1] * s), max_h)
        x, y = max(0, (screen_w - width) // 2), max(0, (screen_h - height) // 3)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(min(int(MIN_SIZE[0] * s), width), min(int(MIN_SIZE[1] * s), height))

    def _build_menu(self) -> None:
        bar = tk.Menu(self.root)
        file_menu = tk.Menu(bar, tearoff=False)
        file_menu.add_command(label="새 여행 시작", command=self.on_new_trip)
        file_menu.add_command(label="예시 데이터 불러오기", command=self.on_load_demo)
        file_menu.add_separator()
        file_menu.add_command(label="정산 결과를 TXT로 저장", command=lambda: self.export_page.on_export("txt"))
        file_menu.add_command(label="정산 결과를 CSV로 저장", command=lambda: self.export_page.on_export("csv"))
        file_menu.add_command(label="저장 폴더 열기", command=self.open_data_folder)
        file_menu.add_separator()
        file_menu.add_command(label="종료", command=self.on_close)
        bar.add_cascade(label="파일", menu=file_menu)

        go_menu = tk.Menu(bar, tearoff=False)
        for i, (key, label) in enumerate(PAGES, 1):
            go_menu.add_command(label=label, accelerator=f"Ctrl+{i}", command=lambda k=key: self.show_page(k))
            self.root.bind_all(f"<Control-Key-{i}>", lambda _e, k=key: self.show_page(k))
        bar.add_cascade(label="이동", menu=go_menu)

        help_menu = tk.Menu(bar, tearoff=False)
        help_menu.add_command(label="사용 방법", command=self.show_help)
        help_menu.add_command(label="프로그램 정보", command=self.show_about)
        bar.add_cascade(label="도움말", menu=help_menu)
        self.root.configure(menu=bar)

    def show_help(self) -> None:
        messagebox.showinfo("사용 방법", HELP_TEXT, parent=self.root)

    def show_about(self) -> None:
        messagebox.showinfo("프로그램 정보", ABOUT_TEXT, parent=self.root)

    # ---------- 저장/불러오기 ----------
    def _report_startup(self) -> None:
        """시작할 때 저장 파일 상태를 사용자에게 알린다. 프로그램은 어떤 경우에도 종료되지 않는다."""
        res = self.startup
        if res.status == storage.RECOVERED:
            messagebox.showwarning("저장 파일 복구", res.message, parent=self.root)
        elif res.status == storage.CORRUPT:
            new_trip = messagebox.askyesno(
                "저장 파일 오류",
                f"저장된 여행 데이터를 불러오지 못했습니다.\n\n{res.message}\n\n"
                "새 여행을 만들까요?\n(예: 새 여행 만들기 / 아니오: 예시 데이터로 시작)",
                icon="error", parent=self.root)
            self.trip = Trip() if new_trip else demo_trip()
            self._autosave()
            self.refresh()
            if new_trip:
                self.dashboard_page.name_entry.focus_set()
        elif res.status == storage.NEW:
            self._autosave()  # 첫 실행: 예시 데이터를 바로 저장해 저장 위치를 만들어 둔다
            self.show_notice("처음 실행하셨네요! 가상 예시 데이터로 시작합니다. "
                             "'파일 > 새 여행 시작'으로 직접 만들 수 있어요.", C_AMBER, C_AMBER_BG)

    def _autosave(self, show_error: bool = True) -> bool:
        """저장 성공 여부를 반환한다. 실패해도 프로그램은 계속 동작하며, 오류 창은 성공할 때까지 한 번만 띄운다."""
        try:
            save_trip(self.trip, self.data_path)
        except OSError as exc:
            if show_error and not self._save_error_shown:
                self._save_error_shown = True
                messagebox.showerror(
                    "저장 실패",
                    f"데이터를 자동 저장하지 못했습니다.\n저장 위치: {self.data_path}\n{exc}\n\n"
                    "프로그램은 계속 사용할 수 있지만, 종료하면 변경 내용이 사라질 수 있습니다.",
                    parent=self.root)
            return False
        self._save_error_shown = False
        return True

    def on_close(self) -> None:
        if not self._autosave(show_error=False):
            if not messagebox.askyesno("저장 실패", "데이터를 저장하지 못했습니다.\n저장하지 않고 종료할까요?",
                                       icon="warning", parent=self.root):
                return
        self.root.destroy()

    def open_data_folder(self) -> None:
        try:
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            os.startfile(self.data_path.parent)  # Windows 전용
        except (OSError, AttributeError) as exc:
            messagebox.showinfo("저장 폴더", f"저장 위치:\n{self.data_path.parent}\n\n(폴더를 열지 못했습니다: {exc})",
                                parent=self.root)

    # ---------- UI 구성 ----------
    def _setup_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TEntry", fieldbackground="white", bordercolor=C_BORDER,
                        lightcolor=C_BORDER, darkcolor=C_BORDER, padding=6)
        style.map("TEntry", bordercolor=[("focus", C_ACCENT)], lightcolor=[("focus", C_ACCENT)],
                  darkcolor=[("focus", C_ACCENT)])
        style.configure("Primary.TButton", background=C_ACCENT, foreground="white",
                        font=(FONT, 10, "bold"), padding=(14, 7), borderwidth=0)
        style.map("Primary.TButton", background=[("active", "#1e40af"), ("disabled", "#9ca3af")],
                  foreground=[("disabled", "white")])
        style.configure("Soft.TButton", background=C_ACCENT_SOFT, foreground=C_ACCENT,
                        font=(FONT, 10), padding=(12, 6), borderwidth=0)
        style.map("Soft.TButton", background=[("active", "#dbe4ff")])
        style.configure("Danger.TButton", background=C_RED_BG, foreground=C_RED,
                        font=(FONT, 10), padding=(12, 6), borderwidth=0)
        style.map("Danger.TButton", background=[("active", "#fecaca")])
        style.configure("Small.TButton", background=C_ACCENT_SOFT, foreground=C_ACCENT,
                        font=(FONT, 9), padding=(8, 3), borderwidth=0)
        style.map("Small.TButton", background=[("active", "#dbe4ff")])
        style.configure("SmallDanger.TButton", background=C_RED_BG, foreground=C_RED,
                        font=(FONT, 9), padding=(8, 3), borderwidth=0)
        style.map("SmallDanger.TButton", background=[("active", "#fecaca")])

    def _build_ui(self) -> None:
        self._build_topbar()
        self.notice = tk.Label(self.root, anchor="w", padx=16, pady=6, font=(FONT, 10))  # 필요할 때만 표시
        body = self.body = tk.Frame(self.root, bg=C_BG)
        body.pack(fill="both", expand=True)
        self.nav_rows: dict[str, tuple[tk.Frame, tk.Label]] = {}
        self._build_sidebar(body)
        self.content = tk.Frame(body, bg=C_BG)
        self.content.pack(side="left", fill="both", expand=True)

        # 각 화면은 스크롤 영역 안에 둔다: 작은 화면에서도 모든 기능에 접근할 수 있다.
        self.areas = {key: ScrollArea(self.content) for key, _label in PAGES}
        inner = {key: area.inner for key, area in self.areas.items()}
        self.dashboard_page = DashboardPage(inner["dashboard"], self)
        self.participants_page = ParticipantsPage(inner["participants"], self)
        self.expense_page = ExpensePage(inner["expenses"], self)
        self.result_page = ResultPage(inner["result"], self)
        self.stats_page = StatsPage(inner["stats"], self)
        self.export_page = ExportPage(inner["export"], self)
        self.pages = {"dashboard": self.dashboard_page, "participants": self.participants_page,
                      "expenses": self.expense_page, "result": self.result_page,
                      "stats": self.stats_page, "export": self.export_page}
        for page in self.pages.values():
            page.pack(fill="both", expand=True)
        self.current_page = ""
        self.show_page("dashboard")

    def _build_topbar(self) -> None:
        bar = tk.Frame(self.root, bg=C_BG, padx=18, pady=10)
        bar.pack(fill="x")
        avatar(bar, "T", C_ACCENT, 30).pack(side="left")
        tk.Label(bar, text="TripShare", bg=C_BG, fg=C_TEXT, font=(FONT, 14, "bold")).pack(side="left", padx=(8, 18))
        tk.Frame(bar, bg=C_BORDER, width=1).pack(side="left", fill="y", pady=2)
        tk.Label(bar, text="현재 여행", bg=C_BG, fg=C_MUTED, font=(FONT, 10)).pack(side="left", padx=(18, 8))
        self.top_trip = tk.Label(bar, bg=C_BG, fg=C_TEXT, font=(FONT, 13, "bold"))
        self.top_trip.pack(side="left")
        tk.Label(bar, text="변경 사항은 자동 저장됩니다", bg=C_BG, fg=C_MUTED, font=(FONT, 9)).pack(side="right")
        tk.Frame(self.root, bg=C_BORDER, height=1).pack(fill="x")

    def _build_sidebar(self, parent: tk.Frame) -> None:
        side = tk.Frame(parent, bg=C_SIDEBAR, width=int(210 * ui.SCALE), highlightbackground=C_BORDER,
                        highlightthickness=1)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Frame(side, bg=C_SIDEBAR, height=10).pack()

        for key, text in PAGES:
            row = tk.Frame(side, bg=C_SIDEBAR, padx=18, pady=9, cursor="hand2")
            row.pack(fill="x", padx=8, pady=1)
            lbl = tk.Label(row, text=text, bg=C_SIDEBAR, fg=C_TEXT, font=(FONT, 10), cursor="hand2")
            lbl.pack(side="left")
            self.nav_rows[key] = (row, lbl)
            for w in (row, lbl):
                w.bind("<Button-1>", lambda _e, k=key: self.show_page(k))

        bottom = tk.Frame(side, bg=C_SIDEBAR, padx=18, pady=16)
        bottom.pack(side="bottom", fill="x")
        for text, cmd in (("새 여행 시작", self.on_new_trip), ("예시 데이터 불러오기", self.on_load_demo),
                          ("저장 폴더 열기", self.open_data_folder)):
            lbl = link(bottom, text, cmd)
            lbl.configure(bg=C_SIDEBAR, font=(FONT, 10))
            lbl.pack(anchor="w", pady=3)
        tk.Label(bottom, text="인터넷 연결 없이 동작합니다", bg=C_SIDEBAR, fg=C_MUTED,
                 font=(FONT, 8)).pack(anchor="w", pady=(10, 0))

    # ---------- 화면 전환 / 갱신 ----------
    def show_page(self, key: str) -> None:
        if self.current_page != key:
            if self.current_page:
                self.areas[self.current_page].pack_forget()
                self.hide_notice()
            self.current_page = key
            self.areas[key].pack(fill="both", expand=True)
            self.areas[key].canvas.yview_moveto(0)
        for k, (row, lbl) in self.nav_rows.items():
            active = k == key
            bg = C_ACCENT_SOFT if active else C_SIDEBAR
            row.configure(bg=bg)
            lbl.configure(bg=bg, fg=C_ACCENT if active else C_TEXT,
                          font=(FONT, 10, "bold" if active else "normal"))
        self.pages[key].refresh()

    def refresh(self, reset_form: bool = True) -> None:
        """모든 화면을 현재 데이터로 갱신한다. reset_form=False면 입력 중인 지출 폼은 건드리지 않는다."""
        self.top_trip.configure(text=self.trip.name or "(여행 이름을 입력하세요)")
        for key, page in self.pages.items():
            if key == "expenses":
                page.refresh(reset_form=reset_form)
            else:
                page.refresh()

    def show_notice(self, text: str, fg: str, bg: str) -> None:
        self.notice.configure(text=text, fg=fg, bg=bg)
        self.notice.pack(fill="x", before=self.body)

    def hide_notice(self) -> None:
        self.notice.pack_forget()

    # ---------- 새 여행 / 예시 ----------
    def on_load_demo(self) -> None:
        if not messagebox.askyesno("예시 데이터", "현재 입력한 내용이 사라지고 가상 예시 데이터로 바뀝니다.\n계속할까요?",
                                   parent=self.root):
            return
        self.trip = demo_trip()
        self._autosave()
        self.refresh()
        self.show_page("dashboard")

    def on_new_trip(self) -> None:
        if not messagebox.askyesno("새 여행", "현재 입력한 내용이 모두 사라집니다.\n새 여행을 시작할까요?",
                                   parent=self.root):
            return
        self.trip = Trip()
        self._autosave()
        self.refresh()
        self.show_page("dashboard")
        self.dashboard_page.name_entry.focus_set()


def main() -> None:
    try:  # 고해상도 화면에서 글자가 흐려지지 않도록 (Windows)
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    TripShareApp(root)
    root.mainloop()
