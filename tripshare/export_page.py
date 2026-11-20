"""데이터 내보내기 화면: TXT 저장 / CSV 저장."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import exporter, ui
from .models import ValidationError
from .ui import C_BG, C_GREEN, C_MUTED, C_TEXT, FONT, card

TXT_ITEMS = ["여행 이름, 참가자 목록", "전체 여행 경비, 여행 예산", "참가자별 결제 금액 · 부담 금액 · 정산 차액",
             "정산 결과(누가 누구에게 얼마를 보낼지)", "지출 내역"]
CSV_ITEMS = ["Excel에서 한글이 깨지지 않는 UTF-8 BOM 형식", "[여행 정보] [지출 내역] 구역",
             "[참가자별 정산] [송금 결과] 구역", "금액은 쉼표 없는 숫자(계산에 바로 사용 가능)"]


class ExportPage(tk.Frame):
    def __init__(self, parent: tk.Misc, app) -> None:
        super().__init__(parent, bg=C_BG, padx=28, pady=22)
        self.app = app
        head = card(self, padx=20, pady=14)
        head.pack(fill="x")
        tk.Label(head, text="데이터 내보내기", bg=C_BG, fg=C_TEXT, font=(FONT, 16, "bold")).pack(anchor="w")
        tk.Label(head, text="현재 여행의 정산 결과를 파일로 저장해 친구에게 공유하거나 Excel에서 열어 볼 수 있습니다.",
                 bg=C_BG, fg=C_MUTED, font=(FONT, 10)).pack(anchor="w", pady=(4, 0))

        cols = tk.Frame(self, bg=C_BG)
        cols.pack(fill="x", pady=(14, 0))
        cols.columnconfigure((0, 1), weight=1, uniform="c")
        self._option(cols, 0, "TXT 저장", "읽기 쉬운 문서 형식", TXT_ITEMS, "TXT 파일로 저장", "txt")
        self._option(cols, 1, "CSV 저장", "Excel용 표 형식", CSV_ITEMS, "CSV 파일로 저장", "csv")

        self.save_label = tk.Label(self, bg=C_BG, fg=C_GREEN, font=(FONT, 10), anchor="w", justify="left",
                                   wraplength=int(720 * ui.SCALE))
        self.save_label.pack(anchor="w", pady=(14, 0))

    def _option(self, parent: tk.Frame, col: int, title: str, subtitle: str, items: list[str],
                button_text: str, kind: str) -> None:
        box = card(parent, padx=20, pady=16)
        box.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 7, 7 if col == 0 else 0))
        tk.Label(box, text=title, bg=C_BG, fg=C_TEXT, font=(FONT, 13, "bold")).pack(anchor="w")
        tk.Label(box, text=subtitle, bg=C_BG, fg=C_MUTED, font=(FONT, 10)).pack(anchor="w", pady=(2, 10))
        for item in items:
            tk.Label(box, text="• " + item, bg=C_BG, fg=C_TEXT, font=(FONT, 10), anchor="w", justify="left",
                     wraplength=int(340 * ui.SCALE)).pack(anchor="w", pady=1)
        ttk.Button(box, text=button_text, style="Primary.TButton",
                   command=lambda: self.on_export(kind)).pack(anchor="w", pady=(14, 0))

    def refresh(self) -> None:
        self.save_label.configure(text="")

    def on_export(self, kind: str) -> None:
        trip = self.app.trip
        try:
            exporter.build_txt(trip)  # 정산 가능한 상태인지 먼저 확인 (참가자 2명 이상)
        except ValidationError as exc:
            messagebox.showwarning("내보내기", f"{exc}\n'참가자 관리'에서 참가자를 등록해 주세요.", parent=self.app.root)
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
