from .conftest import create_quotation


def test_dashboard_reflects_persisted_quotation_and_cleanup(api_client, admin_headers):
    quotation = create_quotation(api_client, admin_headers)
    quotation_id = quotation["id"]
    try:
        summary = api_client.get("/dashboard/summary", headers=admin_headers)
        assert summary.status_code == 200, summary.text
        assert summary.json()["total_quotations"] >= 1

        chart = api_client.get(
            "/dashboard/charts",
            headers=admin_headers,
            params={"type": "by_month"},
        )
        assert chart.status_code == 200, chart.text
        assert isinstance(chart.json(), list)

        deletion = api_client.delete(f"/quotations/{quotation_id}", headers=admin_headers)
        assert deletion.status_code == 200, deletion.text
        assert api_client.get(
            f"/quotations/{quotation_id}",
            headers=admin_headers,
        ).status_code == 404
    finally:
        api_client.delete(f"/quotations/{quotation_id}", headers=admin_headers)
