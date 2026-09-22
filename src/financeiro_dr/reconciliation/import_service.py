from __future__ import annotations
from dataclasses import dataclass
from datetime import date,datetime
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
import csv,hashlib,re,sqlite3

class ImportFormatError(ValueError): pass
@dataclass(frozen=True)
class ImportSummary: created:int; duplicates:int; import_id:int

def _cents(value)->int:
    text=str(value).strip().replace("R$","").replace(" ","")
    if "," in text and "." in text: text=text.replace(".","").replace(",",".")
    elif "," in text: text=text.replace(",",".")
    return int((Decimal(text)*100).quantize(Decimal("1"),rounding=ROUND_HALF_UP))
def _date(value)->date:
    if isinstance(value,datetime): return value.date()
    if isinstance(value,date): return value
    s=str(value).strip()
    for fmt in ("%Y-%m-%d","%d/%m/%Y","%d-%m-%Y","%Y%m%d"):
        try:return datetime.strptime(s[:10],fmt).date()
        except ValueError: pass
    raise ImportFormatError(f"Data inválida: {value}")
def _hash(external_id,posted,amount,description):
    source=f"{external_id or ''}|{posted.isoformat()}|{amount}|{' '.join(description.casefold().split())}"; return hashlib.sha256(source.encode()).hexdigest()

class ImportService:
    def __init__(self,connection:sqlite3.Connection): self.connection=connection
    def _rows_csv(self,path:Path,mapping=None):
        with path.open("r",encoding="utf-8-sig",newline="") as f:
            reader=csv.DictReader(f); fields=reader.fieldnames or []; mp=mapping or {"date":"data","description":"descricao","amount":"valor","external_id":"id"}
            for required in ("date","description","amount"):
                if mp[required] not in fields: raise ImportFormatError(f"Arquivo sem coluna obrigatória: {mp[required]}")
            for r in reader: yield r.get(mp.get("external_id","")) or None,_date(r[mp['date']]),_cents(r[mp['amount']]),str(r[mp['description']]).strip()
    def _rows_xlsx(self,path:Path,mapping=None):
        try: from openpyxl import load_workbook
        except ImportError as exc: raise ImportFormatError("Suporte a Excel não instalado.") from exc
        ws=load_workbook(path,read_only=True,data_only=True).active; rows=ws.iter_rows(values_only=True); headers=[str(x or '').strip() for x in next(rows)]; mp=mapping or {"date":"data","description":"descricao","amount":"valor","external_id":"id"}; idx={h:i for i,h in enumerate(headers)}
        for required in ("date","description","amount"):
            if mp[required] not in idx: raise ImportFormatError(f"Arquivo sem coluna obrigatória: {mp[required]}")
        for r in rows: yield (r[idx[mp['external_id']]] if mp.get('external_id') in idx else None),_date(r[idx[mp['date']]]),_cents(r[idx[mp['amount']]]),str(r[idx[mp['description']]] or '').strip()
    def _rows_ofx(self,path:Path):
        text=path.read_text(encoding="utf-8",errors="ignore")
        for block in re.findall(r"<STMTTRN>(.*?)(?:</STMTTRN>|(?=<STMTTRN>)|$)",text,re.I|re.S):
            def tag(n):
                m=re.search(rf"<{n}>([^<\r\n]+)",block,re.I); return m.group(1).strip() if m else None
            dt=tag("DTPOSTED"); amt=tag("TRNAMT"); desc=tag("NAME") or tag("MEMO") or "Movimento OFX"
            if dt and amt: yield tag("FITID"),_date(dt[:8]),_cents(amt),desc
    def import_file(self,account_id:int,path:Path,mapping=None)->ImportSummary:
        path=Path(path); ext=path.suffix.lower(); parser=self._rows_csv if ext=='.csv' else self._rows_xlsx if ext in {'.xlsx','.xlsm'} else self._rows_ofx if ext in {'.ofx','.qfx'} else None
        if parser is None: raise ImportFormatError("Formato de extrato não suportado.")
        rows=list(parser(path,mapping) if parser in {self._rows_csv,self._rows_xlsx} else parser(path))
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            cur=self.connection.execute("INSERT INTO statement_import(account_id,source_name,row_count) VALUES (?,?,?)",(account_id,path.name,len(rows))); iid=int(cur.lastrowid); created=dups=0
            for external,posted,amount,description in rows:
                raw=_hash(external,posted,amount,description)
                try:self.connection.execute("INSERT INTO statement_row(import_id,account_id,external_id,posted_date,amount_cents,description,raw_hash) VALUES (?,?,?,?,?,?,?)",(iid,account_id,external,posted.isoformat(),amount,description,raw)); created+=1
                except sqlite3.IntegrityError: dups+=1
            self.connection.commit(); return ImportSummary(created,dups,iid)
        except Exception:
            self.connection.rollback(); raise
