"""Calcule les montants des lignes et le total d'une cotation."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable


def calculate_line_total(quantity: Decimal, unit_price: Decimal) -> Decimal:
    quantity = Decimal(quantity)
    unit_price = Decimal(unit_price)
    total = quantity * unit_price
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_quotation_total(articles: Iterable) -> Decimal:
    total = Decimal("0")
    for article in articles:
        line_total = getattr(article, "line_total", None)
        if line_total is None:
            line_total = article.get("line_total") if isinstance(article, dict) else None
        total += Decimal(line_total)
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_vat_amount(
    tax_base: Decimal,
    vat_mode: str | None,
    vat_rate: Decimal | None,
) -> Decimal:
    if vat_mode != "avec_tva" or vat_rate is None:
        return Decimal("0.00")

    amount = Decimal(tax_base) * Decimal(vat_rate) / Decimal("100")
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
