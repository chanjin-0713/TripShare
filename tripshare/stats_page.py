"""지출 통계 화면: Tkinter Canvas로 그린 막대그래프(기본)와 원형(도넛) 그래프."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

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
GAP_DEGREES = 1.2  # 도넛 조각 사이 틈
ROW_H = 28


class BarChart(tk.Canvas):
    """가로 막대그래프. rows = [(라벨, 값, 값 옆에 쓸 글자, 색)] (가장 큰 값을 기준으로 막대 길이 결정)"""

    def __init__(self, parent: tk.Misc, label_width: int = 120, value_width: int = 230) -> None:
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
    TITLE_PAYER = "참가자별 결제 금액"
    TITLE_CATEGORY = "카테고리별 지출 금액 · 비중"

    def __init__(self, parent: tk.Misc, app) -> None:
        super().__init__(parent, bg=C_BG, padx=28, pady=22)
        self.app = app
        self.mode = "bar"

        head = card(self, padx=20, pady=14)
        head.pack(fill="x")
        top = tk.Frame(head, bg=C_BG)
        top.pack(fill="x")
        tk.Label(top, text="통계", bg=C_BG, fg=C_TEXT, font=(FONT, 16, "bold")).pack(side="left")
        self.donut_button = ttk.Button(top, text="원형 그래프", command=lambda: self.set_mode("donut"))
        self.donut_button.pack(side="right")
        self.bar_button = ttk.Button(top, text="막대그래프", command=lambda: self.set_mode("bar"))
        self.bar_button.pack(side="right", padx=(0, 6))
        self.total_label = tk.Label(head, bg=C_BG, fg=C_ACCENT, font=(FONT, 20, "bold"), anchor="w")
        self.total_label.pack(anchor="w", pady=(4, 2))
        self.chip_row = tk.Frame(head, bg=C_BG)
        self.chip_row.pack(anchor="w")
        self.empty_label = tk.Label(self, anchor="w", padx=12, pady=6, font=(FONT, 10), fg=C_AMBER, bg=C_AMBER_BG,
                                    text="아직 등록된 지출이 없습니다. '지출 내역'에서 경비를 등록하면 통계가 표시됩니다.")

        # 막대그래프 보기: 세로로 두 개
        self.bar_view = tk.Frame(self, bg=C_BG)
        self.payer_bars = self._bar_section(self.TITLE_PAYER)
        self.category_bars = self._bar_section(self.TITLE_CATEGORY)

        # 원형 그래프 보기: 가로로 두 개 + 범례
        self.donut_view = tk.Frame(self, bg=C_BG)
        self.donut_view.columnconfigure((0, 1), weight=1, uniform="col")
        self.payer_donut, self.payer_legend = self._donut_section(0, self.TITLE_PAYER)
        self.category_donut, self.category_legend = self._donut_section(1, self.TITLE_CATEGORY)
        self.set_mode("bar")

    # ---------- 구성 ----------
    def _bar_section(self, title: str) -> BarChart:
        tk.Label(self.bar_view, text=title, bg=C_BG, fg=C_TEXT, font=(FONT, 11, "bold")).pack(anchor="w", pady=(16, 6))
        box = card(self.bar_view, padx=16, pady=10)
        box.pack(fill="x")
        chart = BarChart(box)
        chart.pack(fill="x")
        return chart

    def _donut_section(self, col: int, title: str) -> tuple[DonutChart, tk.Frame]:
        box = card(self.donut_view, padx=16, pady=14)
        box.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 7, 7 if col == 0 else 0))
        tk.Label(box, text=title, bg=C_BG, fg=C_TEXT, font=(FONT, 11, "bold")).pack(anchor="w")
        donut = DonutChart(box)
        donut.pack(pady=(10, 8))
        legend = tk.Frame(box, bg=C_BG)
        legend.pack(fill="x")
        legend.columnconfigure(1, weight=1)
        return donut, legend

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.bar_view.pack_forget()
        self.donut_view.pack_forget()
        (self.bar_view if mode == "bar" else self.donut_view).pack(fill="both", expand=True, pady=(0, 0))
        self.bar_button.configure(style="Primary.TButton" if mode == "bar" else "Soft.TButton")
        self.donut_button.configure(style="Primary.TButton" if mode == "donut" else "Soft.TButton")

    @staticmethod
    def _fill_legend(legend: tk.Frame, rows: list[tuple[str, str, str]]) -> None:
        """rows = [(색, 이름, 오른쪽 글자)] — 값이 큰 순서대로 정렬되어 있어야 한다."""
        for w in legend.winfo_children():
            w.destroy()
        for i, (color, name, text) in enumerate(rows):
            muted = text.startswith("0원")
            tk.Label(legend, bg=color, width=2).grid(row=i, column=0, pady=3, padx=(0, 8))
            tk.Label(legend, text=name, bg=C_BG, fg=C_MUTED if muted else C_TEXT, font=(FONT, 10),
                     anchor="w").grid(row=i, column=1, sticky="w")
            tk.Label(legend, text=text, bg=C_BG, fg=C_MUTED if muted else C_TEXT, font=(FONT, 10),
                     anchor="e").grid(row=i, column=2, sticky="e", padx=(12, 0))

    # ---------- 갱신 ----------
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

        # 참가자별: 색은 참가자 순서 기준으로 고정, 원형은 금액이 큰 순서로 표시
        payers = [(AVATAR_COLORS[i % len(AVATAR_COLORS)], p) for i, p in enumerate(stats.payers)]
        self.payer_bars.set_rows([
            (p.name, p.amount, f"{p.amount:,}원" + (f" ({p.count}건)" if p.count else ""), c) for c, p in payers])
        by_amount = sorted(payers, key=lambda x: -x[1].amount)
        self.payer_donut.set_data([(p.amount, c) for c, p in by_amount], total_text)
        self._fill_legend(self.payer_legend, [
            (c, p.name, f"{p.amount:,}원 ({p.share_text})" if p.amount else "0원") for c, p in by_amount])

        cats = stats.categories
        self.category_bars.set_rows([
            (c.category, c.amount, f"{c.amount:,}원 ({c.share_text})", CATEGORY_COLORS[c.category]) for c in cats])
        sorted_cats = sorted(cats, key=lambda c: -c.amount)
        self.category_donut.set_data([(c.amount, CATEGORY_COLORS[c.category]) for c in sorted_cats], total_text)
        self._fill_legend(self.category_legend, [
            (CATEGORY_COLORS[c.category], c.category,
             f"{c.amount:,}원 ({c.share_text})" if c.amount else "0원") for c in sorted_cats])
