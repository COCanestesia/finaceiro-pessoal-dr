from __future__ import annotations

from datetime import date, datetime
import json
import sqlite3
from typing import Any


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def _json(snapshot: dict[str, Any]) -> str:
    return json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=_text)


class AuditService:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def record_create(self, entity: str, entity_id: int, snapshot: dict) -> None:
        self.connection.execute("INSERT INTO audit_log(entity, entity_id, action, snapshot_json) VALUES (?, ?, 'CREATE', ?)", (entity, entity_id, _json(snapshot)))

    def record_update(self, entity: str, entity_id: int, before: dict, after: dict) -> None:
        for key in sorted(set(before) | set(after)):
            old, new = before.get(key), after.get(key)
            if old == new:
                continue
            self.connection.execute("INSERT INTO audit_log(entity, entity_id, action, field_name, old_value, new_value) VALUES (?, ?, 'UPDATE', ?, ?, ?)", (entity, entity_id, key, _text(old), _text(new)))

    def record_delete(self, entity: str, entity_id: int, before: dict) -> None:
        self.connection.execute("INSERT INTO audit_log(entity, entity_id, action, snapshot_json) VALUES (?, ?, 'DELETE', ?)", (entity, entity_id, _json(before)))
