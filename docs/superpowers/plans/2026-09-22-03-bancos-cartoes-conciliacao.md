# Bancos, Cartões e Conciliação Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar controle de contas bancárias e cartões, transferências internas corretas, faturas, importação OFX/CSV/XLSX e conciliação automática/manual.

**Architecture:** Contas e cartões são módulos próprios, mas continuam vinculados a `financial_entry`. O saldo bancário é calculado a partir do saldo inicial mais movimentações liquidadas. A conciliação importa movimentos externos para uma área de staging, calcula candidatos e só cria vínculo definitivo após confirmação ou score suficientemente alto com regra explícita.

**Tech Stack:** Python 3.12+, PySide6, SQLite, csv, openpyxl, ofxtools, pytest.

**Spec:** `docs/superpowers/specs/2026-09-22-financeiro-pessoal-dr-design.md`

## Global Constraints

- Transferências entre contas próprias não contam como receita ou despesa.
- Cartão controla limite, fechamento, vencimento, fatura atual e próximas faturas.
- Compras parceladas devem aparecer nas faturas futuras.
- Conciliação importa OFX, CSV e Excel.
- Estados de conciliação: Conciliado, Pendente e Divergente.
- Duplicidades de importação precisam ser detectadas.

## Review Focus

- Transferência deve debitar uma conta e creditar outra sem alterar resultado; Task 1 testa isso.
- Compra feita depois do fechamento precisa ir para a fatura seguinte; Task 2 testa isso.
- Importar o mesmo extrato duas vezes não pode duplicar movimentos; Task 3 testa isso.
- Valores iguais em datas próximas não podem ser ligados silenciosamente ao lançamento errado; Task 4 exige confirmação em caso ambíguo.
- CSV/XLSX com colunas ausentes precisa falhar com mensagem clara; Task 3 testa isso.

---

### Task 1: Contas bancárias, saldos e transferências

**Files:**
- Create: `src/financeiro_dr/database/migrations/004_bank_accounts.sql`
- Create: `src/financeiro_dr/banking/models.py`
- Create: `src/financeiro_dr/banking/repository.py`
- Create: `src/financeiro_dr/banking/service.py`
- Create: `tests/banking/test_bank_service.py`

**Interfaces:**
- Produces: `BankService.create_account(institution: str, name: str, opening_balance_cents: int = 0) -> int`
- Produces: `BankService.balance(account_id: int, at_date: date | None = None) -> int`
- Produces: `BankService.transfer(source_id: int, target_id: int, amount_cents: int, transfer_date: date, description: str) -> TransferResult`

- [ ] **Step 1: Criar migração de contas e vínculos de transferência**

Criar `bank_account` e `internal_transfer`. `internal_transfer` guarda IDs de origem/destino e os dois `financial_entry_id` gerados para rastreabilidade.

- [ ] **Step 2: Testar saldo**

```python
def test_balance_uses_opening_balance_and_settled_entries(bank_service, finance_service, account_id):
    finance_service.create_entry(make_paid_expense(amount_cents=3000, bank_account_id=account_id))
    assert bank_service.balance(account_id) == 7000  # saldo inicial 10000
```

- [ ] **Step 3: Testar transferência sem impacto no resultado**

```python
def test_internal_transfer_moves_balance_without_income_or_expense(bank_service, dashboard, source, target):
    bank_service.transfer(source, target, 2500, date.today(), "Reserva")
    snap = dashboard.snapshot(date.today())
    assert snap.income_cents == 0
    assert snap.expense_cents == 0
```

- [ ] **Step 4: Implementar transferência atômica**

A operação cria duas entradas `TRANSFERENCIA` ligadas pelo mesmo registro. Se uma gravação falhar, tudo deve fazer rollback.

- [ ] **Step 5: Rodar testes e commit**

Run: `pytest tests/banking tests/core -v`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add bank accounts and internal transfers"
```

---

### Task 2: Cartões, fechamento, faturas e parcelamento

**Files:**
- Create: `src/financeiro_dr/database/migrations/005_cards.sql`
- Create: `src/financeiro_dr/cards/models.py`
- Create: `src/financeiro_dr/cards/billing.py`
- Create: `src/financeiro_dr/cards/service.py`
- Create: `tests/cards/test_billing_cycle.py`
- Create: `tests/cards/test_card_service.py`

**Interfaces:**
- Produces: `CardService.create_card(issuer: str, holder: str, limit_cents: int, closing_day: int, due_day: int) -> int`
- Produces: `invoice_period_for(purchase_date: date, closing_day: int) -> tuple[int, int]`
- Produces: `CardService.add_purchase(...) -> list[int]`
- Produces: `CardService.invoice(card_id: int, year: int, month: int) -> CardInvoice`

- [ ] **Step 1: Criar tabelas**

Criar `credit_card`, `card_purchase`, `card_installment` e `card_invoice_payment`. `card_installment` deve referenciar `financial_entry` para manter classificação por pessoa/categoria.

- [ ] **Step 2: Fixar regra de fechamento**

```python
def test_purchase_after_closing_goes_to_next_invoice():
    assert invoice_period_for(date(2026, 9, 11), closing_day=10) == (2026, 10)
    assert invoice_period_for(date(2026, 9, 10), closing_day=10) == (2026, 9)
```

- [ ] **Step 3: Implementar parcelas**

Compra de R$100,00 em 3x deve distribuir centavos de forma determinística: 3334, 3333, 3333. A soma das parcelas deve sempre ser igual ao total original.

- [ ] **Step 4: Calcular limites**

`used_limit_cents` soma parcelas ainda não pagas/canceladas; `available_limit_cents = limit - used`. Limite nunca pode ser negativo silenciosamente: retornar alerta quando a compra exceder.

- [ ] **Step 5: Rodar testes e commit**

Run: `pytest tests/cards -v`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add cards installments and invoices"
```

---

### Task 3: Importadores OFX, CSV e XLSX com deduplicação

**Files:**
- Create: `src/financeiro_dr/database/migrations/006_statement_import.sql`
- Create: `src/financeiro_dr/reconciliation/importers/base.py`
- Create: `src/financeiro_dr/reconciliation/importers/ofx.py`
- Create: `src/financeiro_dr/reconciliation/importers/csv_importer.py`
- Create: `src/financeiro_dr/reconciliation/importers/xlsx.py`
- Create: `src/financeiro_dr/reconciliation/import_service.py`
- Create: `tests/reconciliation/test_importers.py`
- Create: `tests/reconciliation/fixtures/sample.ofx`
- Create: `tests/reconciliation/fixtures/sample.csv`
- Create: `tests/reconciliation/fixtures/sample.xlsx`

**Interfaces:**
- Produces: `StatementRow(external_id, posted_date, amount_cents, description, raw_hash)`
- Produces: `ImportService.import_file(account_id: int, path: Path, mapping: ColumnMapping | None = None) -> ImportSummary`

- [ ] **Step 1: Criar staging de extrato**

Criar `statement_import` e `statement_row`. Deduplicação usa `UNIQUE(account_id, raw_hash)`, em que hash inclui identificador externo quando disponível; senão data+valor+descrição normalizada.

- [ ] **Step 2: Testar importação duplicada**

```python
def test_importing_same_file_twice_does_not_duplicate(import_service, sample_ofx, account_id):
    first = import_service.import_file(account_id, sample_ofx)
    second = import_service.import_file(account_id, sample_ofx)
    assert first.created > 0
    assert second.created == 0
    assert second.duplicates == first.created
```

- [ ] **Step 3: Implementar CSV/XLSX com mapeamento explícito**

Campos mínimos: data, descrição e valor. Se faltar coluna obrigatória, levantar `ImportFormatError("Arquivo sem coluna obrigatória: valor")` ou equivalente.

- [ ] **Step 4: Implementar OFX**

Usar identificador FITID quando existir. Valor negativo representa saída; positivo representa entrada.

- [ ] **Step 5: Rodar testes e commit**

Run: `pytest tests/reconciliation/test_importers.py -v`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add statement importers"
```

---

### Task 4: Motor de conciliação automática e manual

**Files:**
- Create: `src/financeiro_dr/database/migrations/007_reconciliation.sql`
- Create: `src/financeiro_dr/reconciliation/matcher.py`
- Create: `src/financeiro_dr/reconciliation/service.py`
- Create: `tests/reconciliation/test_matcher.py`
- Create: `tests/reconciliation/test_reconciliation_service.py`

**Interfaces:**
- Produces: `score_match(statement: StatementRow, entry: FinancialEntry) -> MatchScore`
- Produces: `ReconciliationService.suggest(statement_row_id: int) -> list[MatchCandidate]`
- Produces: `ReconciliationService.confirm(statement_row_id: int, entry_id: int) -> None`
- Produces: `ReconciliationService.mark_divergent(statement_row_id: int, note: str) -> None`

- [ ] **Step 1: Definir score**

Pontuação base:
- valor exatamente igual: +60;
- data igual: +25;
- data ±1 dia: +18;
- descrição normalizada com similaridade >=0,8: +15.

Auto-sugestão forte: >=85. Auto-confirmação não deve ocorrer quando houver dois candidatos com diferença de score <=5.

- [ ] **Step 2: Testar ambiguidade**

```python
def test_equal_candidates_require_manual_confirmation(matcher, statement, two_equal_entries):
    result = matcher.rank(statement, two_equal_entries)
    assert result.auto_confirm is False
    assert len(result.candidates) == 2
```

- [ ] **Step 3: Criar tabela de vínculo**

`reconciliation_link` guarda statement row, entry, status, score, confirmed_at, note. Um movimento e um lançamento só podem ter um vínculo conciliado ativo.

- [ ] **Step 4: Implementar estados**

Sem vínculo: PENDENTE. Vínculo confirmado: CONCILIADO. Divergência manual ou diferença de valor confirmada: DIVERGENTE.

- [ ] **Step 5: Rodar testes e commit**

Run: `pytest tests/reconciliation -v`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add automatic reconciliation engine"
```

---

### Task 5: Telas de bancos, cartões e conciliação

**Files:**
- Create: `src/financeiro_dr/ui/pages/banks_page.py`
- Create: `src/financeiro_dr/ui/pages/cards_page.py`
- Create: `src/financeiro_dr/ui/pages/reconciliation_page.py`
- Modify: `src/financeiro_dr/ui/pages/entries_page.py`
- Modify: `src/financeiro_dr/ui/pages/dashboard_page.py`
- Modify: `src/financeiro_dr/ui/app_window.py`
- Create: `tests/ui/test_reconciliation_page.py`

**Interfaces:**
- Consumes: BankService, CardService, ImportService, ReconciliationService.

- [ ] **Step 1: Adicionar Bancos e Contas**

Tela deve mostrar instituição, conta, saldo atual e ativo/inativo. Botão de transferência abre diálogo com origem, destino, valor, data e descrição.

- [ ] **Step 2: Adicionar Cartões**

Mostrar limite total/usado/disponível, fechamento, vencimento, fatura atual e próximas faturas. Permitir cadastrar compra e parcelamento.

- [ ] **Step 3: Adicionar importação e conciliação lado a lado**

Coluna esquerda: extrato. Coluna direita: melhor candidato no sistema. Mostrar valor, data, descrição, diferença, score e status. Ações: Confirmar, Escolher outro lançamento, Marcar divergente, Ignorar duplicidade.

- [ ] **Step 4: Integrar alertas ao dashboard**

Adicionar faturas em aberto, faturas próximas do vencimento, cartões próximos do limite e contagem de conciliações pendentes.

- [ ] **Step 5: Testar UI e suíte completa**

Run: `pytest -q`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src tests
 git commit -m "feat: add banking cards and reconciliation screens"
```

## Definition of Done

- Contas bancárias calculam saldo corretamente.
- Transferências internas não distorcem receitas/despesas.
- Cartões geram faturas e parcelas no mês correto.
- OFX/CSV/XLSX são importados com deduplicação.
- Conciliação sugere candidatos e exige confirmação em casos ambíguos.
- Dashboard exibe pendências de conciliação e faturas.
- `pytest -q` passa antes do Plano 4.
