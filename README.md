# AI Business Operations & Logistics Assistant (Backend)

An enterprise multi-agent AI backend for logistics operations, compliance verification, real-time analytics, and automated notification dispatch. Built with **FastAPI**, **LangChain / LangGraph**, **Google Gemini**, and **PostgreSQL + pgvector**.

---

## Architecture Overview

```
                      +-----------------------------+
                      |   User / Frontend Client    |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |  FastAPI Application Server |
                      |         (server.py)         |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |   Security Schema Guard     |
                      |  (3-Layer Pre/Post Defense) |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |    Router & Orchestrator    |
                      |    (Deterministic + LLM)    |
                      +--------------+--------------+
                                     |
       +-----------------+-----------+-----------+-----------------+
       |                 |                       |                 |
       v                 v                       v                 v
+--------------+  +---------------+       +---------------+  +---------------+
|  Operations  |  |    Policy     |       |    Report     |  |     Email     |
|    Agent     |  |     Agent     |       |     Agent     |  |     Agent     |
+-------+------+  +-------+-------+       +-------+-------+  +-------+-------+
        |                 |                       |                  |
        | (SQLAlchemy)    | (pgvector RAG)        | (Read-Only SQL)  | (SMTP + CID)
        v                 v                       v                  v
+--------------+  +---------------+       +---------------+  +---------------+
|  PostgreSQL  |  |  768-dim SOP  |       | Charts Cache  |  | Secure Email  |
|  Operations  |  |  Embeddings   |       | & Aggregates  |  |   Dispatch    |
+--------------+  +---------------+       +---------------+  +---------------+
```

---

## Specialist Agents

1. **Orchestrator & Router Agent (`app/agent/agent.py`, `app/agent/router.py`)**
   - Routes incoming queries based on intent and conversational context into single or chained workflows.
   - Executes fact-then-compliance pipelines when both live data and policy validation are needed.
   - Enforces pre-route and post-response security schema shielding.

2. **Operations Agent (`app/agent/operational_agent.py`)**
   - Queries live operational PostgreSQL records across 7 core entities:
     - **Customers** (`customer_lookup`)
     - **Shipments** (`get_shipment_status`)
     - **Invoices** (`get_invoice_details`)
     - **Warehouse Receipts** (`get_warehouse_receipt_details`)
     - **Cargo Releases** (`get_cargo_release_details`)
     - **Quotations** (`get_quotation_details`)
     - **Drivers & Employees** (`get_driver_details`)

3. **Policy & Compliance Agent (`app/agent/policy_agent.py`)**
   - Performs semantic vector retrieval (`rag_search`) over company policies, standard operating procedures (SOPs), and codes of conduct.
   - Strictly evaluates factual operational data against retrieved policy texts without hallucinating internal states.

4. **Report & Analytics Agent (`app/agent/report_agent.py`)**
   - Converts natural-language reporting queries into safe, read-only SQL statements.
   - Computes period-over-period comparisons, KPIs, and aggregates.
   - Generates visual charts (bar, line, pie, donut, scatter) via Matplotlib, caching images in-memory and passing lightweight tokens to the conversation.

5. **Email Notification Agent (`app/agent/email_agent.py`)**
   - Drafts structured confirmation emails with explicit user review steps before dispatch.
   - Supports HTML tables, summary bullet points, and inline embedded CID charts.

---

## Security & Reliability Design

- **Zero Hardcoded Secrets:** All credentials, API keys, and connection strings are strictly managed via environment variables (`.env`).
- **3-Layer Database Schema Shield (`app/tools/schema_guard.py`):**
  1. *Regex Pre-filter:* Intercepts meta-queries targeting database table layouts, column names, DDL, or ER diagrams.
  2. *Semantic Classifier:* Evaluates intent to differentiate legitimate operational requests from schema extraction prompts.
  3. *Output Leak Scanner:* Validates generated responses to block accidental exposure of table or column names while permitting real business data values.
- **Enforced Read-Only SQL Execution:**
  - Queries must begin with `SELECT` or `WITH`.
  - Rejection of DDL/DML keywords (`DROP`, `INSERT`, `UPDATE`, `DELETE`, `ALTER`, etc.).
  - Database-level execution under `SET TRANSACTION READ ONLY`.

---

## Directory Structure

```
backend/
├── app/
│   ├── agent/                 # Multi-agent orchestrator, specialist agents, prompts
│   │   ├── agent.py           # Master OrchestratorAgent
│   │   ├── checkpointer.py    # In-memory thread checkpointing
│   │   ├── email_agent.py     # Email specialist agent
│   │   ├── email_prompt.py    # Email drafting and verification prompt
│   │   ├── llm.py             # Google Gemini client configuration
│   │   ├── operational_agent.py
│   │   ├── policy_agent.py    # SOP & Compliance specialist agent
│   │   ├── prompt.py          # Operational & General prompts
│   │   ├── report_agent.py    # Analytics & SQL specialist agent
│   │   ├── report_prompt.py   # Reporting system prompt
│   │   ├── router.py          # Intent classification router
│   │   └── utils.py           # Message parsing utilities
│   ├── database/              # SQLAlchemy session and engine management
│   │   └── connection.py      # Database connection handler
│   ├── policies/              # Knowledge documents for vector ingestion
│   │   └── docs/              # Company Policies PDF documents
│   ├── rag/                   # RAG loader, chunker, embedder, and ingestion
│   │   ├── chunker.py         # Overlapping passage chunking
│   │   ├── embedder.py        # Gemini embedding generation
│   │   ├── ingest.py          # Document vector pipeline
│   │   ├── loader.py          # PDF / DOCX / TXT document loader
│   │   └── eval/              # RAG benchmarking & evaluation suite
│   ├── services/              # Domain service layer for operational models
│   │   ├── cargo_release_service.py
│   │   ├── customer_service.py
│   │   ├── driver_service.py
│   │   ├── email_service.py
│   │   ├── invoice_service.py
│   │   ├── policy_service.py
│   │   ├── quotation_service.py
│   │   ├── shipment_service.py
│   │   └── warehouse_receipt_service.py
│   ├── tools/                 # LangChain tool interfaces
│   │   ├── cargo_release_tools.py
│   │   ├── chart_tool.py
│   │   ├── customer_tools.py
│   │   ├── db_readonly_tool.py
│   │   ├── driver_tool.py
│   │   ├── email_langchain_tool.py
│   │   ├── invoice_tools.py
│   │   ├── quotation_tools.py
│   │   ├── rag.py
│   │   ├── report_langchain_tools.py
│   │   ├── schema_guard.py
│   │   ├── shipment_tools.py
│   │   └── smtp_email_tool.py
│   └── chat_history_manager.py# JSON session store manager
├── data/                      # Local session storage (.gitignore protected)
│   └── .gitkeep
├── database/                  # SQL seed and schema scripts
│   └── premier_logistic.sql   # PostgreSQL database dump with pgvector
├── .env.example               # Environment variables template
├── .gitignore                 # Comprehensive Git ignore rules
├── chat.py                    # Interactive CLI chat interface
├── requirements.txt           # Python dependencies
├── server.py                  # FastAPI server entry point
└── test_automation.py         # Automated test suite
```

---

## Getting Started

### 1. Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- PostgreSQL 15+ with the `pgvector` extension installed
- Google Gemini API key ([Google AI Studio](https://aistudio.google.com/))

### 2. Environment Setup

Clone this repository and create a virtual environment:

```bash
# Clone the repository
git clone <your-repo-url>
cd <repo-folder>

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Setup

Create the PostgreSQL database and restore the schema dump:

```bash
# Create database
createdb -U postgres premier_logistic

# Restore tables and sample records (includes pgvector extension)
psql -U postgres -d premier_logistic < database/premier_logistic.sql
```

### 4. Configuration

Copy the `.env.example` file to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
# Database Settings
DB_HOST=localhost
DB_PORT=5432
DB_NAME=premier_logistic
DB_USER=postgres
DB_PASSWORD=your_password_here

# Google Gemini API Settings
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001

# SMTP Settings (Optional, for email agent)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your_account@gmail.com
SMTP_PASSWORD=your_google_app_password
```

### 5. Ingest Knowledge Documents (RAG)

Run the ingestion script to chunk, embed, and store company policies into PostgreSQL:

```bash
python -m app.rag.ingest
```

---

## Running the Application

### Option A: Run the FastAPI REST Server

```bash
# Run using Python
python server.py

# Or run directly with Uvicorn
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation will be available at:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Option B: Interactive CLI Chat

```bash
python chat.py
```

### Option C: Run Automated Tests

```bash
python test_automation.py
```

---

## REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/assistant/chat` | Send a query to the multi-agent orchestrator |
| `GET` | `/api/chats` | List summary headers of all saved chat sessions |
| `GET` | `/api/chats/{thread_id}` | Retrieve full conversation turn history for a session |
| `DELETE` | `/api/chats/{thread_id}` | Delete a chat session |
| `GET` | `/api/charts/{chart_id}` | Retrieve generated PNG chart image |
| `GET` | `/api/dashboard/stats` | Retrieve operational stats and query counts |
| `GET` | `/api/policies` | List registered policy governance documents |
| `GET` | `/api/audit` | View query audit logs |

---

## License

This project is licensed under the MIT License.
