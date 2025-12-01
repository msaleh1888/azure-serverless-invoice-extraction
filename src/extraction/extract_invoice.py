# src/extraction/extract_invoice.py

import os
import time
import json
import logging
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()   # <-- This reads DOCINT_ENDPOINT and DOCINT_KEY
logger = logging.getLogger(__name__)

AZURE_API_VERSION = "2023-07-31"
MAX_WAIT_SECONDS = 60         # maximum total polling time
POLL_INTERVAL = 1             # seconds between polls

def extract_invoice(pdf_bytes: bytes):
    """
    Sends invoice PDF bytes to Azure Document Intelligence (prebuilt invoice model)
    and returns raw JSON result.
    Now includes:
    - Timeout
    - Structured logging
    - Better error messages
    """

    endpoint = os.getenv("DOCINT_ENDPOINT")
    key = os.getenv("DOCINT_KEY")

    if not endpoint or not key:
        raise ValueError("Missing DOCINT_ENDPOINT or DOCINT_KEY environment variables.")
    
    # 1. Send the PDF to Document Intelligence
    url = (
        f"{endpoint}/formrecognizer/documentModels/prebuilt-invoice:analyze"
        f"?api-version={AZURE_API_VERSION}"
    )

    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/pdf"
    }

    logger.info("Sending invoice to Azure DI...")

    response = requests.post(url, headers=headers, data=pdf_bytes)

    if response.status_code != 202:
        logger.error("Azure DI did not accept the document: %s", response.text)
        raise RuntimeError(
            f"Azure DI error: {response.status_code}. Expected 202. Body: {response.text}"
        )

    # 2. Get the operation location URL
    operation_url = response.headers["Operation-Location"]
    if not operation_url:
        raise RuntimeError("Azure DI response missing Operation-Location header.")

    # 3. Poll for results
    logger.info("Polling Azure DI for result...")

    start_time = time.time()

    while True:
        elapsed = time.time() - start_time

        if elapsed > MAX_WAIT_SECONDS:
            logger.error("Azure DI polling timed out after %s seconds", MAX_WAIT_SECONDS)
            raise TimeoutError(
                f"Azure Document Intelligence timeout ({MAX_WAIT_SECONDS}s)"
            )

        poll_headers = {"Ocp-Apim-Subscription-Key": key}
        poll_resp = requests.get(operation_url, headers=poll_headers)

        # Defensive: Azure sometimes returns empty body during warm-up
        try:
            result_json = poll_resp.json()
        except json.JSONDecodeError:
            logger.warning("Azure DI returned invalid JSON during polling.")
            time.sleep(POLL_INTERVAL)
            continue

        status = result_json.get("status")

        if status == "succeeded":
            duration = int((time.time() - start_time) * 1000)
            logger.info("Azure DI extraction succeeded in %sms", duration)
            return result_json

        if status == "failed":
            logger.error("Azure DI reported failure: %s", result_json)
            raise RuntimeError("Azure DI failed to process the document.")

        # Unknown states: notStarted, running
        logger.debug("Azure DI status: %s (elapsed=%s)", status, int(elapsed))
        time.sleep(POLL_INTERVAL)