# Pessoas, Classificação e Orçamentos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Classificar cada despesa/receita por pessoa, categoria, subcategoria e centro de custo e entregar orçamento mensal com alertas configuráveis e detalhamento.

**Architecture:** O plano adiciona tabelas de referência e um serviço de orçamento sobre os lançamentos existentes. Lançamentos continuam sendo a fonte de realizado; o orçamento guarda apenas o valor planejado e filtros de escopo. A UI reutiliza o shell existente e injeta novos seletores no formulário de lançamento.

**Tech Stack:** Python 3.12+, PySide6, SQLite, pytest, pytest-qt.

**Spec:** `docs/superpowers/specs/2026-09-22-financeiro-pessoal-dr-design.md`

## Global Constraints

- Pessoas/beneficiários servem para identificar para quem a despesa foi realizada; não existe reembolso familiar automático.
- Estrutura de classificação: Categoria → Subcategoria → Centro de Custo → Pessoa/Beneficiário.
- Centros de custo são personalizáveis.
- Orçamento mensal pode ser por pessoa, categoria, centro de custo ou combinação.
- Alertas precisam suportar 80%, 100% e acima de 100%.
- Registros inativos permanecem visíveis no histórico, mas não aparecem como opção padrão para novos lançamentos.

## Review Focus

- Desativar pessoa/categoria usada em lançamentos antigos não pode quebrar relatórios; Task 1 testa isso.
- Subcategoria precisa pertencer à categoria selecionada; Task 2 testa validação.
- Orçamento sem um dos filtros deve funcionar como escopo amplo, não como valor zero; Task 3 testa isso.
- Lançamento cancelado/excluído não pode consumir orçamento; Task 3 testa isso.
- Alertas de 80/100/>100 precisam ser determinísticos e não duplicados; Task 4 testa isso.

---

### Task 1: Pessoas/beneficiários

**Files:**
- Create: `src/financeiro_dr/database/migrations/002_people_classification.sql`
- Create: `src/financeiro_dr/people/models.py`
- Create: `src/financeiro_dr/people/repository.py`
- Create: `src/financeiro_dr/people/service.py`
- Create: `tests/people/test_people_service.py`

**Interfaces:**
- Produces: `PeopleService.create(name: str, relationship: str | None, nickname: str | None, notes: str | None) -> int`
- Produces: `PeopleService.list_active() -> list[Person]`
- Produces: `PeopleService.set_active(person_id: int, active: bool) -> None`

- [ ] **Step 1: Criar migração**

Criar `person(id, name, relationship, nickname, notes, active, created_at, updated_at)` e índices em `name` e `active`. Atualizar `financial_entry.beneficiary_id` por uso lógico, sem apagar valores existentes.

- [ ] **Step 2: Escrever teste de inativação preservando histórico**

```python
def test_inactive_person_still_resolves_existing_entry(people_service, finance_service, repo):
    pid = people_service.create("Pessoa X", "Família", None, None)
    eid = finance_service.create_entry(make_expense(beneficiary_id=pid))
    people_service.set_active(pid, False)
    assert all(p.id != pid for p in people_service.list_active())
    assert repo.get(eid).beneficiary_id == pid
```

- [ ] **Step 3: Implementar serviço e auditoria**

Criação, edição e inativação devem usar `AuditService`.

- [ ] **Step 4: Rodar testes e commit**

Run: `pytest tests/people -v`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add beneficiaries"
```

---

### Task 2: Categorias, subcategorias e centros de custo

**Files:**
- Create: `src/financeiro_dr/classification/models.py`
- Create: `src/financeiro_dr/classification/repository.py`
- Create: `src/financeiro_dr/classification/service.py`
- Create: `tests/classification/test_classification_service.py`

**Interfaces:**
- Produces: `ClassificationService.create_category(name: str) -> int`
- Produces: `ClassificationService.create_subcategory(category_id: int, name: str) -> int`
- Produces: `ClassificationService.create_cost_center(name: str) -> int`
- Produces: `ClassificationService.validate_selection(category_id, subcategory_id, cost_center_id) -> None`

- [ ] **Step 1: Criar tabelas e sementes iniciais**

Adicionar `category`, `subcategory(category_id FK)`, `cost_center`. Criar centros iniciais: Casa, Família, Veículos, Viagens, Imóveis, Funcionários, Saúde, Educação, Investimentos.

- [ ] **Step 2: Testar subcategoria fora da categoria**

```python
def test_subcategory_must_belong_to_selected_category(service):
    a = service.create_category("Saúde")
    b = service.create_category("Educação")
    sub = service.create_subcategory(a, "Medicamentos")
    with pytest.raises(ValueError, match="Subcategoria não pertence"):
        service.validate_selection(b, sub, None)
```

- [ ] **Step 3: Integrar validação ao `FinancialService`**

Antes de salvar lançamento com IDs de classificação, validar existência, atividade e relação categoria/subcategoria.

- [ ] **Step 4: Rodar testes e commit**

Run: `pytest tests/classification tests/core -v`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add categories subcategories and cost centers"
```

---

### Task 3: Motor de orçamento mensal

**Files:**
- Create: `src/financeiro_dr/database/migrations/003_budgets.sql`
- Create: `src/financeiro_dr/budgets/models.py`
- Create: `src/financeiro_dr/budgets/repository.py`
- Create: `src/financeiro_dr/budgets/service.py`
- Create: `tests/budgets/test_budget_service.py`

**Interfaces:**
- Produces: `BudgetService.create(month: str, amount_cents: int, person_id: int | None = None, category_id: int | None = None, cost_center_id: int | None = None) -> int`
- Produces: `BudgetService.snapshot(budget_id: int) -> BudgetSnapshot`
- Produces: `BudgetService.month_summary(year: int, month: int) -> list[BudgetSnapshot]`

- [ ] **Step 1: Criar tabela de orçamento**

`budget` deve conter `year`, `month`, `amount_cents`, `person_id`, `category_id`, `cost_center_id`, `active`, timestamps e `UNIQUE(year, month, person_id, category_id, cost_center_id)` tratado por serviço para campos nulos.

- [ ] **Step 2: Testar escopo amplo**

```python
def test_category_only_budget_counts_all_people_and_cost_centers(budget_service, seed_expenses):
    bid = budget_service.create("2026-09", 500000, category_id=seed_expenses.health_category_id)
    snap = budget_service.snapshot(bid)
    assert snap.spent_cents == seed_expenses.health_total_cents
```

- [ ] **Step 3: Testar exclusão de cancelados e excluídos**

Criar três despesas iguais: paga, cancelada, excluída logicamente. Somente a paga deve entrar em `spent_cents`.

- [ ] **Step 4: Implementar cálculo**

`spent_cents` usa lançamentos `DESPESA` não cancelados e não excluídos no mês de competência. `remaining_cents = amount_cents - spent_cents`; `percent_used = 0` se orçamento for zero, senão `(spent / planned) * 100`.

- [ ] **Step 5: Rodar testes e commit**

Run: `pytest tests/budgets -v`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add monthly budgets"
```

---

### Task 4: Alertas de orçamento e integração com painel

**Files:**
- Create: `src/financeiro_dr/budgets/alerts.py`
- Create: `tests/budgets/test_budget_alerts.py`
- Modify: `src/financeiro_dr/core/financeiro/dashboard.py`

**Interfaces:**
- Produces: `BudgetAlertService.for_month(year: int, month: int) -> list[BudgetAlert]`
- Extends: `DashboardSnapshot.budget_alerts`

- [ ] **Step 1: Escrever testes de faixas**

```python
@pytest.mark.parametrize(("percent", "level"), [(79.99, None), (80, "WARNING"), (100, "LIMIT"), (100.01, "OVER")])
def test_budget_alert_thresholds(percent, level):
    alert = classify_budget_percent(percent)
    assert (alert.level if alert else None) == level
```

- [ ] **Step 2: Implementar alertas sem duplicar o mesmo orçamento**

Cada orçamento gera no máximo um alerta, sempre a faixa mais alta alcançada.

- [ ] **Step 3: Integrar ao dashboard**

Mostrar contagem e lista curta: nome do escopo, previsto, realizado, percentual e nível.

- [ ] **Step 4: Rodar testes e commit**

Run: `pytest tests/budgets tests/integration -v`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add budget alerts to dashboard"
```

---

### Task 5: Telas de pessoas, classificação, orçamento e filtros

**Files:**
- Create: `src/financeiro_dr/ui/pages/people_page.py`
- Create: `src/financeiro_dr/ui/pages/categories_page.py`
- Create: `src/financeiro_dr/ui/pages/cost_centers_page.py`
- Create: `src/financeiro_dr/ui/pages/budgets_page.py`
- Modify: `src/financeiro_dr/ui/pages/entries_page.py`
- Modify: `src/financeiro_dr/ui/app_window.py`
- Create: `tests/ui/test_classification_in_entry_form.py`
- Create: `tests/ui/test_budgets_page.py`

**Interfaces:**
- Consumes: PeopleService, ClassificationService, BudgetService, BudgetAlertService.

- [ ] **Step 1: Adicionar páginas ao menu**

Adicionar Pessoas/Beneficiários, Categorias e Subcategorias, Centros de Custo e Orçamentos.

- [ ] **Step 2: Habilitar seletores no lançamento**

Ao escolher categoria, recarregar apenas subcategorias ativas daquela categoria. Pessoa e centro de custo devem listar ativos, mas exibir o nome histórico ao editar lançamento antigo vinculado a item inativo.

- [ ] **Step 3: Construir tela de orçamento**

Tabela: mês, escopo, previsto, realizado, saldo, percentual, alerta. Formulário deve permitir qualquer combinação válida de pessoa/categoria/centro de custo.

- [ ] **Step 4: Testar UI**

```python
def test_entry_category_filters_subcategories(qtbot, page, seeded_classification):
    page.category_combo.setCurrentData(seeded_classification.health_id)
    values = [page.subcategory_combo.itemData(i) for i in range(page.subcategory_combo.count())]
    assert seeded_classification.medicine_id in values
    assert seeded_classification.school_fee_id not in values
```

- [ ] **Step 5: Rodar suíte completa**

Run: `pytest -q`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src tests
 git commit -m "feat: add classification and budget screens"
```

## Definition of Done

- Despesas podem ser atribuídas a pessoa, categoria, subcategoria e centro de custo.
- Itens inativos preservam histórico e deixam de aparecer para novos cadastros.
- Orçamentos mensais calculam previsto x realizado corretamente.
- Alertas 80/100/>100 aparecem no orçamento e no painel.
- Financeiro consegue filtrar e entender gasto por pessoa e classificação.
- `pytest -q` passa antes do Plano 3.
