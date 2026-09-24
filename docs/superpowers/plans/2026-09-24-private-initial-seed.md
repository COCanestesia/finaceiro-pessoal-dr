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

Run:

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

`models.py` must define frozen dataclasses for manifest/record/expected totals and `SeedApplyResult(inserted, reused, warnings)`. `loader.py` must parse UTF-8 JSON, enforce `schema_version == 1`, non-empty `seed_id`, SHA-256 format, unique positive `source_row`, known classifications (`RECEITA`, `DESPESA` after trim/uppercase), ISO date and non-negative integer cents. Before returning, recompute record/income/expense counts and totals and compare with the `expected` block; mismatch raises `InitialSeedError`.

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

1. Return no-op when `initial_seed_batch.seed_id` exists.
2. Use `BEGIN IMMEDIATE` only when not already in a transaction; otherwise use a SAVEPOINT so callers/tests are safe.
3. Resolve/create `person` by trimmed case-insensitive exact name.
4. Resolve/create category after explicit normalizer (`strip`, collapse spaces, uppercase comparison, explicit aliases).
5. Build exact-match query using date, normalized description, amount, entry type, beneficiary id and normalized payment method; reuse only when exactly one candidate exists.
6. Otherwise insert directly with `FinancialRepository.insert(CreateEntry(...))` using `allow_duplicate=True` semantics at seed level without calling user-facing duplicate guard.
7. Insert `initial_seed_record` for every source row.
8. Validate applied record count against manifest expected count before inserting `initial_seed_batch`.
9. Commit/release only on success; rollback/rollback-to-savepoint on any exception and raise `InitialSeedError`.

- [ ] **Step 8: Add rollback and duplicate-safety tests**

Add tests proving:

- a manual unrelated entry remains untouched;
- one exact candidate is marked `REUSED_EXISTING`;
- two exact candidates cause a fresh seed insertion instead of collapsing them;
- forced invalid record midway leaves no batch and no seed records/entries.

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

Tests must set temporary `LOCALAPPDATA`/`APPDATA` and verify:

```python
paths = AppPaths.from_environment()
assert paths.initial_seed_file == paths.data_dir / "initial-seed.json"
```

Then create a synthetic valid seed at that path, call a new helper `_apply_initial_seed(paths, connection)`, and assert the batch exists. A second call must not duplicate. With no file, helper returns cleanly.

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

Call this after migrations + DB health validation and before login/setup password. For normal GUI startup, seed errors show a critical message and exit without opening the app. For `--smoke-test`, return non-zero instead of requiring GUI interaction.

- [ ] **Step 4: Verify bootstrap GREEN and regression suite**

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
- Create: `tools/build_private_seed.py`
- Modify: `.gitignore`
- Create: `tests/initial_seed/test_private_seed_builder.py`

**Interfaces:**
- Produces CLI: `python tools/build_private_seed.py INPUT OUTPUT --seed-id ID --sheet Entrada_dados`.
- Output compatible with `load_manifest()` from Task 2.

- [ ] **Step 1: Write generator RED test**

No test may use the private workbook. Build a synthetic workbook in `tmp_path` using openpyxl with headers `TITULAR, DATA, MÊS, DESCRIÇÃO, CONTA, VALOR, CATEGORIA, TIPO DE DESPESA, CLASSIFICAÇÃO`, then run the builder function and assert:

- Decimal `12.34` becomes `1234` cents;
- classification with trailing spaces becomes `DESPESA`;
- blank amount becomes `0` plus `MISSING_AMOUNT` warning;
- output passes `load_manifest()`.

- [ ] **Step 2: Run generator test and verify RED**

```bash
pytest tests/initial_seed/test_private_seed_builder.py -v
```

Expected: builder module missing.

- [ ] **Step 3: Implement builder**

Implementation requirements:

```python
REQUIRED_HEADERS = (
    "TITULAR", "DATA", "DESCRIÇÃO", "CONTA", "VALOR",
    "CATEGORIA", "TIPO DE DESPESA", "CLASSIFICAÇÃO",
)
```

Use `openpyxl.load_workbook(input_path, data_only=True, read_only=True)`. Use `Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` then multiply by 100 and convert to int. Compute source SHA-256 by streaming file bytes. Compute expected counts/totals from generated records. Write JSON with `ensure_ascii=False`, indent 2, UTF-8.

- [ ] **Step 4: Add privacy ignore rules**

Append to `.gitignore`:

```gitignore
*.initial-seed.json
private-seed/
private-release/
Dashboard*.xlsm
```

Also add a test that reads `.gitignore` and asserts the first three generic rules exist; the workbook-name rule is defense-in-depth for this project.

- [ ] **Step 5: Run generator tests and full suite**

```bash
pytest tests/initial_seed/test_private_seed_builder.py -v
pytest -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/build_private_seed.py .gitignore tests/initial_seed/test_private_seed_builder.py
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

Create a text-level contract test that loads `packaging/installer.iss` and requires:

```python
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

Add under `[Files]`:

```ini
Source: "{src}\FinanceiroPessoalDr.initial-seed.json"; DestDir: "{localappdata}\FinanceiroPessoalDr"; DestName: "initial-seed.json"; Flags: external skipifsourcedoesntexist ignoreversion
```

This must not reference any repository seed path.

- [ ] **Step 4: Extend Windows CI with synthetic external-seed install check**

After installer build, create a synthetic seed JSON next to `Setup.exe`, set temporary `LOCALAPPDATA`/`APPDATA`, run installer silently, then verify the copied seed exists. Run installed executable with `--smoke-test`, then inspect the temporary SQLite with Python and assert `initial_seed_batch` has one synthetic batch and expected synthetic entries. Delete synthetic seed after the test.

The workflow must continue uploading only `Setup.exe` and portable ZIP, never the synthetic seed file.

- [ ] **Step 5: Run packaging contract locally and push for CI**

```bash
pytest tests/packaging/test_installer_contract.py -v
pytest -q
```

Expected: PASS. Then wait for Linux test + Windows build/install/smoke jobs to complete successfully.

- [ ] **Step 6: Commit**

```bash
git add packaging/installer.iss .github/workflows/full-v1.yml tests/packaging/test_installer_contract.py
git commit -m "feat: support optional private seed beside installer"
```

---

### Task 6: Gerar e validar o seed real fora do GitHub

**Files:**
- Private input: user-provided Excel file, never commit.
- Private output: `/mnt/data/FinanceiroPessoalDr.initial-seed.json`, never commit.
- Private report: `/mnt/data/FinanceiroPessoalDr-seed-validation.txt`, never commit.

**Interfaces:**
- Consumes `tools/build_private_seed.py` from Task 4.
- Produces the actual private seed consumed by the installer/app.

- [ ] **Step 1: Run the builder against the uploaded workbook**

Use a stable seed id that includes the source date/version but no private person name, for example:

```bash
python tools/build_private_seed.py "/mnt/data/Dashboard (ATUALIZADO).xlsm" "/mnt/data/FinanceiroPessoalDr.initial-seed.json" --seed-id "financeiro-historico-2026-09-v1"
```

- [ ] **Step 2: Validate the real seed without printing private rows**

Run a validation script that loads the manifest and reports only:

- schema valid;
- record count matches manifest;
- income/expense counts and cents match manifest;
- no duplicate `source_row`;
- all dates parse;
- all classifications are known;
- warning count;
- source SHA-256 matches manifest.

Do not print holder names, descriptions, values per row, or the seed content into logs/chat.

- [ ] **Step 3: Apply the real seed to a throwaway SQLite copy**

Create a temporary SQLite, apply all migrations, run `InitialDataSeedService.apply(manifest)`, then compare database aggregate invariants to the private manifest. Run apply a second time and assert no count/totals change.

- [ ] **Step 4: Save a private validation report**

Write only high-level PASS/FAIL and aggregate consistency to `/mnt/data/FinanceiroPessoalDr-seed-validation.txt`.

- [ ] **Step 5: Never commit private outputs**

Before any Git operation, confirm:

```bash
git status --short
```

must show neither `FinanceiroPessoalDr.initial-seed.json` nor the private workbook.

---

### Task 7: Montar pacote privado e fazer verificação final

**Files:**
- Downloaded public artifact: validated `FinanceiroPessoalDr-Setup.exe` from successful GitHub Actions run.
- Private seed: `/mnt/data/FinanceiroPessoalDr.initial-seed.json`.
- Output: `/mnt/data/FinanceiroPessoalDr-Privado-Com-Dados.zip`.

**Interfaces:**
- Package root must contain exactly the public setup executable, private seed, and a short `LEIA-ME.txt` instructing the user to extract both files into the same folder before running Setup.

- [ ] **Step 1: Verify public CI from the final commit**

Require fresh success for:

- full pytest Linux;
- full pytest Windows;
- PyInstaller build;
- packaged EXE smoke test;
- Inno installer build;
- synthetic external-seed installer/app smoke test;
- public artifact upload.

- [ ] **Step 2: Download the installer artifact from that exact workflow run**

Do not reuse an installer from an earlier commit.

- [ ] **Step 3: Create private package outside GitHub**

ZIP contents:

```text
FinanceiroPessoalDr-Setup.exe
FinanceiroPessoalDr.initial-seed.json
LEIA-ME.txt
```

`LEIA-ME.txt` says: extract the ZIP, keep the two files together, execute `FinanceiroPessoalDr-Setup.exe`, and do not send/share the JSON because it contains private financial history.

- [ ] **Step 4: Verify ZIP contents**

Assert there are exactly three root files and that the seed filename matches the installer contract.

- [ ] **Step 5: Final regression and privacy review**

Run `pytest -q` on the final public branch and inspect the branch diff to confirm no private seed/workbook/content was committed. Search repository paths/text for `initial-seed.json` and verify all hits are generic code/docs/tests only, never real payload.

- [ ] **Step 6: Deliver private artifacts to the user**

Provide links to:

- `FinanceiroPessoalDr-Privado-Com-Dados.zip` (recommended);
- `FinanceiroPessoalDr-seed-validation.txt` (validation summary).

Do not upload the private seed separately unless the user explicitly asks for it.

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