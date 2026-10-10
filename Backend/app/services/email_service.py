import os
"""Prépare et envoie les emails contenant les cotations et les relances."""

import smtplib
from email.message import EmailMessage
from typing import Optional

from app.core.config import settings
from app.models.quotation import Quotation
from app.models.payment_reminder import PaymentReminder


def _open_smtp_connection() -> smtplib.SMTP:
    host = settings.SMTP_HOST or ""
    port = int(settings.SMTP_PORT) if getattr(settings, "SMTP_PORT", None) else 25
    if not host:
        raise ValueError("SMTP host not configured")

    if port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=10)
    else:
        server = smtplib.SMTP(host, port, timeout=10)
        if port == 587:
            server.ehlo()
            server.starttls()
            server.ehlo()
    return server


def _send_email(msg: EmailMessage) -> bool:
    user = settings.SMTP_USER or None
    password = settings.SMTP_PASSWORD or None
    try:
        server = _open_smtp_connection()
        if user and password:
            server.login(user, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception:
        return False


def send_quotation_email(quotation: Quotation, pdf_path: str) -> bool:
    """Envoie le PDF d'une cotation en pièce jointe et indique le succès."""
    if not settings.MAIL_FROM:
        return False
    msg = EmailMessage()
    subject = f"Quotation {quotation.reference}"
    msg["Subject"] = subject
    msg["From"] = settings.MAIL_FROM
    msg["To"] = quotation.client_email
    body = f"Bonjour {quotation.client_name},\n\nVeuillez trouver en pièce jointe le devis {quotation.reference}.\n\nCordialement,\n{settings.COMPANY_NAME}"
    msg.set_content(body)

    # Ajoute le PDF généré en pièce jointe.
    try:
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        msg.add_attachment(pdf_data, maintype="application", subtype="pdf", filename=os.path.basename(pdf_path))
    except Exception:
        return False

    return _send_email(msg)


def send_payment_reminder_email(quotation: Quotation, reminder: PaymentReminder) -> bool:
    """Envoie une relance pour une cotation non réglée."""
    if not settings.MAIL_FROM:
        return False
    msg = EmailMessage()
    subject = f"Rappel de paiement - Devis {quotation.reference}"
    msg["Subject"] = subject
    msg["From"] = settings.MAIL_FROM
    msg["To"] = quotation.client_email
    body = (
        f"Bonjour {quotation.client_name},\n\n"
        f"Ceci est un rappel de paiement pour le devis {quotation.reference}.\n"
        f"Montant dû : {quotation.total_amount} €.\n"
        f"Date d'échéance du devis : {quotation.validity_date or 'N/A'}.\n\n"
        f"Merci de procéder au règlement dès que possible.\n\n"
        f"Cordialement,\n{settings.COMPANY_NAME}"
    )
    msg.set_content(body)
    return _send_email(msg)
