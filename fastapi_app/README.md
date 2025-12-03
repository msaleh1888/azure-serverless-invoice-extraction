# FastAPI Application — Azure Invoice Extraction Service

In addition to the Azure Functions implementation, this repository includes an **optional FastAPI app** under `fastapi_app/`.

The FastAPI app exposes a similar HTTP interface for local development, experimentation, or alternative hosting (e.g. Docker, App Service, Kubernetes). It reuses the same core extraction service in `src/extraction`.

---

## 1. Purpose

- Provide a non-serverless, always-on HTTP API using FastAPI.
- Reuse the **same business logic** as the Azure Functions implementation:
  - `service.process_invoice_bytes(...)`
  - `extract_invoice.py`
  - `normalize_output.py`
- Make it easy to:
  - Debug the extraction logic locally.
  - Integrate with tools that assume a traditional web server (e.g. Docker-based deployments).

---

## 2. Environment Variables

The FastAPI app reads the same core configuration values as the Functions app.

For local development, you can create a `.env` file based on the provided `.env.example`:

```bash
cp .env.example .env
```

Then set:

- `DOCINT_ENDPOINT` — Azure Document Intelligence endpoint, e.g.:  
  `https://<your-docint-resource>.cognitiveservices.azure.com/`
- `DOCINT_KEY` — API key for Document Intelligence.
- `APP_VERSION` — Optional version string (useful for logging / health responses).

FastAPI will typically load these via `python-dotenv` (see `fastapi_app/main.py` for details).

---

## 3. Running FastAPI Locally

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r functions/requirements.txt
# and any extra dependencies for FastAPI if needed (e.g. fastapi, uvicorn)
```

Then start the app (example command, adjust to match `fastapi_app/main.py`):

```bash
uvicorn fastapi_app.main:app --reload --port 8000
```

You should see output similar to:

```text
Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

---

## 4. FastAPI Endpoints (Typical Setup)

Exact routes are defined in `fastapi_app/main.py`. The typical pattern is:

- `POST /api/invoice-extractor`
  - Accepts `Content-Type: application/pdf`
  - Reads the request body as bytes
  - Calls `process_invoice_bytes(pdf_bytes)`
  - Returns normalized JSON

- `GET /api/health`
  - Optional health endpoint mirroring the Azure Functions `health_check`
  - Returns a small JSON document indicating status and version

Consult `fastapi_app/main.py` to confirm the final path names in your version of the project.

---

## 5. Relationship to Azure Functions Implementation

- **Shared logic**:
  - Both the Azure Function (`invoice_extractor`) and the FastAPI app call into `src/extraction/service.py`.
  - You get identical extraction behavior regardless of hosting technology.

- **Different hosting models**:
  - **Azure Functions**:
    - Serverless, scales automatically.
    - Integrated with Function App, Azure Storage, and Application Insights.
  - **FastAPI**:
    - Runs as a traditional web app (e.g. behind uvicorn/gunicorn).
    - Easier to host on containers, VMs, App Service, or Kubernetes.

You can choose the hosting model that best fits your scenario while keeping the same core invoice extraction logic.

---

## 6. When to Use Which

- Use **Azure Functions** when:
  - You want true serverless behavior (scale-to-zero, pay-per-use).
  - You care about tight integration with Azure’s Function platform and built-in triggers.

- Use **FastAPI** when:
  - You prefer a standard web framework and deployment model.
  - You want more control over middleware, routing, or OpenAPI docs.
  - You plan to host in containers or non-serverless environments.

Both options are kept in the repo to demonstrate flexibility and good separation between **infrastructure** and **business logic**.
