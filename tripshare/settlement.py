"""기능 3: 여행 경비 자동 정산 계산 (GUI와 독립, 정수 연산만 사용).

계산 순서
 1. 전체 지출 합산
 2. 참가자 수로 1인당 부담액 계산 (균등 분담)
 3. 참가자별 실제 결제액 계산
 4. 결제액 - 부담액 = 정산 차액
 5. 차액이 +이면 받을 사람, -이면 보낼 사람
 6. 보낼 사람과 받을 사람을 짝지어 송금 목록 생성
 7. 읽기 쉬운 문장으로 변환

나누어떨어지지 않는 나머지(원)는 참가자 목록 앞쪽부터 1원씩 더 부담한다.
이렇게 하면 부담액의 합이 항상 총 지출과 정확히 같아져 1원의 오차도 남지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .models import MIN_PARTICIPANTS, Trip, ValidationError


@dataclass(frozen=True)
class Balance:
    name: str
    paid: int    # 실제 결제한 금액
    share: int   # 부담해야 할 금액
    diff: int    # paid - share (+면 받을 돈, -면 보낼 돈)

    @property
    def status(self) -> str:
        if self.diff > 0:
            return "받을 돈"
        if self.diff < 0:
            return "보낼 돈"
        return "정산 완료"


@dataclass(frozen=True)
class Transfer:
    sender: str
    receiver: str
    amount: int

    def sentence(self) -> str:
        return f"{self.sender}님이 {self.receiver}님에게 {self.amount:,}원을 보내세요."


@dataclass(frozen=True)
class Settlement:
    total: int
    count: int
    base_share: int   # 1인당 기본 부담액 (total // count)
    remainder: int    # 나누어떨어지지 않고 남은 원 (0 ~ count-1)
    balances: list[Balance] = field(default_factory=list)
    transfers: list[Transfer] = field(default_factory=list)


def calculate_transfers(diffs: dict[str, int], order: list[str]) -> list[Transfer]:
    """차액(+받을 돈/-보낼 돈)으로 송금 목록을 만든다.

    가장 많이 보낼 사람이 가장 많이 받을 사람에게 먼저 보내는 방식(그리디)이며,
    송금 횟수는 (정산 대상자 수 - 1)건을 넘지 않는다.
    """
    rank = {name: i for i, name in enumerate(order)}
    debtors = sorted(((-d, n) for n, d in diffs.items() if d < 0), key=lambda x: (-x[0], rank[x[1]]))
    creditors = sorted(((d, n) for n, d in diffs.items() if d > 0), key=lambda x: (-x[0], rank[x[1]]))
    debtors = [list(x) for x in debtors]
    creditors = [list(x) for x in creditors]
    transfers: list[Transfer] = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        pay = min(debtors[i][0], creditors[j][0])
        if pay > 0:
            transfers.append(Transfer(debtors[i][1], creditors[j][1], pay))
        debtors[i][0] -= pay
        creditors[j][0] -= pay
        if debtors[i][0] == 0:
            i += 1
        if creditors[j][0] == 0:
            j += 1
    transfers.sort(key=lambda t: (rank[t.sender], rank[t.receiver]))
    return transfers


def calculate(trip: Trip) -> Settlement:
    names = list(trip.participants)
    n = len(names)
    if n < MIN_PARTICIPANTS:
        raise ValidationError(f"정산하려면 참가자가 최소 {MIN_PARTICIPANTS}명 필요합니다.")

    total = sum(e.amount for e in trip.expenses)                       # 1
    base, remainder = divmod(total, n)                                  # 2
    paid = {name: 0 for name in names}                                  # 3
    for e in trip.expenses:
        if e.payer not in paid:
            raise ValidationError(f"지출 '{e.title}'의 결제자 '{e.payer}'가 참가자 목록에 없습니다.")
        paid[e.payer] += e.amount

    balances = []
    for i, name in enumerate(names):
        share = base + (1 if i < remainder else 0)
        balances.append(Balance(name, paid[name], share, paid[name] - share))  # 4, 5

    transfers = calculate_transfers({b.name: b.diff for b in balances}, names)  # 6
    return Settlement(total, n, base, remainder, balances, transfers)
