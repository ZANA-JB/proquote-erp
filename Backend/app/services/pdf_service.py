"""Rend le modèle HTML des cotations et produit leur fichier PDF."""

import base64
import mimetypes
import os
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings
from app.models.quotation import Quotation
from app.services.calculation_service import (
    calculate_line_total,
    calculate_quotation_total,
    calculate_vat_amount,
)


TEMPLATE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "templates"))
LOGO_FALLBACK_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "REFERENCE", "logo.jpeg"))


def _ensure_windows_gtk_runtime() -> None:
    if os.name != "nt":
        return

    candidates = [
        r"C:\Program Files\GTK3-Runtime Win64\bin",
        r"C:\Program Files (x86)\GTK3-Runtime Win64\bin",
        r"C:\Program Files\GTK3-Runtime Win32\bin",
    ]

    current_path = os.environ.get("PATH", "")
    for candidate in candidates:
        if os.path.isdir(candidate):
            os.environ["PATH"] = candidate + os.pathsep + current_path
            try:
                os.add_dll_directory(candidate)
            except (AttributeError, OSError):
                pass
            return


_ensure_windows_gtk_runtime()

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except Exception:
    HTML = None
    WEASYPRINT_AVAILABLE = False



def _sanitize_reference(reference: str | None) -> str:
    value = str(reference or "quotation").strip()
    if not value:
        value = "quotation"
    safe_value = re.sub(r"[^A-Za-z0-9_#-]", "_", value)
    return safe_value.strip("._") or "quotation"


def _resolve_logo_path() -> Path:
    configured_path = (settings.COMPANY_LOGO_URL or "").strip()
    candidates: list[Path] = []

    if configured_path:
        candidates.extend([
            Path(configured_path),
            Path.cwd() / configured_path,
            Path(__file__).resolve().parents[2] / configured_path,
        ])

    candidates.append(Path(LOGO_FALLBACK_PATH))

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return Path(LOGO_FALLBACK_PATH)


def _encode_logo_to_data_uri() -> str | None:
    logo_path = _resolve_logo_path()
    if not logo_path.exists():
        return None

    mime_type, _ = mimetypes.guess_type(str(logo_path))
    if not mime_type:
        mime_type = "application/octet-stream"

    try:
        with open(logo_path, "rb") as logo_file:
            encoded = base64.b64encode(logo_file.read()).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"
    except Exception:
        return None


def _format_date(value) -> str:
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")
    return str(value)


def _normalize_multiline(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("\\n", "\n")


def render_quotation_html(quotation: Quotation) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("quotation_pdf.html")

    quotation_total = _get_quotation_total(quotation)
    vat_amount = calculate_vat_amount(
        quotation_total,
        getattr(quotation, "vat_mode", "sans_tva"),
        getattr(quotation, "vat_rate", None),
    )
    total_including_tax = quotation_total + vat_amount
    articles = list(getattr(quotation, "articles", []) or [])
    return template.render(
        company_name=settings.COMPANY_NAME,
        company_address=_normalize_multiline(settings.COMPANY_ADDRESS),
        company_contacts=_normalize_multiline(settings.COMPANY_CONTACTS),
        company_bank_details=_normalize_multiline(settings.COMPANY_BANK_DETAILS),
        company_logo_url=_encode_logo_to_data_uri(),
        quotation=quotation,
        quotation_total=quotation_total,
        vat_amount=vat_amount,
        total_including_tax=total_including_tax,
        amount_in_words=_number_to_words_fr(total_including_tax),
        incoterm_label=_get_incoterm_label(quotation),
        article_line_total=_get_article_line_total,
        format_quantity=_format_quantity,
        format_date=_format_date,
        format_currency=_format_currency,
    )


def get_pdf_path(reference: str | None) -> str:
    filename = f"{_sanitize_reference(reference)}.pdf"
    return os.path.join(settings.PDF_STORAGE_PATH, filename)


def _format_currency(value) -> str:
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    whole_amount = int(amount)
    fractional_amount = int((abs(amount) - abs(whole_amount)) * 100)
    formatted = f"{whole_amount:,}".replace(",", " ")
    if fractional_amount:
        formatted += f",{fractional_amount:02d}"
    return f"{formatted} FCFA"


def _format_quantity(value) -> str:
    quantity = Decimal(str(value))
    return format(quantity.normalize(), "f")


def _number_to_words_fr(value: Decimal | float | int) -> str:
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    is_negative = amount < 0
    amount = abs(amount)
    whole = int(amount)
    cents = int((amount - whole) * 100)

    units = [
        "zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf",
        "dix", "onze", "douze", "treize", "quatorze", "quinze", "seize",
        "dix-sept", "dix-huit", "dix-neuf",
    ]
    tens = [
        "",
        "",
        "vingt",
        "trente",
        "quarante",
        "cinquante",
        "soixante",
        "soixante-dix",
        "quatre-vingt",
        "quatre-vingt-dix",
    ]

    def under_100(n: int) -> str:
        if n < 20:
            return units[n]
        tens_digit = n // 10
        unit_digit = n % 10
        if tens_digit in (2, 3, 4, 5, 6):
            if unit_digit == 1:
                return f"{tens[tens_digit]} et un"
            if unit_digit == 0:
                return tens[tens_digit]
            return f"{tens[tens_digit]}-{units[unit_digit]}"
        if tens_digit == 7:
            remainder = n - 60
            if remainder == 11:
                return "soixante et onze"
            return f"soixante-{units[remainder]}"
        if n == 80:
            return "quatre-vingts"
        return f"quatre-vingt-{units[n - 80]}"

    def under_1000(n: int) -> str:
        if n < 100:
            return under_100(n)
        hundreds = n // 100
        remainder = n % 100
        if hundreds == 1 and remainder == 0:
            return "cent"
        if hundreds == 1:
            return f"cent {under_100(remainder)}"
        if remainder == 0:
            return f"{units[hundreds]} cent"
        return f"{units[hundreds]} cent {under_100(remainder)}"

    def to_words(n: int) -> str:
        if n < 1000:
            return under_1000(n)
        if n < 1_000_000:
            thousands = n // 1000
            remainder = n % 1000
            if thousands == 1 and remainder == 0:
                return "mille"
            if remainder == 0:
                return f"{under_1000(thousands)} mille"
            return f"{under_1000(thousands)} mille {under_1000(remainder)}"
        if n < 1_000_000_000:
            millions = n // 1_000_000
            remainder = n % 1_000_000
            if remainder == 0:
                if millions == 1:
                    return "un million"
                return f"{under_1000(millions)} millions"
            if millions == 1:
                return f"un million {to_words(remainder)}"
            return f"{under_1000(millions)} millions {to_words(remainder)}"
        billions = n // 1_000_000_000
        remainder = n % 1_000_000_000
        scale = "milliard" if billions == 1 else "milliards"
        if remainder == 0:
            return f"{to_words(billions)} {scale}"
        return f"{to_words(billions)} {scale} {to_words(remainder)}"

    words = to_words(whole)

    if is_negative:
        words = f"moins {words}"
    if cents:
        return f"{words} FCFA et {under_1000(cents)} centimes"
    return f"{words} FCFA"


def _get_article_line_total(article) -> Decimal:
    return calculate_line_total(
        Decimal(str(article.quantity)),
        Decimal(str(article.unit_price)),
    )


def _get_quotation_total(quotation: Quotation) -> Decimal:
    articles = list(getattr(quotation, "articles", []) or [])
    if not articles:
        return Decimal(str(getattr(quotation, "total_amount", 0) or 0)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    return calculate_quotation_total(
        {"line_total": _get_article_line_total(article)}
        for article in articles
    )


def _get_incoterm_label(quotation: Quotation) -> str | None:
    incoterm = getattr(quotation, "incoterm", None)
    if incoterm is None:
        return None
    if hasattr(incoterm, "value"):
        incoterm = incoterm.value
    if isinstance(incoterm, str):
        incoterm = incoterm.strip()
    if not incoterm:
        return None
    return incoterm


def generate_pdf(quotation: Quotation) -> str:
    if not WEASYPRINT_AVAILABLE or HTML is None:
        raise RuntimeError("WeasyPrint is required to generate quotation PDFs.")

    reference = getattr(quotation, "reference", None) or getattr(quotation, "id", None) or "quotation"
    file_path = get_pdf_path(reference)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    html_content = render_quotation_html(quotation)
    HTML(string=html_content).write_pdf(file_path)
    return file_path
