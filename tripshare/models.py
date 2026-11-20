"""TripShare 데이터 모델과 검증 로직 (GUI와 독립, 표준 라이브러리만 사용).

금액은 모두 정수(원)로 다룬다.
"""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

MIN_PARTICIPANTS = 2
MAX_PARTICIPANTS = 10
MAX_NAME_LEN = 12          # 참가자 이름 최대 길이
MAX_TRIP_NAME_LEN = 30     # 여행 이름 최대 길이
MAX_BUDGET = 10_000_000_000  # 100억 원
MAX_EXPENSE_TITLE_LEN = 30
MAX_EXPENSE_AMOUNT = 10_000_000_000  # 100억 원
CATEGORIES = ["숙박비", "식비", "교통비", "관광 및 입장료", "쇼핑", "기타"]
DEFAULT_CATEGORY = "기타"
SCHEMA_VERSION = 2


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
    """지출 내역. participants가 비어 있으면 '참가자 전원이 균등 부담'을 뜻한다(기능 3에서 세분화)."""
    title: str
    amount: int
    payer: str
    participants: list[str] = field(default_factory=list)
    category: str = DEFAULT_CATEGORY

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

    # ---- 지출 ----
    @staticmethod
    def validate_expense_title(title: str) -> str:
        title = _normalize(title)
        if not title:
            raise ValidationError("지출 항목 이름을 입력해 주세요.")
        if len(title) > MAX_EXPENSE_TITLE_LEN:
            raise ValidationError(f"지출 항목 이름은 {MAX_EXPENSE_TITLE_LEN}자 이하로 입력해 주세요.")
        if _has_control_chars(title):
            raise ValidationError("지출 항목 이름에 사용할 수 없는 문자가 있습니다.")
        return title

    @staticmethod
    def validate_expense_amount(value: int | str) -> int:
        amount = parse_amount(value) if isinstance(value, str) else value
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise ValidationError("금액은 정수(원 단위)로 입력해 주세요.")
        if amount < 1:
            raise ValidationError("지출 금액은 1원 이상이어야 합니다.")
        if amount > MAX_EXPENSE_AMOUNT:
            raise ValidationError(f"지출 금액은 {MAX_EXPENSE_AMOUNT:,}원 이하로 입력해 주세요.")
        return amount

    def _check_expense_fields(self, title: str, amount: int | str, payer: str,
                              category: str) -> tuple[str, int, str, str]:
        title = self.validate_expense_title(title)
        amount = self.validate_expense_amount(amount)
        if payer not in self.participants:
            raise ValidationError("결제한 사람을 참가자 목록에서 선택해 주세요.")
        if category not in CATEGORIES:
            raise ValidationError("지출 카테고리를 목록에서 선택해 주세요.")
        return title, amount, payer, category

    def add_expense(self, title: str, amount: int | str, payer: str, category: str) -> Expense:
        title, amount, payer, category = self._check_expense_fields(title, amount, payer, category)
        expense = Expense(title, amount, payer, [], category)
        self.expenses.append(expense)
        return expense

    def update_expense(self, index: int, title: str, amount: int | str, payer: str, category: str) -> Expense:
        if not 0 <= index < len(self.expenses):
            raise ValidationError("수정할 지출 내역을 찾을 수 없습니다.")
        title, amount, payer, category = self._check_expense_fields(title, amount, payer, category)
        expense = self.expenses[index]
        expense.title, expense.amount, expense.payer, expense.category = title, amount, payer, category
        return expense

    def remove_expense(self, index: int) -> Expense:
        if not 0 <= index < len(self.expenses):
            raise ValidationError("삭제할 지출 내역을 찾을 수 없습니다.")
        return self.expenses.pop(index)

    @property
    def total_spent(self) -> int:
        return sum(e.amount for e in self.expenses)

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
                 "participants": list(e.participants), "category": e.category}
                for e in self.expenses
            ],
        }

    @classmethod
    def from_dict(cls, data: object) -> "Trip":
        """저장 파일 내용을 엄격히 검증하며 복원한다. 이상하면 ValidationError."""
        if not isinstance(data, dict):
            raise ValidationError("저장 파일 형식이 올바르지 않습니다.")
        version = data.get("version", 1)
        if isinstance(version, bool) or not isinstance(version, int) or version > SCHEMA_VERSION:
            raise ValidationError("이 프로그램보다 새로운 버전에서 저장한 파일이라 열 수 없습니다.")
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
                amount = trip.validate_expense_amount(item.get("amount"))
                title = trip.validate_expense_title(item.get("title", ""))
                category = item.get("category", DEFAULT_CATEGORY)
                if category not in CATEGORIES:
                    raise ValidationError("지출 카테고리가 올바르지 않습니다.")
                payer = item.get("payer")
                members = item.get("participants", [])
                if payer not in trip.participants or not isinstance(members, list) \
                        or any(m not in trip.participants for m in members):
                    raise ValidationError("지출 항목의 참가자가 올바르지 않습니다.")
                trip.expenses.append(Expense(title, amount, payer, list(members), category))
            return trip
        except (TypeError, AttributeError) as exc:  # 예상치 못한 자료형
            raise ValidationError("저장 파일 내용이 올바르지 않습니다.") from exc


def demo_trip() -> Trip:
    """시연용 가상 데이터. 실제 개인정보를 사용하지 않는다."""
    return Trip(
        name="제주도 3박4일 (예시)",
        budget=1_200_000,
        participants=["가상민수", "가상지은", "가상서준", "가상하윤"],
        expenses=[
            Expense("펜션 1박", 360_000, "가상민수", [], "숙박비"),
            Expense("흑돼지 점심", 84_000, "가상지은", [], "식비"),
            Expense("렌터카", 120_000, "가상서준", [], "교통비"),
            Expense("성산일출봉 입장료", 52_000, "가상하윤", [], "관광 및 입장료"),
            Expense("기념품", 38_500, "가상민수", [], "쇼핑"),
        ],
    )


# ---- 파일 저장 ----
def default_data_path() -> Path:
    base = os.environ.get("APPDATA")
    root = Path(base) if base else Path.home()
    return root / "TripShare" / "trip.json"


def backup_path(path: Path) -> Path:
    """직전 정상 저장본 위치 (trip.json -> trip.json.bak)."""
    path = Path(path)
    return path.with_name(path.name + ".bak")


def save_trip(trip: Trip, path: Path) -> None:
    """안전한 저장: 임시 파일에 완전히 쓰고 디스크에 반영한 뒤 os.replace로 한 번에 교체한다.

    저장 도중 오류가 나거나 프로세스가 중단되어도 기존 파일은 손상되지 않는다.
    교체 직전에 기존(정상) 파일을 .bak로 복사해 직전 저장본도 보관한다.
    실패하면 OSError를 발생시킨다.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    payload = json.dumps(trip.to_dict(), ensure_ascii=False, indent=2)
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        if path.exists():
            try:
                json.loads(path.read_text(encoding="utf-8"))  # 정상 파일일 때만 백업으로 보관
                shutil.copy2(path, backup_path(path))
            except (OSError, ValueError):
                pass
        os.replace(tmp, path)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def load_trip(path: Path) -> Trip:
    """파일이 없으면 FileNotFoundError, 읽을 수 없거나 손상되었으면 ValidationError."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError("저장 파일을 읽을 수 없습니다(문자 인코딩 오류).") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError("저장 파일이 손상되었습니다.") from exc
    return Trip.from_dict(data)
