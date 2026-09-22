# Financeiro Pessoal do Dr. — Design do Sistema

Data: 2026-09-22  
Status: aprovado pelo usuário em 2026-09-22.

## 1. Objetivo

Criar um aplicativo desktop completo para o financeiro pessoal do Dr., utilizado exclusivamente no computador do responsável financeiro pessoal. O sistema deve funcionar localmente, sem Supabase e sem depender de internet para o uso diário.

O aplicativo será a fonte oficial dos dados financeiros pessoais do Dr. Planilhas, CSV, OFX e outros arquivos servirão como entrada/importação ou saída/exportação, e não como base principal.

## 2. Plataforma e arquitetura

- Aplicativo desktop para Windows.
- Python como linguagem principal.
- PySide6 para interface gráfica.
- SQLite como banco de dados local oficial.
- Funcionamento offline.
- Login local com senha protegida por hash; a senha não será armazenada em texto puro.
- Documentos e comprovantes armazenados localmente e vinculados aos registros financeiros.
- Backup automático para uma pasta do Google Drive sincronizada no computador.
- Botão manual de "Fazer backup agora".
- Função de restauração de backup.
- Instalador para Windows e atalho na área de trabalho.

## 3. Estrutura geral de navegação

Menu lateral principal:

1. Início
2. Lançamentos
3. Contas a Pagar
4. Contas a Receber
5. Agenda Financeira
6. Bancos e Contas
7. Cartões
8. Conciliação Financeira
9. Pessoas / Beneficiários
10. Categorias e Subcategorias
11. Centros de Custo
12. Orçamentos
13. Patrimônio
14. Investimentos
15. Documentos
16. Relatórios
17. Histórico de Alterações
18. Backup
19. Configurações

## 4. Painel inicial

A tela inicial deve apresentar de forma clara:

- Saldo total disponível.
- Receitas do mês.
- Despesas do mês.
- Resultado líquido do mês.
- Patrimônio total.
- Investimentos.
- Dívidas/obrigações.
- Patrimônio líquido.
- Contas atrasadas.
- O que precisa pagar hoje.
- O que vence amanhã.
- Próximos 7 dias.
- Próximos 30 dias.
- Faturas de cartão em aberto.
- Alertas de orçamento.
- Pendências de conciliação financeira.
- Indicadores e gráficos com acesso ao detalhamento dos lançamentos.

## 5. Lançamentos

Cada lançamento financeiro deve suportar:

- Data de competência.
- Data de vencimento.
- Data de pagamento ou recebimento.
- Descrição.
- Valor.
- Tipo: Receita, Despesa, Transferência ou Investimento.
- Categoria.
- Subcategoria.
- Centro de custo.
- Pessoa / Beneficiário.
- Conta bancária ou cartão.
- Forma de pagamento.
- Status: Pendente, Pago, Recebido, Atrasado ou Cancelado.
- Observações.
- Documentos ou comprovantes anexados.
- Indicação de recorrência.
- Indicação de parcelamento.

O sistema deve permitir duplicar um lançamento para agilizar o uso, mantendo verificação contra duplicidade acidental.

## 6. Contas a pagar e a receber

### Contas a pagar

O sistema deve separar automaticamente:

- Atrasadas.
- Vencendo hoje.
- Amanhã.
- Próximos 7 dias.
- Próximos 30 dias.

Quando uma conta for paga, o usuário informa a conta/cartão utilizado e o caixa deve ser atualizado automaticamente.

### Contas a receber

Controlar entradas como:

- Pró-labore / salário.
- Distribuição de lucros.
- Recebimentos de empresas.
- Aluguéis.
- Rendimentos de investimentos.
- Reembolsos.
- Transferências recebidas.
- Outras receitas.

## 7. Agenda financeira

Calendário financeiro diário e mensal mostrando:

- Total a pagar por dia.
- Total previsto para receber por dia.
- Contas vencidas.
- Eventos financeiros recorrentes.
- Faturas de cartão próximas do vencimento.

## 8. Despesas recorrentes e parceladas

Suportar despesas recorrentes contínuas, como:

- Condomínio.
- Escola.
- Funcionários.
- Seguros.
- Assinaturas.
- Pensões.
- Aluguéis.
- Manutenções recorrentes.

Também suportar compras parceladas com criação automática das parcelas futuras.

## 9. Bancos e contas

Cada conta deve ter:

- Instituição financeira.
- Nome da conta.
- Identificação opcional.
- Saldo inicial.
- Saldo atual calculado.
- Histórico de movimentações.
- Situação ativa/inativa.

Transferências entre contas do próprio Dr. não devem ser contabilizadas como receita ou despesa, evitando distorção nos relatórios.

## 10. Cartões de crédito

Cada cartão deve controlar:

- Banco ou emissor.
- Titular.
- Limite total.
- Limite utilizado.
- Limite disponível.
- Dia de fechamento.
- Dia de vencimento.
- Fatura atual.
- Próximas faturas.
- Histórico de faturas.

Compras parceladas devem aparecer automaticamente nas faturas futuras.

Cada compra deve poder ser vinculada a categoria, subcategoria, centro de custo e pessoa/beneficiário.

Alertas:

- Fatura próxima do vencimento.
- Limite comprometido.
- Compra ainda não conciliada.

## 11. Conciliação financeira

A conciliação será um módulo central do sistema.

Formatos de importação:

- OFX.
- CSV.
- Excel.

O motor de conciliação deve tentar associar automaticamente movimentos do extrato a lançamentos existentes, usando principalmente:

- Valor.
- Data.
- Descrição.

Estados de conciliação:

- Conciliado.
- Pendente.
- Divergente.

A tela deve exibir lado a lado:

- Movimento do extrato.
- Lançamento correspondente no sistema.
- Diferença encontrada.
- Conta bancária.
- Data.
- Status.

Filtros devem permitir visualizar pendências, divergências e possíveis duplicidades.

## 12. Pessoas / Beneficiários

O sistema deve permitir cadastrar pessoas cujas despesas são pagas pelo Dr., especialmente familiares.

Dados básicos:

- Nome.
- Parentesco.
- Apelido ou identificação opcional.
- Observação.
- Status ativo/inativo.

Cada despesa pode ser vinculada a uma pessoa.

Não haverá regra de reembolso para familiares por padrão; o vínculo serve para identificar para quem a despesa foi realizada.

## 13. Categorias, subcategorias e centros de custo

Estrutura principal de classificação:

Categoria → Subcategoria → Centro de Custo → Pessoa/Beneficiário.

Exemplos:

- Educação → Mensalidade Escolar → Família → Pessoa X.
- Veículos → Combustível → Carro Y → Dr.
- Saúde → Medicamentos → Família → Pessoa Y.

Centros de custo devem ser personalizáveis, com exemplos iniciais:

- Casa.
- Família.
- Veículos.
- Viagens.
- Imóveis.
- Funcionários.
- Saúde.
- Educação.
- Investimentos.

## 14. Orçamentos

Permitir orçamento mensal por:

- Pessoa.
- Categoria.
- Centro de custo.
- Combinação de pessoa + categoria + centro de custo.

Exibir:

- Previsto.
- Realizado.
- Saldo disponível.
- Percentual consumido.

Alertas configuráveis devem ocorrer ao atingir níveis como:

- 80% do orçamento.
- 100% do orçamento.
- Acima de 100%.

Também deve haver comparativos mensais e históricos.

## 15. Patrimônio

Permitir cadastrar:

- Imóveis.
- Veículos.
- Terrenos.
- Outros bens.

Campos esperados:

- Tipo do bem.
- Descrição.
- Data de aquisição.
- Valor de aquisição.
- Valor atual estimado.
- Observações.
- Documentos vinculados.

Despesas podem ser vinculadas a um patrimônio específico, como manutenção, imposto, seguro ou reforma.

## 16. Investimentos

Controlar:

- Instituição.
- Conta ou aplicação.
- Tipo de investimento.
- Aportes.
- Resgates.
- Rendimentos.
- Saldo atual.
- Histórico de movimentações.

Os investimentos entram no cálculo do patrimônio líquido.

## 17. Documentos e comprovantes

Cada lançamento pode possuir anexos, como:

- Boleto.
- Nota fiscal.
- Recibo.
- Comprovante PIX/TED.
- Contrato.
- Fatura.
- Documento de imóvel ou veículo.

Os arquivos devem ser organizados localmente e incluídos no backup.

O sistema deve permitir localizar documentos por lançamento, pessoa, categoria, período ou tipo.

## 18. Histórico de alterações

Não haverá fechamento mensal bloqueando alterações.

Em vez disso, todas as alterações importantes devem ser auditáveis.

O histórico deve armazenar:

- Data e hora.
- Tipo da ação: inclusão, edição ou exclusão.
- Registro afetado.
- Campo alterado.
- Valor anterior.
- Valor novo.

Exclusões não devem apagar o rastro de auditoria.

## 19. Relatórios

Relatórios principais:

- Despesas por pessoa.
- Despesas por categoria.
- Despesas por subcategoria.
- Despesas por centro de custo.
- Despesas por conta bancária.
- Despesas por cartão.
- Despesas por período.
- Fixas x variáveis.
- Pagas x pendentes.
- Receitas por origem.
- Contas a pagar.
- Contas a receber.
- Orçamento previsto x realizado.
- Conciliação financeira.
- Faturas de cartão.
- Fluxo de caixa.
- Evolução mensal.
- Patrimônio.
- Investimentos.
- Patrimônio líquido.

Todos os relatórios devem permitir filtro por período e, quando aplicável, pessoa, categoria, conta, cartão, centro de custo e status.

Deve haver exportação para:

- PDF.
- Excel.

Os relatórios devem permitir ir do resumo para o detalhamento dos lançamentos que formam o número exibido.

## 20. Backup e recuperação

O sistema continuará funcionando offline mesmo sem internet.

O backup deve copiar:

- Banco SQLite.
- Documentos e comprovantes.
- Configurações essenciais.

Destino principal: pasta local sincronizada pelo Google Drive.

Funções:

- Backup automático diário.
- Botão "Fazer backup agora".
- Registro da data/hora do último backup.
- Restauração de backup selecionado.
- Verificação de integridade antes da restauração.

## 21. Segurança local

- Login com senha local.
- Senha armazenada apenas como hash seguro.
- Opção de troca de senha nas configurações.
- O aplicativo não depende de conta online para autenticação.
- Dados financeiros permanecem locais no computador, além das cópias de backup sincronizadas pelo Google Drive.

## 22. Organização do código

Separar o projeto em módulos claros:

- ui: telas, componentes, menus e formulários.
- core/financeiro: regras de lançamentos, recorrências, parcelas, contas a pagar/receber e transferências.
- conciliacao: importação e associação de extratos.
- cartoes: cartões, compras, parcelas e faturas.
- orcamentos: limites, consumo e alertas.
- patrimonio: bens e despesas relacionadas.
- investimentos: aportes, resgates e rendimentos.
- documentos: anexos e organização de arquivos.
- relatorios: PDF, Excel, gráficos e detalhamento.
- auditoria: histórico de alterações.
- backup: cópia, validação e restauração.
- database: acesso ao SQLite, migrações e integridade dos dados.

## 23. Fluxo de dados

1. O usuário registra ou importa uma movimentação.
2. O sistema valida os campos.
3. O dado é salvo no SQLite.
4. Regras relacionadas são atualizadas, como conta, cartão, orçamento e agenda.
5. A alteração é registrada no histórico de auditoria.
6. Relatórios e painel passam a refletir o novo estado.
7. O backup periódico copia banco e documentos para a pasta sincronizada pelo Google Drive.

## 24. Tratamento de erros

O sistema deve tratar explicitamente:

- Arquivos OFX/CSV/Excel inválidos.
- Duplicidades de importação.
- Falha de escrita em disco.
- Banco bloqueado ou corrompido.
- Pasta de backup indisponível.
- Documento anexado removido externamente.
- Restauração de backup inválido.

Mensagens de erro devem ser claras para o usuário e não expor detalhes técnicos desnecessários.

## 25. Testes

Testes mínimos previstos:

- Regras de lançamentos.
- Cálculo de saldos.
- Transferências sem impacto em receita/despesa.
- Geração de parcelas.
- Geração de recorrências.
- Fechamento e vencimento de cartão.
- Conciliação por valor/data/descrição.
- Orçamentos e alertas.
- Auditoria de edição e exclusão.
- Backup e restauração.
- Importação OFX/CSV/Excel.
- Relatórios com filtros.

Também deverão existir testes manuais de fluxo completo no Windows antes da criação do instalador final.

## 26. Critérios de sucesso

O projeto será considerado funcional quando:

- O financeiro conseguir realizar o controle diário sem internet.
- Todos os dados ficarem salvos localmente com segurança.
- O painel mostrar corretamente o que deve ser pago hoje e nos próximos períodos.
- A conciliação identificar automaticamente boa parte dos lançamentos compatíveis.
- Despesas puderem ser analisadas por pessoa, categoria, subcategoria e centro de custo.
- Cartões e parcelas refletirem corretamente nas faturas.
- Orçamentos gerarem alertas configurados.
- Relatórios puderem ser exportados para PDF e Excel.
- O histórico de alterações preservar rastreabilidade.
- O backup automático e a restauração forem testados com sucesso.

## 27. Fora do escopo inicial

- Supabase.
- Servidor web obrigatório.
- Acesso multiusuário em rede.
- Aplicativo móvel.
- Integração bancária direta por API.
- Fechamento mensal com bloqueio de período.
- Sistema de reembolso familiar automático.

Esses itens podem ser considerados futuramente, mas não fazem parte da primeira versão.
