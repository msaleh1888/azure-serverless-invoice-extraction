# src/extraction/normalize_output.py

def get_value(field):
    """
    Azure Document Intelligence REST API returns values using keys like:
    - valueString
    - valueNumber
    - valueDate
    - valueCurrency (returns the numeric 'amount')
    - valueArray
    - valueObject

    This helper extracts the correct type automatically.
    """
    if not field:
        return None

    # Strings
    if "valueString" in field:
        return field["valueString"]

    # Numbers
    if "valueNumber" in field:
        return field["valueNumber"]

    # Dates
    if "valueDate" in field:
        return field["valueDate"]

    # Currency → we return just the numeric amount
    if "valueCurrency" in field:
        currency = field["valueCurrency"]
        # Typically has keys: currencySymbol, amount, currencyCode
        return currency.get("amount")

    # Arrays
    if "valueArray" in field:
        return field["valueArray"]

    # Objects
    if "valueObject" in field:
        return field["valueObject"]

    # If none of the known types exist
    return None


def normalize_invoice(raw_json: dict) -> dict:
    """
    Takes the raw JSON returned by your extract_invoice() function,
    and returns a clean, simple Python dict.
    """

    doc = raw_json["analyzeResult"]["documents"][0]
    fields = doc["fields"]

    # ---- Extract simple scalar fields ----
    invoice_id = get_value(fields.get("InvoiceId"))
    vendor_name = get_value(fields.get("VendorName"))
    vendor_address = get_value(fields.get("VendorAddress"))
    customer_name = get_value(fields.get("CustomerName"))

    invoice_date = get_value(fields.get("InvoiceDate"))
    due_date = get_value(fields.get("DueDate"))

    total_amount = get_value(fields.get("InvoiceTotal"))
    total_tax = get_value(fields.get("TotalTax"))

    # ---- Extract items array ----
    items_raw = get_value(fields.get("Items")) or []  # list of valueObject items

    items = []
    for item in items_raw:
        obj = get_value(item)  # this is the valueObject dict

        if not obj:
            continue

        items.append({
            "description": get_value(obj.get("Description")),
            "quantity": get_value(obj.get("Quantity")),
            "unit_price": get_value(obj.get("UnitPrice")),
            "amount": get_value(obj.get("Amount")),
        })

    # ---- Build final normalized structure ----
    normalized = {
        "invoice_id": invoice_id,
        "invoice_date": invoice_date,
        "due_date": due_date,
        "vendor_name": vendor_name,
        "vendor_address": vendor_address,
        "customer_name": customer_name,
        "total_amount": total_amount,
        "total_tax": total_tax,
        "items": items,
        "confidence": doc.get("confidence")
    }

    return normalized