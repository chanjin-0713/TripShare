"""공통 색상/글꼴/작은 위젯 도우미."""
from __future__ import annotations

import tkinter as tk

FONT = "맑은 고딕"
C_BG = "#ffffff"
C_SIDEBAR = "#f9fafb"
C_BORDER = "#e5e7eb"
C_TEXT = "#111827"
C_MUTED = "#6b7280"
C_ACCENT = "#1d4ed8"
C_ACCENT_SOFT = "#eef2ff"
C_GREEN, C_GREEN_BG = "#166534", "#dcfce7"
C_RED, C_RED_BG = "#b91c1c", "#fee2e2"
C_AMBER, C_AMBER_BG = "#92400e", "#fef3c7"
AVATAR_COLORS = ["#ef4444", "#f59e0b", "#10b981", "#3b82f6", "#8b5cf6",
                 "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#84cc16"]
GRID_COLUMNS = 3
SCALE = 1.0  # 화면 배율(DPI). set_scale()로 갱신


def set_scale(value: float) -> None:
    global SCALE
    SCALE = value


def card(parent: tk.Misc, **kw) -> tk.Frame:
    return tk.Frame(parent, bg=C_BG, highlightbackground=C_BORDER, highlightthickness=1, **kw)


def chip(parent: tk.Misc, text: str, fg: str, bg: str) -> tk.Label:
    return tk.Label(parent, text=text, fg=fg, bg=bg, font=(FONT, 9, "bold"), padx=8, pady=1)


def link(parent: tk.Misc, text: str, command, fg: str = C_MUTED) -> tk.Label:
    lbl = tk.Label(parent, text=text, fg=fg, bg=parent["bg"], font=(FONT, 9), cursor="hand2")
    lbl.bind("<Button-1>", lambda _e: command())
    lbl.bind("<Enter>", lambda _e: lbl.configure(font=(FONT, 9, "underline")))
    lbl.bind("<Leave>", lambda _e: lbl.configure(font=(FONT, 9)))
    return lbl


def avatar(parent: tk.Misc, text: str, color: str, size: int = 40) -> tk.Canvas:
    points = max(8, int(size * 0.3))  # 글꼴 pt는 Tk가 DPI에 맞춰 자동 확대
    size = int(size * SCALE)
    c = tk.Canvas(parent, width=size, height=size, bg=parent["bg"], highlightthickness=0)
    c.create_oval(1, 1, size - 1, size - 1, fill=color, outline=color)
    c.create_text(size / 2, size / 2, text=text, fill="white", font=(FONT, points, "bold"))
    return c
