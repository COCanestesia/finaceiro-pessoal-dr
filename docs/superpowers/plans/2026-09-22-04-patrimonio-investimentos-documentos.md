# Patrimônio, Investimentos e Documentos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar controle patrimonial, investimentos e documentos/comprovantes locais vinculados a lançamentos e bens.

**Architecture:** Patrimônio e investimentos têm tabelas próprias e serviços independentes, mas alimentam o painel consolidado. Documentos são copiados para uma estrutura local controlada pelo aplicativo; o banco guarda metadados e vínculos, nunca bytes grandes. O serviço de documentos valida existência e hash do arquivo para detectar remoção externa.

**Tech Stack:** Python 3.12+, PySide6, SQLite, pathlib, hashlib, shutil, pytest.

**Spec:** `docs/superpowers/specs/2026-09-22-financeiro-pessoal-dr-design.md`

## Global Constraints

- Patrimônio precisa suportar imóveis, veículos, terrenos e outros bens.
- Despesas podem ser vinculadas a um bem específico.
- Investimentos controlam aportes, resgates, rendimentos e saldo atual.
- Investimentos entram no patrimônio líquido.
- Documentos e comprovantes ficam locais e entram no backup.
- Documentos precisam ser localizáveis por lançamento, pessoa, categoria, período ou tipo.

## Review Focus

- Alterar valor estimado de um bem não pode apagar o valor de aquisição; Task 1 testa isso.
- Resgate não pode ser somado como rendimento; Task 2 testa isso.
- Documento com mesmo nome de arquivo não pode sobrescrever outro silenciosamente; Task 3 testa isso.
- Arquivo removido externamente precisa aparecer como ausente, sem quebrar a tela; Task 3 testa isso.
- Patrimônio líquido deve subtrair obrigações e somar investimentos uma única vez; Task 4 testa isso.

---

### Task 1: Cadastro de patrimônio e vínculo de despesas

**Files:**
- Create: `src/financeiro_dr/database/migrations/008_assets.sql`
- Create: `src/financeiro_dr/assets/models.py`
- Create: `src/financeiro_dr/assets/repository.py`
- Create: `src/financeiro_dr/assets/service.py`
- Create: `tests/assets/test_asset_service.py`

**Interfaces:**
- Produces: `AssetService.create(asset_type: str, description: str, acquisition_date: date | None, acquisition_value_cents: int, estimated_value_cents: int, notes: str | None) -> int`
- Produces: `AssetService.update_estimated_value(asset_id: int, value_cents: int) -> None`
- Produces: `AssetService.expenses(asset_id: int, start: date | None = None, end: date | None = None) -> list[FinancialEntry]`

- [ ] **Step 1: Criar migração**

Criar `asset` e adicionar `asset_id` opcional a `financial_entry`. Tipos permitidos: `IMOVEL`, `VEICULO`, `TERRENO`, `OUTRO`.

- [ ] **Step 2: Testar preservação do valor de aquisição**

```python
def test_estimated_value_update_preserves_acquisition_value(asset_service, asset_repo):
    aid = asset_service.create("IMOVEL", "Casa", date(2020, 1, 1), 50000000, 70000000, None)
    asset_service.update_estimated_value(aid, 75000000)
    asset = asset_repo.get(aid)
    assert asset.acquisition_value_cents == 50000000
    assert asset.estimated_value_cents == 75000000
```

- [ ] **Step 3: Integrar vínculo de despesa**

`FinancialService` deve aceitar `asset_id` apenas se o bem existir e estiver ativo. Relatório de despesas do bem usa lançamentos vinculados, sem duplicar o valor no patrimônio.

- [ ] **Step 4: Rodar testes e commit**

Run: `pytest tests/assets tests/core -v`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add assets and linked expenses"
```

---

### Task 2: Investimentos e movimentos

**Files:**
- Create: `src/financeiro_dr/database/migrations/009_investments.sql`
- Create: `src/financeiro_dr/investments/models.py`
- Create: `src/financeiro_dr/investments/repository.py`
- Create: `src/financeiro_dr/investments/service.py`
- Create: `tests/investments/test_investment_service.py`

**Interfaces:**
- Produces: `InvestmentService.create(institution: str, account_name: str, investment_type: str) -> int`
- Produces: `InvestmentService.add_movement(investment_id: int, movement_type: str, amount_cents: int, movement_date: date, notes: str | None = None) -> int`
- Produces: `InvestmentService.balance(investment_id: int, at_date: date | None = None) -> int`
- Produces: `InvestmentService.summary() -> InvestmentSummary`

- [ ] **Step 1: Criar tabelas**

Criar `investment_account` e `investment_movement`. Tipos de movimento: `APORTE`, `RESGATE`, `RENDIMENTO`, `AJUSTE`.

- [ ] **Step 2: Testar saldo e rendimento separado**

```python
def test_redemption_reduces_balance_but_is_not_return(investment_service, investment_id):
    investment_service.add_movement(investment_id, "APORTE", 100000, date(2026, 1, 1))
    investment_service.add_movement(investment_id, "RENDIMENTO", 5000, date(2026, 1, 31))
    investment_service.add_movement(investment_id, "RESGATE", 20000, date(2026, 2, 1))
    summary = investment_service.summary()
    assert summary.balance_cents == 85000
    assert summary.return_cents == 5000
```

- [ ] **Step 3: Implementar regras**

Saldo = aportes + rendimentos + ajustes positivos - resgates - ajustes negativos. Rendimentos são reportados separadamente de aportes/resgates.

- [ ] **Step 4: Rodar testes e commit**

Run: `pytest tests/investments -v`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add investments"
```

---

### Task 3: Armazenamento e busca de documentos

**Files:**
- Create: `src/financeiro_dr/database/migrations/010_documents.sql`
- Create: `src/financeiro_dr/documents/models.py`
- Create: `src/financeiro_dr/documents/storage.py`
- Create: `src/financeiro_dr/documents/service.py`
- Create: `tests/documents/test_document_storage.py`
- Create: `tests/documents/test_document_search.py`

**Interfaces:**
- Produces: `DocumentService.attach(source: Path, document_type: str, entry_id: int | None = None, asset_id: int | None = None, person_id: int | None = None) -> int`
- Produces: `DocumentService.resolve_path(document_id: int) -> Path | None`
- Produces: `DocumentService.search(filters: DocumentFilters) -> list[DocumentRecord]`

- [ ] **Step 1: Criar metadados**

Tabela `document` deve guardar nome original, nome armazenado, hash SHA-256, tamanho, MIME opcional, tipo, caminho relativo, datas e vínculos opcionais a lançamento, bem e pessoa.

- [ ] **Step 2: Implementar nome físico único**

Formato: `YYYY/MM/<document_id>_<sha8>_<safe_original_name>`. O arquivo só é copiado após reservar o ID na transação; em falha de cópia, rollback do registro.

- [ ] **Step 3: Testar dois arquivos com mesmo nome**

```python
def test_same_filename_does_not_overwrite(document_service, tmp_path):
    a = tmp_path / "recibo.pdf"
    a.write_bytes(b"A")
    first = document_service.attach(a, "RECIBO")
    a.write_bytes(b"B")
    second = document_service.attach(a, "RECIBO")
    assert document_service.resolve_path(first) != document_service.resolve_path(second)
```

- [ ] **Step 4: Testar arquivo removido externamente**

`resolve_path()` deve retornar `None` e o registro deve continuar pesquisável com flag `missing=True`.

- [ ] **Step 5: Implementar busca**

Filtros: período, pessoa, categoria via lançamento, tipo de documento, lançamento e patrimônio.

- [ ] **Step 6: Rodar testes e commit**

Run: `pytest tests/documents -v`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add local document storage and search"
```

---

### Task 4: Consolidação de patrimônio líquido no painel

**Files:**
- Create: `src/financeiro_dr/networth/service.py`
- Create: `tests/networth/test_networth_service.py`
- Modify: `src/financeiro_dr/core/financeiro/dashboard.py`

**Interfaces:**
- Produces: `NetWorthService.snapshot(at_date: date) -> NetWorthSnapshot`
- Extends: `DashboardSnapshot.assets_cents`, `investments_cents`, `obligations_cents`, `net_worth_cents`

- [ ] **Step 1: Definir fórmula**

`net_worth = bank_balances + investments + estimated_asset_values - open_obligations`.

Não somar saldo de investimento duas vezes caso exista lançamento de aporte/transferência no fluxo de caixa.

- [ ] **Step 2: Testar consolidação**

```python
def test_net_worth_consolidates_once(networth_service, seeded_finances):
    snap = networth_service.snapshot(date(2026, 9, 30))
    assert snap.net_worth_cents == (
        snap.bank_balances_cents + snap.investments_cents + snap.assets_cents - snap.obligations_cents
    )
```

- [ ] **Step 3: Integrar dashboard**

Adicionar cartões de Patrimônio, Investimentos, Obrigações e Patrimônio Líquido.

- [ ] **Step 4: Rodar testes e commit**

Run: `pytest tests/networth tests/integration -v`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add net worth consolidation"
```

---

### Task 5: Telas de patrimônio, investimentos e documentos

**Files:**
- Create: `src/financeiro_dr/ui/pages/assets_page.py`
- Create: `src/financeiro_dr/ui/pages/investments_page.py`
- Create: `src/financeiro_dr/ui/pages/documents_page.py`
- Modify: `src/financeiro_dr/ui/pages/entries_page.py`
- Modify: `src/financeiro_dr/ui/app_window.py`
- Create: `tests/ui/test_documents_page.py`

**Interfaces:**
- Consumes: AssetService, InvestmentService, DocumentService, NetWorthService.

- [ ] **Step 1: Criar tela de patrimônio**

Tabela com tipo, descrição, aquisição, valor de aquisição, valor estimado e despesas vinculadas. Botão abre detalhes e documentos.

- [ ] **Step 2: Criar tela de investimentos**

Mostrar instituição, aplicação, saldo, aportes, resgates e rendimentos. Formulário de movimento deve deixar claro o tipo.

- [ ] **Step 3: Criar central de documentos**

Filtros por período, pessoa, categoria, tipo e vínculo. Linhas com arquivo ausente exibem aviso `Arquivo não encontrado no disco` e permitem localizar/substituir a cópia sem apagar histórico.

- [ ] **Step 4: Integrar anexos no lançamento**

Tela de lançamento deve permitir anexar, abrir e listar comprovantes.

- [ ] **Step 5: Rodar suíte completa e commit**

Run: `pytest -q`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add assets investments and documents screens"
```

## Definition of Done

- Bens e despesas vinculadas funcionam.
- Investimentos calculam saldo, aportes, resgates e rendimentos corretamente.
- Patrimônio líquido é consolidado sem dupla contagem.
- Documentos ficam organizados localmente, pesquisáveis e detectam arquivos ausentes.
- Dashboard exibe patrimônio, investimentos, obrigações e patrimônio líquido.
- `pytest -q` passa antes do Plano 5.
