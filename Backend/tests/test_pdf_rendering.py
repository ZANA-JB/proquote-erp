from datetime import date
import base64
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from types import SimpleNamespace

import pytest
from PyPDF2 import PdfReader

from app.core.config import settings
from app.services.calculation_service import calculate_line_total
from app.services import pdf_service


@pytest.fixture
def isolated_pdf_environment(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "PDF_STORAGE_PATH", str(tmp_path))
    monkeypatch.setattr(settings, "COMPANY_NAME", "Trident Test Services")
    monkeypatch.setattr(settings, "COMPANY_ADDRESS", "Adresse de test")
    monkeypatch.setattr(settings, "COMPANY_CONTACTS", "Contact de test")
    monkeypatch.setattr(settings, "COMPANY_BANK_DETAILS", "Coordonnées bancaires de test")
    monkeypatch.setattr(settings, "COMPANY_LOGO_URL", "")
    monkeypatch.setattr(pdf_service, "_encode_logo_to_data_uri", lambda: None)
    return tmp_path


def _article(designation: str, quantity: str, unit_price: str, unit: str = "u"):
    quantity_value = Decimal(quantity)
    unit_price_value = Decimal(unit_price)
    return SimpleNamespace(
        designation=designation,
        quantity=quantity_value,
        unit=unit,
        unit_price=unit_price_value,
        line_total=calculate_line_total(quantity_value, unit_price_value),
    )


def _quotation(articles, **overrides):
    values = {
        "reference": "TEST-PDF-001",
        "client_name": "Client PDF de test",
        "client_email": "client@example.test",
        "client_address": "Adresse client de test",
        "client_reference": "REF-TEST-001",
        "creation_date": date(2026, 10, 25),
        "validity_date": date(2026, 11, 25),
        "delivery_duration": "10 jours",
        "incoterm": "DDP",
        "status": "BROUILLON",
        "articles": articles,
        "total_amount": sum((article.line_total for article in articles), Decimal("0.00")),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _generate_and_read_pdf(quotation, output_dir: Path):
    pdf_path = Path(pdf_service.generate_pdf(quotation))
    assert pdf_path.exists()
    assert pdf_path.parent == output_dir
    assert pdf_path.read_bytes().startswith(b"%PDF-")

    reader = PdfReader(str(pdf_path))
    assert reader.pages
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return reader, " ".join(text.split())


def test_generated_pdf_uses_configured_company_and_real_quotation_values(
    isolated_pdf_environment,
):
    quotation = _quotation([_article("Maintenance industrielle", "2", "1500")])

    reader, text = _generate_and_read_pdf(quotation, isolated_pdf_environment)

    assert len(reader.pages) == 1
    assert "TRIDENT TEST SERVICES" in text
    assert "TEST-PDF-001" in text
    assert "Client PDF de test" in text
    assert "client@example.test" in text
    assert "25/10/2026" in text
    assert "25/11/2026" in text
    assert "Maintenance industrielle" in text
    assert "1 500 FCFA" in text
    assert "3 000 FCFA" in text
    assert "trois mille FCFA" in text
    assert "Incoterm" in text
    assert "DDP" in text
    assert "Coordonnées bancaires de test" in text
    assert "Libellé" in text
    assert "PU HT" in text
    assert "Montant HT" in text


def test_generated_pdf_restores_company_logo_and_background_watermark(
    isolated_pdf_environment,
    monkeypatch,
):
    logo_path = Path(__file__).resolve().parents[2] / "REFERENCE" / "logo.jpeg"
    logo_data = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    monkeypatch.setattr(
        pdf_service,
        "_encode_logo_to_data_uri",
        lambda: f"data:image/jpeg;base64,{logo_data}",
    )
    quotation = _quotation([_article("Article avec logo", "1", "1000")])

    reader, text = _generate_and_read_pdf(quotation, isolated_pdf_environment)
    html = pdf_service.render_quotation_html(quotation)

    assert 'class="company-logo"' in html
    assert 'class="watermark"' in html
    assert "Article avec logo" in text
    resources = reader.pages[0]["/Resources"].get_object()
    xobjects = resources["/XObject"].get_object()
    assert any(
        xobject.get_object().get("/Subtype") == "/Image"
        for xobject in xobjects.values()
    )


def test_generated_pdf_sums_multiple_articles_and_decimal_quantities(
    isolated_pdf_environment,
):
    quotation = _quotation(
        [
            _article("Prestation A", "1", "1250"),
            _article("Prestation B", "1.5", "2000", "h"),
        ]
    )

    _, text = _generate_and_read_pdf(quotation, isolated_pdf_environment)

    assert "1,5" in text or "1.5" in text
    assert "3 000 FCFA" in text
    assert "4 250 FCFA" in text
    assert "quatre mille deux cent cinquante FCFA" in text


def test_generated_pdf_wraps_long_designations_without_losing_text(
    isolated_pdf_environment,
):
    designation = "Équipement industriel spécialisé " * 20
    quotation = _quotation([_article(designation, "1", "500")])

    _, text = _generate_and_read_pdf(quotation, isolated_pdf_environment)

    assert text.count("Équipement industriel spécialisé") == 20
    assert "500 FCFA" in text


def test_generated_pdf_omits_unavailable_payment_tax_and_bank_information(
    isolated_pdf_environment,
    monkeypatch,
):
    monkeypatch.setattr(settings, "COMPANY_ADDRESS", "")
    monkeypatch.setattr(settings, "COMPANY_CONTACTS", "")
    monkeypatch.setattr(settings, "COMPANY_BANK_DETAILS", "")
    quotation = _quotation(
        [_article("Article sans informations facultatives", "1", "1000")],
        incoterm=None,
        client_email=None,
        client_address=None,
        client_reference=None,
        validity_date=None,
        delivery_duration=None,
    )

    _, text = _generate_and_read_pdf(quotation, isolated_pdf_environment)

    assert "TVA" not in text
    assert "TTC" not in text
    assert "Règlement" not in text
    assert "Échéance" not in text
    assert "Coordonnées bancaires" not in text
    assert "Incoterm" not in text
    assert "Non précisé" not in text
    assert "Article sans informations facultatives" in text


def test_generated_pdf_repeats_table_heading_across_pages(isolated_pdf_environment):
    articles = [
        _article(f"Article de test {index:03d} - description détaillée", "1", "100")
        for index in range(1, 81)
    ]
    quotation = _quotation(articles, reference="TEST-PDF-MULTI")

    reader, text = _generate_and_read_pdf(quotation, isolated_pdf_environment)

    assert len(reader.pages) > 1
    assert "Article de test 001" in text
    assert "Article de test 080" in text
    assert text.count("Libellé") >= 2
    assert "8 000 FCFA" in text


def test_pdf_currency_and_amount_in_words_share_decimal_rounding():
    amount = Decimal("3000.505")

    rounded = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    assert rounded == Decimal("3000.51")
    assert pdf_service._format_currency(rounded) == "3 000,51 FCFA"
    assert pdf_service._number_to_words_fr(rounded) == (
        "trois mille FCFA et cinquante et un centimes"
    )


def test_generated_pdf_recalculates_line_and_total_from_saved_quantity_and_price(
    isolated_pdf_environment,
):
    article = _article("Ligne à recalculer", "2", "125")
    article.line_total = Decimal("0.01")
    quotation = _quotation([article], total_amount=Decimal("0.01"))

    _, text = _generate_and_read_pdf(quotation, isolated_pdf_environment)

    assert "250 FCFA" in text
    assert "0,01 FCFA" not in text
