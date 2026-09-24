from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ExpectedTotals:
    record_count: int
    income_count: int
    expense_count: int
    income_cents: int
    expense_cents: int


@dataclass(frozen=True)
class InitialSeedRecord:
    source_row: int
    holder: str
    date: date
    description: str
    payment_method: str | None
    amount_cents: int
    category: str | None
    raw_type: str | None
    classification: str
    warning: str | None = None


@dataclass(frozen=True)
class InitialSeedManifest:
    schema_version: int
    seed_id: str
    source_label: str
    source_sha256: str
    expected: ExpectedTotals
    records: tuple[InitialSeedRecord, ...]


@dataclass(frozen=True)
class SeedApplyResult:
    inserted: int
    reused: int
    warnings: int
