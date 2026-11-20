"""기능 5: 지출 통계 계산 (GUI와 독립, 정수 연산만 사용)."""
from __future__ import annotations

from dataclasses import dataclass

from .models import CATEGORIES, Trip


@dataclass(frozen=True)
class PayerStat:
    name: str
    amount: int       # 실제 결제한 금액
    count: int        # 결제 건수


@dataclass(frozen=True)
class CategoryStat:
    category: str
    amount: int
    count: int
    share_tenths: int  # 비중(%)의 10배. 예: 125 = 12.5%

    @property
    def share_text(self) -> str:
        return f"{self.share_tenths / 10:.1f}%"


@dataclass(frozen=True)
class Statistics:
    total: int
    expense_count: int
    payers: list[PayerStat]
    categories: list[CategoryStat]


def _shares_tenths(amounts: list[int]) -> list[int]:
    """비중을 소수 첫째 자리(%)까지 계산하되, 합이 정확히 100.0%가 되도록 최대잔여법으로 보정한다."""
    total = sum(amounts)
    if total == 0:
        return [0] * len(amounts)
    base = [a * 1000 // total for a in amounts]
    leftover = 1000 - sum(base)
    order = sorted(range(len(amounts)), key=lambda i: (-(amounts[i] * 1000 % total), i))
    for i in order[:leftover]:
        base[i] += 1
    return base


def compute(trip: Trip) -> Statistics:
    paid = {name: [0, 0] for name in trip.participants}
    cat_amount = {c: 0 for c in CATEGORIES}
    cat_count = {c: 0 for c in CATEGORIES}
    for e in trip.expenses:
        if e.payer in paid:
            paid[e.payer][0] += e.amount
            paid[e.payer][1] += 1
        cat_amount[e.category] += e.amount
        cat_count[e.category] += 1

    shares = _shares_tenths([cat_amount[c] for c in CATEGORIES])
    categories = [CategoryStat(c, cat_amount[c], cat_count[c], shares[i]) for i, c in enumerate(CATEGORIES)]
    payers = [PayerStat(n, a, k) for n, (a, k) in paid.items()]
    return Statistics(sum(e.amount for e in trip.expenses), len(trip.expenses), payers, categories)
