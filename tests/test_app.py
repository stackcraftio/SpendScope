import io

from app import create_app


def test_dashboard_loads(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.sqlite"),
    })

    client = app.test_client()
    response = client.get("/")

    assert response.status_code == 200
    assert b"SpendScope" in response.data
    assert b"No transactions yet" in response.data


def test_upload_and_export(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.sqlite"),
    })

    client = app.test_client()

    csv_data = b"""date,description,amount
2026-01-01,ACME PAYROLL,2000
2026-01-02,TESCO STORES,-55
"""

    response = client.post(
        "/upload",
        data={"file": (io.BytesIO(csv_data), "transactions.csv")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Imported 2 transactions" in response.data
    assert b"TESCO STORES" in response.data

    export_response = client.get("/export")
    assert export_response.status_code == 200
    assert b"category" in export_response.data
    assert b"Groceries" in export_response.data
