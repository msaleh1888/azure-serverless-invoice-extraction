# API Reference — Azure Invoice Extraction Service

This document describes the HTTP API exposed by the **Azure Invoice Extraction Service**.

The service consists of:

- An **Azure Functions** app with:
  - `invoice_extractor` — POST endpoint that accepts a PDF invoice and returns normalized JSON.
  - `health_check` — lightweight GET endpoint used by uptime tests and deployment pipelines.
- Supporting Python modules in `src/extraction/` that encapsulate the business logic.

---

## 1. Base URLs

### Local development (Azure Functions Core Tools)

```text
http://localhost:7071
```

When running locally with `func start`, Azure Functions automatically prefixes all routes with `/api`.

### Cloud (Azure Function App)

```text
https://msaleh-invoice-extractor-cfcafygge9heg7hc.westeurope-01.azurewebsites.net
```

In the rest of this document we refer to this as `{BASE_URL}`.

> **Note**  
> The host name will be different if you fork this repo and deploy your own Function App. Replace it accordingly.

---

## 2. Endpoints overview

| Endpoint                       | Method | Description                                                  |
| ----------------------------- | ------ | ------------------------------------------------------------ |
| `/api/health`                 | GET    | Lightweight health probe used by uptime tests and CI/CD.     |
| `/api/invoice-extractor`      | POST   | Main API. Accepts a PDF invoice and returns normalized JSON. |

All endpoints are currently **anonymous** (no authentication) and are intended for demo / portfolio use. For production, you should enable authentication and authorization.

---

## 3. Health check — `GET /api/health`

### Purpose

- Verify that the Function App is running.
- Expose the currently deployed application version.
- Provide a simple JSON payload that can be used by:
  - **Application Insights availability tests**
  - **GitHub Actions post‑deploy smoke tests**
  - External uptime monitors

### Request

```http
GET {BASE_URL}/api/health
```

No body is required.

### Successful response

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{
  "status": "ok",
  "source": "azure-function-health-check",
  "app_version": "v0.4.0",
  "timestamp_utc": "2025-12-03T19:10:21Z"
}
```

Fields:

- `status`: `"ok"` when the function is healthy.
- `source`: Identifier of this health probe.
- `app_version`: Value of the `APP_VERSION` environment variable (set from the latest Git tag).
- `timestamp_utc`: Time when the health check response was generated.

### Error responses

The health check is intentionally simple. Typical failures you would see in clients / monitors:

- `5xx` — Function App is down or throwing unhandled exceptions.
- Timeout — Function App is not responding within the configured SLA.

---

## 4. Invoice extraction — `POST /api/invoice-extractor`

### Purpose

Accept a **single PDF invoice** and return a clean, normalized JSON representation based on Azure Document Intelligence's **prebuilt invoice** model.

### Request

```http
POST {BASE_URL}/api/invoice-extractor
Content-Type: application/pdf
```

#### Body

- Raw binary content of a **single invoice PDF**.
- Multi-page invoices are supported by Azure Document Intelligence.
- Maximum file size is constrained by your Function App plan and HTTP limits (not enforced by code).

#### Example (curl — local)

```bash
curl -i   -H "Content-Type: application/pdf"   --data-binary "@samples/example_invoice_1.pdf"   "http://localhost:7071/api/invoice-extractor"
```

#### Example (curl — cloud)

```bash
curl -i   -H "Content-Type: application/pdf"   --data-binary "@samples/example_invoice_1.pdf"   "https://msaleh-invoice-extractor-cfcafygge9heg7hc.westeurope-01.azurewebsites.net/api/invoice-extractor"
```

### Successful response

On success the function:

1. Reads the raw PDF bytes from the request.
2. Calls `process_invoice_bytes(pdf_bytes)` in `src/extraction/service.py`, which:
   - Sends the PDF to **Azure Document Intelligence** (`extract_invoice(...)`).
   - Normalizes the raw result with `normalize_invoice(...)`.
3. Returns the normalized JSON with HTTP **200 OK**.

#### Status

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

#### Body (example)

The exact shape depends on the invoice, but the normalized schema is:

```jsonc
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
  "confidence": 1.0
}
```

Field semantics:

- `invoice_id` — Invoice number, if recognized.
- `invoice_date` — ISO‑8601 invoice date.
- `due_date` — ISO‑8601 due date (if available).
- `vendor_name` / `vendor_address` — Supplier information.
- `customer_name` — Buyer name.
- `total_amount` — Grand total including tax.
- `total_tax` — Total tax amount (if parsed).
- `items[]` — Line items:
  - `description` — Item / service description.
  - `quantity` — Numeric quantity.
  - `unit_price` — Unit price.
  - `amount` — Line total.
- `confidence` — Internal confidence score (0–1) derived from Azure Document Intelligence.

---

## 5. Error handling

The Azure Function uses a small helper (`_json_response`) to ensure that **all responses are JSON**, even on error.

### Common HTTP status codes

| Status | When it happens                                                                 |
| ------ | ------------------------------------------------------------------------------- |
| `200`  | Invoice parsed successfully.                                                    |
| `400`  | Bad request (e.g. empty body, invalid PDF, or validation error).               |
| `405`  | Wrong HTTP method (anything other than `POST` for `/api/invoice-extractor`).   |
| `415`  | Unsupported media type (e.g. missing or non‑PDF `Content-Type`).               |
| `500`  | Unexpected server error (uncaught exception).                                   |
| `502`/`503` | Downstream issue calling Azure Document Intelligence.                     |

> The precise mapping depends on the exception raised inside `extract_invoice(...)` and `normalize_invoice(...)`. Those internals are intentionally hidden behind `process_invoice_bytes(...)`.

### Error payload format

On error the response body has a consistent structure:

```jsonc
{
  "error": "Human readable summary of the problem.",
  "details": "Optional, more technical description for logs / debugging."
}
```

Examples:

```json
{
  "error": "Empty request body. Please POST a PDF file.",
  "details": "Received 0 bytes in request body."
}
```

```json
{
  "error": "Unexpected server error.",
  "details": "Traceback or message from the underlying exception."
}
```

---

## 6. CI / CD & automated health checks

Two GitHub Actions workflows support the API:

1. **`ci.yml`** — runs on every push and pull request:
   - Sets up Python.
   - Installs dependencies.
   - Runs tests with coverage (`pytest --cov=src --cov=fastapi_app`).
   - Compiles Python modules (`python -m compileall`) as a basic syntax check.

2. **`deploy-azure-function.yml`** — runs on version tags (e.g. `v0.4.0`):
   - Builds the Azure Functions app from the `functions/` folder.
   - Deploys using `azure/functions-action@v1` and a publish profile.
   - Sets the `APP_VERSION` setting based on the Git tag.
   - Performs a **post‑deploy health check** by calling `{BASE_URL}/api/health`.  
     The deployment is marked as failed if the health check does not return HTTP 200.

These workflows make the invoice extraction API:

- **Repeatable** — deployments are tag‑driven.
- **Observable** — health checks run both from GitHub Actions and Application Insights.
- **Safe to evolve** — tests and syntax checks run before every merge.

---

## 7. Using this API in other systems

Typical integration patterns:

- Call `/api/invoice-extractor` from:
  - Python scripts (e.g. ETL jobs, Airflow tasks).
  - Backend services (Django, .NET, Node.js, etc.).
  - Low‑code tools (Power Automate, Logic Apps, Zapier via Webhooks).
- Store the normalized JSON in:
  - SQL / NoSQL databases.
  - Data lakes or blob storage.
- Feed the extracted invoices into:
  - ERP / accounting systems.
  - Analytics dashboards.
  - Automated approval workflows.

This API reference is kept in sync with the current implementation of the **Azure Invoice Extraction Service**. If you change the schema or endpoints, update this document accordingly.
