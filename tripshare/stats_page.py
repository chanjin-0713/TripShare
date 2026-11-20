"""기능 5: 지출 통계 화면 (Tkinter Canvas 도넛 차트)."""
from __future__ import annotations

import tkinter as tk

from . import ui
from .stats import Statistics, compute
from .ui import (
    AVATAR_COLORS, C_ACCENT, C_ACCENT_SOFT, C_AMBER, C_AMBER_BG, C_BG, C_MUTED, C_TEXT,
    FONT, card, chip,
)

CATEGORY_COLORS = {"숙박비": "#6366f1", "식비": "#f97316", "교통비": "#0ea5e9",
                   "관광 및 입장료": "#10b981", "쇼핑": "#ec4899", "기타": "#9ca3af"}
DONUT_SIZE = 240
RING_WIDTH = 42
GAP_DEGREES = 1.2  # 조각 사이 틈


class DonutChart(tk.Canvas):
    """도넛 차트. slices = [(값, 색)], 가운데에 합계를 표시한다."""

    def __init__(self, parent: tk.Misc) -> None:
        size = int(DONUT_SIZE * ui.SCALE)
        super().__init__(parent, width=size, height=size, bg=C_BG, highlightthickness=0)
        self.size = size
        self.slices: list[tuple[int, str]] = []
        self.center_title = "총 지출"
        self.center_value = ""

    def set_data(self, slices: list[tuple[int, str]], center_value: str) -> None:
        self.slices = [s for s in slices if s[0] > 0]
        self.center_value = center_value
        self.draw()

    def draw(self) -> None:
        self.delete("all")
        size = self.size
        ring = int(RING_WIDTH * ui.SCALE)
        inset = ring / 2 + 2
        box = (inset, inset, size - inset, size - inset)
        total = sum(v for v, _c in self.slices)
        if total == 0:
            self.create_oval(*box, outline="#e5e7eb", width=ring)
        elif len(self.slices) == 1:
            self.create_oval(*box, outline=self.slices[0][1], width=ring)
        else:
            angle = 90.0  # 12시 방향에서 시작, 시계 방향
            for value, color in self.slices:
                sweep = 360.0 * value / total
                draw_sweep = max(sweep - GAP_DEGREES, 0.5)
                self.create_arc(*box, start=angle - GAP_DEGREES / 2, extent=-draw_sweep, style="arc",
                                outline=color, width=ring)
                angle -= sweep
        self.create_text(size / 2, size / 2 - int(12 * ui.SCALE), text=self.center_title, fill=C_MUTED,
                         font=(FONT, 10))
        self.create_text(size / 2, size / 2 + int(10 * ui.SCALE), text=self.center_value, fill=C_TEXT,
                         font=(FONT, 13, "bold"))


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

        grid = tk.Frame(self, bg=C_BG)
        grid.pack(fill="both", expand=True, pady=(14, 0))
        grid.columnconfigure((0, 1), weight=1, uniform="col")
        self.payer_donut, self.payer_legend = self._section(grid, 0, "참가자별 실제 결제 금액")
        self.category_donut, self.category_legend = self._section(grid, 1, "카테고리별 지출 합계 · 비중")

    def _section(self, parent: tk.Frame, col: int, title: str) -> tuple[DonutChart, tk.Frame]:
        box = card(parent, padx=16, pady=14)
        box.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 7, 7 if col == 0 else 0))
        tk.Label(box, text=title, bg=C_BG, fg=C_TEXT, font=(FONT, 11, "bold")).pack(anchor="w")
        donut = DonutChart(box)
        donut.pack(pady=(10, 8))
        legend = tk.Frame(box, bg=C_BG)
        legend.pack(fill="x")
        legend.columnconfigure(1, weight=1)
        return donut, legend

    @staticmethod
    def _fill_legend(legend: tk.Frame, rows: list[tuple[str, str, str]]) -> None:
        """rows = [(색, 이름, 오른쪽 글자)] — 값이 큰 순서대로 이미 정렬되어 있어야 한다."""
        for w in legend.winfo_children():
            w.destroy()
        for i, (color, name, text) in enumerate(rows):
            muted = text.startswith("0원")
            tk.Label(legend, bg=color, width=2).grid(row=i, column=0, pady=3, padx=(0, 8))
            tk.Label(legend, text=name, bg=C_BG, fg=C_MUTED if muted else C_TEXT, font=(FONT, 10),
                     anchor="w").grid(row=i, column=1, sticky="w")
            tk.Label(legend, text=text, bg=C_BG, fg=C_MUTED if muted else C_TEXT, font=(FONT, 10),
                     anchor="e").grid(row=i, column=2, sticky="e", padx=(12, 0))

    def refresh(self) -> None:
        stats: Statistics = compute(self.app.trip)
        total_text = f"{stats.total:,}원"
        self.total_label.configure(text=f"전체 지출 합계 {total_text}")
        for w in self.chip_row.winfo_children():
            w.destroy()
        chip(self.chip_row, f"지출 {stats.expense_count}건", C_ACCENT, C_ACCENT_SOFT).pack(side="left")
        if stats.expense_count == 0:
            self.empty_label.pack(fill="x", pady=(10, 0), after=self.winfo_children()[0])
        else:
            self.empty_label.pack_forget()

        # 참가자별: 색은 참가자 순서 기준으로 고정하고, 표시는 금액이 큰 순서
        payers = [(AVATAR_COLORS[i % len(AVATAR_COLORS)], p) for i, p in enumerate(stats.payers)]
        payers.sort(key=lambda x: -x[1].amount)
        self.payer_donut.set_data([(p.amount, c) for c, p in payers], total_text)
        self._fill_legend(self.payer_legend, [
            (c, p.name, f"{p.amount:,}원 ({p.share_text})" if p.amount else "0원") for c, p in payers])

        cats = sorted(stats.categories, key=lambda c: -c.amount)
        self.category_donut.set_data([(c.amount, CATEGORY_COLORS[c.category]) for c in cats], total_text)
        self._fill_legend(self.category_legend, [
            (CATEGORY_COLORS[c.category], c.category,
             f"{c.amount:,}원 ({c.share_text})" if c.amount else "0원") for c in cats])
