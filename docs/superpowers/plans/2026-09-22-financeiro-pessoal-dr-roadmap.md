# Financeiro Pessoal do Dr. — Roadmap de Implementação

> Este roadmap divide a especificação aprovada em seis planos independentes e testáveis. Cada plano entrega software executável e preserva as interfaces necessárias para o plano seguinte.

**Spec:** `docs/superpowers/specs/2026-09-22-financeiro-pessoal-dr-design.md`

## Ordem de execução

1. `2026-09-22-01-fundacao-financeiro-diario.md`
   - Estrutura do projeto, SQLite, migrações, login local, auditoria, lançamentos, recorrências, parcelas, contas a pagar/receber, agenda financeira e painel inicial mínimo.
   - Entrega: aplicativo Windows executável em modo de desenvolvimento, com fluxo financeiro diário funcionando offline.

2. `2026-09-22-02-pessoas-classificacao-orcamentos.md`
   - Pessoas/beneficiários, categorias, subcategorias, centros de custo, orçamentos e alertas.
   - Entrega: despesas classificadas por pessoa e estrutura financeira, com previsto x realizado.

3. `2026-09-22-03-bancos-cartoes-conciliacao.md`
   - Contas bancárias, transferências, cartões, faturas, compras parceladas, importação OFX/CSV/XLSX e conciliação automática/manual.
   - Entrega: saldos, cartões e conciliação operacional.

4. `2026-09-22-04-patrimonio-investimentos-documentos.md`
   - Patrimônio, investimentos, documentos/comprovantes, busca e vínculos com lançamentos.
   - Entrega: visão patrimonial e arquivos financeiros organizados localmente.

5. `2026-09-22-04b-integridade-auditoria-indicadores.md`
   - Origem de receitas, despesas fixas x variáveis, auditoria completa, histórico de alterações, integridade do banco e gráficos com drill-down.
   - Entrega: requisitos transversais fechados antes da geração dos relatórios finais e do instalador.

6. `2026-09-22-05-relatorios-backup-instalador.md`
   - Relatórios PDF/Excel, detalhamento, backup automático/manual, restauração, configurações e empacotamento para Windows.
   - Entrega: versão 1 instalável e pronta para uso diário no computador do financeiro pessoal.

## Interfaces estáveis entre planos

- Banco: SQLite com migrações numeradas em `src/financeiro_dr/database/migrations/`.
- Dinheiro: sempre `INTEGER` em centavos no banco; nunca `REAL` para valores monetários.
- Datas: ISO `YYYY-MM-DD`; data/hora de auditoria em UTC ISO 8601.
- IDs: inteiros autoincrementais internos; UUID não é necessário na versão local.
- Exclusão: registros financeiros usam exclusão lógica quando houver impacto histórico; auditoria nunca é apagada pela interface.
- Serviços: regras de negócio ficam fora das telas PySide6.
- UI: telas chamam serviços e repositórios; não executam SQL direto.
- Configuração local: JSON em `%APPDATA%/FinanceiroPessoalDr/config.json`; banco e anexos em `%LOCALAPPDATA%/FinanceiroPessoalDr/`.
- Testes: `pytest`; regras críticas precisam de testes unitários e integração com SQLite temporário.

## Critério de conclusão da versão 1

A versão 1 termina somente quando os seis planos estiverem implementados e verificados, incluindo teste manual no Windows, backup/restauração e geração do instalador.
