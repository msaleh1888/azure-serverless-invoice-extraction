from src.extraction.extract_invoice import extract_invoice
from src.extraction.normalize_output import normalize_invoice

def process_invoice_bytes(pdf_bytes: bytes) -> dict:
    """
    Core business logic:
    - Takes raw PDF bytes
    - Calls Azure Document Intelligence
    - Normalizes the result
    - Returns the normalized JSON dict

    This function does NOT know anything about HTTP, status codes,
    request headers, or frameworks.
    """
    if not pdf_bytes:
        raise ValueError("PDF bytes are empty.")

    # 1) Call Azure Document Intelligence
    raw_result = extract_invoice(pdf_bytes)

    # 2) Normalize
    normalized = normalize_invoice(raw_result)

    return normalized