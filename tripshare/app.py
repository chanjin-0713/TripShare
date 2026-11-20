"""TripShare GUI (Tkinter/ttk) - 기능 1: 여행 기본정보 설정."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from .models import (
    MAX_NAME_LEN, MAX_PARTICIPANTS, MIN_PARTICIPANTS, Trip, ValidationError,
    default_data_path, demo_trip, load_trip, save_trip,
)

APP_TITLE = "TripShare - 여행 경비 자동 정산"
PRIVACY_NOTE = "※ 실제 이름·연락처 등 개인정보는 입력하지 마세요. 가상의 이름(예: 가상민수)을 사용하세요."


class TripShareApp:
    def __init__(self, root: tk.Tk, data_path: Path | None = None) -> None:
        self.root = root
        self.data_path = Path(data_path) if data_path else default_data_path()
        self.trip = self._load_initial()

        root.title(APP_TITLE)
        root.minsize(520, 560)
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

    # ---------- UI ----------
    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="TripShare", font=("맑은 고딕", 18, "bold")).pack(anchor="w")
        ttk.Label(outer, text="1단계. 여행 기본정보를 설정하세요", foreground="#555").pack(anchor="w", pady=(0, 6))
        ttk.Label(outer, text=PRIVACY_NOTE, foreground="#b45309", wraplength=480).pack(anchor="w", pady=(0, 10))

        # 여행 정보
        info = ttk.LabelFrame(outer, text=" 여행 정보 ", padding=10)
        info.pack(fill="x")
        info.columnconfigure(1, weight=1)
        self.name_var = tk.StringVar()
        self.budget_var = tk.StringVar()
        ttk.Label(info, text="여행 이름").grid(row=0, column=0, sticky="w", pady=3)
        name_entry = ttk.Entry(info, textvariable=self.name_var)
        name_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=3)
        ttk.Label(info, text="여행 예산 (원)").grid(row=1, column=0, sticky="w", pady=3)
        budget_entry = ttk.Entry(info, textvariable=self.budget_var)
        budget_entry.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=3)
        ttk.Button(info, text="정보 저장", command=self.on_save_info).grid(row=2, column=1, sticky="e", pady=(6, 0))
        for entry in (name_entry, budget_entry):
            entry.bind("<Return>", lambda _e: self.on_save_info())
        self.name_entry = name_entry

        # 참가자
        box = ttk.LabelFrame(outer, text=" 여행 참가자 ", padding=10)
        box.pack(fill="both", expand=True, pady=(12, 0))
        box.columnconfigure(0, weight=1)
        box.rowconfigure(1, weight=1)

        self.count_label = ttk.Label(box)
        self.count_label.grid(row=0, column=0, columnspan=2, sticky="w")

        self.listbox = tk.Listbox(box, height=8, activestyle="none", exportselection=False,
                                  font=("맑은 고딕", 11))
        self.listbox.grid(row=1, column=0, sticky="nsew", pady=6)
        scroll = ttk.Scrollbar(box, orient="vertical", command=self.listbox.yview)
        scroll.grid(row=1, column=1, sticky="ns", pady=6)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.bind("<Double-Button-1>", lambda _e: self.on_rename())
        self.listbox.bind("<Delete>", lambda _e: self.on_remove())

        side = ttk.Frame(box)
        side.grid(row=1, column=2, sticky="n", padx=(10, 0), pady=6)
        ttk.Button(side, text="이름 변경", command=self.on_rename).pack(fill="x", pady=(0, 4))
        ttk.Button(side, text="선택 삭제", command=self.on_remove).pack(fill="x")

        add = ttk.Frame(box)
        add.grid(row=2, column=0, columnspan=3, sticky="ew")
        add.columnconfigure(0, weight=1)
        self.new_name_var = tk.StringVar()
        self.new_entry = ttk.Entry(add, textvariable=self.new_name_var)
        self.new_entry.grid(row=0, column=0, sticky="ew")
        self.new_entry.bind("<Return>", lambda _e: self.on_add())
        self.add_button = ttk.Button(add, text="참가자 추가", command=self.on_add)
        self.add_button.grid(row=0, column=1, padx=(8, 0))
        ttk.Label(add, text=f"이름은 {MAX_NAME_LEN}자 이하, 중복 불가", foreground="#777")\
            .grid(row=1, column=0, sticky="w", pady=(2, 0))

        # 하단 도구/상태
        tools = ttk.Frame(outer)
        tools.pack(fill="x", pady=(10, 0))
        ttk.Button(tools, text="예시 데이터 불러오기", command=self.on_load_demo).pack(side="left")
        ttk.Button(tools, text="새 여행 시작", command=self.on_new_trip).pack(side="left", padx=6)

        self.status_var = tk.StringVar()
        self.status = ttk.Label(outer, textvariable=self.status_var, relief="sunken", anchor="w", padding=4)
        self.status.pack(fill="x", pady=(10, 0))

    # ---------- 화면 갱신 ----------
    def refresh(self) -> None:
        self.name_var.set(self.trip.name)
        self.budget_var.set(f"{self.trip.budget:,}")
        self.refresh_participants()

    def refresh_participants(self, select: str | None = None) -> None:
        self.listbox.delete(0, "end")
        for i, n in enumerate(self.trip.participants, 1):
            self.listbox.insert("end", f"{i}. {n}")
        if select in self.trip.participants:
            idx = self.trip.participants.index(select)
            self.listbox.selection_set(idx)
            self.listbox.see(idx)
        count = len(self.trip.participants)
        self.count_label.configure(text=f"참가자 {count}명 (최소 {MIN_PARTICIPANTS}명 ~ 최대 {MAX_PARTICIPANTS}명)")
        full = count >= MAX_PARTICIPANTS
        self.add_button.state(["disabled"] if full else ["!disabled"])
        self.new_entry.state(["disabled"] if full else ["!disabled"])
        problems = self.trip.setup_problems()
        if problems:
            self.set_status("⚠ " + " ".join(problems), error=True)
        else:
            self.set_status("설정 완료: 다음 단계(지출 입력)를 진행할 수 있습니다.")

    def set_status(self, text: str, error: bool = False) -> None:
        self.status_var.set(text)
        self.status.configure(foreground="#b91c1c" if error else "#166534")

    def _selected_name(self) -> str | None:
        sel = self.listbox.curselection()
        if not sel:
            return None
        return self.trip.participants[sel[0]]

    # ---------- 이벤트 ----------
    def on_save_info(self) -> None:
        try:
            self.trip.set_basic_info(self.name_var.get(), self.budget_var.get())
        except ValidationError as exc:
            messagebox.showwarning("입력 확인", str(exc), parent=self.root)
            return
        self._autosave()
        self.refresh()
        self.set_status("여행 정보를 저장했습니다.")

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

    def on_remove(self) -> None:
        name = self._selected_name()
        if name is None:
            messagebox.showinfo("참가자 삭제", "삭제할 참가자를 목록에서 먼저 선택해 주세요.", parent=self.root)
            return
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

    def on_rename(self) -> None:
        name = self._selected_name()
        if name is None:
            messagebox.showinfo("이름 변경", "이름을 바꿀 참가자를 목록에서 먼저 선택해 주세요.", parent=self.root)
            return
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
    root = tk.Tk()
    TripShareApp(root)
    root.mainloop()
