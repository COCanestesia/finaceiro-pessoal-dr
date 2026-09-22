from datetime import datetime
class BackupScheduler:
    def __init__(self,last_success_date=None):self.last_success_date=last_success_date
    def should_run(self,now:datetime)->bool:return self.last_success_date!=now.date()
