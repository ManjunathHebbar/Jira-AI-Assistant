# Jira AI Assistant 🚀

An AI-powered Jira automation platform that automatically:

- Translates multilingual Jira tickets
- Generates AI-powered issue summaries
- Detects customer sentiment
- Summarizes Jira comments
- Prevents duplicate processing
- Supports Knowledge Base (RAG)
- Updates Jira tickets automatically
- Runs fully locally using Ollama (No paid APIs)

Built using:

- Python — core backend language for Jira processing, AI orchestration, and KB ingestion
- FastAPI — exposes the `/jira-webhook` endpoint that Jira Automation calls
- Ollama — runs the local LLM used for summaries, translation, sentiment, and root-cause analysis
- SQLite — stores processed ticket hashes and processing locks to prevent duplicate webhook loops
- ChromaDB — local vector database for retrieving relevant knowledge base entries
- Sentence Transformers — converts KB documents and ticket text into embeddings for similarity search
- Jira REST API — fetches Jira issue details and updates the AI custom field
- ngrok — exposes the local FastAPI server to Jira Cloud during development/testing

---

# 🚀 Features

---

# ✅ AI Ticket Summarization

Automatically generates:

- English Title
- Business Summary
- Root Cause
- Suggested Fix
- Priority
- Action Items

---

# ✅ Multilingual Translation

Supports tickets written in:

- Hindi
- Japanese
- Chinese
- German
- French
- Spanish
- Korean
- Portuguese
- Arabic
- etc.

Automatically translates them into English.

---

# ✅ Comment Summarization

Long Jira discussions become:

- concise
- actionable
- developer-friendly
- handoff-ready

---

# ✅ Sentiment Analysis

Detects customer tone:

- Positive
- Neutral
- Frustrated
- Escalated
- Angry

---

# ✅ Knowledge Base (RAG)

The system now supports:

- internal troubleshooting knowledge
- historical issue patterns
- known fixes
- reusable production learnings

The AI uses your internal KB while generating summaries.

Example:

If a Jira ticket mentions:

```text
Login issue with expired token
```

The AI can automatically relate it to:

```text
Login failures are usually caused by expired JWT tokens
```

from your knowledge base.

---

# ✅ Smart Duplicate Prevention

Avoids infinite Jira webhook loops using:

- input hashing
- SQLite cache
- change detection

Only processes tickets when actual content changes.

---

# ✅ Fully Local AI (Privacy Safe)

Uses:

- Ollama
- Mistral LLM

No OpenAI APIs required.

No external AI providers.

Perfect for:

- enterprise
- banking
- healthcare
- on-prem systems
- secure environments

---

# 🏗️ System Architecture

```text
Jira Ticket Updated
        ↓
Jira Native Webhook or Jira Automation Rule
        ↓
Webhook hits FastAPI
        ↓
Fetch Jira Ticket
        ↓
Extract:
   - Summary
   - Description
   - Comments
   - Status
        ↓
Knowledge Base Retrieval (RAG from ChromaDB)
        ↓
Ollama generates:
   - AI Summary
   - Translation
   - Sentiment
   - Comment Summary
        ↓
Update Jira Custom Field
        ↓
If resolved, save useful ticket learning into ChromaDB
        ↓
Store Hash in SQLite after successful Jira and KB updates
```

---

# 📁 Project Structure

```text
Jira-api/
│
├── app/
│   │
│   ├── ai/
│   │   ├── language_detector.py
│   │   ├── ollama_client.py
│   │   ├── rag.py
│   │   ├── sentiment.py
│   │   ├── summarizer.py
│   │   └── translator.py
│   │
│   ├── cache/
│   │   └── sqlite_cache.py
│   │
│   ├── jira/
│   │   ├── adf_builder.py
│   │   ├── fetcher.py
│   │   └── updater.py
│   │
│   ├── prompts/
│   │   ├── comments.txt
│   │   ├── sentiment.txt
│   │   ├── summary.txt
│   │   └── translation.txt
│   │
│   ├── utils/
│   │   ├── extractor.py
│   │   └── logger.py
│   │
│   └── main.py
│
├── knowledge_base/
│   ├── docs/
│   │   ├── login_issue.txt
│   │   └── payment_issue.txt
│   ├── resolved_snapshots/
│   ├── jira_kb.txt
│   ├── build_index.py
│   ├── ingest.py
│   ├── kb_updater.py
│   ├── root_cause_analyzer.py
│   └── vector_store.py
│
├── chroma_db/
│
├── .env
├── requirements.txt
├── README.md
└── .gitignore
```

---

# 🧠 Knowledge Base (RAG)

---

# What is RAG?

RAG = Retrieval Augmented Generation

Instead of relying only on the LLM knowledge,
the system retrieves relevant internal knowledge before generating the response.

---

# Example

Knowledge Base:

```text
Webhook infinite loops happen when Jira updates trigger webhook again.
```

Jira Ticket:

```text
Webhook repeatedly processing same ticket
```

AI automatically uses KB context while generating summary.

---

# Current Knowledge Base Example

```text
Login failures are usually caused by:
- expired JWT tokens
- invalid credentials
- authentication middleware issues

Webhook infinite loops happen when Jira updates trigger the webhook again.

A Jira API response code 204 means update success.
```

---

# 🛠️ Installation Guide

---

# Step 1 — Clone Project

```bash
git clone <your_repo_url>
```

```bash
cd Jira-api
```

---

# Step 2 — Create Virtual Environment

```bash
python3 -m venv venv
```

Activate:

Mac/Linux:

```bash
source venv/bin/activate
```

Windows:

```bash
venv\Scripts\activate
```

---

# Step 3 — Install Dependencies

```bash
pip3 install -r requirements.txt
```

---

# Step 4 — Install Ollama

Download:

https://ollama.com/download

Verify:

```bash
ollama --version
```

---

# Step 5 — Pull AI Model

```bash
ollama pull mistral
```

---

# Step 6 — Download Embedding Model

The knowledge base uses `sentence-transformers/all-MiniLM-L6-v2`.
Download it once before running in fully local mode:

```bash
python3 - <<'PY'
from sentence_transformers import SentenceTransformer
SentenceTransformer("all-MiniLM-L6-v2")
PY
```

After this, the app loads the embedding model from the local cache.

---

# Step 7 — Start Ollama

```bash
ollama serve
```

---

# Step 8 — Configure Environment Variables

Create `.env`

```env
JIRA_DOMAIN=https://your-domain.atlassian.net

EMAIL=your-email@gmail.com

API_TOKEN=your-jira-api-token

PROJECT_KEY=MS

CUSTOM_FIELD_ID=customfield_10119

OLLAMA_MODEL=mistral

OLLAMA_URL=http://localhost:11434/api/generate
```

The app also accepts `JIRA_EMAIL` and `JIRA_API_TOKEN` as aliases for `EMAIL` and `API_TOKEN`.

---

# Step 9 — Generate Jira API Token

Open:

https://id.atlassian.com/manage-profile/security/api-tokens

Steps:

1. Create API Token
2. Copy token
3. Add token into `.env`

---

# Step 10 — Build Knowledge Base Index

Run this after editing `knowledge_base/jira_kb.txt` or files under `knowledge_base/docs/`:

```bash
python3 knowledge_base/ingest.py
```

Expected:

```text
Knowledge Base Ingested Successfully
Collection: jira_knowledge
```

This indexes the static knowledge base documents into ChromaDB. Resolved Jira tickets are added automatically at runtime by `knowledge_base/kb_updater.py`.

---

# Step 11 — Start FastAPI Server

```bash
python3 -m uvicorn app.main:app --reload
```

Expected:

```text
Uvicorn running on http://127.0.0.1:8000
```

---

# Step 12 — Install ngrok

Download:

https://ngrok.com/download

Authenticate:

```bash
ngrok config add-authtoken YOUR_TOKEN
```

---

# Step 13 — Start ngrok Tunnel

```bash
ngrok http 8000
```

Example:

```text
Forwarding https://abc123.ngrok-free.dev -> http://localhost:8000
```

Copy the HTTPS URL.

---

# ⚙️ Jira Webhook Setup

---

# Option 1 — Jira Native Webhook

Open:

```text
Jira Settings → System → Webhooks
```

Create a webhook with:

```text
URL:
https://YOUR_NGROK_URL.ngrok-free.dev/jira-webhook

Events:
- Issue updated

JQL:
project = MS
```

Native webhooks send the full Jira payload. The app reads the issue key from the `issue.key` field and then fetches the latest Jira issue details through the Jira REST API.

The AI summary still updates for normal issue changes like title, description, comments, or status.

Knowledge base saving only happens when the native webhook changelog shows the issue status changed to a Done-like status:

```text
Done
Closed
Resolved
Complete
Completed
```

Other issue updates still refresh the AI field, but skip KB saving with:

```text
TICKET RESOLVED BUT STATUS DID NOT JUST CHANGE TO DONE - skipping KB save
```

---

# Option 2 — Jira Automation Rule

Open:

```text
Project Settings → Automation
```

Trigger:

```text
Issue Updated
```

Action:

```text
Send Web Request
```

URL:

```text
https://YOUR_NGROK_URL.ngrok-free.dev/jira-webhook
```

HTTP Method:

```text
POST
```

Headers:

| Key | Value |
|------|------|
| Content-Type | application/json |

Choose:

```text
Custom Data
```

Paste:

```json
{
  "issue": {
    "key": "{{issue.key}}"
  }
}
```

Both setup options use the same FastAPI endpoint. Native Jira webhook events outside issue updates are ignored safely.

---

# 🧠 Knowledge Base Setup

---

# Step 1 — Add KB Data

Edit:

```text
knowledge_base/jira_kb.txt
```

You can also add smaller topic files under:

```text
knowledge_base/docs/
```

Example:

```text
Login failures are usually caused by expired JWT tokens.

Webhook infinite loops happen when Jira updates trigger the webhook again.

Loader issues may happen because frontend state never updates.
```

---

# Step 2 — Generate Vector Database

Run:

```bash
python3 knowledge_base/ingest.py
```

Expected:

```text
Knowledge Base Ingested Successfully
Database Path: .../Jira-api/chroma_db
Collection: jira_knowledge
```

---

# Step 3 — Restart FastAPI

```bash
python3 -m uvicorn app.main:app --reload
```

---

# ✅ Automatic KB Updates from Resolved Tickets

When Jira sends a webhook for a resolved ticket, the app can save that ticket as reusable knowledge.

Runtime flow:

1. `app/main.py` fetches the Jira issue and reads the status.
2. If the status is resolved/done/closed, it calls `knowledge_base/kb_updater.py`.
3. `kb_updater.py` checks whether the ticket has useful summary/root-cause/fix content.
4. It redacts sensitive values and avoids near-duplicate KB entries.
5. It writes a review snapshot to `knowledge_base/resolved_snapshots/`.
6. It upserts the final text into ChromaDB as embeddings in the `jira_knowledge` collection.

Important:

- `resolved_snapshots/` is only for human review.
- The actual searchable KB entry is stored in ChromaDB.
- `knowledge_base/ingest.py` is only needed when static KB files change.
- Status is included in the processed-ticket hash, so moving a ticket to Done can trigger the KB update even when the summary/description/comments did not change.

---

# 🔥 Example AI Output

```text
🤖 AI ISSUE SUMMARY

Title:
User Login Failure

Summary:
Users unable to login due to expired JWT tokens.

Root Cause:
Authentication token validation failure.

Suggested Fix:
Refresh token handling middleware.

Priority:
High
```

---

# 🧪 Sample Multilingual Tickets

---

# Hindi Ticket

```text
उपयोगकर्ता लॉगिन नहीं कर पा रहा है।
```

---

# Japanese Ticket

```text
ログイン時にローダーが表示されません。
```

---

# French Ticket

```text
Le webhook Jira boucle indéfiniment.
```

---

# German Ticket

```text
Die Datenbankverbindung schlägt fehl.
```

---

# 🔐 Security

- Fully local AI
- No external LLM APIs
- Internal KB support
- Enterprise safe
- GDPR friendly
- Jira update errors are not cached as successful processing

---

# 🧯 Runtime Behavior

- Jira API fetch/update calls use a 30 second timeout.
- Failed Jira fetch/update responses raise clear errors.
- The AI custom field is updated with temporary processing states while work is running.
- Processing states use Jira ADF panels, headings, and progress bullets.
- The temporary processing state is replaced by the final AI summary when generation completes.
- If generation fails after the ticket is claimed, the custom field is updated with a failed state.
- The processed-ticket hash is saved only after the final Jira update succeeds.
- For resolved tickets, the hash is saved only after the KB update succeeds too.
- If a resolved-ticket KB update fails, the processing lock is cleared so Jira can retry later.
- Duplicate webhook processing is prevented with SQLite processing locks.
- Stale processing locks expire after 30 minutes so interrupted work can retry.
- Blocking Jira, Ollama, ChromaDB, and SQLite work runs in FastAPI's threadpool using `run_in_threadpool`.
- Runtime cache is stored at `cache/processed_tickets.db`.

Why `run_in_threadpool` is used:

FastAPI endpoints are async, but this project uses blocking libraries for Jira REST calls, Ollama calls, ChromaDB access, and SQLite cache writes. `run_in_threadpool` moves that blocking work off the main event loop, so the API can still accept other webhook requests while one ticket is being processed.

---

# 🧰 Tech Stack

| Technology | Usage |
|------------|-------|
| FastAPI | Backend |
| Ollama | Local LLM |
| Mistral | AI Model |
| ChromaDB | Vector Database |
| Sentence Transformers | Embeddings |
| SQLite | Cache |
| Jira REST API | Jira Integration |
| ngrok | Public Tunnel |

---

# 📦 requirements.txt

```txt
fastapi
uvicorn
requests
python-dotenv
langdetect
langcodes
language_data
ollama
chromadb
sentence-transformers
transformers
torch
```

---

# 📄 .gitignore

```gitignore
__pycache__/
*.pyc
venv/
.env
*.db
*.log
.DS_Store
.vscode/
.idea/
chroma_db/
cache/
```

---

# 👨‍💻 Author

AI-Powered Jira Automation System 🚀

Built with:
- FastAPI
- Ollama
- RAG
- Local AI
- Jira Automation
