# Azure Invoice Extraction Service — Architecture

This document describes the architecture of the **Azure Invoice Extraction Service**, which turns PDF invoices into structured JSON using **Azure Document Intelligence** and an **Azure Functions HTTP API**.

---

## 1. High-Level Overview (Simple Diagram)

```mermaid
flowchart LR
    A[Client<br/>(App / Script / Tool)] --> B[HTTP API<br/>/api/invoice-extractor]
    B --> C[Azure Function<br/>invoice_extractor]
    C --> D[Azure Document Intelligence<br/>Prebuilt Invoice Model]
    D --> C
    C --> E[JSON Response<br/>Normalized Invoice Data]
```

---

## 2. Detailed Architecture (Components & Layers)

```mermaid
flowchart TB

    subgraph ClientSide[Client Side]
        C1[Client App / Script]
    end

    subgraph AzureFunctionHost[Azure Functions Host (Local via Docker / Cloud)]
        direction TB

        subgraph HttpLayer[HTTP Layer]
            F1[HTTP Trigger<br/>invoice_extractor Function]
            F2[Request Validation<br/>(Content-Type, non-empty body)]
        end

        subgraph LogicLayer[Business Logic Layer]
            L1[extract_invoice.py<br/>(calls Document Intelligence)]
            L2[normalize_output.py<br/>(maps fields to schema)]
        end

        subgraph ConfigLayer[Configuration]
            S1[local.settings.json<br/>(DOCINT_ENDPOINT, DOCINT_KEY)]
            S2[Environment Variables<br/>(Azure / Docker)]
        end

        subgraph PythonDeps[Python Dependencies]
            P1[.python_packages/lib/site-packages<br/>requests, python-dotenv]
        end
    end

    subgraph AzureCognitive[Azure Document Intelligence]
        D1[Prebuilt Invoice Model<br/>(formrecognizer/documentModels/prebuilt-invoice)]
    end

    C1 -->|POST PDF /api/invoice-extractor| F1
    F1 --> F2
    F2 --> L1
    L1 -->|REST API Call<br/>endpoint + key| D1
    D1 -->|Raw JSON Result| L1
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

