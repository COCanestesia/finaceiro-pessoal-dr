from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

@dataclass(frozen=True)
class AppPaths:
    data_dir: Path
    config_dir: Path
    documents_dir: Path
    database_file: Path

    @property
    def initial_seed_file(self) -> Path:
        return self.data_dir / "initial-seed.json"

    @classmethod
    def from_environment(cls) -> "AppPaths":
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        roaming = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
        data_dir = local / "FinanceiroPessoalDr"
        config_dir = roaming / "FinanceiroPessoalDr"
        documents_dir = data_dir / "documents"
        for path in (data_dir, config_dir, documents_dir):
            path.mkdir(parents=True, exist_ok=True)
        return cls(data_dir, config_dir, documents_dir, data_dir / "financeiro.db")
