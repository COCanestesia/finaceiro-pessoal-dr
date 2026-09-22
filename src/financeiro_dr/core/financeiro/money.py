from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

_CENT = Decimal("0.01")

def parse_money(text: str) -> int:
    raw = text.strip().replace("R$", "").replace(" ", "")
    if not raw:
        raise ValueError("Informe um valor.")
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        value = Decimal(raw).quantize(_CENT, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError("Valor monetário inválido.") from exc
    if value < 0:
        raise ValueError("O valor não pode ser negativo.")
    return int(value * 100)

def format_money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    absolute = abs(cents)
    reais, centavos = divmod(absolute, 100)
    inteiro = f"{reais:,}".replace(",", ".")
    return f"{sign}R$ {inteiro},{centavos:02d}"
