"""분석 파이프라인 진행 로그 인메모리 저장소.

서버 재시작 시 사라짐. UX용 단기 로그 표시 목적.
"""
from collections import defaultdict
from datetime import datetime
from typing import Dict, List

_store: Dict[int, List[dict]] = defaultdict(list)
_MAX_ENTRIES = 50


def emit(bid_id: int, message: str, level: str = "info") -> None:
    entries = _store[bid_id]
    entries.append({
        "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "level": level,
        "message": message,
    })
    if len(entries) > _MAX_ENTRIES:
        del entries[: len(entries) - _MAX_ENTRIES]


def get(bid_id: int) -> List[dict]:
    return list(_store.get(bid_id, []))


def clear(bid_id: int) -> None:
    _store.pop(bid_id, None)
