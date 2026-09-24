from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import re

from .models import ExpectedTotals, InitialSeedManifest, InitialSeedRecord


class InitialSeedError(RuntimeError):
    pass


_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_VALID_CLASSIFICATIONS = {"RECEITA", "DESPESA"}


def _clean_text(value, *, required: bool = False, field_name: str = "campo") -> str | None:
    if value is None:
        text = ""
    else:
        text = " ".join(str(value).strip().split())
    if required and not text:
        raise InitialSeedError(f"O {field_name} da base inicial é obrigatório.")
    return text or None


def _non_negative_int(value, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InitialSeedError(f"O campo {field_name} da base inicial é inválido.")
    return value


def load_manifest(path: Path) -> InitialSeedManifest:
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InitialSeedError("Não foi possível ler a base inicial privada.") from exc

    if not isinstance(raw, dict):
        raise InitialSeedError("A estrutura da base inicial privada é inválida.")
    if raw.get("schema_version") != 1:
        raise InitialSeedError("A versão da base inicial não é suportada.")

    seed_id = _clean_text(raw.get("seed_id"), required=True, field_name="identificador")
    source_label = _clean_text(raw.get("source_label"), required=True, field_name="nome da fonte")
    source_sha256 = _clean_text(raw.get("source_sha256"), required=True, field_name="hash da fonte")
    if source_sha256 is None or not _SHA256_RE.fullmatch(source_sha256):
        raise InitialSeedError("O hash da fonte da base inicial é inválido.")

    expected_raw = raw.get("expected")
    if not isinstance(expected_raw, dict):
        raise InitialSeedError("Os totais esperados da base inicial são inválidos.")
    expected = ExpectedTotals(
        record_count=_non_negative_int(expected_raw.get("record_count"), "record_count"),
        income_count=_non_negative_int(expected_raw.get("income_count"), "income_count"),
        expense_count=_non_negative_int(expected_raw.get("expense_count"), "expense_count"),
        income_cents=_non_negative_int(expected_raw.get("income_cents"), "income_cents"),
        expense_cents=_non_negative_int(expected_raw.get("expense_cents"), "expense_cents"),
    )

    records_raw = raw.get("records")
    if not isinstance(records_raw, list):
        raise InitialSeedError("Os registros da base inicial são inválidos.")

    records: list[InitialSeedRecord] = []
    seen_rows: set[int] = set()
    for item in records_raw:
        if not isinstance(item, dict):
            raise InitialSeedError("Existe um registro inválido na base inicial.")
        source_row = item.get("source_row")
        if isinstance(source_row, bool) or not isinstance(source_row, int) or source_row <= 0:
            raise InitialSeedError("A linha de origem da base inicial é inválida.")
        if source_row in seen_rows:
            raise InitialSeedError("A base inicial possui linhas de origem duplicadas.")
        seen_rows.add(source_row)

        date_text = _clean_text(item.get("date"), required=True, field_name="data")
        try:
            competence_date = date.fromisoformat(date_text or "")
        except ValueError as exc:
            raise InitialSeedError("Existe uma data inválida na base inicial.") from exc

        classification = (_clean_text(item.get("classification"), required=True, field_name="classificação") or "").upper()
        if classification not in _VALID_CLASSIFICATIONS:
            raise InitialSeedError("Existe uma classificação desconhecida na base inicial.")

        amount_cents = _non_negative_int(item.get("amount_cents"), "amount_cents")
        records.append(
            InitialSeedRecord(
                source_row=source_row,
                holder=_clean_text(item.get("holder"), required=True, field_name="titular") or "",
                date=competence_date,
                description=_clean_text(item.get("description"), required=True, field_name="descrição") or "",
                payment_method=_clean_text(item.get("payment_method")),
                amount_cents=amount_cents,
                category=_clean_text(item.get("category")),
                raw_type=_clean_text(item.get("raw_type")),
                classification=classification,
                warning=_clean_text(item.get("warning")),
            )
        )

    income_records = [record for record in records if record.classification == "RECEITA"]
    expense_records = [record for record in records if record.classification == "DESPESA"]
    actual = ExpectedTotals(
        record_count=len(records),
        income_count=len(income_records),
        expense_count=len(expense_records),
        income_cents=sum(record.amount_cents for record in income_records),
        expense_cents=sum(record.amount_cents for record in expense_records),
    )
    if actual != expected:
        raise InitialSeedError("Os totais da base inicial não conferem com os registros.")

    return InitialSeedManifest(
        schema_version=1,
        seed_id=seed_id or "",
        source_label=source_label or "",
        source_sha256=source_sha256.lower(),
        expected=expected,
        records=tuple(records),
    )
