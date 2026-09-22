from __future__ import annotations

from PySide6.QtWidgets import QLineEdit
from financeiro_dr.core.financeiro.money import parse_money

class MoneyEdit(QLineEdit):
    """Small currency input that exposes the parsed value in integer cents."""
    def cents(self) -> int:
        return parse_money(self.text())
