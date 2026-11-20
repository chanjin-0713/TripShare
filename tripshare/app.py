"""TripShare GUI (Tkinter/ttk) - 기능 1: 여행 기본정보 설정.

레이아웃: 왼쪽 사이드바 + 오른쪽 본문(여행 헤더 카드 / 여행 정보 카드 / 참가자 카드 격자).
"""
from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from . import storage
from .models import (
    MAX_NAME_LEN, MAX_PARTICIPANTS, MIN_PARTICIPANTS, Trip, ValidationError,
    default_data_path, demo_trip, save_trip,
)

APP_TITLE = "TripShare - 여행 경비 자동 정산"
PRIVACY_NOTE = "실제 이름·연락처 등 개인정보는 입력하지 마세요. 가상의 이름(예: 가상민수)을 사용하세요."

DEFAULT_SIZE = (1050, 700)  # 기본 창 크기(픽셀, 100% 배율 기준)
MIN_SIZE = (820, 560)       # 이보다 작아지면 내용은 스크롤로 사용
PAGES = [("settings", "여행 설정"), ("expenses", "지출 내역"), ("stats", "지출 통계"),
         ("budget", "예산 관리"), ("result", "정산 결과")]
HELP_TEXT = """TripShare는 여행 경비를 입력하면 누가 누구에게 얼마를 보내야 하는지 자동으로 계산해 줍니다.

1. 여행 설정: 여행 이름, 예산, 참가자(2~10명)를 등록합니다.
2. 지출 내역: 지출 항목, 금액, 결제한 사람, 카테고리를 입력합니다.
3. 정산 결과: 참가자별 부담 금액과 송금 목록을 확인하고 TXT/CSV로 저장합니다.
4. 지출 통계, 예산 관리: 카테고리별 비중과 예산 사용률을 확인합니다.

입력한 내용은 바로 자동 저장되며, 인터넷 연결이 필요 없습니다.
실제 개인정보 대신 가상의 이름을 사용해 주세요."""
ABOUT_TEXT = """TripShare - 여행 경비 자동 정산

친구·가족과 함께한 여행의 공동 경비를 균등하게 나누어
누가 누구에게 얼마를 송금하면 되는지 계산해 주는 프로그램입니다.

모든 데이터는 이 컴퓨터에만 저장되며 외부로 전송되지 않습니다."""

from . import ui
from .ui import ScrollArea
from .expense_page import ExpensePage
from .result_page import ResultPage
from .budget_page import BudgetPage
from .stats_page import StatsPage
from .budget import evaluate
from .ui import (
    AVATAR_COLORS, C_ACCENT, C_ACCENT_SOFT, C_AMBER, C_AMBER_BG, C_BG, C_BORDER, C_GREEN, C_GREEN_BG,
    C_MUTED, C_RED, C_SIDEBAR, C_TEXT, FONT, GRID_COLUMNS, avatar as _avatar, card as _card,
    chip as _chip, link as _link,
)



class TripShareApp:
    def __init__(self, root: tk.Tk, data_path: Path | None = None) -> None:
        self.root = root
        self.data_path = Path(data_path) if data_path else default_data_path()
        self._save_error_shown = False
        self.startup = storage.startup_load(self.data_path)
        self.trip = self.startup.trip or Trip()

        ui.set_scale(max(1.0, root.winfo_fpixels("1i") / 96))
        SCALE = ui.SCALE
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
        file_menu.add_command(label="정산 결과를 TXT로 저장", command=lambda: self._export("txt"))
        file_menu.add_command(label="정산 결과를 CSV로 저장", command=lambda: self._export("csv"))
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

    def _export(self, kind: str) -> None:
        self.show_page("result")
        self.result_page.on_export(kind)

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
                self.name_entry.focus_set()
        elif res.status == storage.NEW:
            self._autosave()  # 첫 실행: 예시 데이터를 바로 저장해 저장 위치를 만들어 둔다
            self.set_status("처음 실행하셨네요! 가상 예시 데이터로 시작합니다. '새 여행 시작'으로 직접 만들 수 있어요.",
                            C_AMBER, C_AMBER_BG)

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

    def _build_ui(self) -> None:
        self.nav_rows: dict[str, tuple[tk.Frame, tk.Label]] = {}
        self._build_sidebar()
        self.content = tk.Frame(self.root, bg=C_BG)
        self.content.pack(side="left", fill="both", expand=True)
        # 각 화면은 스크롤 영역 안에 둔다: 작은 화면에서도 모든 기능에 접근할 수 있다.
        self.areas = {key: ScrollArea(self.content) for key, _label in PAGES}
        main = tk.Frame(self.areas["settings"].inner, bg=C_BG, padx=28, pady=22)
        main.pack(fill="both", expand=True)
        self.settings_page = main
        self._build_header(main)
        self._build_info_card(main)
        self._build_participants(main)
        self.expense_page = ExpensePage(self.areas["expenses"].inner, self)
        self.stats_page = StatsPage(self.areas["stats"].inner, self)
        self.budget_page = BudgetPage(self.areas["budget"].inner, self)
        self.result_page = ResultPage(self.areas["result"].inner, self)
        for page in (self.expense_page, self.stats_page, self.budget_page, self.result_page):
            page.pack(fill="both", expand=True)
        self.pages = self.areas
        self.current_page = ""
        self.show_page("settings")

    def show_page(self, key: str) -> None:
        if self.current_page != key:
            if self.current_page:
                self.areas[self.current_page].pack_forget()
            self.current_page = key
            self.areas[key].pack(fill="both", expand=True)
            self.areas[key].canvas.yview_moveto(0)
        for k, (row, lbl) in self.nav_rows.items():
            active = k == key
            bg = C_ACCENT_SOFT if active else C_SIDEBAR
            row.configure(bg=bg)
            lbl.configure(bg=bg, fg=C_ACCENT if active else C_TEXT,
                          font=(FONT, 10, "bold" if active else "normal"))
        if key == "expenses":
            self.expense_page.refresh()
        elif key == "stats":
            self.stats_page.refresh()
        elif key == "budget":
            self.budget_page.refresh()
        elif key == "result":
            self.result_page.refresh()

    def _build_sidebar(self) -> None:
        side = tk.Frame(self.root, bg=C_SIDEBAR, width=int(210 * ui.SCALE), highlightbackground=C_BORDER, highlightthickness=1)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        logo = tk.Frame(side, bg=C_SIDEBAR, padx=18, pady=18)
        logo.pack(fill="x")
        _avatar(logo, "T", C_ACCENT, 30).pack(side="left")
        tk.Label(logo, text="TripShare", bg=C_SIDEBAR, fg=C_TEXT, font=(FONT, 13, "bold")).pack(side="left", padx=8)

        def nav(key: str, text: str, soon: bool = False) -> None:
            row = tk.Frame(side, bg=C_SIDEBAR, padx=18, pady=9)
            row.pack(fill="x", padx=8, pady=1)
            lbl = tk.Label(row, text=text, bg=C_SIDEBAR, fg=C_MUTED if soon else C_TEXT, font=(FONT, 10))
            lbl.pack(side="left")
            if soon:
                tk.Label(row, text="준비 중", bg=C_SIDEBAR, fg=C_MUTED, font=(FONT, 8)).pack(side="right")
                return
            self.nav_rows[key] = (row, lbl)
            for w in (row, lbl):
                w.configure(cursor="hand2")
                w.bind("<Button-1>", lambda _e, k=key: self.show_page(k))

        nav("settings", "여행 설정")
        nav("expenses", "지출 내역")
        nav("stats", "지출 통계")
        nav("budget", "예산 관리")
        nav("result", "정산 결과")

        bottom = tk.Frame(side, bg=C_SIDEBAR, padx=18, pady=16)
        bottom.pack(side="bottom", fill="x")
        for text, cmd in (("새 여행 시작", self.on_new_trip), ("예시 데이터 불러오기", self.on_load_demo),
                          ("저장 폴더 열기", self.open_data_folder)):
            lbl = _link(bottom, text, cmd)
            lbl.configure(bg=C_SIDEBAR, font=(FONT, 10))
            lbl.pack(anchor="w", pady=3)
        tk.Label(bottom, text="변경 사항은 자동 저장됩니다\n인터넷 연결 없이 동작합니다", bg=C_SIDEBAR, fg=C_MUTED, justify="left",
                 font=(FONT, 8)).pack(anchor="w", pady=(10, 0))

    def _build_header(self, parent: tk.Frame) -> None:
        card = _card(parent, padx=20, pady=16)
        card.pack(fill="x")
        self.header_avatar_holder = tk.Frame(card, bg=C_BG)
        self.header_avatar_holder.pack(side="left")
        text = tk.Frame(card, bg=C_BG)
        text.pack(side="left", padx=16, fill="x", expand=True)
        self.header_title = tk.Label(text, bg=C_BG, fg=C_TEXT, font=(FONT, 18, "bold"), anchor="w")
        self.header_title.pack(anchor="w")
        self.header_members = tk.Label(text, bg=C_BG, fg=C_MUTED, font=(FONT, 10), anchor="w",
                                       wraplength=560, justify="left")
        self.header_members.pack(anchor="w", pady=(2, 6))
        self.chip_row = tk.Frame(text, bg=C_BG)
        self.chip_row.pack(anchor="w")

        self.status_var = tk.StringVar()
        self.status = tk.Label(parent, textvariable=self.status_var, anchor="w", padx=12, pady=6,
                               font=(FONT, 10))
        self.status.pack(fill="x", pady=(10, 0))

    def _build_info_card(self, parent: tk.Frame) -> None:
        card = _card(parent, padx=20, pady=14)
        card.pack(fill="x", pady=(14, 0))
        card.columnconfigure(1, weight=1)
        card.columnconfigure(3, weight=1)
        tk.Label(card, text="여행 정보", bg=C_BG, fg=C_TEXT, font=(FONT, 11, "bold")).grid(
            row=0, column=0, columnspan=5, sticky="w", pady=(0, 8))
        self.name_var = tk.StringVar()
        self.budget_var = tk.StringVar()
        tk.Label(card, text="여행 이름", bg=C_BG, fg=C_MUTED, font=(FONT, 10)).grid(row=1, column=0, sticky="w")
        self.name_entry = ttk.Entry(card, textvariable=self.name_var, font=(FONT, 10))
        self.name_entry.grid(row=1, column=1, sticky="ew", padx=(10, 20))
        tk.Label(card, text="예산 (원)", bg=C_BG, fg=C_MUTED, font=(FONT, 10)).grid(row=1, column=2, sticky="w")
        budget_entry = ttk.Entry(card, textvariable=self.budget_var, font=(FONT, 10), justify="right")
        budget_entry.grid(row=1, column=3, sticky="ew", padx=(10, 20))
        ttk.Button(card, text="정보 저장", style="Primary.TButton", command=self.on_save_info).grid(row=1, column=4)
        for e in (self.name_entry, budget_entry):
            e.bind("<Return>", lambda _e: self.on_save_info())
        tk.Label(card, text=PRIVACY_NOTE, bg=C_BG, fg=C_AMBER, font=(FONT, 9)).grid(
            row=2, column=0, columnspan=5, sticky="w", pady=(8, 0))

    def _build_participants(self, parent: tk.Frame) -> None:
        top = tk.Frame(parent, bg=C_BG)
        top.pack(fill="x", pady=(18, 8))
        self.count_label = tk.Label(top, bg=C_BG, fg=C_TEXT, font=(FONT, 11, "bold"))
        self.count_label.pack(side="left")
        tk.Label(top, text=f"  (최소 {MIN_PARTICIPANTS}명 ~ 최대 {MAX_PARTICIPANTS}명)", bg=C_BG, fg=C_MUTED,
                 font=(FONT, 9)).pack(side="left")

        self.grid_frame = tk.Frame(parent, bg=C_BG)
        self.grid_frame.pack(fill="x")
        for c in range(GRID_COLUMNS):
            self.grid_frame.columnconfigure(c, weight=1, uniform="col")

        add = tk.Frame(parent, bg=C_BG)
        add.pack(fill="x", pady=(14, 0))
        self.new_name_var = tk.StringVar()
        self.new_entry = ttk.Entry(add, textvariable=self.new_name_var, font=(FONT, 10), width=28)
        self.new_entry.pack(side="left")
        self.new_entry.bind("<Return>", lambda _e: self.on_add())
        self.add_button = ttk.Button(add, text="+ 참가자 추가", style="Primary.TButton", command=self.on_add)
        self.add_button.pack(side="left", padx=10)
        tk.Label(add, text=f"이름은 {MAX_NAME_LEN}자 이하, 중복 불가", bg=C_BG, fg=C_MUTED,
                 font=(FONT, 9)).pack(side="left")

    # ---------- 화면 갱신 ----------
    def refresh(self) -> None:
        self.name_var.set(self.trip.name)
        self.budget_var.set(f"{self.trip.budget:,}")
        self.refresh_header()
        self.refresh_participants()
        if hasattr(self, "expense_page"):
            self.expense_page.refresh(reset_form=True)
            self.budget_page.refresh()
            self.stats_page.refresh()

    def on_budget_changed(self) -> None:
        """예산 관리 화면에서 예산을 바꿨을 때, 입력 중인 다른 화면의 내용은 건드리지 않고 갱신."""
        self.budget_var.set(f"{self.trip.budget:,}")
        self.refresh_header()
        self.expense_page.refresh()
        self.budget_page.refresh()

    def refresh_header(self) -> None:
        for w in self.header_avatar_holder.winfo_children():
            w.destroy()
        _avatar(self.header_avatar_holder, (self.trip.name or "?")[0], C_ACCENT, 56).pack()
        self.header_title.configure(text=self.trip.name or "여행 이름을 입력하세요")
        members = ", ".join(self.trip.participants)
        self.header_members.configure(text=members or "아직 등록된 참가자가 없습니다")
        for w in self.chip_row.winfo_children():
            w.destroy()
        st = evaluate(self.trip.budget, self.trip.total_spent)
        text = "예산 미설정" if st.is_unset else f"예산 {st.budget:,}원 ({st.percent_text} 사용)"
        _chip(self.chip_row, text, C_ACCENT, C_ACCENT_SOFT).pack(side="left")
        _chip(self.chip_row, f"참가자 {len(self.trip.participants)}/{MAX_PARTICIPANTS}명",
              C_GREEN, C_GREEN_BG).pack(side="left", padx=6)

    def refresh_participants(self, select: str | None = None) -> None:
        for w in self.grid_frame.winfo_children():
            w.destroy()
        for i, name in enumerate(self.trip.participants):
            self._participant_card(i, name)
        count = len(self.trip.participants)
        self.count_label.configure(text=f"여행 참가자 {count}명")
        full = count >= MAX_PARTICIPANTS
        self.add_button.state(["disabled"] if full else ["!disabled"])
        self.new_entry.state(["disabled"] if full else ["!disabled"])
        self.refresh_header()
        problems = self.trip.setup_problems()
        if problems:
            self.set_status("⚠ " + " ".join(problems), C_AMBER, C_AMBER_BG)
        else:
            self.set_status("✔ 설정 완료: 다음 단계(지출 입력)를 진행할 수 있습니다.", C_GREEN, C_GREEN_BG)

    def _participant_card(self, index: int, name: str) -> None:
        card = _card(self.grid_frame, padx=12, pady=10)
        card.grid(row=index // GRID_COLUMNS, column=index % GRID_COLUMNS, sticky="ew", padx=4, pady=4)
        _avatar(card, name[0], AVATAR_COLORS[index % len(AVATAR_COLORS)], 38).pack(side="right")
        info = tk.Frame(card, bg=C_BG)
        info.pack(side="left", fill="x", expand=True)
        tk.Label(info, text=name, bg=C_BG, fg=C_TEXT, font=(FONT, 11, "bold"), anchor="w").pack(anchor="w")
        actions = tk.Frame(info, bg=C_BG)
        actions.pack(anchor="w", pady=(4, 0))
        _link(actions, "이름 변경", lambda n=name: self.on_rename(n)).pack(side="left")
        tk.Label(actions, text="·", bg=C_BG, fg=C_MUTED).pack(side="left", padx=4)
        _link(actions, "삭제", lambda n=name: self.on_remove(n), fg=C_RED).pack(side="left")

    def set_status(self, text: str, fg: str = C_GREEN, bg: str = C_GREEN_BG) -> None:
        self.status_var.set(text)
        self.status.configure(fg=fg, bg=bg)

    # ---------- 이벤트 ----------
    def on_save_info(self) -> None:
        try:
            self.trip.set_basic_info(self.name_var.get(), self.budget_var.get())
        except ValidationError as exc:
            messagebox.showwarning("입력 확인", str(exc), parent=self.root)
            return
        self._autosave()
        self.refresh()
        self.set_status("✔ 여행 정보를 저장했습니다.", C_GREEN, C_GREEN_BG)

    def on_add(self) -> None:
        try:
            added = self.trip.add_participant(self.new_name_var.get())
        except ValidationError as exc:
            messagebox.showwarning("참가자 추가", str(exc), parent=self.root)
            self.new_entry.focus_set()
            return
        self.new_name_var.set("")
        self._autosave()
        self.refresh_participants(select=added)
        self.new_entry.focus_set()

    def on_remove(self, name: str) -> None:
        # 연결된 지출/최소 인원 위반은 확인창 이전에 차단
        try:
            probe = Trip(participants=list(self.trip.participants), expenses=self.trip.expenses)
            probe.remove_participant(name)
        except ValidationError as exc:
            messagebox.showwarning("삭제할 수 없음", str(exc), parent=self.root)
            return
        if not messagebox.askyesno("참가자 삭제", f"'{name}'님을 삭제할까요?", parent=self.root):
            return
        self.trip.remove_participant(name)
        self._autosave()
        self.refresh_participants()

    def on_rename(self, name: str) -> None:
        new = simpledialog.askstring("이름 변경", f"'{name}'의 새 이름:", initialvalue=name, parent=self.root)
        if new is None:
            return
        try:
            result = self.trip.rename_participant(name, new)
        except ValidationError as exc:
            messagebox.showwarning("이름 변경", str(exc), parent=self.root)
            return
        self._autosave()
        self.refresh_participants(select=result)

    def on_load_demo(self) -> None:
        if not messagebox.askyesno("예시 데이터", "현재 입력한 내용이 사라지고 가상 예시 데이터로 바뀝니다.\n계속할까요?",
                                   parent=self.root):
            return
        self.trip = demo_trip()
        self._autosave()
        self.refresh()

    def on_new_trip(self) -> None:
        if not messagebox.askyesno("새 여행", "현재 입력한 내용이 모두 사라집니다.\n새 여행을 시작할까요?",
                                   parent=self.root):
            return
        self.trip = Trip()
        self._autosave()
        self.refresh()
        self.name_entry.focus_set()


def main() -> None:
    try:  # 고해상도 화면에서 글자가 흐려지지 않도록 (Windows)
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    TripShareApp(root)
    root.mainloop()
