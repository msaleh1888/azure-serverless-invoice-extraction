# tests/test_api_fastapi.py

from fastapi.testclient import TestClient

from fastapi_app.main import app
import fastapi_app.main as main
from src.extraction import service

client = TestClient(app)

def test_extract_endpoint_happy_path(monkeypatch):
    """
    Goal:
    - Simulate sending a PDF to /extract using TestClient.
    - Mock process_invoice_bytes() so we don't call Azure.
    - Assert we get back the normalized dict that fake_process returns.
    """

    # 1) Define what we want the endpoint to return
    fake_normalized = {
        "invoice_id": "INV-123",
        "vendor_name": "Contoso Ltd.",
        "total": 1234.56,
        "items": [],
    }

    # 2) Define fake process_invoice_bytes
    def fake_process(pdf_bytes: bytes) -> dict:
        # Check that we received some bytes from the upload
        assert isinstance(pdf_bytes, (bytes, bytearray))
        assert len(pdf_bytes) > 0
        return fake_normalized
    
    # 3) Monkeypatch the real function with our fake one
    monkeypatch.setattr(
        main,
        "process_invoice_bytes",
        fake_process,
        raising=True,
    )

    # 4) Build a fake "file upload" for TestClient
    files = {
        "file": ("invoice.pdf", b"%PDF-1.4 fake content", "application/pdf")
    }

    # 5) Call the endpoint
    response = client.post("/extract", files=files)

    # 6) Assert everything is correct
    assert response.status_code == 200
    assert response.json() == fake_normalized

def test_extract_endpoint_rejects_non_pdf():
    """
    The endpoint should reject uploads with content types
    other than application/pdf or application/octet-stream.
    """

    files = {
        "file": ("notes.txt", b"Hello", "text/plain")
    }

    response = client.post("/extract", files=files)

    # Should return a 400
    assert response.status_code == 400

    body = response.json()
    assert body["detail"] == (
        "Unsupported content type: text/plain. Expected application/pdf."
    )

def test_extract_endpoint_empty_file_returns_400(monkeypatch):
    """
    If the uploaded file is empty, the endpoint should return 400 with
    'Uploaded file is empty.' detail.
    """

    # We don’t need to mock process_invoice_bytes, because we fail before it.
    files = {
        "file": ("empty.pdf", b"", "application/pdf")  # empty content
    }

    response = client.post("/extract", files=files)

    assert response.status_code == 400
    body = response.json()
    assert body["detail"] == "Uploaded file is empty."

def test_extract_endpoint_service_error_returns_502(monkeypatch):
    """
    If process_invoice_bytes raises an exception, the endpoint should
    catch it and return a 502 with the appropriate error message.
    """
    def fake_process(pdf_bytes: bytes):
        raise RuntimeError("Something went wrong in service layer")

    # Patch the function imported in main.py
    monkeypatch.setattr(main, "process_invoice_bytes", fake_process, raising=True)

    files = {
        "file": ("invoice.pdf", b"%PDF-1.4 content", "application/pdf")
    }

    response = client.post("/extract", files=files)

    assert response.status_code == 502
    body = response.json()
    assert "Error processing invoice: Something went wrong in service layer" in body["detail"]

def test_health_check():
    """
    /health should return 200 and a simple JSON status.
    """
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}