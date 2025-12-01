# tests/test_extract_invoice.py

import pytest

from src.extraction import extract_invoice as ei

class FakePostResponse:
    """
    Fake object that looks enough like requests.Response for the POST call.
    We only implement the attributes extract_invoice() actually uses:
    - status_code
    - headers
    - text
    """
    def __init__(self, status_code=202, headers=None, text=""):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text

class FakeGetResponse:
    """
    Fake object that looks enough like requests.Response for the GET call.
    We only implement .json(), since that's what extract_invoice() uses.
    """
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

def test_extract_invoice_success(monkeypatch):
    """
    Scenario:
    - Env vars are set.
    - POST returns 202 + Operation-Location header.
    - GET to Operation-Location returns status='succeeded' with analyzeResult.
    Expectation:
    - extract_invoice() returns that JSON dict.
    """

    # 1) Set fake environment variables
    # DOCINT_ENDPOINT is the base URL your code uses.
    monkeypatch.setenv(
        "DOCINT_ENDPOINT",
        "https://fake-resource.cognitiveservices.azure.com",
    )
    monkeypatch.setenv("DOCINT_KEY", "fake-key")

    # 2) Define fake POST to simulate Azure accepting the document
    def fake_post(url, headers, data):
        # We can assert basic correctness of the request:
        assert url.startswith("https://fake-resource.cognitiveservices.azure.com")
        assert "prebuilt-invoice:analyze" in url

        # Header checks
        assert headers["Ocp-Apim-Subscription-Key"] == "fake-key"
        assert headers["Content-Type"] == "application/pdf"

        # Body check
        assert data == b"dummy-pdf"

        # Simulate Azure returning 202 + operation URL
        return FakePostResponse(
            status_code=202,
            headers={"Operation-Location": "https://fake-op-url"},
            text="",
        )
    
    # 3) Define fake GET to simulate polling reaching 'succeeded'
    def fake_get(url, headers):
        # Ensure the correct URL and headers are used
        assert url == "https://fake-op-url"
        assert headers["Ocp-Apim-Subscription-Key"] == "fake-key"

        # This is what Azure would return on success
        payload = {
            "status": "succeeded",
            "analyzeResult": {
                "documents": [],
            },
        }
        return FakeGetResponse(payload)
    
    # 4) Apply monkeypatches so extract_invoice() uses our fakes
    monkeypatch.setattr(ei.requests, "post", fake_post, raising=True)
    monkeypatch.setattr(ei.requests, "get", fake_get, raising=True)

    # 5) Call the function under test with fake PDF bytes
    result = ei.extract_invoice(b"dummy-pdf")

    # 6) Validate the result
    assert result["status"] == "succeeded"
    assert "analyzeResult" in result
    assert "documents" in result["analyzeResult"]

def test_extract_invoice_non_202_raises(monkeypatch):
    """
    Scenario:
    - POST returns a non-202 status code (e.g. 400 Bad Request).
    Expectation:
    - extract_invoice() raises RuntimeError.
    """

    monkeypatch.setenv(
        "DOCINT_ENDPOINT",
        "https://fake-resource.cognitiveservices.azure.com",
    )
    monkeypatch.setenv("DOCINT_KEY", "fake-key")

    def fake_post(url, headers, data):
        return FakePostResponse(
            status_code=400,
            headers={},
            text="Bad request",
        )

    monkeypatch.setattr(ei.requests, "post", fake_post, raising=True)

    with pytest.raises(RuntimeError) as excinfo:
        ei.extract_invoice(b"dummy-pdf")

    msg = str(excinfo.value)
    assert "Azure DI error: 400" in msg
    assert "Bad request" in msg

def test_extract_invoice_timeout(monkeypatch):
    """
    Scenario:
    - Azure keeps returning status='running' (never finishes).
    - We reduce MAX_WAIT_SECONDS so we don't wait a real minute.
    - We fake time.time() so elapsed > MAX_WAIT_SECONDS after a few loops.
    Expectation:
    - extract_invoice() raises TimeoutError.
    """
    # 1) Set fake env vars so the function doesn't fail on config
    monkeypatch.setenv(
        "DOCINT_ENDPOINT",
        "https://fake-resource.cognitiveservices.azure.com",
    )
    monkeypatch.setenv("DOCINT_KEY", "fake-key")

    # 2) Shrink the timeout to 1 second for the test
    monkeypatch.setattr(ei, "MAX_WAIT_SECONDS", 1, raising=True)
    
    # 3) Fake POST: Azure accepts the document and gives us an operation URL
    def fake_post(url, headers, data):
        return FakePostResponse(
            status_code=202,
            headers={"Operation-Location": "https://fake-op-url"},
            text="",
        )

    # 4) Fake GET: Azure always says "running" (never "succeeded" or "failed")
    def fake_get(url, headers):
        payload = {
            "status": "running"
        }
        return FakeGetResponse(payload)
    
    # 5) Fake time: simulate time moving from 0 → 2 seconds
    class FakeTime:
        def __init__(self):
            self.calls = 0

        def time(self):
            self.calls += 1
            if self.calls == 1:
                return 0.0         # start_time
            elif self.calls == 2:
                return 0.5         # elapsed = 0.5 (no timeout yet)
            else:
                return 2.0         # elapsed = 2.0 > 1 → timeout
    
    fake_time = FakeTime()

    # Patch the time module used inside extract_invoice.py
    monkeypatch.setattr(ei.time, "time", fake_time.time, raising=True)

    # 6) Make sleep a no-op so the test is instant
    monkeypatch.setattr(ei.time, "sleep", lambda s: None, raising=True)

    # 7) Apply HTTP monkeypatches
    monkeypatch.setattr(ei.requests, "post", fake_post, raising=True)
    monkeypatch.setattr(ei.requests, "get", fake_get, raising=True)

    # 8) Call the function and expect a TimeoutError
    with pytest.raises(TimeoutError) as excinfo:
        ei.extract_invoice(b"dummy-pdf")

    msg = str(excinfo.value)
    assert "timeout" in msg.lower()

def test_extract_invoice_failed_status_raises(monkeypatch):
    """
    Scenario:
    - POST returns 202 + operation URL (normal).
    - GET to Operation-Location returns status='failed'.
    Expectation:
    - extract_invoice() raises RuntimeError indicating failure.
    """

    monkeypatch.setenv(
        "DOCINT_ENDPOINT",
        "https://fake-resource.cognitiveservices.azure.com",
    )
    monkeypatch.setenv("DOCINT_KEY", "fake-key")

    # Fake POST: normal acceptance
    def fake_post(url, headers, data):
        return FakePostResponse(
            status_code=202,
            headers={"Operation-Location": "https://fake-op-url"},
            text="",
        )

    # Fake GET: Azure says "failed"
    def fake_get(url, headers):
        payload = {
            "status": "failed",
            "error": {"code": "SomeError", "message": "Processing failed"},
        }
        return FakeGetResponse(payload)

    monkeypatch.setattr(ei.requests, "post", fake_post, raising=True)
    monkeypatch.setattr(ei.requests, "get", fake_get, raising=True)

    with pytest.raises(RuntimeError) as excinfo:
        ei.extract_invoice(b"dummy-pdf")

    msg = str(excinfo.value)
    # Adjust string check to how you implemented the error message
    assert "failed to process" in msg.lower() or "failed" in msg.lower()