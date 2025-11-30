# Azure Invoice Extraction Service

A lightweight, production-friendly backend service for **extracting structured invoice data from PDF files** using **Azure Document Intelligence (prebuilt-invoice)** and serving it through an **Azure Functions HTTP API**.

This project is part of a professional AI/Cloud portfolio and demonstrates:
- Cloud AI integration  
- Serverless architecture  
- Clean Python engineering  
- Real-world invoice automation use cases  

---

## What This Service Does

It takes a **PDF invoice** as input and returns clean, structured JSON containing:

- Invoice ID  
- Invoice Date / Due Date  
- Vendor Name  
- Customer Name  
- Total Amount  
- Tax Amount  
- Line Items (description, quantity, price, amount)  
- Overall extraction confidence  

This replaces manual data entry and enables automation in:
- Accounting workflows  
- ERP/finance integrations  
- Back-office operations  
- Expense management apps  

---

## Architecture Overview

**Flow:**

```
Client → Azure Function (HTTP POST) → Azure Document Intelligence  
      → Normalization Layer → JSON Response
```

The Azure Function:
1. Accepts raw PDF bytes  
2. Sends them to Azure Document Intelligence  
3. Polls until extraction is done  
4. Normalizes the data into a predictable structure  
5. Returns JSON to the client  

Works locally using **Docker** and fully deployable to Azure.

---

## 📂 Project Structure

```
.
├── host.json
├── local.settings.json            # Not committed (contains secrets)
├── requirements.txt
├── .env                           # For local testing scripts
│
├── invoice_extractor/             # Azure Function (HTTP trigger)
│   ├── __init__.py
│   └── function.json
│
├── src/
│   └── extraction/
│       ├── extract_invoice.py
│       ├── normalize_output.py
│       └── test_extract_local.py
│
├── azure/
│   ├── API_REFERENCE.md
│   ├── architecture.md
│   └── system_design.md
│
└── samples/
    ├── example_invoice_1.pdf
    ├── raw_output_example.json
    └── normalized_output_example.json
```

---

## Running Locally (Docker)

### 1. Ensure `local.settings.json` contains your Azure DI keys:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "DOCINT_ENDPOINT": "https://<your-resource>.cognitiveservices.azure.com",
    "DOCINT_KEY": "<your-key>"
  }
}
```

### 2. Install dependencies for Azure Functions runtime:

```bash
python -m pip install --target .python_packages/lib/site-packages requests python-dotenv
```

### 3. Start the Function locally (PowerShell):

```powershell
docker run --rm -it `
  -p 7071:80 `
  -v D:\GitHub\06_invoice-extraction-azure:/home/site/wwwroot `
  -e AzureWebJobsScriptRoot=/home/site/wwwroot `
  mcr.microsoft.com/azure-functions/python:4-python3.10
```

You should see:

```
Found the following functions:
    invoice_extractor
```

---

## Test the API

```bash
curl -X POST ^
  -H "Content-Type: application/pdf" ^
  --data-binary @samples/example_invoice_1.pdf ^
  http://localhost:7071/api/invoice-extractor
```

Example response:

```json
{
  "invoice_id": "INV-100",
  "invoice_date": "2019-11-15",
  "due_date": "2019-12-15",
  "vendor_name": "CONTOSO LTD.",
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

---

## API Reference

### **POST** `/api/invoice-extractor`

#### Request
- **Content-Type:** `application/pdf`
- **Body:** binary PDF file content

#### Response
- **200 OK** + JSON with extracted invoice fields  
- **400** if no PDF  
- **500** if extraction fails on Azure DI  

---

## Technology Stack

- **Python**  
- **Azure Functions (HTTP Trigger)**  
- **Azure Document Intelligence (Prebuilt-Invoice)**  
- **Docker**  
- **REST APIs**  

---

## Why This Project Exists

Many organizations still rely on manual data entry for processing supplier invoices.
This creates bottlenecks in accounting, operations, and finance workflows.

This project demonstrates how **cloud-based AI** and **serverless backend architecture** can automate that process:

- PDF invoices → extracted → structured JSON

- Removes manual typing

- Enables automation in ERP, finance, and analytics systems

- Provides consistent, machine-readable data even when invoice formats differ

It’s a practical example of applying AI to a real business challenge.

---

## Future Improvements

Potential enhancements for future versions include:

- Support for multiple invoices inside a single PDF

- Automatic validation of extracted fields (detect missing totals, dates, line items)

- Batch processing for bulk invoice ingestion

- Public deployment to Azure Function App

- Adding an authentication layer for production use

- Integrations with accounting tools (SAP, QuickBooks, Odoo, Xero)

- Adding a simple web UI for uploading invoices and viewing results

- Converting the normalized JSON output into CSV or Excel exports

- Storing processed invoices in Azure Blob Storage or a database

