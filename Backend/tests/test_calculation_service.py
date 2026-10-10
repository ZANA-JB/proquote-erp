from decimal import Decimal

from app.services.calculation_service import calculate_line_total, calculate_quotation_total


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
