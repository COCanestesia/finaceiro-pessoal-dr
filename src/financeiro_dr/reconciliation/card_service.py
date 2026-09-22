from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path
import sqlite3
from .import_service import ImportSummary,_hash,parse_statement_file
@dataclass(frozen=True)
class CardMatch:purchase_id:int;score:int
@dataclass(frozen=True)
class CardMatchResult:candidates:tuple[CardMatch,...];auto_confirm:bool
class CardStatementImportService:
    def __init__(self,connection:sqlite3.Connection):self.connection=connection
    def import_file(self,card_id:int,path:Path,mapping=None)->ImportSummary:
        if not self.connection.execute('SELECT 1 FROM credit_card WHERE id=?',(card_id,)).fetchone():raise ValueError('Cartão não encontrado.')
        rows=parse_statement_file(Path(path),mapping);self.connection.execute('BEGIN IMMEDIATE')
        try:
            cur=self.connection.execute('INSERT INTO card_statement_import(card_id,source_name,row_count) VALUES (?,?,?)',(card_id,Path(path).name,len(rows)));iid=int(cur.lastrowid);created=dups=0
            for external,posted,amount,description in rows:
                raw=_hash(external,posted,amount,description)
                try:self.connection.execute('INSERT INTO card_statement_row(import_id,card_id,external_id,posted_date,amount_cents,description,raw_hash) VALUES (?,?,?,?,?,?,?)',(iid,card_id,external,posted.isoformat(),amount,description,raw));created+=1
                except sqlite3.IntegrityError:dups+=1
            self.connection.commit();return ImportSummary(created,dups,iid)
        except Exception:self.connection.rollback();raise
class CardReconciliationService:
    def __init__(self,connection:sqlite3.Connection):self.connection=connection
    def suggest(self,row_id:int)->CardMatchResult:
        row=self.connection.execute('SELECT * FROM card_statement_row WHERE id=?',(row_id,)).fetchone()
        if row is None:raise ValueError('Movimento da fatura não encontrado.')
        purchases=self.connection.execute('SELECT * FROM card_purchase WHERE card_id=? AND total_cents=?',(row['card_id'],abs(int(row['amount_cents'])))).fetchall();ranked=[];posted=date.fromisoformat(row['posted_date']);desc=' '.join(row['description'].casefold().split())
        for p in purchases:
            score=60;pd=date.fromisoformat(p['purchase_date']);delta=abs((posted-pd).days);score+=25 if delta==0 else 18 if delta==1 else 0
            if SequenceMatcher(None,desc,' '.join(p['description'].casefold().split())).ratio()>=.8:score+=15
            ranked.append(CardMatch(int(p['id']),score))
        ranked.sort(key=lambda x:x.score,reverse=True);auto=bool(ranked and ranked[0].score>=85 and (len(ranked)==1 or ranked[0].score-ranked[1].score>5));return CardMatchResult(tuple(ranked),auto)
    def confirm(self,row_id:int,purchase_id:int)->None:
        result=self.suggest(row_id);match=next((x for x in result.candidates if x.purchase_id==purchase_id),None)
        if match is None:raise ValueError('Compra não é candidata válida.')
        self.connection.execute("INSERT INTO card_reconciliation_link(statement_row_id,purchase_id,status,score,confirmed_at) VALUES (?,?,'CONCILIADO',?,strftime('%Y-%m-%dT%H:%M:%fZ','now'))",(row_id,purchase_id,match.score));self.connection.commit()
    def mark_divergent(self,row_id:int,note:str)->None:self.connection.execute("INSERT INTO card_reconciliation_link(statement_row_id,status,note,confirmed_at) VALUES (?,'DIVERGENTE',?,strftime('%Y-%m-%dT%H:%M:%fZ','now'))",(row_id,note));self.connection.commit()
    def ignore(self,row_id:int)->None:self.connection.execute('UPDATE card_statement_row SET ignored=1 WHERE id=?',(row_id,));self.connection.commit()
    def pending_count(self)->int:return int(self.connection.execute("SELECT COUNT(*) FROM card_statement_row sr WHERE sr.ignored=0 AND NOT EXISTS(SELECT 1 FROM card_reconciliation_link rl WHERE rl.statement_row_id=sr.id AND rl.status IN ('CONCILIADO','DIVERGENTE'))").fetchone()[0])
