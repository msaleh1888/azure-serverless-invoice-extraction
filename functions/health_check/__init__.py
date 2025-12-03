import datetime as dt
import json
import logging
import os

import azure.functions as func
import requests

# Keep this in sync with src/extraction/extract_invoice.py
AZURE_API_VERSION = "2023-07-31"

REQUIRED_ENV_VARS = [
    "DOCINT_ENDPOINT",
    "DOCINT_KEY",
]

def check_env_vars() -> dict:
    """
    Verify that required environment variables are present.
    """
    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]

    status = "ok" if not missing else "error"
    details: dict = {}
    if missing:
        details["missing"] = missing

    return {
        "name": "environment",
        "status": status,
        "details": details,
    }

def check_document_intelligence() -> dict:
    """
    Light connectivity check to Azure Document Intelligence.

    Calls the 'info' endpoint, which is cheap and read-only.
    Does NOT send any documents, so it’s safe to run every few minutes.
    """
    endpoint = os.getenv("DOCINT_ENDPOINT")
    key = os.getenv("DOCINT_KEY")

    if not endpoint or not key:
        return {
            "name": "document_intelligence",
            "status": "error",
            "details": "Missing DOCINT_ENDPOINT or DOCINT_KEY",
        }

    base_url = endpoint.rstrip("/")
    url = f"{base_url}/formrecognizer/info?api-version={AZURE_API_VERSION}"

    headers = {
        "Ocp-Apim-Subscription-Key": key,
    }

    try:
        resp = requests.get(url, headers=headers, timeout=5)
    except Exception as exc:  # network / DNS / SSL, etc.
        logging.exception("Document Intelligence health check failed with exception.")
        return {
            "name": "document_intelligence",
            "status": "error",
            "details": {"error": str(exc)},
        }

    if resp.status_code == 200:
        return {
            "name": "document_intelligence",
            "status": "ok",
            "details": {"status_code": 200},
        }

    # Any non-200 means configuration or service problem
    logging.error(
        "Document Intelligence health check returned %s: %s",
        resp.status_code,
        resp.text[:200],  # avoid logging a huge body
    )
    return {
        "name": "document_intelligence",
        "status": "error",
        "details": {
            "status_code": resp.status_code,
            "body_preview": resp.text[:200],
        },
    }

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP GET /api/health

    Returns a JSON payload summarizing the health of external dependencies.
    """
    logging.info("Health check request received.")

    checks = [
        check_env_vars(),
        check_document_intelligence(),
    ]

    overall_ok = all(c["status"] == "ok" for c in checks)
    overall_status = "ok" if overall_ok else "degraded"

    body = {
        "status": overall_status,
        "service": "invoice-extraction-api",
        "timestamp_utc": dt.datetime.utcnow().isoformat() + "Z",
        "version": os.getenv("APP_VERSION", "v0.1.0"),
        "checks": checks,
    }

    return func.HttpResponse(
        body=json.dumps(body, indent=2),
        status_code=200 if overall_ok else 503,
        mimetype="application/json",
    )