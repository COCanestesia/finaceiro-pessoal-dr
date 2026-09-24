# Design — carga inicial do Dashboard Excel no Financeiro Pessoal do Dr.

Data: 2026-09-24

## 1. Objetivo

A nova instalação/atualização do Financeiro Pessoal do Dr. deve abrir já com o histórico financeiro fornecido em `Dashboard (ATUALIZADO).xlsm`, sem exigir que o usuário importe a planilha manualmente. Depois da carga, o SQLite local continua sendo a fonte oficial do aplicativo; o Excel não é necessário para o uso diário.

A carga deve funcionar também em uma instalação existente: se a base inicial ainda não foi aplicada, ela é carregada uma única vez; se já foi aplicada, a inicialização é um no-op e não duplica dados.

## 2. Fonte analisada

Arquivo: `Dashboard (ATUALIZADO).xlsm`
SHA-256: `91725c31149d747a910a87c8a4d9c326fb850a5c478329bfac7289ffa6b815c5`

A aba fonte é `Entrada_dados`, intervalo `A1:I2115`, com 2.114 registros de dados e as colunas:

- TITULAR
- DATA
- MÊS
- DESCRIÇÃO
- CONTA
- VALOR
- CATEGORIA
- TIPO DE DESPESA
- CLASSIFICAÇÃO

Faixa de datas: 2026-01-02 a 2026-09-22.

Distribuição por titular:

- DR. UBIRAJARA: 1.769
- DONA IARA: 271
- LEONARDO: 74

Classificação financeira normalizada:

- DESPESA: 1.917 registros, total R$ 2.869.732,82
- RECEITA: 197 registros, total R$ 755.855,27

Formas de pagamento presentes:

- TRANSFERÊNCIA BANCÁRIA: 2.009
- ESPÉCIE: 105

Foram detectadas pequenas inconsistências de origem que a migração deve tratar sem apagar informação: espaços finais em categoria/classificação/tipo; variantes como `CARTAO DE CREDITO` x `CARTÃO DE CRÉDITO`, `MORADIA ` x `MORADIA`, `DESPESA DIARIA ` x `DESPESA DIÁRIA`; 196 registros sem categoria; e um registro (`EMPRESTIMO MUTUO COC`) sem valor preenchido.

## 3. Abordagem aprovada

Será usada uma **carga inicial embutida no aplicativo**, e não um SQLite pré-preenchido nem o Excel bruto dentro da pasta de trabalho do usuário.

Durante o desenvolvimento/build, a aba `Entrada_dados` é transformada em um recurso de seed versionado e mínimo, contendo apenas os campos necessários para o aplicativo e a proveniência da linha de origem. Dashboard, fórmulas, macros, tabelas dinâmicas e demais abas não entram no banco nem são necessárias em produção.

Na inicialização do aplicativo, depois das migrations do SQLite, um `InitialDataSeedService` verifica se esse seed já foi aplicado. Se não foi, aplica toda a carga dentro de uma única transação. Se qualquer registro falhar, ocorre rollback integral: o usuário nunca fica com uma carga parcial.

## 4. Mapeamento Excel → aplicativo

### TITULAR

Cria/reutiliza `person` como Pessoa/Beneficiário, mantendo os nomes da origem:

- DR. UBIRAJARA
- DONA IARA
- LEONARDO

Parentesco e apelido ficam vazios porque a planilha não informa esses dados.

### DATA

- `financial_entry.competence_date` = DATA
- `financial_entry.settled_date` = DATA
- `financial_entry.due_date` = NULL

Não será inventado vencimento que não existe na fonte.

### DESCRIÇÃO

Vai integralmente para `financial_entry.description`, após remoção apenas de espaços externos desnecessários.

### CONTA

Vai para `financial_entry.payment_method`.

`ESPÉCIE` e `TRANSFERÊNCIA BANCÁRIA` não serão cadastradas como contas bancárias, porque a coluna representa forma de pagamento, não uma instituição/conta identificável.

### VALOR

Convertido para centavos inteiros usando arredondamento decimal de duas casas; não usar float binário para persistência.

O único registro sem VALOR será preservado com `amount_cents = 0` e um aviso de proveniência (`MISSING_AMOUNT`) para que o histórico não perca a linha existente no Excel.

### CATEGORIA

Categorias não vazias são criadas/reutilizadas em `category`.

Normalização para chave de comparação:

- trim de espaços
- compactação de espaços repetidos
- comparação sem diferença de caixa
- comparação tolerante a acentos para identificar somente variantes evidentes

A etiqueta canônica preserva acentuação correta já existente. Assim, `MORADIA ` é reunida com `MORADIA`, e `CARTAO DE CREDITO` com `CARTÃO DE CRÉDITO`.

Registros sem categoria continuam com `category_id = NULL`; não será inventada uma categoria financeira nova.

### TIPO DE DESPESA

O tipo original é preservado na proveniência e usado para classificar natureza da despesa:

- `MENSAL RECORRENTE` e `ANUAL` → `expense_nature = FIXA`
- variantes de `DESPESA DIÁRIA`, `INVESTIMENTO`, `APORTE HCT` e vazio → `expense_nature = VARIAVEL`
- receitas → `expense_nature = NULL`

`MENSAL RECORRENTE`/`ANUAL` podem ser marcadas como recorrentes para identificação visual, mas **nenhuma regra automática de recorrência futura será criada a partir do histórico**. Isso evita gerar novas cobranças com base em meses passados e criar duplicidades.

Os 50 registros cujo tipo bruto é `INVESTIMENTO` continuam respeitando `CLASSIFICAÇÃO = DESPESA` na carga inicial, para que os totais históricos do aplicativo conciliem com o Excel. A migração não reinterpreta contabilmente a fonte.

### CLASSIFICAÇÃO

É a regra principal para `entry_type`:

- `DESPESA` (após trim/normalização) → `DESPESA`
- `RECEITA` → `RECEITA`

Todos os registros foram confirmados pelo usuário como já liquidados:

- DESPESA → `status = PAGO`
- RECEITA → `status = RECEBIDO`

Mesmo quando `TIPO DE DESPESA` contiver texto incoerente com a classificação, `CLASSIFICAÇÃO` vence. Existem dois registros classificados como RECEITA cujo tipo bruto contém `DESPESA DIÁRIA`; eles permanecem RECEITA.

### MÊS

Não é importado como campo separado. O mês é derivado de DATA nos relatórios do aplicativo.

### Campos sem origem suficiente

Ficam nulos/sem vínculo na carga inicial:

- subcategoria
- centro de custo
- conta bancária específica
- cartão específico
- patrimônio
- origem da receita

Isso evita inventar dados que o Excel não fornece.

## 5. Proveniência, idempotência e segurança contra duplicidade

Adicionar uma migration com duas tabelas isoladas do domínio financeiro:

### `initial_seed_batch`

Registra:

- `seed_id` (PK)
- nome lógico da fonte
- SHA-256 da fonte
- quantidade esperada
- quantidade inserida/reutilizada
- quantidade de avisos
- data/hora da aplicação

Seed inicial: `dashboard-atualizado-2026-09-22-v1`.

### `initial_seed_record`

Registra por linha:

- `seed_id`
- linha da aba fonte
- hash determinístico dos campos relevantes
- `financial_entry_id`
- ação (`INSERTED` ou `REUSED_EXISTING`)
- código de aviso opcional

A existência de `initial_seed_batch.seed_id` torna a operação idempotente: abrir o sistema novamente ou instalar uma atualização não reaplica os 2.114 registros.

Para uma instalação já existente sem o marcador de seed, o serviço preserva lançamentos já cadastrados. Antes de inserir uma linha, procura uma correspondência **exata** por data, descrição normalizada, valor, tipo, beneficiário e forma de pagamento. Somente quando houver exatamente uma correspondência inequívoca ela pode ser reutilizada; zero ou múltiplas correspondências levam à inserção do registro do seed, preservando multiplicidade legítima.

Nenhum lançamento do usuário é apagado ou sobrescrito pela carga inicial.

## 6. Fluxo de inicialização

1. abrir SQLite local
2. aplicar migrations
3. validar saúde básica do banco
4. aplicar `InitialDataSeedService.apply_if_needed()`
5. se a carga falhar: rollback integral + mensagem crítica; não continuar com base parcialmente migrada
6. continuar para criação/login da senha
7. backup automático continua depois do login como já ocorre hoje

Uma instalação nova recebe a base histórica antes mesmo do primeiro uso. Uma instalação antiga recebe a base ao atualizar para a versão que contém o seed, desde que o seed ainda não tenha sido registrado.

## 7. Recurso embutido

O `.xlsm` não será necessário no computador do financeiro. O build contém um payload de seed mínimo e versionado, gerado a partir da aba `Entrada_dados`.

O payload guarda somente:

- source_row
- titular
- data
- descrição
- forma de pagamento
- valor em centavos
- categoria normalizada
- tipo bruto
- classificação
- aviso de origem, quando existir

O instalador não depende de Excel, Power BI, internet, Supabase ou macros para fazer a carga.

## 8. Relatórios e conciliação após a carga

Como os registros entram em `financial_entry`, eles passam a alimentar automaticamente as telas e relatórios existentes por período, pessoa, categoria, natureza e classificação.

Critérios de conciliação da migração:

- total de linhas após seed: 2.114 registros de origem contabilizados (inseridos ou reutilizados)
- receitas históricas: 197 / R$ 755.855,27
- despesas históricas: 1.917 / R$ 2.869.732,82
- data mínima: 2026-01-02
- data máxima: 2026-09-22
- beneficiários da origem: 3

Os valores acima serão usados como invariantes de teste da carga.

## 9. Tratamento de erros

A carga inteira roda sob uma transação SQLite única.

Erros de estrutura do payload, classificação desconhecida, data inválida ou falha de banco cancelam a transação inteira. O erro deve informar que a base inicial não foi carregada e que nenhuma alteração parcial foi mantida.

Inconsistências conhecidas e toleráveis da planilha (espaços, variantes de acento e valor ausente) são normalizadas/registradas como avisos e não interrompem a carga.

## 10. Testes obrigatórios

### Unidade

- normalização de categorias e tipos
- conversão decimal → centavos
- trim de `DESPESA ` → `DESPESA`
- `DESPESA DIARIA ` → natureza VARIAVEL
- `MENSAL RECORRENTE`/`ANUAL` → natureza FIXA
- classificação vence tipo bruto incoerente
- linha sem valor → R$ 0,00 + aviso

### Integração — SQLite vazio

Após aplicar o seed:

- 2.114 registros contabilizados
- 1.917 DESPESAS PAGO
- 197 RECEITAS RECEBIDO
- receitas somam 75.585.527 centavos
- despesas somam 286.973.282 centavos
- 3 pessoas da origem presentes
- datas mínima/máxima corretas
- nenhum registro parcialmente aplicado

### Idempotência

Executar o seed duas vezes mantém os mesmos totais e a mesma quantidade de registros.

### Banco existente

Um lançamento manual não relacionado permanece intacto após a carga. Correspondência exata inequívoca pode ser vinculada como `REUSED_EXISTING`; múltiplas correspondências não são colapsadas.

### Falha transacional

Forçar erro durante a carga deve deixar zero registros do seed e nenhum `initial_seed_batch` aplicado.

### Build Windows

O CI deve executar a suíte completa no Windows, criar o executável/instalador, executar o smoke test empacotado e validar também a presença/leitura do payload de seed no pacote final.

## 11. Fora de escopo desta mudança

- importar fórmulas, dashboard ou macros do Excel
- substituir o Excel usado pelo Power BI
- inventar bancos/cartões específicos a partir de `CONTA`
- criar recorrências futuras automaticamente a partir do histórico
- reclassificar os 50 registros históricos de INVESTIMENTO para o módulo de investimentos
- inferir centro de custo, subcategoria ou origem de receita não informados na fonte

## 12. Resultado esperado

Ao instalar/atualizar a versão com esta mudança, o usuário abre o Financeiro Pessoal do Dr. e já encontra o histórico do Excel nas telas e relatórios. A planilha deixa de ser necessária para o aplicativo, o banco continua local/offline e o seed nunca é aplicado duas vezes na mesma base.