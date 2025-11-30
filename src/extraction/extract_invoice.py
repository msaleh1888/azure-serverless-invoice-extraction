# src/extraction/extract_invoice.py

import os
import time
import json
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()   # <-- This reads DOCINT_ENDPOINT and DOCINT_KEY

def extract_invoice(pdf_bytes: bytes):
    """
    Sends invoice PDF bytes to Azure Document Intelligence (prebuilt invoice model)
    and returns raw JSON result.
    """

    endpoint = os.getenv("DOCINT_ENDPOINT")
    key = os.getenv("DOCINT_KEY")

    if not endpoint or not key:
        raise ValueError("Missing DOCINT_ENDPOINT or DOCINT_KEY environment variables.")
    
    # 1. Send the PDF to Document Intelligence
    url = f"{endpoint}/formrecognizer/documentModels/prebuilt-invoice:analyze?api-version=2023-07-31"

    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/pdf"
    }

    print("[INFO] Sending invoice to Azure Document Intelligence...")
    response = requests.post(url, headers=headers, data=pdf_bytes)

    if response.status_code != 202:
        raise RuntimeError(f"Error: {response.status_code}, {response.text}")

    # 2. Get the operation location URL
    operation_url = response.headers["Operation-Location"]

    # 3. Poll for results
    print("[INFO] Waiting for extraction result...")
    while True:
        result_response = requests.get(operation_url, headers={"Ocp-Apim-Subscription-Key": key})
        result_json = result_response.json()

        if "status" in result_json and result_json["status"] == "succeeded":
            print("[INFO] Extraction succeeded.")
            return result_json
        
        if result_json.get("status") == "failed":
            raise RuntimeError("Document Intelligence failed to process the document.")
        
        time.sleep(1)