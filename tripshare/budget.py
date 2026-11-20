"""기능 4: 여행 예산 관리 계산 (GUI와 독립, 정수 연산만 사용)."""
from __future__ import annotations

from dataclasses import dataclass

CAUTION_PERCENT = 80  # 예산의 80% 이상 사용 시 '주의'

UNSET, OK, CAUTION, OVER = "unset", "ok", "caution", "over"


@dataclass(frozen=True)
class BudgetStatus:
    budget: int
    spent: int
    remaining: int            # budget - spent (초과 시 음수)
    level: str                # unset | ok | caution | over
    percent: float | None     # 사용률(%), 소수 첫째 자리 내림. 예산 미설정이면 None
    bar_ratio: float          # 진행 막대 채움 비율 0.0 ~ 1.0

    @property
    def is_unset(self) -> bool:
        return self.level == UNSET

    @property
    def over_amount(self) -> int:
        return max(0, self.spent - self.budget)

    @property
    def percent_text(self) -> str:
        return "예산 미설정" if self.percent is None else f"{self.percent:.1f}%"

    @property
    def message(self) -> str:
        if self.level == UNSET:
            return "예산 미설정: 예산을 입력하면 사용률과 남은 예산을 계산해 드립니다."
        if self.level == OVER:
            return f"경고: 예산을 {self.over_amount:,}원 초과했습니다."
        if self.level == CAUTION:
            if self.remaining == 0:
                return "주의: 예산을 모두 사용했습니다. 더 쓰면 예산을 초과합니다."
            return f"주의: 예산의 {CAUTION_PERCENT}% 이상을 사용했습니다. 남은 예산은 {self.remaining:,}원입니다."
        return f"예산 범위 안에서 사용 중입니다. 남은 예산은 {self.remaining:,}원입니다."


def evaluate(budget: int, spent: int) -> BudgetStatus:
    """예산과 지출액으로 상태를 계산한다. 예산이 0원이면 사용률을 계산하지 않는다."""
    remaining = budget - spent
    if budget <= 0:
        return BudgetStatus(budget, spent, remaining, UNSET, None, 0.0)
    percent = (spent * 1000 // budget) / 10          # 소수 첫째 자리까지 내림 (정수 연산)
    if spent > budget:
        level = OVER
    elif spent * 100 >= budget * CAUTION_PERCENT:     # 부동소수점 없이 비교
        level = CAUTION
    else:
        level = OK
    return BudgetStatus(budget, spent, remaining, level, percent, min(spent, budget) / budget)
