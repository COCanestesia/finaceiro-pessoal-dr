"""Interactive local administration for central-server accounts.

Run on the finance host only. Credentials are never placed in source code.
"""
from __future__ import annotations

import argparse
import getpass
import sqlite3

from financeiro_dr.app_paths import AppPaths
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.security.access_service import AccessService


def add_account(connection, username: str, display_name: str, role: str, password: str) -> int:
    if len(password) < 12:
        raise ValueError("A senha precisa ter pelo menos 12 caracteres.")
    if role not in ("admin", "financeiro", "consulta"):
        raise ValueError("Perfil inválido.")
    user_id = AccessService(connection).create_user(username, display_name, password, role)
    connection.commit()
    return user_id


def list_accounts(connection):
    return [dict(row) for row in connection.execute(
        "SELECT id, username, display_name, role, active FROM access_user ORDER BY username"
    ).fetchall()]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Gestão local dos usuários remotos")
    parser.add_argument("operation", choices=("list", "add"))
    args = parser.parse_args(argv)
    con = Database(AppPaths.from_environment().database_file).connect()
    try:
        MigrationRunner().apply_all(con)
        if args.operation == "list":
            for user in list_accounts(con):
                print(f'{user["id"]}: {user["username"]} ({user["role"]}) - ' +
                      ("ativo" if user["active"] else "inativo"))
            return 0
        username = input("Usuário: ").strip()
        display_name = input("Nome de exibição: ").strip()
        role = input("Perfil (admin/financeiro/consulta): ").strip()
        password = getpass.getpass("Senha: ")
        confirmation = getpass.getpass("Confirme a senha: ")
        if password != confirmation:
            raise ValueError("Senhas diferentes.")
        if con.execute("SELECT 1 FROM access_user").fetchone():
            raise PermissionError(
                "Novos usuários devem ser autorizados pela conta administrativa; "
                "a interface de autorização ainda está em desenvolvimento."
            )
        if role != "admin":
            raise PermissionError("A primeira conta deve ser administradora.")
        add_account(con, username, display_name, role, password)
        print("Administrador inicial cadastrado.")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
