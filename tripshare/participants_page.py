"""참가자 관리 화면: 참가자 목록 / 추가 입력창 / 삭제 버튼."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from .models import MAX_NAME_LEN, MAX_PARTICIPANTS, MIN_PARTICIPANTS, Trip, ValidationError
from .ui import (
    AVATAR_COLORS, C_AMBER, C_AMBER_BG, C_BG, C_GREEN, C_GREEN_BG, C_MUTED, C_TEXT, FONT, GRID_COLUMNS,
    avatar, card,
)

PRIVACY_NOTE = "실제 이름·연락처 등 개인정보는 입력하지 마세요. 가상의 이름(예: 가상민수)을 사용하세요."


class ParticipantsPage(tk.Frame):
    def __init__(self, parent: tk.Misc, app) -> None:
        super().__init__(parent, bg=C_BG, padx=28, pady=22)
        self.app = app

        head = card(self, padx=20, pady=14)
        head.pack(fill="x")
        tk.Label(head, text="참가자 관리", bg=C_BG, fg=C_TEXT, font=(FONT, 16, "bold")).pack(anchor="w")
        self.count_label = tk.Label(head, bg=C_BG, fg=C_MUTED, font=(FONT, 10))
        self.count_label.pack(anchor="w", pady=(4, 0))
        tk.Label(head, text=PRIVACY_NOTE, bg=C_BG, fg=C_AMBER, font=(FONT, 9)).pack(anchor="w", pady=(6, 0))

        self.status_var = tk.StringVar()
        self.status = tk.Label(self, textvariable=self.status_var, anchor="w", padx=12, pady=6, font=(FONT, 10))
        self.status.pack(fill="x", pady=(10, 0))

        tk.Label(self, text="참가자 목록", bg=C_BG, fg=C_TEXT, font=(FONT, 11, "bold")).pack(anchor="w", pady=(16, 6))
        self.grid_frame = tk.Frame(self, bg=C_BG)
        self.grid_frame.pack(fill="x")
        for c in range(GRID_COLUMNS):
            self.grid_frame.columnconfigure(c, weight=1, uniform="col")

        add = card(self, padx=16, pady=12)
        add.pack(fill="x", pady=(14, 0))
        tk.Label(add, text="참가자 추가", bg=C_BG, fg=C_TEXT, font=(FONT, 11, "bold")).pack(anchor="w")
        row = tk.Frame(add, bg=C_BG)
        row.pack(fill="x", pady=(8, 0))
        self.new_name_var = tk.StringVar()
        self.new_entry = ttk.Entry(row, textvariable=self.new_name_var, font=(FONT, 10), width=28)
        self.new_entry.pack(side="left")
        self.new_entry.bind("<Return>", lambda _e: self.on_add())
        self.add_button = ttk.Button(row, text="+ 참가자 추가", style="Primary.TButton", command=self.on_add)
        self.add_button.pack(side="left", padx=10)
        tk.Label(row, text=f"이름은 {MAX_NAME_LEN}자 이하, 중복 불가", bg=C_BG, fg=C_MUTED,
                 font=(FONT, 9)).pack(side="left")

    @property
    def trip(self) -> Trip:
        return self.app.trip

    # ---------- 화면 갱신 ----------
    def refresh(self) -> None:
        for w in self.grid_frame.winfo_children():
            w.destroy()
        for i, name in enumerate(self.trip.participants):
            self._card(i, name)
        count = len(self.trip.participants)
        self.count_label.configure(
            text=f"현재 {count}명 등록 (최소 {MIN_PARTICIPANTS}명 ~ 최대 {MAX_PARTICIPANTS}명)")
        full = count >= MAX_PARTICIPANTS
        self.add_button.state(["disabled"] if full else ["!disabled"])
        self.new_entry.state(["disabled"] if full else ["!disabled"])
        problems = self.trip.setup_problems()
        if problems:
            self.set_status("⚠ " + " ".join(problems), C_AMBER, C_AMBER_BG)
        else:
            self.set_status("✔ 참가자 설정이 완료되었습니다. '지출 내역'에서 경비를 등록하세요.", C_GREEN, C_GREEN_BG)

    def _card(self, index: int, name: str) -> None:
        box = card(self.grid_frame, padx=12, pady=10)
        box.grid(row=index // GRID_COLUMNS, column=index % GRID_COLUMNS, sticky="ew", padx=4, pady=4)
        avatar(box, name[0], AVATAR_COLORS[index % len(AVATAR_COLORS)], 38).pack(side="right")
        info = tk.Frame(box, bg=C_BG)
        info.pack(side="left", fill="x", expand=True)
        tk.Label(info, text=name, bg=C_BG, fg=C_TEXT, font=(FONT, 11, "bold"), anchor="w").pack(anchor="w")
        buttons = tk.Frame(info, bg=C_BG)
        buttons.pack(anchor="w", pady=(6, 0))
        ttk.Button(buttons, text="이름 변경", style="Small.TButton",
                   command=lambda n=name: self.on_rename(n)).pack(side="left")
        ttk.Button(buttons, text="삭제", style="SmallDanger.TButton",
                   command=lambda n=name: self.on_remove(n)).pack(side="left", padx=(6, 0))

    def set_status(self, text: str, fg: str, bg: str) -> None:
        self.status_var.set(text)
        self.status.configure(fg=fg, bg=bg)

    # ---------- 이벤트 ----------
    def on_add(self) -> None:
        try:
            self.trip.add_participant(self.new_name_var.get())
        except ValidationError as exc:
            messagebox.showwarning("참가자 추가", str(exc), parent=self.app.root)
            self.new_entry.focus_set()
            return
        self.new_name_var.set("")
        self.app._autosave()
        self.app.refresh(reset_form=False)
        self.new_entry.focus_set()

    def on_remove(self, name: str) -> None:
        # 연결된 지출/최소 인원 위반은 확인창 이전에 차단
        try:
            probe = Trip(participants=list(self.trip.participants), expenses=self.trip.expenses)
            probe.remove_participant(name)
        except ValidationError as exc:
            messagebox.showwarning("삭제할 수 없음", str(exc), parent=self.app.root)
            return
        if not messagebox.askyesno("참가자 삭제", f"'{name}'님을 삭제할까요?", parent=self.app.root):
            return
        self.trip.remove_participant(name)
        self.app._autosave()
        self.app.refresh(reset_form=False)

    def on_rename(self, name: str) -> None:
        new = simpledialog.askstring("이름 변경", f"'{name}'의 새 이름:", initialvalue=name, parent=self.app.root)
        if new is None:
            return
        try:
            self.trip.rename_participant(name, new)
        except ValidationError as exc:
            messagebox.showwarning("이름 변경", str(exc), parent=self.app.root)
            return
        self.app._autosave()
        self.app.refresh(reset_form=False)
