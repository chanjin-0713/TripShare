"""기능 6: 정산 결과 내보내기 (TXT / CSV). GUI와 독립, 표준 라이브러리만 사용.

- TXT, CSV 모두 UTF-8 BOM(utf-8-sig)으로 저장한다. (Excel/구형 메모장에서 한글이 깨지지 않도록)
- CSV는 [여행 정보] [지출 내역] [참가자별 정산] [송금 결과] 구역을 빈 줄과 구역 제목 줄로 구분한다.
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from .budget import evaluate
from .models import Trip
from .settlement import calculate

ENCODING = "utf-8-sig"


# ---------------------------------------------------------------- 공통
def _won(value: int) -> str:
    return f"{value:,}원"


def _signed_won(value: int) -> str:
    return f"+{value:,}원" if value > 0 else f"{value:,}원"


def safe_filename(name: str, fallback: str = "여행") -> str:
    """Windows 파일명에 쓸 수 없는 문자를 제거한다."""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name).strip().strip(".")
    return cleaned[:40] or fallback


def default_filename(trip: Trip, ext: str, now: datetime | None = None) -> str:
    stamp = (now or datetime.now()).strftime("%Y%m%d")
    return f"TripShare_{safe_filename(trip.name)}_{stamp}.{ext}"


# ---------------------------------------------------------------- TXT
def _width(text: str) -> int:
    """한글 등 전각 문자는 2칸으로 계산한 표시 폭."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def _pad(text: str, width: int, right: bool = False) -> str:
    gap = " " * max(0, width - _width(text))
    return gap + text if right else text + gap


def build_txt(trip: Trip, now: datetime | None = None) -> str:
    result = calculate(trip)  # 참가자 2명 미만이면 ValidationError
    budget = evaluate(trip.budget, result.total)
    now = now or datetime.now()
    line = "=" * 56
    out = [line, " TripShare 여행 경비 정산 결과", line, ""]
    out += [f"여행 이름   : {trip.name or '(이름 없음)'}",
            f"내보낸 시각 : {now.strftime('%Y-%m-%d %H:%M')}",
            f"참가자      : {', '.join(trip.participants)} (총 {result.count}명)", ""]

    out += ["[경비 요약]",
            f"전체 여행 경비 : {_won(result.total)}"]
    if budget.is_unset:
        out.append("여행 예산      : 예산 미설정")
    else:
        out.append(f"여행 예산      : {_won(budget.budget)} (사용률 {budget.percent_text}, "
                   + (f"{_won(budget.over_amount)} 초과)" if budget.over_amount else f"남은 예산 {_won(budget.remaining)})"))
    per = _won(result.base_share) if result.remainder == 0 else f"약 {_won(result.base_share)}"
    out.append(f"1인당 부담액   : {per}")
    if result.remainder:
        out.append(f"  ※ 나누어떨어지지 않는 {result.remainder}원은 참가자 목록 앞쪽 {result.remainder}명이 1원씩 더 부담")
    out.append("")

    names_w = max([_width("참가자")] + [_width(b.name) for b in result.balances]) + 2
    cols = [("결제 금액", [_won(b.paid) for b in result.balances]),
            ("부담 금액", [_won(b.share) for b in result.balances]),
            ("정산 차액", [_signed_won(b.diff) for b in result.balances])]
    widths = [max(_width(h), *(_width(v) for v in vals)) + 2 for h, vals in cols]
    out.append("[참가자별 결제 · 부담 금액]")
    out.append(_pad("참가자", names_w) + "".join(_pad(h, w, True) for (h, _v), w in zip(cols, widths)))
    out.append("-" * (names_w + sum(widths)))
    for i, b in enumerate(result.balances):
        out.append(_pad(b.name, names_w) + "".join(_pad(vals[i], w, True) for (_h, vals), w in zip(cols, widths)))
    out.append("")

    out.append("[정산 결과]")
    if result.transfers:
        out.append(f"총 {len(result.transfers)}건의 송금으로 정산이 끝납니다.")
        out += [f"{i}. {t.sentence()}" for i, t in enumerate(result.transfers, 1)]
    elif trip.expenses:
        out.append("모두 낸 만큼 부담해서 따로 송금할 내역이 없습니다.")
    else:
        out.append("등록된 지출이 없어 송금할 내역이 없습니다.")
    out.append("")

    out.append("[지출 내역]")
    if trip.expenses:
        out += [f"{i}. [{e.category}] {e.title} - {_won(e.amount)} ({e.payer} 결제)"
                for i, e in enumerate(trip.expenses, 1)]
    else:
        out.append("(없음)")
    out += ["", line]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- CSV
def _cell(value) -> object:
    """사용자 입력 문자열이 Excel 수식으로 실행되지 않도록(CSV 인젝션) 막는다."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def build_csv(trip: Trip) -> str:
    """구역을 [구역 제목] 줄과 빈 줄로 구분한 CSV 문자열. 금액은 숫자 그대로(천 단위 쉼표 없음)."""
    result = calculate(trip)
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\r\n")

    def section(title: str, header: list[str], rows: list[list]) -> None:
        w.writerow([title])
        w.writerow(header)
        for r in rows:
            w.writerow([_cell(c) for c in r])
        w.writerow([])

    section("[여행 정보]", ["항목", "값"], [
        ["여행 이름", trip.name], ["참가자", ", ".join(trip.participants)], ["참가자 수", result.count],
        ["전체 여행 경비(원)", result.total], ["여행 예산(원)", trip.budget],
        ["1인당 기본 부담액(원)", result.base_share],
    ])
    section("[지출 내역]", ["번호", "항목", "카테고리", "결제한 사람", "금액(원)"],
            [[i, e.title, e.category, e.payer, e.amount] for i, e in enumerate(trip.expenses, 1)])
    section("[참가자별 정산]", ["참가자", "실제 결제 금액(원)", "부담 금액(원)", "정산 차액(원)", "구분"],
            [[b.name, b.paid, b.share, b.diff, b.status] for b in result.balances])
    section("[송금 결과]", ["순서", "보내는 사람", "받는 사람", "금액(원)"],
            [[i, t.sender, t.receiver, t.amount] for i, t in enumerate(result.transfers, 1)])
    return buf.getvalue()


# ---------------------------------------------------------------- 저장
def save_txt(trip: Trip, path: Path, now: datetime | None = None) -> None:
    Path(path).write_text(build_txt(trip, now), encoding=ENCODING, newline="\r\n")


def save_csv(trip: Trip, path: Path) -> None:
    # build_csv가 이미 \r\n 을 쓰므로 newline=""로 그대로 기록
    Path(path).write_text(build_csv(trip), encoding=ENCODING, newline="")
