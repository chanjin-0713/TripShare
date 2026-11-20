"""TripShare GUI (Tkinter/ttk) - 기능 1: 여행 기본정보 설정.

레이아웃: 왼쪽 사이드바 + 오른쪽 본문(여행 헤더 카드 / 여행 정보 카드 / 참가자 카드 격자).
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from .models import (
    MAX_NAME_LEN, MAX_PARTICIPANTS, MIN_PARTICIPANTS, Trip, ValidationError,
    default_data_path, demo_trip, load_trip, save_trip,
)

APP_TITLE = "TripShare - 여행 경비 자동 정산"
PRIVACY_NOTE = "실제 이름·연락처 등 개인정보는 입력하지 마세요. 가상의 이름(예: 가상민수)을 사용하세요."

from . import ui
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
        self.trip = self._load_initial()

        ui.set_scale(max(1.0, root.winfo_fpixels("1i") / 96))
        SCALE = ui.SCALE
        root.title(APP_TITLE)
        root.geometry(f"{int(1000 * SCALE)}x{int(760 * SCALE)}")
        root.minsize(int(900 * SCALE), int(700 * SCALE))
        root.configure(bg=C_BG)
        self._setup_style()
        self._build_ui()
        self.refresh()

    # ---------- 저장/불러오기 ----------
    def _load_initial(self) -> Trip:
        try:
            return load_trip(self.data_path)
        except FileNotFoundError:
            return demo_trip()
        except (ValidationError, OSError, UnicodeDecodeError):
            # 손상된 파일은 보존해 두고 예시 데이터로 시작
            try:
                self.data_path.replace(self.data_path.with_suffix(".bak"))
            except OSError:
                pass
            return demo_trip()

    def _autosave(self) -> None:
        try:
            save_trip(self.trip, self.data_path)
        except OSError as exc:
            messagebox.showerror("저장 실패", f"데이터를 저장하지 못했습니다.\n{exc}", parent=self.root)

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
        main = tk.Frame(self.content, bg=C_BG, padx=28, pady=22)
        self.settings_page = main
        self._build_header(main)
        self._build_info_card(main)
        self._build_participants(main)
        self.expense_page = ExpensePage(self.content, self)
        self.stats_page = StatsPage(self.content, self)
        self.budget_page = BudgetPage(self.content, self)
        self.result_page = ResultPage(self.content, self)
        self.pages = {"settings": self.settings_page, "expenses": self.expense_page,
                      "stats": self.stats_page, "budget": self.budget_page, "result": self.result_page}
        self.current_page = ""
        self.show_page("settings")

    def show_page(self, key: str) -> None:
        if self.current_page:
            self.pages[self.current_page].pack_forget()
        self.current_page = key
        self.pages[key].pack(fill="both", expand=True)
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
        for text, cmd in (("새 여행 시작", self.on_new_trip), ("예시 데이터 불러오기", self.on_load_demo)):
            lbl = _link(bottom, text, cmd)
            lbl.configure(bg=C_SIDEBAR, font=(FONT, 10))
            lbl.pack(anchor="w", pady=3)
        tk.Label(bottom, text="인터넷 연결 없이 동작합니다", bg=C_SIDEBAR, fg=C_MUTED,
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
