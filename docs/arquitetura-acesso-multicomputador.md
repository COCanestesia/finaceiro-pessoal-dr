# Acesso em vários computadores

O banco SQLite deve ficar exclusivamente no computador servidor. Outros computadores devem acessar uma API autenticada, nunca uma pasta compartilhada com o arquivo do banco.

Acesso remoto exclusivamente por rede privada VPN (por exemplo, Tailscale/WireGuard), não abrir a porta do banco na internet.

Identidades individuais: administrador, financeiro e consulta. Permissões validadas no servidor em toda operação, com logs de auditoria.

Antes de migrar: backup íntegro, testes de concorrência, recuperação do servidor, restauração, desconexão e conflitos. Não disponibilizar a versão local como multiusuário antes de integrar e testar a API.

Custos: hospedagem no computador existente pode evitar mensalidade de servidor, mas exige máquina ligada, energia, manutenção e backup fora dela. O acesso externo depende de internet funcionando.
