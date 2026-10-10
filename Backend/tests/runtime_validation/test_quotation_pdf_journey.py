import re
from urllib.parse import unquote

from .conftest import create_quotation


def test_create_persist_generate_and_download_current_pdf(api_client, admin_headers):
    quotation = create_quotation(api_client, admin_headers)
    quotation_id = quotation["id"]
    try:
        assert re.fullmatch(r"\d{3}#\d{2}-\d{2}-\d{4}", quotation["reference"])

        persisted = api_client.get(f"/quotations/{quotation_id}", headers=admin_headers)
        assert persisted.status_code == 200, persisted.text
        assert persisted.json()["reference"] == quotation["reference"]
        assert persisted.json()["articles"][0]["designation"] == "Runtime PDF verification service"
        assert float(persisted.json()["total_amount"]) == 2500

        generated = api_client.post(
            f"/quotations/{quotation_id}/generate-pdf",
            headers=admin_headers,
        )
        assert generated.status_code == 200, generated.text

        downloaded = api_client.get(f"/quotations/{quotation_id}/pdf", headers=admin_headers)
        assert downloaded.status_code == 200, downloaded.text
        assert downloaded.headers["content-type"].startswith("application/pdf")
        assert downloaded.content.startswith(b"%PDF-")
        assert unquote(downloaded.headers["content-disposition"]).endswith(
            f"{quotation['reference']}.pdf"
        )
    finally:
        api_client.delete(f"/quotations/{quotation_id}", headers=admin_headers)
