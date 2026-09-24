# Design — carga inicial privada no Financeiro Pessoal do Dr.

Data: 2026-09-24

## 1. Objetivo

A instalação/atualização do Financeiro Pessoal do Dr. deve conseguir abrir já com o histórico financeiro fornecido em uma planilha privada, sem exigir importação manual no uso diário. Depois da carga, o SQLite local continua sendo a fonte oficial do aplicativo.

O repositório deste projeto é público. Portanto, **nenhum dado pessoal, descrição financeira, nome, valor, total, hash do arquivo privado ou payload de carga pode ser commitado no GitHub**.

## 2. Fonte privada

A fonte é uma planilha Excel fornecida diretamente pelo usuário. A aba de entrada contém os campos necessários para criar lançamentos históricos: titular, data, descrição, forma de pagamento, valor, categoria, tipo e classificação.

A análise detalhada da fonte e seus invariantes reais permanecem fora do repositório público. Eles serão carregados no manifesto privado gerado localmente.

## 3. Abordagem aprovada

Será usado um **seed privado externo ao repositório**.

O código público terá apenas:

- schema e validação do formato do seed;
- serviço transacional de aplicação;
- migration de proveniência/idempotência;
- gerador local que transforma um Excel em seed;
- suporte do instalador para copiar, se presente, um seed privado colocado ao lado do `Setup.exe`;
- testes com dados sintéticos.

O arquivo real de seed será gerado fora do GitHub e entregue ao usuário junto do instalador em um pacote privado.

## 4. Fluxo do instalador

O pacote privado entregue ao usuário conterá:

- `FinanceiroPessoalDr-Setup.exe`
- `FinanceiroPessoalDr.initial-seed.json`

O instalador público permanece genérico. Se encontrar `FinanceiroPessoalDr.initial-seed.json` na mesma pasta do `Setup.exe`, ele o copia para `%LOCALAPPDATA%/FinanceiroPessoalDr/initial-seed.json`.

Se o seed não estiver presente, a instalação continua normalmente e o aplicativo abre sem tentar importar dados privados.

## 5. Fluxo de inicialização do aplicativo

1. abrir o SQLite local;
2. aplicar migrations;
3. validar saúde básica do banco;
4. procurar `%LOCALAPPDATA%/FinanceiroPessoalDr/initial-seed.json`;
5. se não existir, continuar normalmente;
6. se existir, validar schema, versão, seed id e invariantes do manifesto;
7. aplicar o seed em uma única transação SQLite;
8. registrar batch e proveniência por linha;
9. commit da transação somente se tudo for consistente;
10. tentar remover o arquivo de seed após sucesso; falha ao remover não é fatal porque a idempotência impede reaplicação;
11. continuar para criação/login da senha;
12. backup automático continua depois do login.

Se a aplicação do seed falhar, ocorre rollback integral e o app informa que a base inicial não foi aplicada. Nenhuma carga parcial pode ser mantida.

## 6. Formato privado do seed

JSON UTF-8 com envelope versionado:

```json
{
  "schema_version": 1,
  "seed_id": "identificador-unico-da-carga",
  "source_label": "fonte privada",
  "source_sha256": "hash-da-fonte",
  "expected": {
    "record_count": 3,
    "income_count": 1,
    "expense_count": 2,
    "income_cents": 10000,
    "expense_cents": 7500
  },
  "records": [
    {
      "source_row": 2,
      "holder": "PESSOA EXEMPLO",
      "date": "2026-01-02",
      "description": "Lançamento sintético",
      "payment_method": "TRANSFERÊNCIA",
      "amount_cents": 5000,
      "category": "MORADIA",
      "raw_type": "MENSAL RECORRENTE",
      "classification": "DESPESA",
      "warning": null
    }
  ]
}
```

Os valores acima são apenas fixture sintética de documentação e não representam a fonte privada.

## 7. Mapeamento para o SQLite

- titular → cria/reutiliza `person` e alimenta `beneficiary_id`;
- data → `competence_date` e `settled_date`;
- `due_date` fica nulo quando não existir na origem;
- descrição → `description` com trim externo;
- forma de pagamento → `payment_method`;
- valor → `amount_cents` inteiro;
- categoria → cria/reutiliza `category`, com normalização somente de variantes explicitamente suportadas;
- classificação `DESPESA` → `entry_type=DESPESA`, `status=PAGO`;
- classificação `RECEITA` → `entry_type=RECEITA`, `status=RECEBIDO`;
- tipo mensal/anual → `expense_nature=FIXA`, `is_recurring=1`, sem criar `recurrence_rule_id`;
- demais despesas → `expense_nature=VARIAVEL`, `is_recurring=0`;
- receitas → `expense_nature=NULL`, `is_recurring=0`.

Não serão inferidos banco específico, cartão, centro de custo, subcategoria, patrimônio ou origem da receita quando a fonte não os fornecer.

## 8. Proveniência e idempotência

Nova migration cria:

### `initial_seed_batch`

- `seed_id` TEXT PRIMARY KEY;
- `source_label` TEXT;
- `source_sha256` TEXT;
- `expected_count` INTEGER;
- `applied_count` INTEGER;
- `warning_count` INTEGER;
- `applied_at` TEXT.

### `initial_seed_record`

- `seed_id` TEXT;
- `source_row` INTEGER;
- `record_hash` TEXT;
- `financial_entry_id` INTEGER;
- `action` TEXT (`INSERTED` ou `REUSED_EXISTING`);
- `warning_code` TEXT NULL;
- PK composta `(seed_id, source_row)`.

Se `initial_seed_batch.seed_id` já existir, a carga é um no-op.

Em banco existente, o serviço nunca apaga nem sobrescreve lançamento do usuário. Uma linha privada só pode reutilizar um lançamento existente quando houver exatamente uma correspondência inequívoca por data, descrição normalizada, valor, tipo, beneficiário e forma de pagamento. Caso contrário, insere nova linha e preserva multiplicidade legítima.

A carga histórica não cria milhares de eventos `CREATE` no `audit_log`; sua proveniência fica em `initial_seed_record`. Edições futuras feitas pelo operador continuam sendo auditadas normalmente.

## 9. Geração local do seed

Um script público `tools/build_private_seed.py` recebe:

```text
python tools/build_private_seed.py <entrada.xlsm> <saida.json> --seed-id <id>
```

Ele:

- lê somente a aba de entrada configurada;
- valida cabeçalhos obrigatórios;
- converte valores com `Decimal`;
- normaliza somente aliases definidos no código;
- preserva linhas com valor ausente como zero e aviso quando essa regra estiver habilitada para a fonte;
- calcula os invariantes e o hash da fonte;
- grava o JSON privado fora do repositório.

O `.gitignore` deve bloquear `*.initial-seed.json`, `private-seed/` e nomes equivalentes usados para payload privado.

## 10. Segurança

- dados reais nunca entram no repositório;
- CI usa somente fixtures sintéticas;
- workflow público nunca recebe o seed real;
- artefato público do GitHub Actions contém somente instalador genérico/portátil;
- pacote privado final é montado fora do GitHub, juntando instalador validado + seed real;
- o seed é copiado apenas para o computador local durante a instalação;
- o SQLite local continua offline e oficial após a carga.

## 11. Testes obrigatórios

### Unidade

- validação do envelope JSON;
- rejeição de schema version desconhecida;
- normalização de classificação/tipo/categoria;
- conversão Decimal → centavos no gerador;
- classificação vence tipo bruto incoerente;
- valor ausente permitido gera zero + warning;
- arquivo privado nunca faz parte dos package data públicos.

### Integração com fixture sintética

- seed novo cria pessoas, categorias e lançamentos esperados;
- status de despesas/receitas já quitadas é correto;
- totais do banco batem com o bloco `expected` do manifesto;
- rodar duas vezes não duplica;
- banco com lançamento manual não relacionado permanece intacto;
- correspondência única pode ser `REUSED_EXISTING`;
- múltiplas correspondências não são colapsadas;
- erro no meio da aplicação faz rollback integral.

### Bootstrap

- sem arquivo de seed: app continua normalmente;
- com seed válido: seed é aplicado antes do login;
- com seed inválido: app não continua com base parcialmente alterada;
- após seed aplicado, reapresentar o mesmo arquivo não duplica.

### Windows/instalador

- suíte completa no Windows;
- build PyInstaller;
- smoke test do executável sem seed;
- teste do comportamento de instalação/cópia com fixture sintética externa;
- instalador público continua funcionando mesmo sem arquivo externo.

## 12. Fora de escopo

- publicar o seed real no GitHub;
- embutir dados pessoais no executável público;
- importar dashboards, macros ou fórmulas do Excel;
- criar recorrências futuras a partir do histórico;
- inferir campos que não existam na fonte;
- manter dependência do Excel após a carga.

## 13. Resultado esperado

O usuário recebe um pacote privado com o instalador e o arquivo de seed. Ao instalar e abrir o Financeiro Pessoal do Dr., os dados históricos entram automaticamente no SQLite antes do primeiro uso. O mesmo instalador público continua reutilizável para outras máquinas sem expor qualquer dado privado.