"""기능 7: 시작 시 저장 파일 불러오기 (GUI와 독립).

저장 위치는 %APPDATA% 아래 TripShare 폴더의 trip.json (사용자별 폴더)이라 EXE가 있는 폴더에 쓰기 권한이 없어도 된다.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .models import Trip, ValidationError, backup_path, demo_trip, load_trip

LOADED = "loaded"        # 정상적으로 불러옴
NEW = "new"              # 저장 파일 없음 (첫 실행) -> 데모 데이터
RECOVERED = "recovered"  # 본 파일은 손상, 직전 저장본(.bak)으로 복구
CORRUPT = "corrupt"      # 본 파일 손상, 복구 불가 -> 새 여행/데모 선택 필요


@dataclass
class LoadResult:
    status: str
    trip: Trip | None = None
    message: str = ""
    corrupt_copy: Path | None = None  # 손상 파일을 보관한 위치(보관 못 했으면 None)


def _quarantine(path: Path) -> Path | None:
    """손상 파일을 지우지 않고 이름을 바꿔 보관한다."""
    target = path.with_name(f"{path.stem}.corrupt-{datetime.now():%Y%m%d-%H%M%S}{path.suffix}")
    try:
        os.replace(path, target)
        return target
    except OSError:
        return None


def startup_load(path: Path) -> LoadResult:
    path = Path(path)
    try:
        return LoadResult(LOADED, load_trip(path))
    except FileNotFoundError:
        return LoadResult(NEW, demo_trip(), "저장된 여행이 없어 예시 데이터로 시작합니다.")
    except (ValidationError, OSError) as exc:
        problem = str(exc) or "저장 파일을 읽을 수 없습니다."

    moved = _quarantine(path) if path.exists() else None
    kept = f"\n손상된 파일은 '{moved.name}'으로 보관했습니다." if moved else ""
    backup = backup_path(path)
    try:
        trip = load_trip(backup)
    except (FileNotFoundError, ValidationError, OSError):
        return LoadResult(CORRUPT, None, f"{problem}{kept}", moved)
    return LoadResult(RECOVERED, trip, f"{problem}{kept}\n직전에 저장된 데이터로 복구했습니다.", moved)
