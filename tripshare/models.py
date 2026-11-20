"""TripShare 데이터 모델과 검증 로직 (GUI와 독립, 표준 라이브러리만 사용).

금액은 모두 정수(원)로 다룬다.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

MIN_PARTICIPANTS = 2
MAX_PARTICIPANTS = 10
MAX_NAME_LEN = 12          # 참가자 이름 최대 길이
MAX_TRIP_NAME_LEN = 30     # 여행 이름 최대 길이
MAX_BUDGET = 10_000_000_000  # 100억 원
SCHEMA_VERSION = 1


class ValidationError(ValueError):
    """사용자에게 그대로 보여 줄 수 있는 한국어 오류 메시지를 담는다."""


def _normalize(text: str) -> str:
    """앞뒤 공백 제거 + 연속 공백을 한 칸으로."""
    return " ".join(str(text).split())


def _has_control_chars(text: str) -> bool:
    return any(ord(c) < 32 or ord(c) == 127 for c in text)


def parse_amount(text: str) -> int:
    """'1,500,000', '1500000원', ' 300000 ' 등을 정수로 변환한다."""
    cleaned = str(text).strip().replace(",", "").replace(" ", "")
    if cleaned.endswith("원"):
        cleaned = cleaned[:-1]
    if cleaned == "":
        raise ValidationError("금액을 입력해 주세요.")
    if not cleaned.isascii() or not cleaned.isdigit():
        raise ValidationError("금액은 0 이상의 정수(숫자)로 입력해 주세요.")
    return int(cleaned)


@dataclass
class Expense:
    """지출 내역. (기능 2에서 입력 화면이 추가될 예정, 참가자 삭제 검증에 사용)"""
    title: str
    amount: int
    payer: str
    participants: list[str] = field(default_factory=list)

    def involves(self, name: str) -> bool:
        return self.payer == name or name in self.participants


@dataclass
class Trip:
    name: str = ""
    budget: int = 0
    participants: list[str] = field(default_factory=list)
    expenses: list[Expense] = field(default_factory=list)

    # ---- 여행 이름 / 예산 ----
    @staticmethod
    def validate_trip_name(name: str) -> str:
        name = _normalize(name)
        if not name:
            raise ValidationError("여행 이름을 입력해 주세요.")
        if len(name) > MAX_TRIP_NAME_LEN:
            raise ValidationError(f"여행 이름은 {MAX_TRIP_NAME_LEN}자 이하로 입력해 주세요.")
        if _has_control_chars(name):
            raise ValidationError("여행 이름에 사용할 수 없는 문자가 있습니다.")
        return name

    @staticmethod
    def validate_budget(value: int | str) -> int:
        amount = parse_amount(value) if isinstance(value, str) else value
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValidationError("여행 예산은 0 이상의 정수여야 합니다.")
        if amount > MAX_BUDGET:
            raise ValidationError(f"여행 예산은 {MAX_BUDGET:,}원 이하로 입력해 주세요.")
        return amount

    def set_basic_info(self, name: str, budget: int | str) -> None:
        """둘 다 유효할 때만 함께 반영한다(하나만 바뀌는 상태를 방지)."""
        valid_name = self.validate_trip_name(name)
        valid_budget = self.validate_budget(budget)
        self.name = valid_name
        self.budget = valid_budget

    # ---- 참가자 ----
    def _validate_new_name(self, name: str, ignore: str | None = None) -> str:
        name = _normalize(name)
        if not name:
            raise ValidationError("참가자 이름을 입력해 주세요.")
        if len(name) > MAX_NAME_LEN:
            raise ValidationError(f"참가자 이름은 {MAX_NAME_LEN}자 이하로 입력해 주세요.")
        if _has_control_chars(name):
            raise ValidationError("참가자 이름에 사용할 수 없는 문자가 있습니다.")
        for existing in self.participants:
            if existing != ignore and existing.casefold() == name.casefold():
                raise ValidationError(f"'{name}' 이름은 이미 등록되어 있습니다.")
        return name

    def add_participant(self, name: str) -> str:
        if len(self.participants) >= MAX_PARTICIPANTS:
            raise ValidationError(f"참가자는 최대 {MAX_PARTICIPANTS}명까지 등록할 수 있습니다.")
        name = self._validate_new_name(name)
        self.participants.append(name)
        return name

    def expenses_of(self, name: str) -> list[Expense]:
        return [e for e in self.expenses if e.involves(name)]

    def remove_participant(self, name: str) -> None:
        if name not in self.participants:
            raise ValidationError("삭제할 참가자를 찾을 수 없습니다.")
        linked = self.expenses_of(name)
        if linked:
            raise ValidationError(
                f"'{name}'님은 {len(linked)}건의 지출 내역에 연결되어 있어 삭제할 수 없습니다.\n"
                "먼저 해당 지출 내역을 수정하거나 삭제해 주세요."
            )
        if len(self.participants) <= MIN_PARTICIPANTS:
            raise ValidationError(
                f"참가자는 최소 {MIN_PARTICIPANTS}명이 필요합니다.\n"
                "다른 참가자를 먼저 추가한 뒤 삭제해 주세요."
            )
        self.participants.remove(name)

    def rename_participant(self, old: str, new: str) -> str:
        if old not in self.participants:
            raise ValidationError("이름을 바꿀 참가자를 찾을 수 없습니다.")
        new = self._validate_new_name(new, ignore=old)
        self.participants[self.participants.index(old)] = new
        for e in self.expenses:
            if e.payer == old:
                e.payer = new
            e.participants = [new if p == old else p for p in e.participants]
        return new

    def setup_problems(self) -> list[str]:
        """정산을 시작하기 전에 해결해야 할 설정 문제 목록."""
        problems = []
        if not self.name:
            problems.append("여행 이름을 입력해 주세요.")
        if len(self.participants) < MIN_PARTICIPANTS:
            problems.append(f"참가자를 최소 {MIN_PARTICIPANTS}명 등록해 주세요.")
        return problems

    # ---- 직렬화 ----
    def to_dict(self) -> dict:
        return {
            "version": SCHEMA_VERSION,
            "name": self.name,
            "budget": self.budget,
            "participants": list(self.participants),
            "expenses": [
                {"title": e.title, "amount": e.amount, "payer": e.payer,
                 "participants": list(e.participants)}
                for e in self.expenses
            ],
        }

    @classmethod
    def from_dict(cls, data: object) -> "Trip":
        """저장 파일 내용을 엄격히 검증하며 복원한다. 이상하면 ValidationError."""
        if not isinstance(data, dict):
            raise ValidationError("저장 파일 형식이 올바르지 않습니다.")
        try:
            trip = cls()
            raw_name = data.get("name", "")
            if not isinstance(raw_name, str):
                raise ValidationError("여행 이름이 올바르지 않습니다.")
            # 새 여행(이름 미입력) 상태도 저장/복원할 수 있어야 한다.
            trip.name = trip.validate_trip_name(raw_name) if raw_name.strip() else ""
            trip.budget = trip.validate_budget(data.get("budget", 0))
            names = data.get("participants", [])
            if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
                raise ValidationError("참가자 목록이 올바르지 않습니다.")
            for n in names:
                trip.add_participant(n)
            raw = data.get("expenses", [])
            if not isinstance(raw, list):
                raise ValidationError("지출 목록이 올바르지 않습니다.")
            for item in raw:
                if not isinstance(item, dict):
                    raise ValidationError("지출 항목이 올바르지 않습니다.")
                amount = item.get("amount")
                if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
                    raise ValidationError("지출 금액이 올바르지 않습니다.")
                payer = item.get("payer")
                members = item.get("participants", [])
                if payer not in trip.participants or not isinstance(members, list) \
                        or any(m not in trip.participants for m in members):
                    raise ValidationError("지출 항목의 참가자가 올바르지 않습니다.")
                trip.expenses.append(Expense(str(item.get("title", "")), amount, payer, list(members)))
            return trip
        except (TypeError, AttributeError) as exc:  # 예상치 못한 자료형
            raise ValidationError("저장 파일 내용이 올바르지 않습니다.") from exc


def demo_trip() -> Trip:
    """시연용 가상 데이터. 실제 개인정보를 사용하지 않는다."""
    return Trip(
        name="제주도 3박4일 (예시)",
        budget=1_200_000,
        participants=["가상민수", "가상지은", "가상서준", "가상하윤"],
    )


# ---- 파일 저장 ----
def default_data_path() -> Path:
    base = os.environ.get("APPDATA")
    root = Path(base) if base else Path.home()
    return root / "TripShare" / "trip.json"


def save_trip(trip: Trip, path: Path) -> None:
    """임시 파일에 쓴 뒤 교체하여, 저장 중 중단되어도 기존 파일이 깨지지 않게 한다."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(trip.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load_trip(path: Path) -> Trip:
    """파일이 없으면 FileNotFoundError, 손상되었으면 ValidationError."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError("저장 파일이 손상되었습니다.") from exc
    return Trip.from_dict(data)
