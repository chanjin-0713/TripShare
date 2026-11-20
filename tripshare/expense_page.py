"""기능 2: 여행 경비 등록 화면 (등록 / 수정 / 삭제)."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from . import ui
from .budget import CAUTION, OK, OVER, evaluate
from .models import CATEGORIES, DEFAULT_CATEGORY, MIN_PARTICIPANTS, ValidationError
from .ui import (
    C_ACCENT, C_ACCENT_SOFT, C_AMBER, C_AMBER_BG, C_BG, C_BORDER, C_GREEN, C_GREEN_BG, C_MUTED, C_RED,
    C_RED_BG, C_TEXT, FONT, card, chip, link,
)


class ExpensePage(tk.Frame):
    def __init__(self, parent: tk.Misc, app) -> None:
        super().__init__(parent, bg=C_BG, padx=28, pady=22)
        self.app = app
        self.editing: int | None = None  # 수정 중인 지출의 인덱스

        self._setup_style()
        self._build_summary()
        self._build_form()
        self._build_list()

    @property
    def trip(self):
        return self.app.trip

    # ---------- 구성 ----------
    def _setup_style(self) -> None:
        style = ttk.Style(self)
        style.configure("Treeview", rowheight=int(32 * ui.SCALE), font=(FONT, 10), background="white",
                        fieldbackground="white", borderwidth=0, foreground=C_TEXT)
        style.configure("Treeview.Heading", font=(FONT, 9, "bold"), background="#f9fafb",
                        foreground=C_MUTED, relief="flat", padding=(6, 6))
        style.map("Treeview", background=[("selected", C_ACCENT_SOFT)], foreground=[("selected", C_ACCENT)])
        style.map("Treeview.Heading", background=[("active", "#f3f4f6")])
        style.configure("TCombobox", fieldbackground="white", background="white", bordercolor=C_BORDER, padding=5)
        style.map("TCombobox", fieldbackground=[("readonly", "white")], foreground=[("readonly", C_TEXT)],
                  selectbackground=[("readonly", "white")], selectforeground=[("readonly", C_TEXT)])
        self.option_add("*TCombobox*Listbox.font", (FONT, 10))

    def _build_summary(self) -> None:
        box = card(self, padx=20, pady=14)
        box.pack(fill="x")
        tk.Label(box, text="지출 내역", bg=C_BG, fg=C_TEXT, font=(FONT, 16, "bold")).pack(anchor="w")
        self.total_label = tk.Label(box, bg=C_BG, fg=C_TEXT, font=(FONT, 12), anchor="w")
        self.total_label.pack(anchor="w", pady=(2, 6))
        self.chip_row = tk.Frame(box, bg=C_BG)
        self.chip_row.pack(anchor="w")

    def _build_form(self) -> None:
        box = card(self, padx=20, pady=14)
        box.pack(fill="x", pady=(14, 0))
        for col in (1, 3):
            box.columnconfigure(col, weight=1, uniform="f")

        self.form_title = tk.Label(box, bg=C_BG, fg=C_TEXT, font=(FONT, 11, "bold"))
        self.form_title.grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 8))

        self.title_var = tk.StringVar()
        self.amount_var = tk.StringVar()
        self.payer_var = tk.StringVar()
        self.category_var = tk.StringVar(value=DEFAULT_CATEGORY)

        def label(text: str, row: int, col: int) -> None:
            tk.Label(box, text=text, bg=C_BG, fg=C_MUTED, font=(FONT, 10)).grid(
                row=row, column=col, sticky="w", pady=4)

        label("항목 이름", 1, 0)
        self.title_entry = ttk.Entry(box, textvariable=self.title_var, font=(FONT, 10))
        self.title_entry.grid(row=1, column=1, sticky="ew", padx=(10, 20), pady=4)
        label("금액 (원)", 1, 2)
        self.amount_entry = ttk.Entry(box, textvariable=self.amount_var, font=(FONT, 10), justify="right")
        self.amount_entry.grid(row=1, column=3, sticky="ew", padx=(10, 20), pady=4)

        label("결제한 사람", 2, 0)
        self.payer_box = ttk.Combobox(box, textvariable=self.payer_var, state="readonly", font=(FONT, 10))
        self.payer_box.grid(row=2, column=1, sticky="ew", padx=(10, 20), pady=4)
        label("카테고리", 2, 2)
        self.category_box = ttk.Combobox(box, textvariable=self.category_var, values=CATEGORIES,
                                         state="readonly", font=(FONT, 10))
        self.category_box.grid(row=2, column=3, sticky="ew", padx=(10, 20), pady=4)

        buttons = tk.Frame(box, bg=C_BG)
        buttons.grid(row=1, column=4, rowspan=2, sticky="e")
        self.submit_button = ttk.Button(buttons, style="Primary.TButton", command=self.on_submit)
        self.submit_button.pack(fill="x")
        self.cancel_button = ttk.Button(buttons, text="취소", style="Soft.TButton", command=self.cancel_edit)

        self.hint = tk.Label(box, bg=C_BG, fg=C_MUTED, font=(FONT, 9), anchor="w",
                             text="금액은 1원 이상의 정수(예: 35000 또는 35,000)로 입력하세요.")
        self.hint.grid(row=3, column=0, columnspan=5, sticky="w", pady=(6, 0))

        for e in (self.title_entry, self.amount_entry):
            e.bind("<Return>", lambda _e: self.on_submit())
        self.bind_all("<Escape>", self._on_escape, add="+")

    def _build_list(self) -> None:
        top = tk.Frame(self, bg=C_BG)
        top.pack(fill="x", pady=(16, 6))
        self.count_label = tk.Label(top, bg=C_BG, fg=C_TEXT, font=(FONT, 11, "bold"))
        self.count_label.pack(side="left")
        link(top, "선택 삭제", self.on_delete, fg=C_RED).pack(side="right")
        tk.Label(top, text="·", bg=C_BG, fg=C_MUTED).pack(side="right", padx=6)
        link(top, "선택 수정", self.on_edit).pack(side="right")

        wrap = card(self)
        wrap.pack(fill="both", expand=True)
        columns = ("title", "category", "payer", "amount")
        self.tree = ttk.Treeview(wrap, columns=columns, show="headings", selectmode="browse")
        for key, text, width, anchor in (("title", "항목", 260, "w"), ("category", "카테고리", 130, "w"),
                                         ("payer", "결제한 사람", 130, "w"), ("amount", "금액", 140, "e")):
            self.tree.heading(key, text=text, anchor="e" if anchor == "e" else "w")
            self.tree.column(key, width=int(width * ui.SCALE), anchor=anchor, stretch=key == "title")
        scroll = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda _e: self.on_edit())
        self.tree.bind("<Delete>", lambda _e: self.on_delete())
        self.empty_label = tk.Label(wrap, text="아직 등록된 지출이 없습니다.\n위 입력란에서 첫 지출을 등록해 보세요.",
                                    bg="white", fg=C_MUTED, font=(FONT, 11), justify="center")

    # ---------- 화면 갱신 ----------
    def refresh(self, reset_form: bool = False) -> None:
        names = self.trip.participants
        self.payer_box.configure(values=names)
        if self.payer_var.get() not in names:
            self.payer_var.set(names[0] if names else "")
        if reset_form or (self.editing is not None and self.editing >= len(self.trip.expenses)):
            self._leave_edit_mode(clear=True)
        self._refresh_mode_labels()
        self._refresh_list()
        self._refresh_summary()

    def _refresh_mode_labels(self) -> None:
        if self.editing is None:
            self.form_title.configure(text="새 지출 등록")
            self.submit_button.configure(text="+ 지출 등록")
            self.cancel_button.pack_forget()
        else:
            self.form_title.configure(text=f"지출 수정 중 (#{self.editing + 1})")
            self.submit_button.configure(text="수정 저장")
            self.cancel_button.pack(fill="x", pady=(6, 0))

    def _refresh_list(self, select: int | None = None) -> None:
        self.tree.delete(*self.tree.get_children())
        for i, e in enumerate(self.trip.expenses):
            self.tree.insert("", "end", iid=str(i),
                             values=(e.title, e.category, e.payer, f"{e.amount:,}원"))
        self.count_label.configure(text=f"등록된 지출 {len(self.trip.expenses)}건")
        if self.trip.expenses:
            self.empty_label.place_forget()
        else:
            self.empty_label.place(relx=0.5, rely=0.4, anchor="center")
        if select is not None and str(select) in self.tree.get_children():
            self.tree.selection_set(str(select))
            self.tree.see(str(select))

    def _refresh_summary(self) -> None:
        st = evaluate(self.trip.budget, self.trip.total_spent)
        self.total_label.configure(text=f"총 지출 {st.spent:,}원")
        for w in self.chip_row.winfo_children():
            w.destroy()
        chip(self.chip_row, f"{len(self.trip.expenses)}건", C_ACCENT, C_ACCENT_SOFT).pack(side="left")
        if st.is_unset:
            chip(self.chip_row, "예산 미설정", C_AMBER, C_AMBER_BG).pack(side="left", padx=6)
            return
        text = f"예산 {st.over_amount:,}원 초과" if st.level == OVER else f"예산 {st.remaining:,}원 남음"
        fg, bg = {OK: (C_GREEN, C_GREEN_BG), CAUTION: (C_AMBER, C_AMBER_BG), OVER: (C_RED, C_RED_BG)}[st.level]
        chip(self.chip_row, text, fg, bg).pack(side="left", padx=6)
        chip(self.chip_row, f"예산 {st.budget:,}원의 {st.percent_text} 사용", C_MUTED, "#f3f4f6").pack(side="left")

    # ---------- 동작 ----------
    def _selected_index(self) -> int | None:
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _leave_edit_mode(self, clear: bool) -> None:
        self.editing = None
        if clear:
            self.title_var.set("")
            self.amount_var.set("")
            self.category_var.set(DEFAULT_CATEGORY)
        self._refresh_mode_labels()

    def _on_escape(self, _event) -> None:
        if self.editing is not None and self.winfo_ismapped():
            self.cancel_edit()

    def cancel_edit(self) -> None:
        self._leave_edit_mode(clear=True)
        self.tree.selection_remove(self.tree.selection())

    def on_submit(self) -> None:
        if len(self.trip.participants) < MIN_PARTICIPANTS:
            messagebox.showwarning("지출 등록", f"먼저 '여행 설정'에서 참가자를 최소 {MIN_PARTICIPANTS}명 등록해 주세요.",
                                   parent=self.app.root)
            return
        before = evaluate(self.trip.budget, self.trip.total_spent).level
        args = (self.title_var.get(), self.amount_var.get(), self.payer_var.get(), self.category_var.get())
        try:
            if self.editing is None:
                self.trip.add_expense(*args)
                index = len(self.trip.expenses) - 1
            else:
                index = self.editing
                self.trip.update_expense(index, *args)
        except ValidationError as exc:
            messagebox.showwarning("입력 확인", str(exc), parent=self.app.root)
            return
        self.app._autosave()
        self._leave_edit_mode(clear=True)
        self._refresh_list(select=index)
        self._refresh_summary()
        self.title_entry.focus_set()
        self._warn_if_worse(before)

    def _warn_if_worse(self, before: str) -> None:
        """등록/수정으로 예산 상태가 '주의'나 '초과'로 새로 바뀌면 한 번 알려 준다."""
        st = evaluate(self.trip.budget, self.trip.total_spent)
        rank = {"unset": 0, "ok": 0, "caution": 1, "over": 2}
        if rank[st.level] <= rank[before]:
            return  # 상태가 나빠진 경우에만 알린다
        if st.level == OVER:
            messagebox.showwarning("예산 초과 경고", st.message, parent=self.app.root)
        elif st.level == CAUTION:
            messagebox.showinfo("예산 주의", st.message, parent=self.app.root)

    def on_edit(self) -> None:
        index = self._selected_index()
        if index is None:
            messagebox.showinfo("지출 수정", "수정할 지출을 목록에서 먼저 선택해 주세요.", parent=self.app.root)
            return
        e = self.trip.expenses[index]
        self.editing = index
        self.title_var.set(e.title)
        self.amount_var.set(str(e.amount))
        self.payer_var.set(e.payer)
        self.category_var.set(e.category)
        self._refresh_mode_labels()
        self.title_entry.focus_set()

    def on_delete(self) -> None:
        index = self._selected_index()
        if index is None:
            messagebox.showinfo("지출 삭제", "삭제할 지출을 목록에서 먼저 선택해 주세요.", parent=self.app.root)
            return
        e = self.trip.expenses[index]
        if not messagebox.askyesno("지출 삭제", f"'{e.title}' ({e.amount:,}원) 지출을 삭제할까요?",
                                   parent=self.app.root):
            return
        self.trip.remove_expense(index)
        self.app._autosave()
        self._leave_edit_mode(clear=True)  # 인덱스가 밀리므로 수정 상태 해제
        self._refresh_list()
        self._refresh_summary()
