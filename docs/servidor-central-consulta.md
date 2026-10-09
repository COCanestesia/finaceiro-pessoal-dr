# Implantação inicial do servidor de consulta

**Estado:** protótipo de consulta somente; não é um sistema multiusuário completo.

## No computador principal

1. Instale Python 3.12 e o projeto com `python -m pip install -e .`.
2. Faça backup do banco local antes de qualquer alteração.
3. Execute `financeiro-dr-criar-admin` em um terminal privado e crie a primeira conta com senha forte. Execute apenas uma vez.
4. Execute `financeiro-dr-servidor --port 8765`. O serviço escuta **somente 127.0.0.1**.
5. Um proxy HTTPS autenticado por rede VPN privada pode encaminhar ao serviço local. Não libere a porta 8765 no roteador, não compartilhe o banco SQLite por pasta de rede e não publique HTTP sem TLS.

## Em outro computador

Abra **Consulta Remota** e informe a URL HTTPS do proxy privado e as credenciais da conta. Por enquanto são listados até 100 lançamentos recentes em modo somente leitura.

## Limitações e segurança

- O login remoto usa a tabela `access_user`, separada da senha local.
- Não há interface de cadastro ou gestão de outros usuários; isso ainda será implementado.
- A API não permite inclusão, edição ou exclusão remotas.
- O aplicativo continua usando banco SQLite local para suas demais telas; portanto, **não deve ser tratado como multiusuário**.
- Testes com dois computadores, proxy TLS/VPN, revogação de sessões, backups do servidor e indisponibilidade de rede ainda são necessários.
- O computador principal precisa ficar ligado para atender consultas.
