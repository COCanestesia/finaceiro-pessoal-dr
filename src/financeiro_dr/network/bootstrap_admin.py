"""Create the first central administrator interactively on the main computer."""
from __future__ import annotations
import getpass
from financeiro_dr.app_paths import AppPaths
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.security.access_service import AccessService


def main() -> int:
    db = Database(AppPaths.from_environment().database_file).connect()
    try:
        MigrationRunner().apply_all(db)
        if db.execute("SELECT 1 FROM access_user WHERE role='admin' AND active=1").fetchone():
            print("Administrador ativo já cadastrado.")
            return 1
        username = input("Usuário administrador: ").strip()
        name = input("Nome de exibição: ").strip()
        password = getpass.getpass("Senha (mínimo 12 caracteres): ")
        if len(password) < 12:
            print("Senha muito curta.")
            return 1
        AccessService(db).create_user(username, name, password, "admin")
        db.commit()
        print("Administrador cadastrado.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
