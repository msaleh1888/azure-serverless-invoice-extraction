# API Reference — Azure Invoice Extraction Service

This document describes the HTTP API exposed by the **Azure Invoice Extraction Service**.

---

## 1. Base URL

### Local (Docker)

```text
http://localhost:7071
```

### Cloud (Azure Function App, when deployed)

```text
https://<your-func-app>.azurewebsites.net
```

Replace `<your-func-app>` with the name of your Function App.

---

## 2. Endpoint Overview

### `POST /api/invoice-extractor`

Extracts structured invoice data from a PDF file and returns normalized JSON.

- **Method:** `POST`
- **Path:** `/api/invoice-extractor`
- **Auth:**  
  - Local: `anonymous` (no key required)  
  - Cloud: can be configured as `function` or `anonymous` depending on deployment
- **Content-Type:** `application/pdf`
- **Body:** binary PDF file contents

---

## 3. Request Specification

### Headers

```http
Content-Type: application/pdf
```

### Body

- Raw binary content of a **single invoice PDF**.
- Multi-page invoices are supported by Azure Document Intelligence.

#### Example (PowerShell)

```powershell
curl.exe -X POST `
  -H "Content-Type: application/pdf" `
  --data-binary "@samples/example_invoice_1.pdf" `
  http://localhost:7071/api/invoice-extractor
```

#### Example (Git Bash / Linux)

```bash
curl -X POST   -H "Content-Type: application/pdf"   --data-binary @samples/example_invoice_1.pdf   http://localhost:7071/api/invoice-extractor
```

---

## 4. Response Specification

### 4.1 Success Response

- **Status:** `200 OK`
- **Content-Type:** `application/json`

#### Example

```json
{
  "invoice_id": "INV-100",
  "invoice_date": "2019-11-15",
  "due_date": "2019-12-15",
  "vendor_name": "CONTOSO LTD.",
  "vendor_address": null,
  "customer_name": "MICROSOFT CORPORATION",
  "total_amount": 110.0,
  "total_tax": 10.0,
  "items": [
    {
      "description": "Consulting Services",
      "quantity": 2,
      "unit_price": 30.0,
      "amount": 60.0
    },
    {
      "description": "Document Fee",
      "quantity": 3,
      "unit_price": 10.0,
      "amount": 30.0
    },
    {
      "description": "Printing Fee",
      "quantity": 10,
      "unit_price": 1.0,
      "amount": 10.0
    }
  ],
  "confidence": 1
}
```

---

## 5. Error Responses

### 5.1 `400 Bad Request` — Empty or Invalid Input

#### Case: Empty Body

```json
{
  "error": "Request body is empty. Please POST a PDF file."
}
```

#### Case: Wrong Content-Type

```json
{
  "error": "Unsupported content type. Please send a PDF with Content-Type: application/pdf."
}
```

---

### 5.2 `502 Bad Gateway` — Azure Document Intelligence Failure

Occurs if:
- Wrong endpoint/key
- Azure DI service issue
- Network failure

```json
{
  "error": "Failed to extract invoice using Azure Document Intelligence.",
  "details": "<underlying error message>"
}
```

---

### 5.3 `500 Internal Server Error` — Unexpected Errors

Catch-all for unhandled internal errors.

```json
{
  "error": "Unexpected server error.",
  "details": "<exception message>"
}
```

---

## 6. Usage Scenarios

- Back-office automation  
- ERP/accounting integration (SAP, QuickBooks, Odoo, etc.)  
- Data pipelines (store invoice data in a database)  
- Reporting & analytics  
- SaaS invoice processing services  

---

## 7. Versioning

- **Current API version:** `v1`  
- Future changes may introduce:
  - URL versioning (`/api/v2/invoice-extractor`)
  - Header-based versioning  

