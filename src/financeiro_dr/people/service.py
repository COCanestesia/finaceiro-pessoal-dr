from __future__ import annotations
import sqlite3
from financeiro_dr.audit.audit_service import AuditService
from .models import Person

class PeopleService:
    def __init__(self, connection: sqlite3.Connection, audit_service: AuditService | None = None):
        self.connection = connection
        self.audit = audit_service or AuditService(connection)

    def create(self, name: str, relationship: str | None = None, nickname: str | None = None, notes: str | None = None) -> int:
        name = name.strip()
        if not name:
            raise ValueError("Informe o nome da pessoa.")
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            cur = self.connection.execute("INSERT INTO person(name,relationship,nickname,notes) VALUES (?,?,?,?)", (name, relationship, nickname, notes))
            pid = int(cur.lastrowid)
            row = dict(self.connection.execute("SELECT * FROM person WHERE id=?", (pid,)).fetchone())
            self.audit.record_create("person", pid, row)
            self.connection.commit()
            return pid
        except Exception:
            self.connection.rollback(); raise

    def get(self, person_id: int) -> Person | None:
        row = self.connection.execute("SELECT id,name,relationship,nickname,notes,active FROM person WHERE id=?", (person_id,)).fetchone()
        return Person(row[0], row[1], row[2], row[3], row[4], bool(row[5])) if row else None

    def list_active(self) -> list[Person]:
        rows = self.connection.execute("SELECT id,name,relationship,nickname,notes,active FROM person WHERE active=1 ORDER BY name").fetchall()
        return [Person(r[0],r[1],r[2],r[3],r[4],bool(r[5])) for r in rows]

    def list_all(self) -> list[Person]:
        rows = self.connection.execute("SELECT id,name,relationship,nickname,notes,active FROM person ORDER BY active DESC,name").fetchall()
        return [Person(r[0],r[1],r[2],r[3],r[4],bool(r[5])) for r in rows]

    def set_active(self, person_id: int, active: bool) -> None:
        before = self.connection.execute("SELECT * FROM person WHERE id=?", (person_id,)).fetchone()
        if before is None: raise ValueError("Pessoa não encontrada.")
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            self.connection.execute("UPDATE person SET active=?,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?", (1 if active else 0, person_id))
            after = self.connection.execute("SELECT * FROM person WHERE id=?", (person_id,)).fetchone()
            self.audit.record_update("person", person_id, dict(before), dict(after))
            self.connection.commit()
        except Exception:
            self.connection.rollback(); raise
