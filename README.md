# DocuVerify AI

> AI-powered Document Verification and Approval System — Hackathon Project

## Problem

Organizations receive forms, invoices, receipts, and supporting documents. Staff must manually extract information, check for missing data, compare values, request corrections, and make decisions. This is slow, error-prone, and hard to audit.

## Solution

DocuVerify AI automates:
- OCR extraction of key fields from uploaded documents
- Automatic verification checks (missing fields, amount mismatch, date mismatch)
- Evidence-linked review so human reviewers see exactly which text triggered each warning
- A version-aware ChangeMap when replacement documents are submitted
- A grounded AI assistant that answers questions using actual request records

**Final decisions always belong to authorized humans. The system never auto-approves or auto-rejects.**

## Implemented features

- JWT authentication, role checks, and submitter-only public registration
- Expense request lifecycle, required document uploads, version history, and audit events
- PDF text extraction and Tesseract OCR for scanned PDFs/images when Tesseract is installed
- Evidence-linked missing-field, amount, and date checks
- Reviewer correction and information-request workflow; approver decisions with reasons
- Live dashboard metrics and a request-grounded Gemini assistant with an explicitly labeled fallback
- React UI for request, document, review, dashboard, and assistant workflows

Reviewer and approver accounts must be provisioned by an administrator or the demo seed script. Public registration cannot create privileged accounts.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19 + TypeScript + Vite + Tailwind CSS |
| Backend | Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic |
| Database | SQLite (dev) / PostgreSQL (prod — set `DATABASE_URL`) |
| OCR | PyMuPDF text extraction + pytesseract/Tesseract for images and scanned pages |
| AI | Google Gemini Flash (optional — grounded fallback when key absent) |

## Prerequisites

- Python 3.12+ with pip
- Node.js 18+ with npm
- Tesseract OCR binary: <https://github.com/UB-Mannheim/tesseract/wiki>
- (Optional) PostgreSQL for production

## Quick Start

### 1. Clone and configure

```bash
# Create backend/.env from backend/.env.example only if backend/.env does not already exist.
# Create frontend/.env.local from frontend/.env.example only if it does not already exist.
# Preserve existing environment files and secrets.
```

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# Visit http://localhost:5173
```

### 4. API docs

Visit `http://localhost:8000/docs` for interactive FastAPI documentation.

### Demo users

Run `python scripts/seed_demo.py` from `backend/` to add any missing demo accounts. Existing accounts are left unchanged. The password `password123` applies only to accounts newly created by the seed command.

## Environment Variables

See `backend/.env.example` for all variables.

Key variables:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy URL. Default: `sqlite:///./docuverify.db` |
| `SECRET_KEY` | JWT signing secret (generate a long random string) |
| `GEMINI_API_KEY` | Google Gemini key (optional — fallback used if absent) |
| `STORAGE_DIR` | Absolute path to file storage directory (default: `../storage`) |
| `MAX_UPLOAD_MB` | Upload size limit in MB (default: 20) |

## Known limitations

- Text extraction from scanned pages and images requires the Tesseract executable; text-based PDFs can be processed without it.
- Gemini answers require `GEMINI_API_KEY`; without it (or if the provider fails), the API returns a clearly labeled deterministic answer based on stored evidence.
- OCR and regex extraction are decision support. A human reviewer must inspect the evidence and make every final decision.
- The frontend currently provides login but not a public registration screen. Accounts can be created through the API; reviewer and approver roles require trusted provisioning.
- SQLite is intended for local development. Use a PostgreSQL `DATABASE_URL` for deployments requiring concurrent multi-user writes.
