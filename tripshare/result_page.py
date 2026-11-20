"""기능 3: 정산 결과 화면."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import exporter, ui
from .models import ValidationError
from .settlement import calculate
from .ui import (
    C_ACCENT, C_ACCENT_SOFT, C_AMBER, C_AMBER_BG, C_BG, C_GREEN, C_GREEN_BG, C_MUTED, C_RED,
    C_TEXT, FONT, card, chip,
)


class ResultPage(tk.Frame):
    def __init__(self, parent: tk.Misc, app) -> None:
        super().__init__(parent, bg=C_BG, padx=28, pady=22)
        self.app = app
        self._build_summary()
        self.notice = tk.Label(self, anchor="w", padx=12, pady=6, font=(FONT, 10))
        self._build_balance_table()
        self._build_transfer_table()

    # ---------- 구성 ----------
    def _build_summary(self) -> None:
        box = card(self, padx=20, pady=14)
        box.pack(fill="x")
        top = tk.Frame(box, bg=C_BG)
        top.pack(fill="x")
        tk.Label(top, text="정산 결과", bg=C_BG, fg=C_TEXT, font=(FONT, 16, "bold")).pack(side="left")
        ttk.Button(top, text="CSV로 저장", style="Soft.TButton",
                   command=lambda: self.on_export("csv")).pack(side="right")
        ttk.Button(top, text="TXT로 저장", style="Soft.TButton",
                   command=lambda: self.on_export("txt")).pack(side="right", padx=(0, 8))
        self.total_label = tk.Label(box, bg=C_BG, fg=C_ACCENT, font=(FONT, 20, "bold"), anchor="w")
        self.total_label.pack(anchor="w", pady=(4, 2))
        self.chip_row = tk.Frame(box, bg=C_BG)
        self.chip_row.pack(anchor="w", pady=(2, 0))
        self.remainder_label = tk.Label(box, bg=C_BG, fg=C_MUTED, font=(FONT, 9), anchor="w")
        self.remainder_label.pack(anchor="w", pady=(6, 0))
        self.save_label = tk.Label(box, bg=C_BG, fg=C_GREEN, font=(FONT, 9), anchor="w")
        self.save_label.pack(anchor="w")

    def _make_tree(self, parent: tk.Misc, columns, height: int) -> ttk.Treeview:
        wrap = card(parent)
        wrap.pack(fill="both", expand=True)
        tree = ttk.Treeview(wrap, columns=[c[0] for c in columns], show="headings",
                            selectmode="none", height=height)
        for key, text, width, anchor, stretch in columns:
            tree.heading(key, text=text, anchor="e" if anchor == "e" else "w")
            tree.column(key, width=int(width * ui.SCALE), anchor=anchor, stretch=stretch)
        scroll = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)
        tree.tag_configure("plus", foreground=C_GREEN)
        tree.tag_configure("minus", foreground=C_RED)
        tree.tag_configure("even", foreground=C_MUTED)
        return tree

    def _build_balance_table(self) -> None:
        self.balance_frame = tk.Frame(self, bg=C_BG)
        self.balance_frame.pack(fill="both", expand=True, pady=(14, 0))
        tk.Label(self.balance_frame, text="참가자별 정산", bg=C_BG, fg=C_TEXT,
                 font=(FONT, 11, "bold")).pack(anchor="w", pady=(0, 6))
        self.balance_tree = self._make_tree(self.balance_frame, [
            ("name", "참가자", 120, "w", False), ("paid", "실제 결제 금액", 130, "e", False),
            ("share", "부담 금액", 120, "e", False), ("diff", "정산 차액", 120, "e", False),
            ("status", "구분", 120, "w", True),
        ], height=5)

    def _build_transfer_table(self) -> None:
        self.transfer_frame = tk.Frame(self, bg=C_BG)
        self.transfer_frame.pack(fill="both", expand=True, pady=(14, 0))
        head = tk.Frame(self.transfer_frame, bg=C_BG)
        head.pack(fill="x", pady=(0, 6))
        tk.Label(head, text="최종 송금 목록", bg=C_BG, fg=C_TEXT, font=(FONT, 11, "bold")).pack(side="left")
        self.transfer_count = tk.Label(head, bg=C_BG, fg=C_MUTED, font=(FONT, 9))
        self.transfer_count.pack(side="left", padx=8)
        self.transfer_tree = self._make_tree(self.transfer_frame, [
            ("no", "순서", 60, "w", False), ("sentence", "송금 안내", 480, "w", True),
            ("amount", "금액", 140, "e", False),
        ], height=4)

    # ---------- 내보내기 ----------
    def on_export(self, kind: str) -> None:
        trip = self.app.trip
        try:
            exporter.build_txt(trip)  # 정산 가능한 상태인지 먼저 확인 (참가자 2명 이상)
        except ValidationError as exc:
            messagebox.showwarning("내보내기", f"{exc}\n'여행 설정'에서 참가자를 등록해 주세요.", parent=self.app.root)
            return
        label = {"txt": "TXT 파일", "csv": "CSV 파일 (Excel에서 열기)"}[kind]
        path = filedialog.asksaveasfilename(
            parent=self.app.root, title="정산 결과 저장", defaultextension=f".{kind}",
            initialfile=exporter.default_filename(trip, kind),
            filetypes=[(label, f"*.{kind}"), ("모든 파일", "*.*")])
        if not path:  # 사용자가 취소
            return
        try:
            (exporter.save_txt if kind == "txt" else exporter.save_csv)(trip, Path(path))
        except OSError as exc:
            messagebox.showerror(
                "저장 실패",
                "파일을 저장하지 못했습니다.\n"
                "다른 프로그램(예: Excel)에서 같은 파일을 열어 둔 것은 아닌지 확인해 주세요.\n\n"
                f"{exc}",
                parent=self.app.root)
            return
        self.save_label.configure(text=f"✔ 저장했습니다: {path}")

    # ---------- 갱신 ----------
    def _show_notice(self, text: str | None) -> None:
        if text:
            self.notice.configure(text=text, fg=C_AMBER, bg=C_AMBER_BG)
            self.notice.pack(fill="x", pady=(10, 0), after=self.winfo_children()[0])
        else:
            self.notice.pack_forget()

    def refresh(self) -> None:
        trip = self.app.trip
        for tree in (self.balance_tree, self.transfer_tree):
            tree.delete(*tree.get_children())
        for w in self.chip_row.winfo_children():
            w.destroy()
        self.remainder_label.configure(text="")
        self.save_label.configure(text="")
        self.transfer_count.configure(text="")

        try:
            result = calculate(trip)
        except ValidationError as exc:
            self.total_label.configure(text="총 여행 경비 -")
            self._show_notice(f"⚠ {exc} '여행 설정'에서 참가자를 등록해 주세요.")
            return

        self.total_label.configure(text=f"총 여행 경비 {result.total:,}원")
        chip(self.chip_row, f"참가자 {result.count}명", C_ACCENT, C_ACCENT_SOFT).pack(side="left")
        per = f"{result.base_share:,}원" if result.remainder == 0 else f"약 {result.base_share:,}원"
        chip(self.chip_row, f"1인당 부담액 {per}", C_GREEN, C_GREEN_BG).pack(side="left", padx=6)
        if result.remainder:
            self.remainder_label.configure(
                text=f"※ 총액이 {result.count}명으로 나누어떨어지지 않아, 남는 {result.remainder}원은 "
                     f"참가자 목록 앞쪽 {result.remainder}명이 1원씩 더 부담합니다.")

        self._show_notice(None if trip.expenses else "아직 등록된 지출이 없습니다. '지출 내역'에서 경비를 등록하면 자동으로 정산됩니다.")

        for b in result.balances:
            tag = "plus" if b.diff > 0 else "minus" if b.diff < 0 else "even"
            sign = "+" if b.diff > 0 else ""
            self.balance_tree.insert("", "end", tags=(tag,), values=(
                b.name, f"{b.paid:,}원", f"{b.share:,}원", f"{sign}{b.diff:,}원", b.status))

        if result.transfers:
            self.transfer_count.configure(text=f"총 {len(result.transfers)}건의 송금으로 정산이 끝납니다.")
            for i, t in enumerate(result.transfers, 1):
                self.transfer_tree.insert("", "end", values=(i, t.sentence(), f"{t.amount:,}원"))
        else:
            self.transfer_count.configure(text="송금할 내역이 없습니다.")
            if trip.expenses:
                self.transfer_tree.insert("", "end", values=("", "모두 낸 만큼 부담해서 따로 송금할 필요가 없습니다.", ""))
