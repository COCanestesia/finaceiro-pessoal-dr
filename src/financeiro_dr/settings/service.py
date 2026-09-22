from dataclasses import asdict,dataclass
from pathlib import Path
import json
@dataclass(frozen=True)
class AppSettings:
    backup_dir:str=''
    auto_backup_enabled:bool=True
    card_alert_percent:int=85
    budget_warning_percent:int=80
    budget_limit_percent:int=100
class SettingsService:
    def __init__(self,config_file:Path):self.config_file=Path(config_file);self.config_file.parent.mkdir(parents=True,exist_ok=True)
    def load(self)->AppSettings:
        if not self.config_file.exists():return AppSettings()
        try:
            data=json.loads(self.config_file.read_text(encoding='utf-8'));allowed={k:v for k,v in data.items() if k in AppSettings.__dataclass_fields__};return AppSettings(**allowed)
        except Exception:return AppSettings()
    def save(self,settings:AppSettings)->None:
        temp=self.config_file.with_suffix('.tmp');temp.write_text(json.dumps(asdict(settings),ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(self.config_file)
