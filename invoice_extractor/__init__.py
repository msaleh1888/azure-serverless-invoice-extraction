import logging
import json

import azure.functions as func

# IMPORTANT: import from your main src package
from src.extraction.extract_invoice import extract_invoice
from src.extraction.normalize_output import normalize_invoice

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function HTTP trigger:
    - Accepts a PDF invoice via POST
    - Sends it to Azure Document Intelligence
    - Normalizes the result
    - Returns structured JSON
    """
    logging.info("Invoice Extractor function triggered.")

    try:
        # 1. Basic input validation
        pdf_bytes = req.get_body()

        if not pdf_bytes:
            logging.warning("Request body is empty.")
            return _json_response(
                {"error": "Request body is empty. Please POST a PDF file."},
                status_code=400,
            )

        content_type = req.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower():
            logging.warning(f"Unexpected Content-Type: {content_type}")
            return _json_response(
                {
                    "error": "Unsupported content type. "
                             "Please send a PDF with Content-Type: application/pdf."
                },
                status_code=400,
            )

        # 2. Call Azure Document Intelligence
        logging.info("Sending PDF to Azure Document Intelligence...")
        try:
            raw_result = extract_invoice(pdf_bytes)
        except Exception as e:
            logging.error(f"Error calling Document Intelligence: {e}")
            return _json_response(
                {
                    "error": "Failed to extract invoice using Azure Document Intelligence.",
                    "details": str(e),
                },
                status_code=502,
            )

        # 3. Normalize the result
        logging.info("Normalizing extraction result...")
        try:
            normalized = normalize_invoice(raw_result)
        except Exception as e:
            logging.error(f"Error normalizing invoice result: {e}")
            return _json_response(
                {
                    "error": "Failed to normalize invoice result.",
                    "details": str(e),
                },
                status_code=500,
            )

        # 4. Success response
        logging.info(
            "Invoice extraction completed successfully. "
            f"invoice_id={normalized.get('invoice_id')!r}, "
            f"total_amount={normalized.get('total_amount')!r}"
        )

        return _json_response(normalized, status_code=200)

    except Exception as e:
        # Catch-all safeguard
        logging.exception(f"Unexpected error in invoice_extractor: {e}")
        return _json_response(
            {"error": "Unexpected server error.", "details": str(e)},
            status_code=500,
        )

def _json_response(payload: dict, status_code: int = 200) -> func.HttpResponse:
    """
    Small helper to return JSON responses consistently.
    """
    return func.HttpResponse(
        json.dumps(payload, indent=2),
        status_code=status_code,
        mimetype="application/json",
    )