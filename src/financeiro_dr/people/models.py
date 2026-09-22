from dataclasses import dataclass

@dataclass(frozen=True)
class Person:
    id: int
    name: str
    relationship: str | None
    nickname: str | None
    notes: str | None
    active: bool
