from decimal import Decimal

from app.services.calculation_service import (
    calculate_line_total,
    calculate_quotation_total,
    calculate_vat_amount,
)


def test_calculate_line_total_integers():
    assert calculate_line_total(Decimal("2"), Decimal("100")) == Decimal("200.00")


def test_calculate_line_total_decimal_quantity():
    assert calculate_line_total(Decimal("2.5"), Decimal("100")) == Decimal("250.00")


def test_calculate_line_total_rounding():
    assert calculate_line_total(Decimal("1"), Decimal("0.995")) == Decimal("1.00")
    assert calculate_line_total(Decimal("1"), Decimal("0.994")) == Decimal("0.99")


def test_calculate_quotation_total_empty():
    assert calculate_quotation_total([]) == Decimal("0.00")


def test_calculate_quotation_total_multiple_articles():
    articles = [
        {"line_total": Decimal("100.00")},
        {"line_total": Decimal("150.25")},
        {"line_total": Decimal("0.75")},
    ]
    assert calculate_quotation_total(articles) == Decimal("251.00")


def test_calculate_vat_amount_rounds_half_up():
    assert calculate_vat_amount(
        Decimal("1000.00"),
        "avec_tva",
        Decimal("18.00"),
    ) == Decimal("180.00")
    assert calculate_vat_amount(
        Decimal("100.03"),
        "avec_tva",
        Decimal("18.00"),
    ) == Decimal("18.01")


def test_calculate_vat_amount_is_zero_for_explicit_no_vat():
    assert calculate_vat_amount(
        Decimal("1000.00"),
        "sans_tva",
        None,
    ) == Decimal("0.00")
