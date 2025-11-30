# System Design — Azure Invoice Extraction Service

This document describes the system design of the **Azure Invoice Extraction Service**, focusing on architecture, components, data flow, and design decisions.

---

## 1. Goals & Requirements

### 1.1 Functional Requirements

- Accept a **PDF invoice** via an HTTP endpoint.
- Call **Azure Document Intelligence (prebuilt-invoice)** to extract invoice fields.
- Normalize the raw extraction JSON into a **stable, well-defined schema**.
- Return the normalized invoice data as JSON to the client.
- Handle invalid inputs and upstream failures with clear error messages.

### 1.2 Non-Functional Requirements

- **Reliability**: Handle transient failures from Azure DI gracefully.
- **Maintainability**: Clean separation of concerns (trigger, extraction, normalization).
- **Portability**: Run locally via Docker; deployable to Azure Functions in the cloud.
- **Performance**: Reasonable latency for single invoice extraction (seconds, not minutes).

---

## 2. High-Level Architecture

At a high level, the system is a **serverless HTTP API** that acts as a thin wrapper around Azure Document Intelligence, adding normalization and error handling.

- **Client**: Any HTTP client (script, backend service, UI).
- **Azure Function (HTTP trigger)**: Entry point; validates input and orchestrates the flow.
- **Extraction Layer (`extract_invoice.py`)**: Calls Azure Document Intelligence REST API.
- **Normalization Layer (`normalize_output.py`)**: Maps document intelligence output into a consistent schema.
- **Configuration**: Environment variables (local.settings.json / Azure app settings).
- **Dependencies**: Python packages installed into `.python_packages/lib/site-packages`.

See `azure/architecture.md` for diagrams.

---

## 3. Components

### 3.1 HTTP Trigger Function

**File:** `invoice_extractor/__init__.py`

**Responsibilities:**

- Receive HTTP `POST` requests on `/api/invoice-extractor`.
- Validate request:
  - Non-empty body.
  - `Content-Type` includes `pdf`.
- Call `extract_invoice(pdf_bytes)` to obtain raw extraction.
- Call `normalize_invoice(raw_json)` to convert to final shape.
- Handle and log errors:
  - Validation errors → `400`
  - Azure DI errors → `502`
  - Internal/unexpected errors → `500`
- Return JSON responses using a small helper (`_json_response`).

This function is intentionally kept thin and focuses on **orchestration and HTTP concerns**, not business logic.

---

### 3.2 Extraction Layer

**File:** `src/extraction/extract_invoice.py`

**Responsibilities:**

- Read configuration values:
  - `DOCINT_ENDPOINT`
  - `DOCINT_KEY`
- Build the REST endpoint for the **prebuilt invoice model**:
  - `POST {endpoint}/formrecognizer/documentModels/prebuilt-invoice:analyze?api-version=2023-07-31`
- Send PDF bytes in the body with the appropriate headers.
- Receive the initial `202 Accepted` response and extract `Operation-Location`.
- Poll the operation URL until:
  - `status == "succeeded"` → return result JSON.
  - `status == "failed"` → raise a runtime error.
- Handle non-202 HTTP codes from the initial call as immediate failures.

This layer encapsulates all **Azure DI-specific logic** so it can be swapped or extended without changing the trigger or normalization code.

---

### 3.3 Normalization Layer

**File:** `src/extraction/normalize_output.py`

**Responsibilities:**

- Accept the raw JSON returned by Azure Document Intelligence.
- Extract relevant fields, for example:
  - `InvoiceId`
  - `InvoiceDate`
  - `DueDate`
  - `VendorName`
  - `CustomerName`
  - `InvoiceTotal`
  - `TotalTax`
  - `Items` (line items)
- Handle different value types (`valueString`, `valueNumber`, `valueDate`, `valueCurrency`, arrays, objects).
- Normalize line items into a list of dictionaries:

  ```json
  {
    "description": "...",
    "quantity": 2,
    "unit_price": 30.0,
    "amount": 60.0
  }
  ```

- Provide a **single, predictable JSON schema** regardless of supplier invoice format.
- Compute and/or forward confidence scores where available.

This layer isolates the **mapping logic** between Azure DI’s output format and the API’s public contract.

---

### 3.4 Configuration & Secrets

**Files:**

- `local.settings.json` (local use, not committed)
- `local.settings.example.json` (template for others)
- `.env` (optional, used by local scripts)
- Environment variables (Azure Function App configuration)

**Design Choices:**

- Secrets such as `DOCINT_ENDPOINT` and `DOCINT_KEY` are never hard-coded.
- Local development uses `local.settings.json` populated with values from Azure Portal.
- In the cloud, keys are configured as **Application settings** on the Function App.

---

### 3.5 Dependencies

**File:** `requirements.txt`

```text
azure-functions
requests
python-dotenv
```

- `requests`: used for calling the Azure Document Intelligence REST API.
- `python-dotenv`: used for local scripts that load `.env`; Functions rely on `local.settings.json`.
- Dependencies for the Function App are installed to:

```bash
.python_packages/lib/site-packages
```

This pattern is compatible with the Azure Functions Python runtime.

---

## 4. Data Model

### 4.1 Input

- Binary PDF content.
- No other structured input is required.

### 4.2 Output Schema (Normalized)

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
    }
  ],
  "confidence": 1
}
```

The normalization layer acts as the **single source of truth** for this schema.

---

## 5. Request Lifecycle (Sequence)

1. **Client sends HTTP POST** with `Content-Type: application/pdf` and PDF body.
2. **Azure Function HTTP trigger** is invoked:
   - Validates input.
3. **Extraction Layer** (`extract_invoice`) is called:
   - Sends the PDF to Azure DI.
   - Polls until extraction completes.
   - Returns raw JSON.
4. **Normalization Layer** (`normalize_invoice`) processes the raw JSON:
   - Extracts and reshapes fields.
5. **HTTP Response**:
   - On success → `200 OK` with normalized JSON.
   - On validation errors → `400` with JSON error.
   - On Azure DI failure → `502` with JSON error.
   - On internal error → `500` with JSON error.

---

## 6. Error Handling Strategy

### 6.1 Input Validation Errors

- Empty request body
- Missing or incorrect `Content-Type`

Result:

- **HTTP 400**
- Clear error message in JSON.

### 6.2 Upstream Service Errors (Azure DI)

- Invalid endpoint or key
- Service unavailable
- Non-success status from Azure DI

Result:

- **HTTP 502**
- Error message and underlying details (where safe).

### 6.3 Internal Errors

- Unexpected exceptions in extraction or normalization.

Result:

- **HTTP 500**
- Generic error message plus exception details for debugging.

---

## 7. Non-Functional Considerations

### 7.1 Scalability

- In the cloud, Azure Functions scale automatically based on incoming load.
- Each function invocation independently calls Azure DI, which also scales horizontally.
- For high volume, batch processing or queue-based patterns could be added.

### 7.2 Performance

- Main latency driver: Azure DI processing time.
- Optimization options:
  - Reduce polling interval or use long polling/backoff strategies.
  - Parallelize multiple invoice requests client-side.

### 7.3 Security

- Secrets stored in Azure Application Settings / Key Vault (if extended).
- HTTPS enforced in production (via Function App configuration).
- Locally, sensitive files (`local.settings.json`, `.env`) are git-ignored.

### 7.4 Observability

- Uses `logging` in the Azure Function for:
  - Start/end of request
  - Validation failures
  - Azure DI errors
  - Normalization errors
- Can be extended using:
  - Azure Application Insights (telemetry, distributed tracing).

---

## 8. Design Trade-offs

- **Using REST instead of SDK**:
  - Simpler, explicit control over requests.
  - No dependency on Azure-specific Python SDK versions.
- **Single endpoint, single invoice**:
  - Easier to reason about and test.
  - For bulk processing, a batch endpoint or queue-triggered Function could be added later.
- **Serverless over traditional API server**:
  - No infrastructure management.
  - Ideal for workloads triggered by events or uploads.
  - Cold start overhead acceptable for this use case.

---

## 9. Possible Future Enhancements

- Batch processing support (multiple invoices per request or via queue/Blob triggers).
- Integration with storage (save raw PDF + extracted JSON to Azure Blob Storage).
- Authentication/authorization for the HTTP API.
- Multi-language invoice support and localization of currency/number formats.
- Web UI for interactive upload and review.
- CI/CD pipeline for automated deployment to Azure.

---

This system design balances **simplicity**, **clarity**, and **cloud-native best practices**, while leaving room for future expansion into a fully productized invoice processing service.
