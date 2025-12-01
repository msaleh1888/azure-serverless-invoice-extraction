import logging

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from src.extraction.service import process_invoice_bytes

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)

app = FastAPI(
    title="Invoice Extraction API (FastAPI + Azure Document Intelligence)",
    description="Upload a PDF invoice and get normalized JSON back.",
    version="1.0.0",
)

@app.get("/health")
def health_check():
    """
    Simple health endpoint so we can check the service is running.
    """
    return {"status": "ok"}

@app.post("/extract")
async def extract_invoice_endpoint(file: UploadFile = File(...)):
    """
    Accepts a PDF file upload, sends it to Azure Document Intelligence,
    normalizes the result, and returns JSON.
    """
    # 1) HTTP-specific validation
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported content type: {file.content_type}. Expected application/pdf.",
        )
    
    # 2) Read file bytes
    try:
        pdf_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}") from e

    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    
    # 3) Call shared service logic
    try:
        normalized = process_invoice_bytes(pdf_bytes)
    except Exception as e:
        # In a more advanced design, we might distinguish error types
        # For now, treat them as upstream/processing errors.
        raise HTTPException(
            status_code=502,
            detail=f"Error processing invoice: {e}",
        ) from e

    # 4) Return normalized JSON
    return JSONResponse(content=normalized)