# Azure Invoice Extraction Service — Architecture

This document describes the architecture of the **Azure Invoice Extraction Service**, which turns PDF invoices into structured JSON using **Azure Document Intelligence** and an **Azure Functions HTTP API**.

---

## 1. High-Level Overview (Simple Diagram)

```mermaid
flowchart LR
    A[Client: app or script] --> B[HTTP API: /api/invoice-extractor]
    B --> C[Azure Function: invoice_extractor]
    C --> D[Azure Document Intelligence: prebuilt invoice model]
    D --> C
    C --> E[JSON response: normalized invoice data]
```

---

## 2. Detailed Architecture (Components & Layers)

```mermaid
flowchart TB

    subgraph ClientSide
        C1[Client app or script]
    end

    subgraph AzureFunctionHost
        direction TB

        subgraph HttpLayer
            F1[HTTP trigger: invoice_extractor]
            F2[Request validation: content type and non-empty body]
        end

        subgraph LogicLayer
            L1[extract_invoice.py: call Document Intelligence]
            L2[normalize_output.py: map fields to schema]
        end

        subgraph ConfigLayer
            S1[local.settings.json: DOCINT_ENDPOINT, DOCINT_KEY]
            S2[Environment variables: Azure or Docker]
        end

        subgraph PythonDeps
            P1[Python packages: requests, python-dotenv]
        end
    end

    subgraph AzureCognitive
        D1[Azure Document Intelligence: prebuilt invoice model]
    end

    C1 -->|POST PDF /api/invoice-extractor| F1
    F1 --> F2
    F2 --> L1
    L1 -->|REST API call with endpoint and key| D1
    D1 -->|Raw JSON result| L1
    L1 --> L2
    L2 -->|Normalized JSON| F1
    F1 -->|HTTP 200 + JSON| C1

    S1 --> L1
    S2 --> L1
    P1 --> L1
```

---

## 3. Data Flow (Step-by-Step)

1. **Client Upload**  
   Client sends `POST /api/invoice-extractor` with a PDF body.

2. **HTTP Trigger**  
   Azure Function receives the HTTP request, validates header/body, and returns `400` on invalid input.

3. **Call Azure Document Intelligence**  
   Function reads endpoint/key from environment variables and sends the PDF to Document Intelligence.

4. **Normalization**  
   Raw JSON from Azure DI is transformed into a clean, stable structure.

5. **Response**  
   Function returns `200 OK` with normalized JSON, or structured error codes on failure.

---

## 4. Deployment Considerations

### Local Development (Docker)
```powershell
docker run --rm -it `
  -p 7071:80 `
  -v D:\GitHub\06_invoice-extraction-azure:/home/site/wwwroot `
  -e AzureWebJobsScriptRoot=/home/site/wwwroot `
  mcr.microsoft.com/azure-functions/python:4-python3.10
```

### Cloud Deployment (Azure Function App)
1. Create a Function App + Storage Account  
2. Add environment variables in **Configuration**  
3. Deploy using VS Code or Azure CLI  
4. API endpoint becomes:  
   ```
   https://<your-func-app>.azurewebsites.net/api/invoice-extractor
   ```

---

## 5. Why This Architecture

- **Serverless** — no server management, pay-per-execution  
- **Modular** — extraction & normalization logic isolated  
- **Cloud-native AI** — relies on Azure Document Intelligence  
- **Portable** — runs locally via Docker, deployable to Azure  
- **Extensible** — easy to add auth, logging, storage, batching, etc.  

