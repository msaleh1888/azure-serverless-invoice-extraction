# test_extract_local.py

from src.extraction.extract_invoice import extract_invoice
from src.extraction.normalize_output import normalize_invoice
import json

with open("samples/example_invoice_1.pdf", "rb") as f:
    pdf_bytes = f.read()

result = extract_invoice(pdf_bytes)
normalized = normalize_invoice(result)

# Save sample output
with open("samples/normalized_output_example.json", "w") as f:
    json.dump(normalized, f, indent=2)

print("Saved normalized_output_example.json")