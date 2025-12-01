# tests/test_service.py

import json
from pathlib import Path

import pytest

from src.extraction import service

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def test_process_invoice_bytes_happy_path(monkeypatch):
    """
    Goal of this test:
    - We pass some fake PDF bytes to process_invoice_bytes().
    - Inside, it should call extract_invoice() with those bytes.
    - extract_invoice() (mocked) will return a raw JSON we loaded from disk.
    - Then process_invoice_bytes should normalize it and return the final dict.
    - We assert the final dict matches our expected normalized JSON.
    """
    # 1) Load sample raw + expected normalized JSON from your samples folder.
    root = Path(__file__).resolve().parents[1]
    raw_path = root / "samples" / "raw_output_example.json"
    normalized_path = root / "samples" / "normalized_output_example.json"

    with raw_path.open("r", encoding="utf-8") as f:
        raw_sample = json.load(f)

    with normalized_path.open("r", encoding="utf-8") as f:
        expected_normalized = json.load(f)

    # 2) Define a fake extract_invoice function to replace the real Azure call.
    def fake_extract_invoice(pdf_bytes: bytes):
        # This assert checks that process_invoice_bytes forwarded our bytes correctly.
        assert pdf_bytes == b"fake-pdf-data"
        # Instead of calling Azure, just return our raw sample JSON.
        return raw_sample
    
    # 3) Monkeypatch service.extract_invoice so inside service.process_invoice_bytes,
    #    the name "extract_invoice" actually refers to fake_extract_invoice.
    monkeypatch.setattr(
        service, "extract_invoice", fake_extract_invoice, raising=True
    )

    # 4) Call the function under test with some fake bytes.
    result = service.process_invoice_bytes(b"fake-pdf-data")

    # 5) The result should equal the normalized JSON we expect.
    assert result == expected_normalized

def test_process_invoice_bytes_empty_raises():
    """
    Empty PDF bytes should cause process_invoice_bytes to raise ValueError.
    """
    with pytest.raises(ValueError):
        service.process_invoice_bytes(b"")