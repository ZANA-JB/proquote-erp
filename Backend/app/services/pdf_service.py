"""Rend le modèle HTML des cotations et produit leur fichier PDF."""

import base64
import mimetypes
import os
import re
from pathlib import Path
from typing import List
from datetime import date
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings
from app.models.quotation import Incoterm, Quotation


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


def _get_status_label(status) -> str:
    if status is None:
        return "À préciser"
    value = status.value if hasattr(status, "value") else status
    if isinstance(value, str):
        value = value.strip().upper()
    mapping = {
        "BROUILLON": "En attente",
        "ENVOYEE": "Envoyé",
        "ACCEPTEE": "Validé",
        "REFUSEE": "Annulé",
        "EXPIREE": "Expiré",
    }
    return mapping.get(value, str(value))


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
    return template.render(
        company_name=settings.COMPANY_NAME,
        company_address=_normalize_multiline(settings.COMPANY_ADDRESS),
        company_contacts=_normalize_multiline(settings.COMPANY_CONTACTS),
        company_bank_details=_normalize_multiline(settings.COMPANY_BANK_DETAILS),
        company_logo_url=_encode_logo_to_data_uri(),
        quotation=quotation,
        quotation_total=quotation_total,
        amount_in_words=_number_to_words_fr(quotation_total),
        incoterm_label=_get_incoterm_label(quotation),
        quotation_status=_get_status_label(quotation.status),
        format_date=_format_date,
        format_currency=_format_currency,
    )


def get_pdf_path(reference: str | None) -> str:
    filename = f"{_sanitize_reference(reference)}.pdf"
    return os.path.join(settings.PDF_STORAGE_PATH, filename)


def _format_currency(value) -> str:
    try:
        return f"{float(value):,.0f}".replace(",", " ") + " FCFA"
    except (TypeError, ValueError):
        return "0 FCFA"


def _number_to_words_fr(value: float) -> str:
    cents = int(round((value - int(value)) * 100))
    whole = int(value)

    if whole == 0:
        words = "zéro"
    else:
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
            if unit_digit == 0:
                return tens[tens_digit]
            if tens_digit == 7:
                return f"soixante-{units[unit_digit]}"
            if tens_digit == 8:
                return f"quatre-vingt-{units[unit_digit]}"
            if tens_digit == 9:
                if unit_digit == 1:
                    return "quatre-vingt-onze"
                return f"quatre-vingt-{units[unit_digit]}"
            return f"{tens[tens_digit]}-{units[unit_digit]}"

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
            millions = n // 1_000_000
            remainder = n % 1_000_000
            if remainder == 0:
                if millions == 1:
                    return "un million"
                return f"{under_1000(millions)} millions"
            if millions == 1:
                return f"un million {to_words(remainder)}"
            return f"{under_1000(millions)} millions {to_words(remainder)}"

        words = to_words(whole)

    if cents:
        return f"{words} FCFA et {cents} centimes"
    return f"{words} FCFA"


def _get_quotation_total(quotation: Quotation) -> float:
    try:
        article_total = sum(float(getattr(article, 'line_total', 0) or 0) for article in getattr(quotation, 'articles', []) or [])
        if article_total:
            return article_total
    except Exception:
        pass
    try:
        return float(quotation.total_amount or 0)
    except Exception:
        return 0.0


def _get_incoterm_label(quotation: Quotation) -> str:
    incoterm = getattr(quotation, "incoterm", None)
    if incoterm is None:
        return "À définir"
    if hasattr(incoterm, "value"):
        incoterm = incoterm.value
    if isinstance(incoterm, str):
        incoterm = incoterm.strip()
    if not incoterm:
        return "À définir"
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
