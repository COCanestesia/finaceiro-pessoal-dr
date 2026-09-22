# Financeiro Pessoal do Dr. — Teste de aceitação Windows

Marcar todos os itens antes de considerar uma versão pronta para uso diário.

- [ ] Instalar o aplicativo em uma máquina Windows limpa.
- [ ] Abrir pelo atalho e criar a senha local do primeiro acesso.
- [ ] Cadastrar pessoa/beneficiário, categoria, subcategoria e centro de custo.
- [ ] Cadastrar conta bancária e conferir saldo inicial.
- [ ] Criar receita e despesa, incluindo despesa fixa/variável e origem da receita.
- [ ] Criar lançamento parcelado e despesa recorrente.
- [ ] Conferir Contas a Pagar, Contas a Receber e Agenda Financeira.
- [ ] Cadastrar cartão, lançar compra parcelada e conferir fatura/limite.
- [ ] Importar OFX, CSV e XLSX e confirmar que uma segunda importação não duplica movimentos.
- [ ] Conciliar um movimento e marcar outro como divergente.
- [ ] Cadastrar patrimônio e vincular despesa a um bem.
- [ ] Cadastrar investimento, aporte, rendimento e resgate.
- [ ] Anexar comprovante e abrir a Central de Documentos.
- [ ] Criar orçamento e conferir alertas de 80%, 100% e acima de 100%.
- [ ] Conferir Histórico de Alterações.
- [ ] Gerar relatório e exportar PDF e Excel.
- [ ] Configurar uma pasta local sincronizada pelo Google Drive.
- [ ] Fazer backup manual e confirmar criação do ZIP.
- [ ] Fechar e abrir novamente; confirmar funcionamento sem internet.
- [ ] Validar um backup e restaurá-lo em ambiente de teste.
- [ ] Reiniciar e confirmar os dados restaurados.

## Observação

O banco de dados ativo permanece em `%LOCALAPPDATA%\\FinanceiroPessoalDr`. A pasta do Google Drive recebe somente pacotes de backup consistentes; o SQLite ativo nunca deve ficar dentro da pasta sincronizada.
