# Relatórios, Backup e Instalador Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finalizar a versão 1 com relatórios detalhados/exportáveis, backup/restauração confiáveis, configurações e instalador Windows pronto para uso diário.

**Architecture:** Relatórios consomem serviços de consulta sem modificar dados. Exportadores PDF/XLSX recebem um modelo tabular comum para garantir números idênticos na tela e nos arquivos. O backup cria pacote versionado contendo SQLite consistente, documentos e configurações essenciais; a restauração valida integridade antes de substituir dados ativos. O empacotamento usa PyInstaller e instalador Inno Setup.

**Tech Stack:** Python 3.12+, PySide6, SQLite, openpyxl, reportlab, PyInstaller, Inno Setup, pytest.

**Spec:** `docs/superpowers/specs/2026-09-22-financeiro-pessoal-dr-design.md`

## Global Constraints

- Todos os relatórios precisam de filtro por período e, quando aplicável, pessoa, categoria, conta, cartão, centro de custo e status.
- PDF e Excel devem usar os mesmos dados exibidos na tela.
- O usuário precisa conseguir ir do resumo ao detalhamento dos lançamentos.
- Backup automático diário e botão manual são obrigatórios.
- Backup inclui banco, documentos e configurações essenciais.
- Restauração exige verificação de integridade antes de substituir dados.
- Destino principal é uma pasta local sincronizada pelo Google Drive; o aplicativo não chama API do Google Drive.
- A versão final precisa de teste manual no Windows e instalador com atalho.

## Review Focus

- Relatório filtrado precisa totalizar exatamente os lançamentos detalhados exibidos; Task 1 testa isso.
- PDF e XLSX não podem divergir em totais; Task 2 testa isso.
- Backup durante uso do banco precisa ser consistente; Task 3 usa SQLite backup API e testa integridade.
- Restauração inválida não pode destruir a base atual; Task 4 testa rollback/abort.
- Instalador não pode gravar banco dentro de `Program Files`; Task 6 verifica caminhos de dados do usuário.

---

### Task 1: Consultas e modelos de relatório

**Files:**
- Create: `src/financeiro_dr/reports/models.py`
- Create: `src/financeiro_dr/reports/query_service.py`
- Create: `tests/reports/test_query_service.py`

**Interfaces:**
- Produces: `ReportFilters(start: date, end: date, person_id=None, category_id=None, subcategory_id=None, cost_center_id=None, bank_account_id=None, card_id=None, status=None)`
- Produces: `ReportQueryService.expenses(filters) -> ReportTable`
- Produces: `ReportQueryService.income(filters) -> ReportTable`
- Produces: `ReportQueryService.cash_flow(filters) -> ReportTable`
- Produces: `ReportQueryService.budget_vs_actual(filters) -> ReportTable`
- Produces: `ReportQueryService.net_worth(at_date) -> ReportTable`

- [ ] **Step 1: Definir `ReportTable`**

```python
@dataclass(frozen=True)
class ReportTable:
    title: str
    columns: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]
    total_cents: int | None
    detail_entry_ids: tuple[int, ...]
```

- [ ] **Step 2: Testar total x detalhe**

```python
def test_expense_report_total_equals_detail_sum(report_service, seeded_entries):
    report = report_service.expenses(ReportFilters(date(2026, 9, 1), date(2026, 9, 30)))
    detail_total = sum(seeded_entries.by_id(i).amount_cents for i in report.detail_entry_ids)
    assert report.total_cents == detail_total
```

- [ ] **Step 3: Implementar relatórios principais**

Criar consultas para: despesas por pessoa/categoria/subcategoria/centro/conta/cartão/período, fixas x variáveis, pagas x pendentes, receitas por origem, contas a pagar/receber, orçamento, conciliação, faturas, fluxo de caixa, evolução mensal, patrimônio, investimentos e patrimônio líquido.

Cada agrupamento deve retornar linhas de resumo e IDs de lançamentos para drill-down.

- [ ] **Step 4: Rodar testes e commit**

Run: `pytest tests/reports/test_query_service.py -v`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add report query service"
```

---

### Task 2: Exportação PDF e Excel

**Files:**
- Create: `src/financeiro_dr/reports/export_xlsx.py`
- Create: `src/financeiro_dr/reports/export_pdf.py`
- Create: `tests/reports/test_exports.py`

**Interfaces:**
- Produces: `export_xlsx(table: ReportTable, destination: Path) -> Path`
- Produces: `export_pdf(table: ReportTable, destination: Path) -> Path`

- [ ] **Step 1: Implementar XLSX**

Usar openpyxl. Primeira linha: título. Segunda: período/filtros formatados. Cabeçalho em seguida. Valores monetários devem ser gravados como número decimal e formato `R$ #,##0.00`; não gravar moeda como string.

- [ ] **Step 2: Implementar PDF**

Usar ReportLab Platypus com cabeçalho, filtros, tabela paginada, total e data/hora de geração. Relatórios largos devem usar página paisagem automaticamente.

- [ ] **Step 3: Testar paridade de total**

```python
def test_pdf_and_xlsx_use_same_report_table(report_table, tmp_path):
    xlsx = export_xlsx(report_table, tmp_path / "r.xlsx")
    pdf = export_pdf(report_table, tmp_path / "r.pdf")
    assert xlsx.exists() and xlsx.stat().st_size > 0
    assert pdf.exists() and pdf.stat().st_size > 0
    assert report_table.total_cents == 123456
```

A lógica de cálculo não pode existir dentro dos exportadores; ambos recebem o mesmo `ReportTable`.

- [ ] **Step 4: Rodar testes e commit**

Run: `pytest tests/reports/test_exports.py -v`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add pdf and excel report exports"
```

---

### Task 3: Backup consistente e automático

**Files:**
- Create: `src/financeiro_dr/database/migrations/011_backup_log.sql`
- Create: `src/financeiro_dr/backup/models.py`
- Create: `src/financeiro_dr/backup/service.py`
- Create: `src/financeiro_dr/backup/scheduler.py`
- Create: `tests/backup/test_backup_service.py`

**Interfaces:**
- Produces: `BackupService.create(destination_dir: Path, reason: str) -> BackupResult`
- Produces: `BackupService.last_success() -> BackupRecord | None`
- Produces: `BackupScheduler.should_run(now: datetime) -> bool`

- [ ] **Step 1: Criar formato do backup**

Pacote: `FinanceiroPessoalDr_Backup_YYYYMMDD_HHMMSS.zip` contendo:
- `manifest.json` com versão, timestamp, hash do banco e quantidade de documentos;
- `financeiro.db` obtido por `sqlite3.Connection.backup()` para snapshot consistente;
- pasta `documents/`;
- `config.json` sem segredo em texto puro.

- [ ] **Step 2: Testar integridade do snapshot com banco aberto**

```python
def test_backup_is_valid_while_source_database_is_open(backup_service, destination, connection):
    result = backup_service.create(destination, "MANUAL")
    extracted_db = extract_backup_db(result.path)
    con = sqlite3.connect(extracted_db)
    assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
```

- [ ] **Step 3: Implementar scheduler diário**

Executar no máximo uma vez por dia após login/abertura do app quando `auto_backup_enabled=true` e houver pasta configurada. Falha de pasta indisponível deve registrar tentativa e mostrar aviso não bloqueante.

- [ ] **Step 4: Registrar histórico de backups**

Tabela `backup_log`: timestamp, destino, reason (`AUTO`/`MANUAL`), status, mensagem e nome do arquivo.

- [ ] **Step 5: Rodar testes e commit**

Run: `pytest tests/backup/test_backup_service.py -v`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add consistent local backups"
```

---

### Task 4: Restauração segura

**Files:**
- Create: `src/financeiro_dr/backup/restore_service.py`
- Create: `tests/backup/test_restore_service.py`

**Interfaces:**
- Produces: `RestoreService.validate(backup_zip: Path) -> RestoreValidation`
- Produces: `RestoreService.restore(backup_zip: Path) -> RestoreResult`

- [ ] **Step 1: Validar antes de restaurar**

Validações obrigatórias: ZIP abre, `manifest.json` existe, hash do banco confere, `PRAGMA integrity_check='ok'`, versão do schema é suportada e caminhos internos não escapam do diretório de extração.

- [ ] **Step 2: Testar backup inválido preservando base atual**

```python
def test_invalid_restore_does_not_replace_current_database(restore_service, corrupted_backup, current_db):
    before = current_db.read_bytes()
    with pytest.raises(InvalidBackupError):
        restore_service.restore(corrupted_backup)
    assert current_db.read_bytes() == before
```

- [ ] **Step 3: Implementar troca atômica**

Antes de substituir, criar `pre_restore_<timestamp>` da base atual. Restaurar para arquivo temporário, validar novamente, fechar conexões ativas e usar `os.replace()` para troca atômica. Restaurar documentos somente após validação completa do pacote.

- [ ] **Step 4: Rodar testes e commit**

Run: `pytest tests/backup -v`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add validated backup restore"
```

---

### Task 5: Telas de relatórios, backup e configurações

**Files:**
- Create: `src/financeiro_dr/settings/models.py`
- Create: `src/financeiro_dr/settings/service.py`
- Create: `src/financeiro_dr/ui/pages/reports_page.py`
- Create: `src/financeiro_dr/ui/pages/backup_page.py`
- Create: `src/financeiro_dr/ui/pages/settings_page.py`
- Modify: `src/financeiro_dr/ui/app_window.py`
- Create: `tests/ui/test_reports_page.py`
- Create: `tests/ui/test_backup_page.py`

**Interfaces:**
- Produces: `SettingsService.load() -> AppSettings`
- Produces: `SettingsService.save(settings: AppSettings) -> None`
- Consumes: ReportQueryService, exporters, BackupService, RestoreService, AuthService.

- [ ] **Step 1: Implementar configurações**

Configurações: pasta de backup, backup automático ligado/desligado, limiar de alerta de cartão, limiares de orçamento e troca de senha. Salvar em `%APPDATA%/FinanceiroPessoalDr/config.json`.

- [ ] **Step 2: Criar tela de relatórios**

Seletor de relatório + filtros + tabela + total + botão `Ver lançamentos` + `Exportar PDF` + `Exportar Excel`.

- [ ] **Step 3: Criar tela de backup**

Mostrar último backup, destino, histórico, `Fazer backup agora` e `Restaurar backup`. Antes de restaurar, exibir resumo da validação e pedir confirmação explícita.

- [ ] **Step 4: Rodar testes e commit**

Run: `pytest tests/ui/test_reports_page.py tests/ui/test_backup_page.py -v`  
Expected: PASS.

```bash
git add src tests
 git commit -m "feat: add reports backup and settings screens"
```

---

### Task 6: Empacotamento Windows e teste de aceitação

**Files:**
- Create: `packaging/financeiro_dr.spec`
- Create: `packaging/installer.iss`
- Create: `scripts/build_windows.ps1`
- Create: `docs/windows-smoke-test.md`
- Create: `tests/integration/test_app_paths.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: `dist/FinanceiroPessoalDr/FinanceiroPessoalDr.exe`
- Produces: `dist/installer/FinanceiroPessoalDr-Setup.exe`

- [ ] **Step 1: Configurar PyInstaller**

Incluir PySide6, migrações SQL e recursos estáticos. Banco/documentos/configuração nunca devem ser empacotados como dados permanentes; são criados em `%LOCALAPPDATA%`/`%APPDATA%`.

- [ ] **Step 2: Testar caminhos fora de Program Files**

```python
def test_runtime_data_is_not_inside_application_directory(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    paths = AppPaths.from_environment()
    assert "Program Files" not in str(paths.database_file)
```

- [ ] **Step 3: Criar Inno Setup**

Instalar executável em `{autopf}\Financeiro Pessoal Dr`, criar atalho na área de trabalho e menu Iniciar, sem exigir banco pré-existente.

- [ ] **Step 4: Criar script de build**

`scripts/build_windows.ps1` deve executar, nesta ordem: `pytest -q`, limpar `build/dist`, PyInstaller, Inno Setup. Se qualquer comando falhar, parar com código diferente de zero.

- [ ] **Step 5: Executar teste manual Windows**

`docs/windows-smoke-test.md` deve exigir marcação de:
1. instalar em máquina limpa;
2. criar senha;
3. cadastrar conta, pessoa, categoria e lançamento;
4. criar parcela e recorrência;
5. importar extrato e conciliar;
6. cadastrar cartão e verificar fatura;
7. anexar comprovante;
8. gerar PDF/XLSX;
9. fazer backup;
10. fechar aplicativo;
11. restaurar backup;
12. confirmar dados após reinício;
13. testar uso sem internet.

- [ ] **Step 6: Verificação final automatizada**

Run: `pytest -q`  
Expected: PASS.

- [ ] **Step 7: Build final**

Run: `powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1`  
Expected: `FinanceiroPessoalDr-Setup.exe` criado.

- [ ] **Step 8: Commit**

```bash
git add packaging scripts docs pyproject.toml tests
 git commit -m "build: package finance app for windows"
```

## Definition of Done

- Todos os relatórios definidos na especificação existem e filtram corretamente.
- PDF e Excel refletem os mesmos números da tela.
- Drill-down mostra os lançamentos que compõem cada total.
- Backup manual e automático funcionam para pasta local sincronizada pelo Google Drive.
- Restauração rejeita pacote inválido sem danificar a base atual.
- Configurações e troca de senha funcionam.
- Suíte automatizada passa.
- Smoke test no Windows passa integralmente.
- Instalador final cria atalho e mantém dados fora da pasta de instalação.
