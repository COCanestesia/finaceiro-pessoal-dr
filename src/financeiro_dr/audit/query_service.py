from dataclasses import dataclass
from datetime import date
import sqlite3
@dataclass(frozen=True)
class AuditEvent:
    id:int;occurred_at:str;entity:str;entity_id:int;action:str;field_name:str|None;old_value:str|None;new_value:str|None
class AuditQueryService:
    def __init__(self,connection:sqlite3.Connection):self.connection=connection
    def search(self,start:date|None=None,end:date|None=None,entity:str|None=None,action:str|None=None,text:str|None=None):
        q='SELECT * FROM audit_log WHERE 1=1';p=[]
        if start:q+=' AND substr(occurred_at,1,10)>=?';p.append(start.isoformat())
        if end:q+=' AND substr(occurred_at,1,10)<=?';p.append(end.isoformat())
        if entity:q+=' AND entity=?';p.append(entity)
        if action:q+=' AND action=?';p.append(action)
        if text:q+=" AND (COALESCE(field_name,'') LIKE ? OR COALESCE(old_value,'') LIKE ? OR COALESCE(new_value,'') LIKE ? OR COALESCE(snapshot_json,'') LIKE ?)";p.extend([f'%{text}%']*4)
        return [AuditEvent(r['id'],r['occurred_at'],r['entity'],r['entity_id'],r['action'],r['field_name'],r['old_value'],r['new_value']) for r in self.connection.execute(q+' ORDER BY occurred_at DESC,id DESC',p)]
