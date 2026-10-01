"""Small append-only JSONL primitives shared by governance services."""

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, Iterable

_LOCK = threading.RLock()


class GovernancePersistenceError(RuntimeError):
    """Raised when a governance record cannot be durably appended."""


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
        with _LOCK, path.open("a", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    except (OSError, TypeError, ValueError) as exc:
        raise GovernancePersistenceError(f"Governance record could not be persisted: {exc}") from exc


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                records.append(item)
    except OSError:
        return []
    return records
