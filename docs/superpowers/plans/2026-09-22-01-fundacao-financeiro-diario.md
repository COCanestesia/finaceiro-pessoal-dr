# Fundação e Financeiro Diário Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar a primeira versão executável do aplicativo local com login, SQLite, auditoria, lançamentos, recorrências, parcelas, contas a pagar/receber, agenda e painel diário.

**Architecture:** Aplicativo desktop PySide6 dividido em `database`, `security`, `audit`, `core/financeiro` e `ui`. A UI nunca executa SQL diretamente; repositórios persistem dados e serviços aplicam regras de negócio. Valores monetários são persistidos como centavos inteiros e o SQLite roda com `foreign_keys=ON`, WAL e transações explícitas.

**Tech Stack:** Python 3.12+, PySide6 6.8+, SQLite (`sqlite3`), argon2-cffi, pytest, pytest-qt.

**Spec:** `docs/superpowers/specs/2026-09-22-financeiro-pessoal-dr-design.md`

## Global Constraints

- Aplicativo desktop para Windows.
- Python como linguagem principal.
- PySide6 para interface gráfica.
- SQLite como banco de dados local oficial.
- Funcionamento offline.
- Login local com senha protegida por hash; a senha não será armazenada em texto puro.
- Não usar Supabase ou servidor web obrigatório.
- O banco local é a fonte oficial; planilhas/arquivos são apenas entrada ou saída.
- Não existe fechamento mensal com bloqueio; alterações relevantes precisam de auditoria.
- UI não executa SQL diretamente.
- Valores monetários são `INTEGER` em centavos no SQLite.

## Review Focus

- Valor monetário decimal digitado com vírgula/ponto deve virar centavos sem erro de arredondamento; Task 4 fixa isso em teste.
- Transferência não pode entrar como receita/despesa; Task 4 fixa o comportamento em teste.
- Recorrência mensal iniciada em dia 29/30/31 deve ajustar para o último dia válido do mês; Task 5 fixa em teste.
- Edição/exclusão precisa preservar valor anterior na auditoria; Task 3 fixa em teste.
- Banco bloqueado/corrompido deve gerar erro de domínio legível em vez de stack trace na UI; Tasks 1 e 7 fixam em testes.

---

### Task 1: Estrutura do projeto, caminhos locais e banco SQLite

**Files:**
- Create: `pyproject.toml`
- Create: `src/financeiro_dr/__init__.py`
- Create: `src/financeiro_dr/app_paths.py`
- Create: `src/financeiro_dr/database/connection.py`
- Create: `src/financeiro_dr/database/migrations.py`
- Create: `src/financeiro_dr/database/migrations/001_core.sql`
- Create: `tests/database/test_connection.py`
- Create: `tests/database/test_migrations.py`

**Interfaces:**
- Produces: `AppPaths.from_environment() -> AppPaths`
- Produces: `Database.connect() -> sqlite3.Connection`
- Produces: `MigrationRunner.apply_all(connection: sqlite3.Connection) -> None`

- [ ] **Step 1: Escrever teste de configuração SQLite**

```python
from financeiro_dr.database.connection import Database


def test_connection_enables_foreign_keys_and_wal(tmp_path):
    db = Database(tmp_path / "financeiro.db")
    con = db.connect()
    assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert con.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
```

- [ ] **Step 2: Rodar o teste e confirmar falha**

Run: `pytest tests/database/test_connection.py -v`  
Expected: FAIL por módulos inexistentes.

- [ ] **Step 3: Implementar caminhos e conexão**

```python
# src/financeiro_dr/app_paths.py
from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class AppPaths:
    data_dir: Path
    config_dir: Path
    documents_dir: Path
    database_file: Path

    @classmethod
    def from_environment(cls) -> "AppPaths":
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        roaming = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
        data_dir = local / "FinanceiroPessoalDr"
        config_dir = roaming / "FinanceiroPessoalDr"
        documents_dir = data_dir / "documents"
        for path in (data_dir, config_dir, documents_dir):
            path.mkdir(parents=True, exist_ok=True)
        return cls(data_dir, config_dir, documents_dir, data_dir / "financeiro.db")
```

```python
# src/financeiro_dr/database/connection.py
import sqlite3
from pathlib import Path


class DatabaseError(RuntimeError):
    pass


class Database:
    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        try:
            con = sqlite3.connect(self.path, timeout=10, isolation_level=None)
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA foreign_keys=ON")
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA synchronous=FULL")
            return con
        except sqlite3.Error as exc:
            raise DatabaseError("Não foi possível abrir o banco de dados local.") from exc
```

- [ ] **Step 4: Criar migração principal e runner**

`001_core.sql` deve criar: `schema_migrations`, `local_user`, `audit_log`, `financial_entry`, `recurrence_rule` e `installment_group`. `financial_entry` deve conter `competence_date`, `due_date`, `settled_date`, `description`, `amount_cents`, `entry_type`, `status`, `payment_method`, `notes`, `is_recurring`, `installment_number`, `installment_total`, `recurrence_rule_id`, `installment_group_id`, `beneficiary_id`, `category_id`, `subcategory_id`, `cost_center_id`, `bank_account_id`, `card_id`, `created_at`, `updated_at`, `deleted_at`.

Use `CHECK(amount_cents >= 0)`, `CHECK(entry_type IN ('RECEITA','DESPESA','TRANSFERENCIA','INVESTIMENTO'))` e `CHECK(status IN ('PENDENTE','PAGO','RECEBIDO','ATRASADO','CANCELADO'))`.

- [ ] **Step 5: Testar migração idempotente**

```python
def test_migrations_are_idempotent(tmp_path):
    from financeiro_dr.database.connection import Database
    from financeiro_dr.database.migrations import MigrationRunner
    con = Database(tmp_path / "f.db").connect()
    runner = MigrationRunner()
    runner.apply_all(con)
    runner.apply_all(con)
    assert con.execute("select count(*) from schema_migrations").fetchone()[0] == 1
```

- [ ] **Step 6: Rodar testes da task**

Run: `pytest tests/database -v`  
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src tests
 git commit -m "feat: bootstrap local database foundation"
```

---

### Task 2: Login local e troca de senha

**Files:**
- Create: `src/financeiro_dr/security/passwords.py`
- Create: `src/financeiro_dr/security/auth_service.py`
- Create: `tests/security/test_auth_service.py`

**Interfaces:**
- Consumes: `Database.connect()`
- Produces: `AuthService.initialize_password(password: str) -> None`
- Produces: `AuthService.authenticate(password: str) -> bool`
- Produces: `AuthService.change_password(current: str, new: str) -> None`

- [ ] **Step 1: Escrever testes de hash e autenticação**

```python
def test_password_is_never_stored_in_plain_text(auth_service, connection):
    auth_service.initialize_password("Senha Forte 123!")
    stored = connection.execute("select password_hash from local_user where id=1").fetchone()[0]
    assert stored != "Senha Forte 123!"
    assert auth_service.authenticate("Senha Forte 123!") is True
    assert auth_service.authenticate("errada") is False
```

- [ ] **Step 2: Rodar teste e confirmar falha**

Run: `pytest tests/security/test_auth_service.py -v`  
Expected: FAIL.

- [ ] **Step 3: Implementar Argon2**

```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("A senha precisa ter pelo menos 8 caracteres.")
    return _ph.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    try:
        return _ph.verify(stored_hash, password)
    except VerifyMismatchError:
        return False
```

- [ ] **Step 4: Implementar `AuthService` com transação**

A inicialização só pode ocorrer se ainda não existir senha. A troca deve validar a senha atual antes de atualizar o hash.

- [ ] **Step 5: Rodar testes**

Run: `pytest tests/security -v`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/financeiro_dr/security tests/security
 git commit -m "feat: add local password authentication"
```

---

### Task 3: Auditoria imutável para inclusão, edição e exclusão

**Files:**
- Create: `src/financeiro_dr/audit/audit_service.py`
- Create: `src/financeiro_dr/audit/models.py`
- Create: `tests/audit/test_audit_service.py`

**Interfaces:**
- Produces: `AuditService.record_create(entity: str, entity_id: int, snapshot: dict) -> None`
- Produces: `AuditService.record_update(entity: str, entity_id: int, before: dict, after: dict) -> None`
- Produces: `AuditService.record_delete(entity: str, entity_id: int, before: dict) -> None`

- [ ] **Step 1: Escrever teste de edição**

```python
def test_update_records_old_and_new_values(audit_service, connection):
    audit_service.record_update("financial_entry", 10, {"amount_cents": 200000}, {"amount_cents": 250000})
    row = connection.execute(
        "select field_name, old_value, new_value from audit_log where entity_id=10"
    ).fetchone()
    assert tuple(row) == ("amount_cents", "200000", "250000")
```

- [ ] **Step 2: Implementar gravação por campo alterado**

`record_update` deve criar uma linha por campo cujo valor mudou. `record_delete` usa `action='DELETE'` e grava o snapshot anterior em JSON; `audit_log` não terá operação de exclusão exposta por serviço.

- [ ] **Step 3: Testar exclusão lógica e auditoria**

Adicionar teste garantindo que o registro de auditoria continua existindo depois de `deleted_at` ser preenchido no registro de negócio.

- [ ] **Step 4: Rodar testes**

Run: `pytest tests/audit -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/financeiro_dr/audit tests/audit
 git commit -m "feat: add immutable audit trail"
```

---

### Task 4: Lançamentos financeiros e regras monetárias

**Files:**
- Create: `src/financeiro_dr/core/financeiro/money.py`
- Create: `src/financeiro_dr/core/financeiro/models.py`
- Create: `src/financeiro_dr/core/financeiro/repository.py`
- Create: `src/financeiro_dr/core/financeiro/service.py`
- Create: `tests/core/test_money.py`
- Create: `tests/core/test_financial_service.py`

**Interfaces:**
- Produces: `parse_money(text: str) -> int`
- Produces: `format_money(cents: int) -> str`
- Produces: `FinancialService.create_entry(command: CreateEntry) -> int`
- Produces: `FinancialService.update_entry(entry_id: int, changes: dict) -> None`
- Produces: `FinancialService.soft_delete(entry_id: int) -> None`
- Produces: `FinancialService.duplicate_entry(entry_id: int, due_date: date | None = None) -> int`

- [ ] **Step 1: Fixar parsing de moeda brasileira**

```python
@pytest.mark.parametrize(("text", "expected"), [
    ("1.234,56", 123456),
    ("1234,56", 123456),
    ("1234.56", 123456),
    ("0,01", 1),
])
def test_parse_money(text, expected):
    assert parse_money(text) == expected
```

- [ ] **Step 2: Implementar `parse_money` com `Decimal`**

```python
from decimal import Decimal, ROUND_HALF_UP


def parse_money(text: str) -> int:
    raw = text.strip().replace("R$", "").replace(" ", "")
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    value = Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(value * 100)
```

- [ ] **Step 3: Testar criação e transferência**

```python
def test_transfer_is_not_counted_as_income_or_expense(service, repo):
    service.create_entry(CreateEntry(description="Mover", amount_cents=10000, entry_type="TRANSFERENCIA", status="PAGO", competence_date=date.today()))
    totals = repo.month_totals(date.today().year, date.today().month)
    assert totals.income_cents == 0
    assert totals.expense_cents == 0
```

- [ ] **Step 4: Implementar repositório e serviço com auditoria na mesma transação**

Criação, edição e exclusão lógica devem gravar `audit_log` antes do `COMMIT`. Falha de auditoria deve causar rollback do lançamento.

- [ ] **Step 5: Implementar alerta de duplicidade**

`FinancialService.find_possible_duplicate()` deve procurar registros não excluídos com mesma descrição normalizada, mesmo valor e data de competência/vencimento em janela de ±1 dia. Duplicação explícita deve exigir `allow_duplicate=True` no comando interno da UI.

- [ ] **Step 6: Rodar testes**

Run: `pytest tests/core -v`  
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/financeiro_dr/core tests/core
 git commit -m "feat: add audited financial entries"
```

---

### Task 5: Parcelas, recorrências, contas a pagar/receber e agenda

**Files:**
- Create: `src/financeiro_dr/core/financeiro/scheduling.py`
- Create: `src/financeiro_dr/core/financeiro/payables.py`
- Create: `src/financeiro_dr/core/financeiro/agenda.py`
- Create: `tests/core/test_scheduling.py`
- Create: `tests/core/test_payables.py`
- Create: `tests/core/test_agenda.py`

**Interfaces:**
- Produces: `generate_installment_dates(first_due: date, count: int) -> list[date]`
- Produces: `next_monthly_date(current: date, preferred_day: int) -> date`
- Produces: `PayablesService.buckets(today: date) -> PayableBuckets`
- Produces: `AgendaService.month(year: int, month: int) -> list[AgendaDay]`

- [ ] **Step 1: Testar regra de fim de mês**

```python
def test_monthly_recurrence_clamps_day_31():
    assert next_monthly_date(date(2026, 1, 31), 31) == date(2026, 2, 28)
    assert next_monthly_date(date(2028, 1, 31), 31) == date(2028, 2, 29)
```

- [ ] **Step 2: Implementar recorrência e parcelas sem usar 30 dias fixos**

Use `calendar.monthrange(year, month)[1]` para ajustar o dia. Parcelas guardam `installment_group_id`, número e total.

- [ ] **Step 3: Testar buckets de vencimento**

Criar entradas vencidas, hoje, amanhã, +5 dias e +20 dias; confirmar que cada uma aparece em um único grupo: `overdue`, `today`, `tomorrow`, `next_7_days`, `next_30_days`.

- [ ] **Step 4: Implementar contas a receber com a mesma base de lançamento**

Receitas pendentes usam `status='PENDENTE'`; ao receber, `settled_date` é preenchida e o status vira `RECEBIDO`. Despesas quitadas viram `PAGO`.

- [ ] **Step 5: Implementar agenda mensal**

Agrupar por `due_date`, retornando total a pagar e total a receber por dia, sem incluir cancelados e excluídos.

- [ ] **Step 6: Rodar testes**

Run: `pytest tests/core/test_scheduling.py tests/core/test_payables.py tests/core/test_agenda.py -v`  
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/financeiro_dr/core/financeiro tests/core
 git commit -m "feat: add scheduling payables receivables and agenda"
```

---

### Task 6: Shell PySide6, login e telas do financeiro diário

**Files:**
- Create: `src/financeiro_dr/main.py`
- Create: `src/financeiro_dr/ui/app_window.py`
- Create: `src/financeiro_dr/ui/login_dialog.py`
- Create: `src/financeiro_dr/ui/pages/dashboard_page.py`
- Create: `src/financeiro_dr/ui/pages/entries_page.py`
- Create: `src/financeiro_dr/ui/pages/payables_page.py`
- Create: `src/financeiro_dr/ui/pages/receivables_page.py`
- Create: `src/financeiro_dr/ui/pages/agenda_page.py`
- Create: `src/financeiro_dr/ui/widgets/money_edit.py`
- Create: `tests/ui/test_login_dialog.py`
- Create: `tests/ui/test_entries_page.py`

**Interfaces:**
- Consumes: `AuthService`, `FinancialService`, `PayablesService`, `AgendaService`
- Produces: `MainWindow` com menu lateral e `QStackedWidget`

- [ ] **Step 1: Testar login correto/incorreto com `pytest-qt`**

```python
def test_login_rejects_wrong_password(qtbot, login_dialog):
    qtbot.addWidget(login_dialog)
    login_dialog.password_input.setText("errada")
    qtbot.mouseClick(login_dialog.login_button, Qt.LeftButton)
    assert login_dialog.result() == QDialog.Rejected
    assert "Senha incorreta" in login_dialog.error_label.text()
```

- [ ] **Step 2: Implementar shell com menu lateral**

Criar botões: Início, Lançamentos, Contas a Pagar, Contas a Receber, Agenda Financeira, Histórico e Configurações. Outros módulos entram nos planos posteriores sem alterar o contrato do `MainWindow.add_page(key, title, widget)`.

- [ ] **Step 3: Implementar formulário de lançamento**

Campos obrigatórios nesta fase: tipo, descrição, valor, competência, vencimento, status, forma de pagamento, observação, recorrência e parcelamento. Campos de pessoa/categoria/banco/cartão aparecem desabilitados até os planos correspondentes.

- [ ] **Step 4: Implementar telas de pagar/receber e agenda**

Cada linha deve permitir abrir o lançamento. Em contas a pagar, a ação `Marcar como pago` solicita data de pagamento e atualiza o status.

- [ ] **Step 5: Rodar testes de UI**

Run: `pytest tests/ui -v`  
Expected: PASS em ambiente com Qt offscreen (`QT_QPA_PLATFORM=offscreen`).

- [ ] **Step 6: Commit**

```bash
git add src/financeiro_dr/ui src/financeiro_dr/main.py tests/ui
 git commit -m "feat: add desktop shell and daily finance screens"
```

---

### Task 7: Painel diário, tratamento de erro e verificação integrada

**Files:**
- Create: `src/financeiro_dr/core/financeiro/dashboard.py`
- Create: `src/financeiro_dr/ui/error_handler.py`
- Create: `tests/integration/test_daily_finance_flow.py`
- Create: `tests/integration/test_database_error_message.py`
- Modify: `src/financeiro_dr/ui/pages/dashboard_page.py`

**Interfaces:**
- Produces: `DashboardService.snapshot(today: date) -> DashboardSnapshot`
- Produces: `show_user_error(parent, message: str) -> None`

- [ ] **Step 1: Escrever teste de fluxo completo**

```python
def test_daily_flow_updates_dashboard(app_services):
    finance = app_services.finance
    dashboard = app_services.dashboard
    finance.create_entry(CreateEntry(description="Condomínio", amount_cents=150000, entry_type="DESPESA", status="PENDENTE", competence_date=date.today(), due_date=date.today()))
    snap = dashboard.snapshot(date.today())
    assert snap.pay_today_cents == 150000
    assert snap.overdue_count == 0
```

- [ ] **Step 2: Implementar snapshot inicial**

Nesta fase o painel mostra: receitas do mês, despesas do mês, resultado, atrasadas, pagar hoje, amanhã, próximos 7 dias e próximos 30 dias. Patrimônio, investimentos, cartões, orçamento e conciliação entram nos planos seguintes.

- [ ] **Step 3: Testar erro de banco bloqueado**

Simular `sqlite3.OperationalError("database is locked")` e confirmar que a camada de aplicação converte para mensagem `O banco de dados está ocupado. Tente novamente em alguns segundos.` sem exibir traceback na interface.

- [ ] **Step 4: Rodar suíte completa**

Run: `pytest -q`  
Expected: PASS.

- [ ] **Step 5: Rodar aplicação manualmente**

Run: `python -m financeiro_dr.main`  
Expected: tela de definição de senha no primeiro uso; depois login; menu lateral abre as telas; um lançamento persiste após fechar/reabrir.

- [ ] **Step 6: Commit**

```bash
git add src tests
 git commit -m "feat: complete phase one daily finance workflow"
```

## Definition of Done

- Aplicativo abre localmente e funciona sem internet.
- Primeiro uso define senha; usos seguintes exigem login.
- Banco SQLite é criado e migrado automaticamente.
- Lançamentos de receita/despesa/transferência/investimento funcionam.
- Parcelas e recorrências geram vencimentos corretos.
- Contas a pagar/receber e agenda refletem os lançamentos.
- Painel mostra obrigações do dia e próximos períodos.
- Toda inclusão/edição/exclusão relevante gera auditoria.
- `pytest -q` passa antes de iniciar o Plano 2.
