from __future__ import annotations
import sqlite3
from financeiro_dr.audit.audit_service import AuditService

class ClassificationService:
    def __init__(self, connection: sqlite3.Connection, audit_service: AuditService | None = None):
        self.connection=connection; self.audit=audit_service or AuditService(connection)

    def _create(self, table: str, name: str, category_id: int | None = None) -> int:
        name=name.strip()
        if not name: raise ValueError("Informe o nome.")
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            if table == "subcategory":
                if not self.connection.execute("SELECT 1 FROM category WHERE id=? AND active=1",(category_id,)).fetchone(): raise ValueError("Categoria não encontrada ou inativa.")
                cur=self.connection.execute("INSERT INTO subcategory(category_id,name) VALUES (?,?)",(category_id,name))
            else:
                cur=self.connection.execute(f"INSERT INTO {table}(name) VALUES (?)",(name,))
            ident=int(cur.lastrowid); row=dict(self.connection.execute(f"SELECT * FROM {table} WHERE id=?",(ident,)).fetchone()); self.audit.record_create(table,ident,row); self.connection.commit(); return ident
        except Exception:
            self.connection.rollback(); raise

    def create_category(self,name:str)->int: return self._create("category",name)
    def create_subcategory(self,category_id:int,name:str)->int: return self._create("subcategory",name,category_id)
    def create_cost_center(self,name:str)->int: return self._create("cost_center",name)

    def list_categories(self, active_only: bool=True):
        q="SELECT id,name,active FROM category"+(" WHERE active=1" if active_only else "")+" ORDER BY name"
        return [dict(r) for r in self.connection.execute(q)]
    def list_subcategories(self,category_id:int,active_only:bool=True):
        q="SELECT id,category_id,name,active FROM subcategory WHERE category_id=?"+(" AND active=1" if active_only else "")+" ORDER BY name"
        return [dict(r) for r in self.connection.execute(q,(category_id,))]
    def list_cost_centers(self,active_only:bool=True):
        q="SELECT id,name,active FROM cost_center"+(" WHERE active=1" if active_only else "")+" ORDER BY name"
        return [dict(r) for r in self.connection.execute(q)]

    def validate_selection(self, category_id=None, subcategory_id=None, cost_center_id=None) -> None:
        if category_id is not None and not self.connection.execute("SELECT 1 FROM category WHERE id=?",(category_id,)).fetchone(): raise ValueError("Categoria não encontrada.")
        if subcategory_id is not None:
            row=self.connection.execute("SELECT category_id FROM subcategory WHERE id=?",(subcategory_id,)).fetchone()
            if row is None: raise ValueError("Subcategoria não encontrada.")
            if category_id is None or int(row[0]) != int(category_id): raise ValueError("Subcategoria não pertence à categoria selecionada.")
        if cost_center_id is not None and not self.connection.execute("SELECT 1 FROM cost_center WHERE id=?",(cost_center_id,)).fetchone(): raise ValueError("Centro de custo não encontrado.")

    def set_active(self, table:str, item_id:int, active:bool)->None:
        if table not in {"category","subcategory","cost_center"}: raise ValueError("Tipo inválido.")
        before=self.connection.execute(f"SELECT * FROM {table} WHERE id=?",(item_id,)).fetchone()
        if before is None: raise ValueError("Registro não encontrado.")
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            self.connection.execute(f"UPDATE {table} SET active=?,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",(1 if active else 0,item_id))
            after=self.connection.execute(f"SELECT * FROM {table} WHERE id=?",(item_id,)).fetchone(); self.audit.record_update(table,item_id,dict(before),dict(after)); self.connection.commit()
        except Exception:
            self.connection.rollback(); raise
