"""기능 4: 여행 예산 관리 화면."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from . import ui
from .budget import CAUTION, CAUTION_PERCENT, OK, OVER, UNSET, BudgetStatus, evaluate
from .models import MAX_BUDGET, ValidationError
from .ui import (
    C_AMBER, C_AMBER_BG, C_BG, C_BORDER, C_GREEN, C_GREEN_BG, C_MUTED, C_RED, C_RED_BG, C_TEXT,
    FONT, card,
)

# 상태별 (글자색, 배경색, 진행 막대 색)
LEVEL_STYLE = {
    UNSET: (C_AMBER, C_AMBER_BG, "#d1d5db"),
    OK: (C_GREEN, C_GREEN_BG, "#22c55e"),
    CAUTION: (C_AMBER, C_AMBER_BG, "#f97316"),
    OVER: (C_RED, C_RED_BG, "#ef4444"),
}
LEVEL_ICON = {UNSET: "ℹ", OK: "✔", CAUTION: "⚠", OVER: "⛔"}


class BudgetPage(tk.Frame):
    def __init__(self, parent: tk.Misc, app) -> None:
        super().__init__(parent, bg=C_BG, padx=28, pady=22)
        self.app = app
        self.status: BudgetStatus | None = None
        self._build_input()
        self._build_stats()
        self._build_progress()
        self.banner = tk.Label(self, anchor="w", padx=14, pady=10, font=(FONT, 11, "bold"), justify="left")
        self.banner.pack(fill="x", pady=(14, 0))

    # ---------- 구성 ----------
    def _build_input(self) -> None:
        box = card(self, padx=20, pady=14)
        box.pack(fill="x")
        tk.Label(box, text="예산 관리", bg=C_BG, fg=C_TEXT, font=(FONT, 16, "bold")).pack(anchor="w")
        row = tk.Frame(box, bg=C_BG)
        row.pack(fill="x", pady=(10, 0))
        tk.Label(row, text="여행 예산 (원)", bg=C_BG, fg=C_MUTED, font=(FONT, 10)).pack(side="left")
        self.budget_var = tk.StringVar()
        entry = ttk.Entry(row, textvariable=self.budget_var, font=(FONT, 11), justify="right", width=20)
        entry.pack(side="left", padx=10)
        entry.bind("<Return>", lambda _e: self.on_set_budget())
        ttk.Button(row, text="예산 설정", style="Primary.TButton", command=self.on_set_budget).pack(side="left")
        tk.Label(box, text=f"여행 시작 전에 전체 예산을 정해 두세요. 0원이면 '예산 미설정'으로 표시됩니다. "
                           f"(최대 {MAX_BUDGET:,}원)",
                 bg=C_BG, fg=C_MUTED, font=(FONT, 9)).pack(anchor="w", pady=(6, 0))

    def _build_stats(self) -> None:
        grid = tk.Frame(self, bg=C_BG)
        grid.pack(fill="x", pady=(14, 0))
        self.stat_titles: dict[str, tk.Label] = {}
        self.stat_values: dict[str, tk.Label] = {}
        for col, key in enumerate(("budget", "spent", "remaining", "percent")):
            grid.columnconfigure(col, weight=1, uniform="stat")
            box = card(grid, padx=16, pady=12)
            box.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0 if col == 3 else 6))
            title = tk.Label(box, bg=C_BG, fg=C_MUTED, font=(FONT, 10), anchor="w")
            title.pack(anchor="w")
            value = tk.Label(box, bg=C_BG, fg=C_TEXT, font=(FONT, 15, "bold"), anchor="w")
            value.pack(anchor="w", pady=(4, 0))
            self.stat_titles[key], self.stat_values[key] = title, value

    def _build_progress(self) -> None:
        box = card(self, padx=20, pady=16)
        box.pack(fill="x", pady=(14, 0))
        head = tk.Frame(box, bg=C_BG)
        head.pack(fill="x")
        tk.Label(head, text="예산 사용률", bg=C_BG, fg=C_TEXT, font=(FONT, 11, "bold")).pack(side="left")
        self.progress_text = tk.Label(head, bg=C_BG, fg=C_TEXT, font=(FONT, 11, "bold"))
        self.progress_text.pack(side="right")
        self.bar = tk.Canvas(box, height=int(26 * ui.SCALE), bg=C_BG, highlightthickness=0)
        self.bar.pack(fill="x", pady=(10, 2))
        self.bar.bind("<Configure>", lambda _e: self._draw_bar())
        scale = tk.Frame(box, bg=C_BG)
        scale.pack(fill="x")
        tk.Label(scale, text="0%", bg=C_BG, fg=C_MUTED, font=(FONT, 9)).pack(side="left")
        tk.Label(scale, text="100%", bg=C_BG, fg=C_MUTED, font=(FONT, 9)).pack(side="right")
        self.tick_label = tk.Label(scale, text=f"{CAUTION_PERCENT}% 주의선", bg=C_BG, fg=C_MUTED, font=(FONT, 9))
        self.tick_label.place(relx=CAUTION_PERCENT / 100, rely=0, anchor="n")

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
        self.budget_var.set(f"{trip.budget:,}")

        self.stat_titles["budget"].configure(text="설정 예산")
        self.stat_values["budget"].configure(text="예산 미설정" if st.is_unset else f"{st.budget:,}원")
        self.stat_titles["spent"].configure(text="실제 지출액")
        self.stat_values["spent"].configure(text=f"{st.spent:,}원")
        if st.level == OVER:
            self.stat_titles["remaining"].configure(text="초과 금액")
            self.stat_values["remaining"].configure(text=f"{st.over_amount:,}원", fg=C_RED)
        else:
            self.stat_titles["remaining"].configure(text="남은 예산")
            self.stat_values["remaining"].configure(text="-" if st.is_unset else f"{st.remaining:,}원", fg=C_TEXT)
        self.stat_titles["percent"].configure(text="예산 사용률")
        self.stat_values["percent"].configure(text=st.percent_text,
                                              fg=LEVEL_STYLE[st.level][0] if st.level != OK else C_TEXT)

        fg, bg, _bar = LEVEL_STYLE[st.level]
        self.progress_text.configure(text=st.percent_text, fg=fg if not st.is_unset else C_MUTED)
        self.banner.configure(text=f"{LEVEL_ICON[st.level]}  {st.message}", fg=fg, bg=bg)
        self._draw_bar()

    # ---------- 동작 ----------
    def on_set_budget(self) -> None:
        try:
            budget = self.app.trip.validate_budget(self.budget_var.get())
        except ValidationError as exc:
            messagebox.showwarning("예산 설정", str(exc), parent=self.app.root)
            return
        self.app.trip.budget = budget
        self.app._autosave()
        self.app.on_budget_changed()
