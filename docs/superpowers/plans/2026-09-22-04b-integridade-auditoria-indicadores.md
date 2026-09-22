# Integridade, Auditoria e Indicadores Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar requisitos transversais da especificação antes dos relatórios e empacotamento: origem de receitas, fixas x variáveis, auditoria completa, histórico navegável, verificação de integridade do banco e gráficos do painel.

**Architecture:** Este plano não cria um novo domínio; ele endurece contratos usados por todos os módulos. Campos de classificação financeira entram por migração incremental. Auditoria passa a ser aplicada de forma consistente por serviços de domínio. O painel usa serviços de consulta, e a inicialização executa checagem de integridade sem expor erro técnico ao usuário.

**Tech Stack:** Python 3.12+, PySide6, SQLite, QtCharts, pytest, pytest-qt.

**Spec:** `docs/superpowers/specs/2026-09-22-financeiro-pessoal-dr-design.md`

## Global Constraints

- Relatórios precisam separar fixas x variáveis.
- Receitas precisam ser analisáveis por origem.
- Toda alteração importante precisa de histórico com data/hora, ação, registro, campo, valor anterior e novo.
- Banco corrompido/bloqueado precisa gerar mensagem clara.
- Painel deve ter indicadores e gráficos com acesso ao detalhamento.

## Review Focus

- Lançamento de despesa sem natureza definida não pode entrar silenciosamente em relatório fixas x variáveis; Task 1 testa validação.
- Origem de receita inativa deve continuar aparecendo em histórico; Task 1 testa isso.
- Serviços de banco/cartão/orçamento/patrimônio/investimento/documento precisam auditar edição e exclusão; Task 2 testa cobertura.
- Banco com `integrity_check` diferente de `ok` não pode abrir o fluxo normal; Task 3 testa isso.
- Clique em segmento de gráfico deve abrir o conjunto correto de lançamentos; Task 5 testa isso.

---

### Task 1: Natureza da despesa e origem da receita

**Files:**
- Create: `src/financeiro_dr/database/migrations/011_reporting_classification.sql`
- Create: `src/financeiro_dr/income_sources/models.py`
- Create: `src/financeiro_dr/income_sources/service.py`
- Modify: `src/financeiro_dr/core/financeiro/models.py`
- Modify: `src/financeiro_dr/core/financeiro/service.py`
- Modify: `src/financeiro_dr/ui/pages/entries_page.py`
- Create: `tests/core/test_reporting_classification.py`

**Interfaces:**
- Produces: `IncomeSourceService.create(name: str) -> int`
- Produces: `IncomeSourceService.list_active() -> list[IncomeSource]`
- Extends: `CreateEntry.expense_nature: Literal['FIXA','VARIAVEL'] | None`
- Extends: `CreateEntry.income_source_id: int | None`

- [ ] **Step 1: Criar migração**

Criar `income_source(id, name, active, created_at, updated_at)` e adicionar `expense_nature` e `income_source_id` a `financial_entry`. Valores permitidos de `expense_nature`: `FIXA`, `VARIAVEL` ou `NULL` para tipos que não sejam despesa.

- [ ] **Step 2: Criar origens iniciais**

Seed idempotente: Pró-labore/Salário, Distribuição de Lucros, Recebimentos de Empresas, Aluguéis, Rendimentos de Investimentos, Reembolsos, Transferências Recebidas, Outras Receitas.

- [ ] **Step 3: Testar validação**

```python
def test_expense_requires_expense_nature(finance_service):
    with pytest.raises(ValueError, match="Fixa ou Variável"):
        finance_service.create_entry(make_expense(expense_nature=None))
```

Receita deve aceitar `income_source_id`; despesa não deve exigir origem de receita.

- [ ] **Step 4: Testar origem inativa preservando histórico**

Criar receita vinculada, inativar origem e confirmar que o lançamento antigo continua resolvendo o nome da origem.

- [ ] **Step 5: Atualizar formulário de lançamento**

Quando tipo=`DESPESA`, mostrar Natureza com Fixa/Variável. Quando tipo=`RECEITA`, mostrar Origem da Receita. Para outros tipos, ocultar os dois campos.

- [ ] **Step 6: Rodar testes e commit**

Run: `pytest tests/core/test_reporting_classification.py -v`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add expense nature and income sources"
```

---

### Task 2: Cobertura completa de auditoria

**Files:**
- Create: `src/financeiro_dr/audit/change_context.py`
- Modify: `src/financeiro_dr/banking/service.py`
- Modify: `src/financeiro_dr/cards/service.py`
- Modify: `src/financeiro_dr/budgets/service.py`
- Modify: `src/financeiro_dr/assets/service.py`
- Modify: `src/financeiro_dr/investments/service.py`
- Modify: `src/financeiro_dr/documents/service.py`
- Create: `tests/audit/test_cross_module_audit.py`

**Interfaces:**
- Produces: `audited_change(connection, audit_service, entity: str, entity_id: int, before: dict, after: dict, action: str)` context helper.

- [ ] **Step 1: Escrever teste parametrizado de módulos**

```python
@pytest.mark.parametrize("case", ["bank", "card", "budget", "asset", "investment", "document"])
def test_important_update_is_audited(case, domain_fixture, connection):
    entity, entity_id = domain_fixture.perform_update(case)
    count = connection.execute(
        "select count(*) from audit_log where entity=? and entity_id=? and action='UPDATE'",
        (entity, entity_id),
    ).fetchone()[0]
    assert count >= 1
```

- [ ] **Step 2: Padronizar transação e auditoria**

Toda alteração relevante deve gravar dado e auditoria na mesma transação. Se auditoria falhar, alteração deve fazer rollback.

- [ ] **Step 3: Cobrir exclusão/inativação**

Banco/cartão/pessoa/categoria/bem/investimento não devem ser apagados fisicamente quando já referenciados; usar inativação e registrar auditoria.

- [ ] **Step 4: Rodar testes e commit**

Run: `pytest tests/audit -v`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: enforce audit coverage across modules"
```

---

### Task 3: Checagem de integridade e recuperação de erro do banco

**Files:**
- Create: `src/financeiro_dr/database/health.py`
- Modify: `src/financeiro_dr/main.py`
- Modify: `src/financeiro_dr/ui/error_handler.py`
- Create: `tests/database/test_health.py`

**Interfaces:**
- Produces: `DatabaseHealth.check(connection) -> DatabaseHealthResult`
- Produces: `DatabaseHealthResult.ok: bool`, `message: str`

- [ ] **Step 1: Testar integridade**

```python
def test_integrity_check_ok(database):
    con = database.connect()
    result = DatabaseHealth.check(con)
    assert result.ok is True
```

- [ ] **Step 2: Implementar `PRAGMA quick_check` na abertura**

Se resultado for diferente de `ok`, bloquear abertura das telas financeiras e mostrar: `O banco local apresentou problema de integridade. Não faça novos lançamentos. Restaure um backup válido ou procure suporte.`

- [ ] **Step 3: Tratar banco bloqueado**

Mapear `database is locked` para: `O banco de dados está ocupado. Feche outra cópia do Financeiro Pessoal do Dr. e tente novamente.`

- [ ] **Step 4: Rodar testes e commit**

Run: `pytest tests/database/test_health.py tests/integration/test_database_error_message.py -v`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add database health checks"
```

---

### Task 4: Tela de histórico de alterações

**Files:**
- Create: `src/financeiro_dr/ui/pages/audit_history_page.py`
- Create: `src/financeiro_dr/audit/query_service.py`
- Modify: `src/financeiro_dr/ui/app_window.py`
- Create: `tests/ui/test_audit_history_page.py`

**Interfaces:**
- Produces: `AuditQueryService.search(start=None, end=None, entity=None, action=None, text=None) -> list[AuditEvent]`

- [ ] **Step 1: Implementar consulta**

Filtros por período, entidade, ação e texto. Ordenação padrão: mais recente primeiro.

- [ ] **Step 2: Implementar tela**

Colunas: Data/Hora, Ação, Módulo, Registro, Campo, Valor Anterior, Valor Novo. Clique abre o registro quando ele ainda existir.

- [ ] **Step 3: Testar filtro**

Criar eventos CREATE/UPDATE/DELETE e confirmar que filtro `action='UPDATE'` retorna somente alterações.

- [ ] **Step 4: Rodar testes e commit**

Run: `pytest tests/ui/test_audit_history_page.py -v`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add audit history screen"
```

---

### Task 5: Gráficos e drill-down do painel

**Files:**
- Create: `src/financeiro_dr/core/financeiro/dashboard_charts.py`
- Modify: `src/financeiro_dr/ui/pages/dashboard_page.py`
- Create: `tests/core/test_dashboard_charts.py`
- Create: `tests/ui/test_dashboard_drilldown.py`

**Interfaces:**
- Produces: `DashboardChartService.monthly_expense_by_category(year: int, month: int) -> ChartData`
- Produces: `DashboardChartService.monthly_expense_by_person(year: int, month: int) -> ChartData`
- Produces: `DashboardChartService.cash_flow_6_months(end_month: date) -> ChartData`

- [ ] **Step 1: Criar modelos de gráfico sem dependência de Qt**

`ChartData` deve conter labels, valores em centavos e IDs de lançamentos de cada segmento/ponto.

- [ ] **Step 2: Implementar três gráficos iniciais**

1. Despesas do mês por categoria.
2. Despesas do mês por pessoa/beneficiário.
3. Fluxo de caixa dos últimos 6 meses.

- [ ] **Step 3: Testar drill-down**

```python
def test_chart_segment_carries_exact_entry_ids(chart_service, seeded_entries):
    data = chart_service.monthly_expense_by_category(2026, 9)
    health = next(p for p in data.points if p.label == "Saúde")
    assert set(health.entry_ids) == set(seeded_entries.health_ids)
```

- [ ] **Step 4: Integrar QtCharts**

Clique em barra/fatia/ponto abre a lista de lançamentos filtrada pelos IDs daquele elemento.

- [ ] **Step 5: Rodar suíte completa e commit**

Run: `pytest -q`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add dashboard charts and drilldown"
```

## Definition of Done

- Despesas são marcadas como fixas ou variáveis.
- Receitas possuem origem selecionável e histórica.
- Módulos relevantes geram auditoria consistente.
- Histórico de alterações é consultável na interface.
- Banco é checado antes do uso e erros críticos geram mensagens claras.
- Painel possui gráficos com drill-down para os lançamentos.
- `pytest -q` passa antes do plano de Relatórios/Backup/Instalador.
