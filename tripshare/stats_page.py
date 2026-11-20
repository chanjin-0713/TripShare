"""기능 5: 지출 통계 화면 (Tkinter Canvas 막대그래프)."""
from __future__ import annotations

import tkinter as tk

from . import ui
from .stats import Statistics, compute
from .ui import AVATAR_COLORS, C_ACCENT, C_ACCENT_SOFT, C_AMBER, C_AMBER_BG, C_BG, C_MUTED, C_TEXT, FONT, card, chip

CATEGORY_COLORS = {"숙박비": "#6366f1", "식비": "#f97316", "교통비": "#0ea5e9",
                   "관광 및 입장료": "#10b981", "쇼핑": "#ec4899", "기타": "#9ca3af"}
ROW_H = 28


class BarChart(tk.Canvas):
    """가로 막대그래프. rows = [(라벨, 값, 값 옆에 쓸 글자, 색)]"""

    def __init__(self, parent: tk.Misc, label_width: int = 120, value_width: int = 210) -> None:
        super().__init__(parent, bg=C_BG, highlightthickness=0, height=10)
        self.rows: list[tuple[str, int, str, str]] = []
        self.label_w = int(label_width * ui.SCALE)
        self.value_w = int(value_width * ui.SCALE)
        self.bind("<Configure>", lambda _e: self.draw())

    def set_rows(self, rows: list[tuple[str, int, str, str]]) -> None:
        self.rows = rows
        self.configure(height=max(1, len(rows)) * int(ROW_H * ui.SCALE))
        self.draw()

    def draw(self) -> None:
        self.delete("all")
        w = self.winfo_width()
        if w <= 1 or not self.rows:
            return
        row_h = int(ROW_H * ui.SCALE)
        max_bar = max(10, w - self.label_w - self.value_w)
        peak = max((r[1] for r in self.rows), default=0)
        pad = int(5 * ui.SCALE)
        for i, (label, value, text, color) in enumerate(self.rows):
            top = i * row_h
            mid = top + row_h / 2
            self.create_text(0, mid, text=label, anchor="w", fill=C_TEXT, font=(FONT, 10))
            length = int(max_bar * value / peak) if peak > 0 and value > 0 else 0
            if length > 0:
                self.create_rectangle(self.label_w, top + pad, self.label_w + max(length, 2), top + row_h - pad,
                                      fill=color, outline="")
            self.create_text(self.label_w + length + int(8 * ui.SCALE), mid, text=text, anchor="w",
                             fill=C_TEXT if value > 0 else C_MUTED, font=(FONT, 10))


class StatsPage(tk.Frame):
    def __init__(self, parent: tk.Misc, app) -> None:
        super().__init__(parent, bg=C_BG, padx=28, pady=22)
        self.app = app

        head = card(self, padx=20, pady=14)
        head.pack(fill="x")
        tk.Label(head, text="지출 통계", bg=C_BG, fg=C_TEXT, font=(FONT, 16, "bold")).pack(anchor="w")
        self.total_label = tk.Label(head, bg=C_BG, fg=C_ACCENT, font=(FONT, 20, "bold"), anchor="w")
        self.total_label.pack(anchor="w", pady=(4, 2))
        self.chip_row = tk.Frame(head, bg=C_BG)
        self.chip_row.pack(anchor="w")
        self.empty_label = tk.Label(self, anchor="w", padx=12, pady=6, font=(FONT, 10), fg=C_AMBER, bg=C_AMBER_BG,
                                    text="아직 등록된 지출이 없습니다. '지출 내역'에서 경비를 등록하면 통계가 표시됩니다.")

        self.payer_chart = self._section("참가자별 실제 결제 금액", label_width=110)
        self.category_chart = self._section("카테고리별 지출 합계 · 비중", label_width=110, value_width=260)

    def _section(self, title: str, label_width: int, value_width: int = 210) -> BarChart:
        tk.Label(self, text=title, bg=C_BG, fg=C_TEXT, font=(FONT, 11, "bold")).pack(anchor="w", pady=(16, 6))
        box = card(self, padx=16, pady=10)
        box.pack(fill="x")
        chart = BarChart(box, label_width, value_width)
        chart.pack(fill="x")
        return chart

    def refresh(self) -> None:
        stats: Statistics = compute(self.app.trip)
        self.total_label.configure(text=f"전체 지출 합계 {stats.total:,}원")
        for w in self.chip_row.winfo_children():
            w.destroy()
        chip(self.chip_row, f"지출 {stats.expense_count}건", C_ACCENT, C_ACCENT_SOFT).pack(side="left")
        if stats.expense_count == 0:
            self.empty_label.pack(fill="x", pady=(10, 0), after=self.winfo_children()[0])
        else:
            self.empty_label.pack_forget()

        self.payer_chart.set_rows([
            (p.name, p.amount, f"{p.amount:,}원" + (f" ({p.count}건)" if p.count else ""),
             AVATAR_COLORS[i % len(AVATAR_COLORS)])
            for i, p in enumerate(stats.payers)])
        self.category_chart.set_rows([
            (c.category, c.amount, f"{c.amount:,}원 ({c.share_text})", CATEGORY_COLORS[c.category])
            for c in stats.categories])
