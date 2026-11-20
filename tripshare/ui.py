"""공통 색상/글꼴/작은 위젯 도우미."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

FONT = "맑은 고딕"
C_BG = "#ffffff"
C_SIDEBAR = "#f9fafb"
C_BORDER = "#e5e7eb"
C_TEXT = "#111827"
C_MUTED = "#6b7280"
C_ACCENT = "#1d4ed8"
C_ACCENT_SOFT = "#eef2ff"
C_GREEN, C_GREEN_BG = "#166534", "#dcfce7"  # 녹색: 정상
C_RED, C_RED_BG = "#b91c1c", "#fee2e2"  # 빨간색: 초과/오류
C_AMBER, C_AMBER_BG = "#c2410c", "#ffedd5"  # 주황색: 주의/경고
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


class ScrollArea(tk.Frame):
    """내용이 창보다 크면 세로 스크롤(스크롤바·마우스 휠)이 생기는 영역.

    화면이 작아도 모든 기능에 접근할 수 있게 해 준다. 내용은 `inner`에 넣는다.
    창이 충분히 크면 inner가 영역 전체를 채워서 pack(expand=True)가 평소처럼 동작한다.
    """

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, bg=C_BG)
        self.canvas = tk.Canvas(self, bg=C_BG, highlightthickness=0)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self._on_yscroll)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=C_BG)
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda _e: self._fit())
        self.canvas.bind("<Configure>", lambda _e: self._fit())
        self.bind_all("<MouseWheel>", self._on_wheel, add="+")

    def _fit(self) -> None:
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.canvas.itemconfigure(self._window, width=width, height=max(self.inner.winfo_reqheight(), height))
        self.canvas.configure(scrollregion=(0, 0, width, max(self.inner.winfo_reqheight(), height)))

    def _on_yscroll(self, first: str, last: str) -> None:
        self.vbar.set(first, last)
        needed = float(first) > 0.0 or float(last) < 1.0
        if needed and not self.vbar.winfo_ismapped():
            self.vbar.pack(side="right", fill="y")
        elif not needed and self.vbar.winfo_ismapped():
            self.vbar.pack_forget()

    def _on_wheel(self, event) -> None:
        if not self.winfo_ismapped() or not self.vbar.winfo_ismapped():
            return
        if isinstance(event.widget, (ttk.Treeview, tk.Listbox)):
            return  # 목록 위에서는 목록 자체가 스크롤된다
        self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
