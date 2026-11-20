"""대시보드: 총 경비 / 예산 / 남은 예산 / 참가자 수 / 예산 사용률(진행 막대) / 최근 지출 / 여행 정보 수정."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from . import ui
from .budget import CAUTION, OK, OVER, UNSET, BudgetStatus, evaluate, CAUTION_PERCENT
from .models import MAX_BUDGET, ValidationError
from .ui import (
    C_AMBER, C_AMBER_BG, C_BG, C_GREEN, C_GREEN_BG, C_MUTED, C_RED, C_RED_BG, C_TEXT, FONT, card,
)

RECENT_COUNT = 5
# 상태별 (글자색, 배경색, 진행 막대 색): 정상=녹색, 주의=주황, 초과=빨강
LEVEL_STYLE = {
    UNSET: (C_AMBER, C_AMBER_BG, "#d1d5db"),
    OK: (C_GREEN, C_GREEN_BG, "#22c55e"),
    CAUTION: (C_AMBER, C_AMBER_BG, "#f97316"),
    OVER: (C_RED, C_RED_BG, "#ef4444"),
}
LEVEL_ICON = {UNSET: "ℹ", OK: "✔", CAUTION: "⚠", OVER: "⛔"}


class DashboardPage(tk.Frame):
    def __init__(self, parent: tk.Misc, app) -> None:
        super().__init__(parent, bg=C_BG, padx=28, pady=22)
        self.app = app
        self.status: BudgetStatus | None = None
        tk.Label(self, text="대시보드", bg=C_BG, fg=C_TEXT, font=(FONT, 16, "bold")).pack(anchor="w")
        self._build_stats()
        self._build_usage()
        self._build_recent()
        self._build_info()

    # ---------- 구성 ----------
    def _build_stats(self) -> None:
        grid = tk.Frame(self, bg=C_BG)
        grid.pack(fill="x", pady=(12, 0))
        self.stat_titles: dict[str, tk.Label] = {}
        self.stat_values: dict[str, tk.Label] = {}
        keys = ("spent", "budget", "remaining", "people")
        for col, key in enumerate(keys):
            grid.columnconfigure(col, weight=1, uniform="stat")
            box = card(grid, padx=16, pady=12)
            box.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0 if col == len(keys) - 1 else 6))
            title = tk.Label(box, bg=C_BG, fg=C_MUTED, font=(FONT, 10), anchor="w")
            title.pack(anchor="w")
            value = tk.Label(box, bg=C_BG, fg=C_TEXT, font=(FONT, 15, "bold"), anchor="w")
            value.pack(anchor="w", pady=(4, 0))
            self.stat_titles[key], self.stat_values[key] = title, value

    def _build_usage(self) -> None:
        box = card(self, padx=20, pady=14)
        box.pack(fill="x", pady=(12, 0))
        head = tk.Frame(box, bg=C_BG)
        head.pack(fill="x")
        tk.Label(head, text="예산 사용률", bg=C_BG, fg=C_TEXT, font=(FONT, 11, "bold")).pack(side="left")
        self.percent_label = tk.Label(head, bg=C_BG, fg=C_TEXT, font=(FONT, 14, "bold"))
        self.percent_label.pack(side="right")
        self.bar = tk.Canvas(box, height=int(24 * ui.SCALE), bg=C_BG, highlightthickness=0)
        self.bar.pack(fill="x", pady=(8, 2))
        self.bar.bind("<Configure>", lambda _e: self._draw_bar())
        scale = tk.Frame(box, bg=C_BG)
        scale.pack(fill="x")
        tk.Label(scale, text="0%", bg=C_BG, fg=C_MUTED, font=(FONT, 9)).pack(side="left")
        tk.Label(scale, text="100%", bg=C_BG, fg=C_MUTED, font=(FONT, 9)).pack(side="right")
        tk.Label(scale, text=f"{CAUTION_PERCENT}% 주의선", bg=C_BG, fg=C_MUTED, font=(FONT, 9)).place(
            relx=CAUTION_PERCENT / 100, rely=0, anchor="n")
        self.banner = tk.Label(box, anchor="w", padx=12, pady=8, font=(FONT, 10, "bold"), justify="left")
        self.banner.pack(fill="x", pady=(10, 0))

    def _build_recent(self) -> None:
        head = tk.Frame(self, bg=C_BG)
        head.pack(fill="x", pady=(16, 6))
        tk.Label(head, text="최근 지출 목록", bg=C_BG, fg=C_TEXT, font=(FONT, 11, "bold")).pack(side="left")
        ttk.Button(head, text="전체 보기", style="Soft.TButton",
                   command=lambda: self.app.show_page("expenses")).pack(side="right")
        ttk.Button(head, text="+ 지출 등록", style="Primary.TButton",
                   command=lambda: self.app.show_page("expenses")).pack(side="right", padx=(0, 8))

        wrap = card(self)
        wrap.pack(fill="x")
        columns = ("title", "category", "payer", "amount")
        self.tree = ttk.Treeview(wrap, columns=columns, show="headings", selectmode="none", height=RECENT_COUNT)
        for key, text, width, anchor in (("title", "항목", 260, "w"), ("category", "카테고리", 130, "w"),
                                         ("payer", "결제한 사람", 130, "w"), ("amount", "금액", 140, "e")):
            self.tree.heading(key, text=text, anchor="e" if anchor == "e" else "w")
            self.tree.column(key, width=int(width * ui.SCALE), anchor=anchor, stretch=key == "title")
        self.tree.pack(fill="x")
        self.empty_label = tk.Label(wrap, text="아직 등록된 지출이 없습니다.", bg="white", fg=C_MUTED, font=(FONT, 10))

    def _build_info(self) -> None:
        box = card(self, padx=20, pady=14)
        box.pack(fill="x", pady=(16, 0))
        box.columnconfigure(1, weight=1)
        box.columnconfigure(3, weight=1)
        tk.Label(box, text="여행 정보 수정", bg=C_BG, fg=C_TEXT, font=(FONT, 11, "bold")).grid(
            row=0, column=0, columnspan=5, sticky="w", pady=(0, 8))
        self.name_var = tk.StringVar()
        self.budget_var = tk.StringVar()
        tk.Label(box, text="여행 이름", bg=C_BG, fg=C_MUTED, font=(FONT, 10)).grid(row=1, column=0, sticky="w")
        self.name_entry = ttk.Entry(box, textvariable=self.name_var, font=(FONT, 10))
        self.name_entry.grid(row=1, column=1, sticky="ew", padx=(10, 20))
        tk.Label(box, text="여행 예산 (원)", bg=C_BG, fg=C_MUTED, font=(FONT, 10)).grid(row=1, column=2, sticky="w")
        self.budget_entry = ttk.Entry(box, textvariable=self.budget_var, font=(FONT, 10), justify="right")
        self.budget_entry.grid(row=1, column=3, sticky="ew", padx=(10, 20))
        ttk.Button(box, text="정보 저장", style="Primary.TButton", command=self.on_save_info).grid(row=1, column=4)
        for e in (self.name_entry, self.budget_entry):
            e.bind("<Return>", lambda _e: self.on_save_info())
        tk.Label(box, text=f"예산은 0원이면 '예산 미설정'으로 표시됩니다. (최대 {MAX_BUDGET:,}원)",
                 bg=C_BG, fg=C_MUTED, font=(FONT, 9)).grid(row=2, column=0, columnspan=5, sticky="w", pady=(8, 0))

    # ---------- 그리기 / 갱신 ----------
    def _draw_bar(self) -> None:
        c = self.bar
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w <= 1:
            return
        c.create_rectangle(0, 0, w, h, fill="#e5e7eb", outline="")
        if self.status is not None and not self.status.is_unset:
            fill_w = int(w * self.status.bar_ratio)
            if fill_w > 0:
                c.create_rectangle(0, 0, fill_w, h, fill=LEVEL_STYLE[self.status.level][2], outline="")
        x = int(w * CAUTION_PERCENT / 100)
        c.create_line(x, 0, x, h, fill="#6b7280", dash=(3, 2))

    def refresh(self) -> None:
        trip = self.app.trip
        st = self.status = evaluate(trip.budget, trip.total_spent)
        self.name_var.set(trip.name)
        self.budget_var.set(f"{trip.budget:,}")

        self.stat_titles["spent"].configure(text="총 여행 경비")
        self.stat_values["spent"].configure(text=f"{st.spent:,}원")
        self.stat_titles["budget"].configure(text="여행 예산")
        self.stat_values["budget"].configure(text="예산 미설정" if st.is_unset else f"{st.budget:,}원")
        if st.level == OVER:
            self.stat_titles["remaining"].configure(text="초과 금액")
            self.stat_values["remaining"].configure(text=f"{st.over_amount:,}원", fg=C_RED)
        else:
            self.stat_titles["remaining"].configure(text="남은 예산")
            self.stat_values["remaining"].configure(text="-" if st.is_unset else f"{st.remaining:,}원", fg=C_TEXT)
        self.stat_titles["people"].configure(text="참가자 수")
        self.stat_values["people"].configure(text=f"{len(trip.participants)}명")

        fg, bg, _bar = LEVEL_STYLE[st.level]
        self.percent_label.configure(text=st.percent_text, fg=C_MUTED if st.is_unset else fg)
        self.banner.configure(text=f"{LEVEL_ICON[st.level]}  {st.message}", fg=fg, bg=bg)
        self._draw_bar()

        self.tree.delete(*self.tree.get_children())
        recent = list(reversed(trip.expenses))[:RECENT_COUNT]  # 가장 나중에 등록한 지출부터
        for i, e in enumerate(recent):
            self.tree.insert("", "end", iid=str(i), values=(e.title, e.category, e.payer, f"{e.amount:,}원"))
        if recent:
            self.empty_label.place_forget()
        else:
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")

    # ---------- 동작 ----------
    def on_save_info(self) -> None:
        try:
            self.app.trip.set_basic_info(self.name_var.get(), self.budget_var.get())
        except ValidationError as exc:
            messagebox.showwarning("입력 확인", str(exc), parent=self.app.root)
            return
        self.app._autosave()
        self.app.refresh(reset_form=False)
