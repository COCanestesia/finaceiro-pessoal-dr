from __future__ import annotations
import sqlite3

def database_error_message(exc: sqlite3.Error) -> str:
    text=str(exc).casefold()
    if "database is locked" in text or "database table is locked" in text:
        return "O banco de dados está ocupado. Tente novamente em alguns segundos."
    return "Não foi possível concluir a operação no banco de dados local."

def show_user_error(parent, message: str) -> None:
    from PySide6.QtWidgets import QMessageBox
    QMessageBox.critical(parent, "Financeiro Pessoal do Dr.", message)
