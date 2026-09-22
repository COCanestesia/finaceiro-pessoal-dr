from dataclasses import dataclass
import sqlite3
@dataclass(frozen=True)
class DatabaseHealthResult:
    ok:bool; message:str
class DatabaseHealth:
    @staticmethod
    def check(connection:sqlite3.Connection)->DatabaseHealthResult:
        try:
            result=connection.execute('PRAGMA quick_check').fetchone()[0]
            if str(result).lower()=='ok':return DatabaseHealthResult(True,'Banco íntegro.')
            return DatabaseHealthResult(False,'O banco local apresentou problema de integridade. Não faça novos lançamentos. Restaure um backup válido ou procure suporte.')
        except sqlite3.Error as exc:
            if 'locked' in str(exc).lower():return DatabaseHealthResult(False,'O banco de dados está ocupado. Feche outra cópia do Financeiro Pessoal do Dr. e tente novamente.')
            return DatabaseHealthResult(False,'Não foi possível verificar o banco de dados local.')
