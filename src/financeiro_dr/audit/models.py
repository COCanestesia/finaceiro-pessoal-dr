from dataclasses import dataclass

@dataclass(frozen=True)
class AuditChange:
    entity: str
    entity_id: int
    action: str
    field_name: str | None = None
    old_value: str | None = None
    new_value: str | None = None
