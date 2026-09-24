# Private Initial Seed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer o Financeiro Pessoal do Dr. aplicar automaticamente uma carga histórica privada entregue ao lado do instalador, sem publicar nenhum dado pessoal no repositório público.

**Architecture:** O repositório público contém apenas schema, loader, serviço transacional, gerador local e suporte do instalador a arquivo externo. O seed real é gerado fora do GitHub a partir da planilha privada e entregue em um ZIP privado junto do `Setup.exe`. Na primeira abertura, o app procura o seed em `%LOCALAPPDATA%/FinanceiroPessoalDr/initial-seed.json`, valida, aplica em transação única e registra idempotência/proveniência.

**Tech Stack:** Python 3.12, SQLite, PySide6, openpyxl, Inno Setup 6, PyInstaller, pytest, GitHub Actions Windows/Linux.

**Spec:** `docs/superpowers/specs/2026-09-24-dashboard-excel-initial-seed-design.md`

## Global Constraints

- Nenhum dado real, nome, descrição financeira, valor, total ou hash da planilha privada pode ser commitado no GitHub.
- CI usa somente dados sintéticos.
- SQLite local continua sendo a fonte oficial depois da carga.
- Seed é idempotente por `seed_id` e nunca apaga/sobrescreve lançamento manual existente.
- Toda a aplicação do seed é atômica: sucesso integral ou rollback integral.
- Despesa histórica liquidada entra como `PAGO`; receita histórica liquidada entra como `RECEBIDO`.
- Histórico recorrente pode ter `is_recurring=1`, mas não cria `recurrence_rule_id` nem lançamentos futuros.
- O instalador público deve continuar funcionando sem arquivo de seed externo.

## Review Focus

- Seed inválido/corrompido: deve falhar antes de alterar o banco e informar erro sem carga parcial.
- Seed repetido após atualização/reinstalação: deve ser no-op mesmo se o arquivo privado reaparecer.
- Banco com lançamentos manuais semelhantes: só reutilizar correspondência exata e única; não colapsar duplicidades legítimas.
- Instalação sem seed: deve continuar abrindo normalmente, inclusive `--smoke-test`.
- Privacidade do build: nenhum `*.initial-seed.json` ou arquivo privado pode entrar em package data, artifact público ou commit.

---

### Task 1: Persistência de proveniência e idempotência

**Files:**
- Create: `src/financeiro_dr/database/migrations/015_initial_seed.sql`
- Modify: `tests/database/test_migrations.py`

**Interfaces:**
- Consumes: `MigrationRunner.apply_all(connection)` existente.
- Produces: tabelas `initial_seed_batch` e `initial_seed_record` usadas pelo serviço de seed.

- [ ] **Step 1: Write the failing migration test**

Adicionar ao `tests/database/test_migrations.py`:

```python
def test_initial_seed_tables_are_created(tmp_path):
    connection = Database(tmp_path / "db.sqlite").connect()
    MigrationRunner().apply_all(connection)
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert "initial_seed_batch" in tables
    assert "initial_seed_record" in tables
```

- [ ] **Step 2: Run the focused test and verify RED**

```bash
pytest tests/database/test_migrations.py::test_initial_seed_tables_are_created -v
```

Expected: FAIL because the two tables do not exist yet.

- [ ] **Step 3: Add migration 015**

Create `015_initial_seed.sql`:

```sql
CREATE TABLE IF NOT EXISTS initial_seed_batch (
    seed_id TEXT PRIMARY KEY,
    source_label TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    expected_count INTEGER NOT NULL CHECK(expected_count >= 0),
    applied_count INTEGER NOT NULL CHECK(applied_count >= 0),
    warning_count INTEGER NOT NULL CHECK(warning_count >= 0),
    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS initial_seed_record (
    seed_id TEXT NOT NULL REFERENCES initial_seed_batch(seed_id),
    source_row INTEGER NOT NULL,
    record_hash TEXT NOT NULL,
    financial_entry_id INTEGER NOT NULL REFERENCES financial_entry(id),
    action TEXT NOT NULL CHECK(action IN ('INSERTED','REUSED_EXISTING')),
    warning_code TEXT,
    PRIMARY KEY(seed_id, source_row)
);

CREATE INDEX IF NOT EXISTS idx_initial_seed_record_entry
ON initial_seed_record(financial_entry_id);
```

- [ ] **Step 4: Run migration tests and verify GREEN**

```bash
pytest tests/database/test_migrations.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/financeiro_dr/database/migrations/015_initial_seed.sql tests/database/test_migrations.py
git commit -m "feat: add initial seed provenance tables"
```

---

### Task 2: Schema, normalização e serviço transacional do seed

**Files:**
- Create: `src/financeiro_dr/initial_seed/__init__.py`
- Create: `src/financeiro_dr/initial_seed/models.py`
- Create: `src/financeiro_dr/initial_seed/loader.py`
- Create: `src/financeiro_dr/initial_seed/service.py`
- Create: `tests/initial_seed/test_loader.py`
- Create: `tests/initial_seed/test_service.py`

**Interfaces:**
- Produces: `InitialSeedManifest`, `InitialSeedRecord`, `InitialSeedError`, `load_manifest(path: Path) -> InitialSeedManifest`, `InitialDataSeedService(connection).apply(manifest) -> SeedApplyResult`.
- Consumes: tabelas da Task 1 e tabelas existentes `person`, `category`, `financial_entry`.

- [ ] **Step 1: Write loader RED tests**

Create `tests/initial_seed/test_loader.py` with synthetic data only:

```python
import json
import pytest
from financeiro_dr.initial_seed.loader import InitialSeedError, load_manifest


def test_rejects_unknown_schema(tmp_path):
    path = tmp_path / "seed.json"
    path.write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
    with pytest.raises(InitialSeedError, match="versão"):
        load_manifest(path)


def test_loads_valid_synthetic_manifest(tmp_path):
    payload = {
        "schema_version": 1,
        "seed_id": "synthetic-v1",
        "source_label": "fixture",
        "source_sha256": "0" * 64,
        "expected": {
            "record_count": 1,
            "income_count": 0,
            "expense_count": 1,
            "income_cents": 0,
            "expense_cents": 1250,
        },
        "records": [{
            "source_row": 2,
            "holder": "PESSOA TESTE",
            "date": "2026-01-02",
            "description": "Despesa teste",
            "payment_method": "TRANSFERÊNCIA",
            "amount_cents": 1250,
            "category": "MORADIA",
            "raw_type": "MENSAL RECORRENTE",
            "classification": "DESPESA",
            "warning": None,
        }],
    }
    path = tmp_path / "seed.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    manifest = load_manifest(path)
    assert manifest.seed_id == "synthetic-v1"
    assert manifest.records[0].amount_cents == 1250
```

- [ ] **Step 2: Run loader tests and verify RED**

```bash
pytest tests/initial_seed/test_loader.py -v
```

Expected: import/module failure because initial seed module does not exist.

- [ ] **Step 3: Implement manifest models and strict loader**

`models.py` defines frozen dataclasses for manifest/record/expected totals and `SeedApplyResult(inserted, reused, warnings)`. `loader.py` parses UTF-8 JSON, enforces `schema_version == 1`, non-empty `seed_id`, SHA-256 format, unique positive `source_row`, known classifications (`RECEITA`, `DESPESA` after trim/uppercase), ISO date and non-negative integer cents. Before returning, it recomputes record/income/expense counts and totals and compares them with `expected`; mismatch raises `InitialSeedError`.

- [ ] **Step 4: Run loader tests and verify GREEN**

```bash
pytest tests/initial_seed/test_loader.py -v
```

Expected: PASS.

- [ ] **Step 5: Write service RED tests for insertion and idempotency**

Create `tests/initial_seed/test_service.py` with helper manifest containing one paid expense and one received income. Assertions:

```python
result = InitialDataSeedService(connection).apply(manifest)
assert result.inserted == 2
assert result.reused == 0
assert connection.execute("SELECT COUNT(*) FROM financial_entry").fetchone()[0] == 2
assert connection.execute("SELECT COUNT(*) FROM initial_seed_batch").fetchone()[0] == 1

again = InitialDataSeedService(connection).apply(manifest)
assert again.inserted == 0
assert connection.execute("SELECT COUNT(*) FROM financial_entry").fetchone()[0] == 2
```

Also assert `DESPESA/PAGO`, `RECEITA/RECEBIDO`, `settled_date == competence_date`, fixed recurring history has `is_recurring=1` and `recurrence_rule_id IS NULL`.

- [ ] **Step 6: Run service tests and verify RED**

```bash
pytest tests/initial_seed/test_service.py -v
```

Expected: FAIL because service is missing.

- [ ] **Step 7: Implement `InitialDataSeedService.apply`**

Implementation rules:

1. Return no-op when `initial_seed_batch.seed_id` already exists.
2. Use `BEGIN IMMEDIATE` only when not already in a transaction; otherwise use one SAVEPOINT.
3. Insert `initial_seed_batch` **inside that transaction before any `initial_seed_record`**, with `expected_count=manifest.expected.record_count`, `applied_count=0`, `warning_count=0`. This satisfies the FK and is safe because rollback removes the batch too.
4. Resolve/create `person` by trimmed case-insensitive exact name.
5. Resolve/create category after explicit normalizer (`strip`, collapse spaces, uppercase comparison, explicit aliases).
6. Find candidate rows by stable DB fields (date, amount, entry type, beneficiary); perform normalized description/payment comparison in Python; reuse only when exactly one candidate remains.
7. Otherwise insert directly with `FinancialRepository.insert(CreateEntry(...))`, bypassing the user-facing duplicate guard while preserving the seed row as a legitimate historical record.
8. Insert `initial_seed_record` for every source row, including deterministic record hash and optional warning.
9. Validate processed count against manifest expected count, then `UPDATE initial_seed_batch SET applied_count=?, warning_count=?`.
10. Commit/release only on success. On any exception, rollback/rollback-to-savepoint so neither batch, provenance nor new financial rows survive, then raise `InitialSeedError`.

- [ ] **Step 8: Add rollback and duplicate-safety tests**

Add tests proving:

- a manual unrelated entry remains untouched;
- one exact candidate is marked `REUSED_EXISTING`;
- two exact candidates cause a fresh seed insertion instead of collapsing them;
- forced exception after the batch placeholder and at least one row leaves no batch, no seed records and no seed-created financial entries.

- [ ] **Step 9: Run full initial-seed tests and suite**

```bash
pytest tests/initial_seed -v
pytest -q
```

Expected: all PASS.

- [ ] **Step 10: Commit**

```bash
git add src/financeiro_dr/initial_seed tests/initial_seed
git commit -m "feat: apply private initial seed transactionally"
```

---

### Task 3: Bootstrap automático antes do login

**Files:**
- Modify: `src/financeiro_dr/app_paths.py`
- Modify: `src/financeiro_dr/main.py`
- Create: `tests/integration/test_initial_seed_bootstrap.py`

**Interfaces:**
- Produces: `AppPaths.initial_seed_file` property returning `data_dir / "initial-seed.json"`.
- Consumes: `load_manifest()` and `InitialDataSeedService.apply()` from Task 2.

- [ ] **Step 1: Write bootstrap RED tests**

Tests set temporary `LOCALAPPDATA`/`APPDATA` and verify:

```python
paths = AppPaths.from_environment()
assert paths.initial_seed_file == paths.data_dir / "initial-seed.json"
```

Then create a synthetic valid seed at that path, call `_apply_initial_seed(paths, connection)`, and assert the batch exists. A second call must not duplicate. With no file, helper returns `None`.

- [ ] **Step 2: Run bootstrap tests and verify RED**

```bash
pytest tests/integration/test_initial_seed_bootstrap.py -v
```

Expected: missing property/helper.

- [ ] **Step 3: Implement bootstrap helper**

In `main.py`:

```python
def _apply_initial_seed(paths, connection):
    seed_path = paths.initial_seed_file
    if not seed_path.exists():
        return None
    manifest = load_manifest(seed_path)
    result = InitialDataSeedService(connection).apply(manifest)
    try:
        seed_path.unlink()
    except OSError:
        pass
    return result
```

The main flow is:

1. open DB and apply migrations;
2. check DB health;
3. attempt seed before login;
4. for `--smoke-test`, return `0` only after successful/no-op seed processing;
5. for normal startup, if seed fails, create/reuse `QApplication`, show one critical dialog and exit without showing login/window;
6. otherwise continue to login/password setup.

- [ ] **Step 4: Verify bootstrap GREEN and error behavior**

Add test with malformed seed proving `_apply_initial_seed` raises and database has no seed batch. Keep GUI dialog behavior outside the unit helper; smoke path must return non-zero without requiring an interactive dialog.

Run:

```bash
pytest tests/integration/test_initial_seed_bootstrap.py -v
pytest tests/integration/test_cli_smoke.py -v
pytest -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/financeiro_dr/app_paths.py src/financeiro_dr/main.py tests/integration/test_initial_seed_bootstrap.py
git commit -m "feat: bootstrap private seed before login"
```

---

### Task 4: Gerador local do Excel e bloqueios de privacidade

**Files:**
- Create: `tools/__init__.py`
- Create: `tools/build_private_seed.py`
- Modify: `.gitignore`
- Create: `tests/initial_seed/test_private_seed_builder.py`

**Interfaces:**
- Produces CLI: `python tools/build_private_seed.py INPUT OUTPUT --seed-id ID --sheet Entrada_dados`.
- Produces function `build_seed(input_path: Path, output_path: Path, seed_id: str, sheet_name: str) -> dict` used by tests.
- Output compatible with `load_manifest()` from Task 2.

- [ ] **Step 1: Write generator RED test**

No test may use the private workbook. Build a synthetic workbook in `tmp_path` using openpyxl with headers `TITULAR, DATA, MÊS, DESCRIÇÃO, CONTA, VALOR, CATEGORIA, TIPO DE DESPESA, CLASSIFICAÇÃO`, then call `build_seed` and assert:

- Decimal `12.34` becomes `1234` cents;
- classification with trailing spaces becomes `DESPESA`;
- blank amount becomes `0` plus `MISSING_AMOUNT` warning;
- output passes `load_manifest()`.

- [ ] **Step 2: Run generator test and verify RED**

```bash
pytest tests/initial_seed/test_private_seed_builder.py -v
```

Expected: builder module/function missing.

- [ ] **Step 3: Implement builder**

```python
REQUIRED_HEADERS = (
    "TITULAR", "DATA", "DESCRIÇÃO", "CONTA", "VALOR",
    "CATEGORIA", "TIPO DE DESPESA", "CLASSIFICAÇÃO",
)
```

Use `openpyxl.load_workbook(input_path, data_only=True, read_only=True)`. Use `Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` then multiply by 100 and convert to int. Compute source SHA-256 by streaming file bytes. Compute expected counts/totals from generated records. Write JSON with `ensure_ascii=False`, indent 2, UTF-8. Reject a missing worksheet or missing required headers with a clear `ValueError` before writing output.

- [ ] **Step 4: Add privacy ignore rules**

Append to `.gitignore`:

```gitignore
*.initial-seed.json
private-seed/
private-release/
Dashboard*.xlsm
```

Add a test that reads `.gitignore` and asserts the first three generic rules exist; the workbook-name rule is defense-in-depth for this project.

- [ ] **Step 5: Run generator tests and full suite**

```bash
pytest tests/initial_seed/test_private_seed_builder.py -v
pytest -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/__init__.py tools/build_private_seed.py .gitignore tests/initial_seed/test_private_seed_builder.py
git commit -m "feat: add private Excel seed builder"
```

---

### Task 5: Instalador genérico com seed externo opcional

**Files:**
- Modify: `packaging/installer.iss`
- Modify: `.github/workflows/full-v1.yml`
- Create: `tests/packaging/test_installer_contract.py`

**Interfaces:**
- Installer consumes optional sibling file `FinanceiroPessoalDr.initial-seed.json`.
- Installer copies it to `{localappdata}\FinanceiroPessoalDr\initial-seed.json` without embedding it into `Setup.exe`.

- [ ] **Step 1: Write installer contract RED test**

```python
from pathlib import Path


def test_installer_accepts_external_private_seed():
    text = Path("packaging/installer.iss").read_text(encoding="utf-8")
    assert 'FinanceiroPessoalDr.initial-seed.json' in text
    assert 'Flags: external' in text
    assert '{localappdata}\\FinanceiroPessoalDr' in text
```

- [ ] **Step 2: Run and verify RED**

```bash
pytest tests/packaging/test_installer_contract.py -v
```

Expected: FAIL because installer has no external seed rule.

- [ ] **Step 3: Add optional external file rule to Inno Setup**

Under `[Files]` add:

```ini
Source: "{src}\FinanceiroPessoalDr.initial-seed.json"; DestDir: "{localappdata}\FinanceiroPessoalDr"; DestName: "initial-seed.json"; Flags: external skipifsourcedoesntexist ignoreversion
```

The source is runtime `{src}` (folder containing Setup), not a repository path, so the private file is never compiled into the public installer.

- [ ] **Step 4: Extend Windows CI with synthetic external-seed install check**

After installer build:

1. write a two-record synthetic manifest next to `dist/installer/FinanceiroPessoalDr-Setup.exe` as `FinanceiroPessoalDr.initial-seed.json`;
2. point `LOCALAPPDATA` and `APPDATA` at fresh runner temp directories;
3. run Setup with `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART`;
4. assert `%LOCALAPPDATA%\FinanceiroPessoalDr\initial-seed.json` was copied;
5. run the installed EXE with `--smoke-test`;
6. query `%LOCALAPPDATA%\FinanceiroPessoalDr\financeiro.db` using Python `sqlite3` and assert the synthetic batch/entries exist;
7. assert the seed file was removed by successful bootstrap or, if deletion was deliberately skipped by platform behavior, that rerunning `--smoke-test` does not change counts;
8. remove the synthetic file from `dist/installer` before artifact upload.

The workflow upload path remains only Setup + portable ZIP.

- [ ] **Step 5: Run packaging contract and full suite**

```bash
pytest tests/packaging/test_installer_contract.py -v
pytest -q
```

Expected: PASS, then GitHub Actions Linux + Windows jobs must pass from the same final commit.

- [ ] **Step 6: Commit**

```bash
git add packaging/installer.iss .github/workflows/full-v1.yml tests/packaging/test_installer_contract.py
git commit -m "feat: support optional private seed beside installer"
```

---

### Task 6: Gerar e validar o seed real fora do GitHub

**Files:**
- Private input: workbook supplied by user, never commit.
- Private output: `/mnt/data/FinanceiroPessoalDr.initial-seed.json`, never commit.
- Private report: `/mnt/data/FinanceiroPessoalDr-seed-validation.txt`, never commit.

**Interfaces:**
- Consumes `tools/build_private_seed.py` from Task 4.
- Produces the actual private seed consumed by the installer/app.

- [ ] **Step 1: Run the builder against the mounted private workbook**

Resolve the mounted input path at execution time, then run:

```bash
python tools/build_private_seed.py "<private-input.xlsm>" "/mnt/data/FinanceiroPessoalDr.initial-seed.json" --seed-id "financeiro-historico-2026-09-v1"
```

The real input path and seed content must never be added to Git.

- [ ] **Step 2: Validate the real seed without printing private rows**

Load the manifest and report only:

- schema valid;
- record count matches manifest;
- income/expense counts and cents match manifest;
- no duplicate `source_row`;
- all dates parse;
- all classifications are known;
- warning count;
- source SHA-256 matches manifest.

Do not print holder names, descriptions, values per row, or seed content into logs/chat.

- [ ] **Step 3: Apply the real seed to a throwaway SQLite**

Create temporary SQLite, run every migration, apply `InitialDataSeedService.apply(manifest)`, then compare DB aggregate invariants to the private manifest. Apply a second time and assert counts/totals are unchanged.

- [ ] **Step 4: Save private validation report**

Write only PASS/FAIL and aggregate consistency to `/mnt/data/FinanceiroPessoalDr-seed-validation.txt`.

- [ ] **Step 5: Confirm private files are outside Git**

Before any subsequent repository mutation, verify Git status in the execution workspace contains neither private workbook nor `FinanceiroPessoalDr.initial-seed.json`.

---

### Task 7: Montar pacote privado e fazer verificação final

**Files:**
- Downloaded public artifact: validated `FinanceiroPessoalDr-Setup.exe` from successful GitHub Actions run.
- Private seed: `/mnt/data/FinanceiroPessoalDr.initial-seed.json`.
- Output: `/mnt/data/FinanceiroPessoalDr-Privado-Com-Dados.zip`.

**Interfaces:**
- Package root contains exactly the public setup executable, private seed, and `LEIA-ME.txt`.

- [ ] **Step 1: Verify public CI from the final commit**

Require fresh success for:

- full pytest Linux;
- full pytest Windows;
- PyInstaller build;
- packaged EXE smoke test;
- Inno installer build;
- synthetic external-seed installer/app smoke test;
- public artifact upload.

- [ ] **Step 2: Download installer artifact from that exact workflow run**

Do not reuse installer from an earlier commit.

- [ ] **Step 3: Create private package outside GitHub**

ZIP root:

```text
FinanceiroPessoalDr-Setup.exe
FinanceiroPessoalDr.initial-seed.json
LEIA-ME.txt
```

`LEIA-ME.txt` instructs: extract the ZIP, keep Setup and JSON together, execute Setup, and do not send/share the JSON because it contains private financial history.

- [ ] **Step 4: Verify ZIP contents**

Assert exactly three root files and exact seed filename expected by installer.

- [ ] **Step 5: Final regression and privacy review**

Run `pytest -q` on the final public branch and inspect the branch diff to confirm no real seed/workbook/content was committed. Search repository text/paths for `initial-seed.json` and verify hits are generic code/docs/tests only, never payload data.

- [ ] **Step 6: Deliver private artifacts**

Provide user links to:

- `FinanceiroPessoalDr-Privado-Com-Dados.zip` (recommended);
- `FinanceiroPessoalDr-seed-validation.txt`.

Do not expose/upload the private JSON by itself unless user explicitly asks.

---

## Definition of Done

- Public code contains zero real private financial rows.
- Migration 015 exists and passes.
- Seed loader validates schema and manifest invariants.
- Service applies transactionally, idempotently, and safely against existing data.
- Bootstrap happens before login and does nothing when seed is absent.
- Local builder converts Excel to private JSON without float persistence.
- `.gitignore` blocks private seed/workbook paths.
- Generic installer copies optional sibling seed into local app data via `external` rule.
- Public CI passes Linux + Windows + package + synthetic installer/seed smoke test.
- Real private seed validates against its own manifest and applies twice idempotently in throwaway SQLite.
- Final ZIP contains validated Setup + private seed + instructions and is created outside GitHub.