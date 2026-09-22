from __future__ import annotations
from dataclasses import dataclass
from datetime import date,datetime
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
import csv,hashlib,re,sqlite3
class ImportFormatError(ValueError):pass
@dataclass(frozen=True)
class ImportSummary:created:int;duplicates:int;import_id:int
def _cents(value)->int:
    text=str(value).strip().replace('R$','').replace(' ','')
    if ',' in text and '.' in text:text=text.replace('.','').replace(',','.')
    elif ',' in text:text=text.replace(',','.')
    try:return int((Decimal(text)*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    except Exception as exc:raise ImportFormatError(f'Valor inválido: {value}') from exc
def _date(value)->date:
    if isinstance(value,datetime):return value.date()
    if isinstance(value,date):return value
    s=str(value).strip()
    for fmt,size in (('%Y-%m-%d',10),('%d/%m/%Y',10),('%d-%m-%Y',10),('%Y%m%d',8)):
        try:return datetime.strptime(s[:size],fmt).date()
        except ValueError:pass
    raise ImportFormatError(f'Data inválida: {value}')
def _hash(external_id,posted,amount,description):
    source=f"{external_id or ''}|{posted.isoformat()}|{amount}|{' '.join(description.casefold().split())}";return hashlib.sha256(source.encode()).hexdigest()
def parse_statement_file(path:Path,mapping=None):
    path=Path(path);ext=path.suffix.lower()
    if ext=='.csv':
        with path.open('r',encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f);fields=reader.fieldnames or [];mp=mapping or {'date':'data','description':'descricao','amount':'valor','external_id':'id'}
            for required in ('date','description','amount'):
                if mp[required] not in fields:raise ImportFormatError(f"Arquivo sem coluna obrigatória: {mp[required]}")
            return [(r.get(mp.get('external_id','')) or None,_date(r[mp['date']]),_cents(r[mp['amount']]),str(r[mp['description']]).strip()) for r in reader]
    if ext in {'.xlsx','.xlsm'}:
        try:from openpyxl import load_workbook
        except ImportError as exc:raise ImportFormatError('Suporte a Excel não instalado.') from exc
        ws=load_workbook(path,read_only=True,data_only=True).active;it=ws.iter_rows(values_only=True)
        try:headers=[str(x or '').strip() for x in next(it)]
        except StopIteration:raise ImportFormatError('Planilha vazia.')
        mp=mapping or {'date':'data','description':'descricao','amount':'valor','external_id':'id'};idx={h:i for i,h in enumerate(headers)}
        for required in ('date','description','amount'):
            if mp[required] not in idx:raise ImportFormatError(f"Arquivo sem coluna obrigatória: {mp[required]}")
        return [(r[idx[mp['external_id']]] if mp.get('external_id') in idx else None,_date(r[idx[mp['date']]]),_cents(r[idx[mp['amount']]]),str(r[idx[mp['description']]] or '').strip()) for r in it]
    if ext in {'.ofx','.qfx'}:
        text=path.read_text(encoding='utf-8',errors='ignore');out=[]
        for block in re.findall(r'<STMTTRN>(.*?)(?:</STMTTRN>|(?=<STMTTRN>)|$)',text,re.I|re.S):
            def tag(n):
                m=re.search(rf'<{n}>([^<\r\n]+)',block,re.I);return m.group(1).strip() if m else None
            dt=tag('DTPOSTED');amt=tag('TRNAMT');desc=tag('NAME') or tag('MEMO') or 'Movimento OFX'
            if dt and amt:out.append((tag('FITID'),_date(dt[:8]),_cents(amt),desc))
        if not out:raise ImportFormatError('OFX sem movimentações reconhecidas.')
        return out
    raise ImportFormatError('Formato de extrato não suportado.')
class ImportService:
    def __init__(self,connection:sqlite3.Connection):self.connection=connection
    def import_file(self,account_id:int,path:Path,mapping=None)->ImportSummary:
        if not self.connection.execute('SELECT 1 FROM bank_account WHERE id=?',(account_id,)).fetchone():raise ValueError('Conta não encontrada.')
        rows=parse_statement_file(Path(path),mapping);self.connection.execute('BEGIN IMMEDIATE')
        try:
            cur=self.connection.execute('INSERT INTO statement_import(account_id,source_name,row_count) VALUES (?,?,?)',(account_id,Path(path).name,len(rows)));iid=int(cur.lastrowid);created=dups=0
            for external,posted,amount,description in rows:
                raw=_hash(external,posted,amount,description)
                try:self.connection.execute('INSERT INTO statement_row(import_id,account_id,external_id,posted_date,amount_cents,description,raw_hash) VALUES (?,?,?,?,?,?,?)',(iid,account_id,external,posted.isoformat(),amount,description,raw));created+=1
                except sqlite3.IntegrityError:dups+=1
            self.connection.commit();return ImportSummary(created,dups,iid)
        except Exception:self.connection.rollback();raise
