# Triage & Recovery Hub - Backend

**AI-powered customer support ticket triage system** using FastAPI, PostgreSQL, Redis, Huey, and **FREE Google Gemini API**.

🆓 **COST: $0** - No credit card required!

---

## 🎯 Overview

The Triage & Recovery Hub backend provides a REST API for intelligent customer support ticket management:

1. **Ingest** customer complaints via POST API
2. **Process** asynchronously using Google Gemini AI
3. **Categorize** by type (Billing/Technical/Feature Request)
4. **Prioritize** by urgency (High/Medium/Low)
5. **Analyze** sentiment (1-10 scale)
6. **Generate** AI draft responses
7. **Allow** agent editing and ticket resolution

## 🏗️ Architecture

```
FastAPI (Port 8000)
    ↓
PostgreSQL (Tickets Storage)
    ↓
Redis (Task Queue)
    ↓
Huey Worker (Background Processing)
    ↓
Google Gemini API (FREE - AI Triage)
```

**Workflow:**

1. Client creates ticket → API returns immediately (201 Created)
2. Background worker picks up task from queue
3. Worker calls Gemini API for triage
4. Worker updates ticket with AI results
5. Client polls for status updates

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development without Docker)
- Google Gemini API key (FREE): https://aistudio.google.com/app/apikey

### 1. Setup Environment

```bash
# Clone repository
git clone <repo-url>
cd triage-recovery-hub-be

# Create .env from example
cp .env.example .env

# Edit .env and add your Gemini API key
# GOOGLE_API_KEY=AIzaSyD...
```

### 2. Start with Docker Compose

```bash
# Development (with exposed ports, volume mounts, default credentials)
docker-compose up -d

# Production (requires .env with all credentials set)
docker-compose -f docker-compose.yml up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f worker
```

### 3. Verify

```bash
# Health check
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# API documentation
open http://localhost:8000/docs
```

---

## 📡 API Endpoints

All endpoints are under `/api/tickets` prefix.

### Swagger Documentation

Interactive API docs: **http://localhost:8000/docs**

### Endpoints Summary

| Method  | Endpoint                    | Description                            |
| ------- | --------------------------- | -------------------------------------- |
| `POST`  | `/api/tickets`              | Create ticket (triggers AI processing) |
| `GET`   | `/api/tickets`              | List tickets with filters & pagination |
| `GET`   | `/api/tickets/{id}`         | Get single ticket detail               |
| `PATCH` | `/api/tickets/{id}`         | Update ticket (agent edits)            |
| `POST`  | `/api/tickets/{id}/resolve` | Mark ticket as resolved                |
| `GET`   | `/health`                   | Health check                           |

### Example: Create & Process Ticket

```bash
# 1. Create ticket
curl -X POST http://localhost:8000/api/tickets \
  -H "Content-Type: application/json" \
  -d '{"customer_complaint": "I was charged twice for order #12345!"}'

# Response (201 Created):
# {
#   "id": 1,
#   "customer_complaint": "I was charged twice for order #12345!",
#   "status": "pending",
#   "category": null,
#   ...
# }

# 2. Wait 3-5 seconds for AI processing...

# 3. Check ticket status
curl http://localhost:8000/api/tickets/1

# Response (200 OK):
# {
#   "id": 1,
#   "status": "completed",
#   "category": "Billing",
#   "sentiment_score": 3,
#   "urgency": "High",
#   "ai_draft_response": "We sincerely apologize for the double charge...",
#   ...
# }
```

---

## 💻 Local Development (without Docker)

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows

# Install packages
pip install -r requirements.txt
```

### 2. Setup PostgreSQL

```bash
# Option A: Use Docker for PostgreSQL only
docker run -d \
  -p 5432:5432 \
  -e POSTGRES_USER=triage_user \
  -e POSTGRES_PASSWORD=triage_pass123 \
  -e POSTGRES_DB=triage_db \
  postgres:16-alpine

# Option B: Install PostgreSQL locally
# Then create database: CREATE DATABASE triage_db;
```

### 3. Run Database Migrations

```bash
# Apply existing migrations to your database
alembic upgrade head

# To create new migrations after model changes:
# alembic revision --autogenerate -m "Description of changes"
```

### 4. Start Backend

```bash
# Terminal 1: Start FastAPI
uvicorn app.main:app --reload --port 8000

# Terminal 2: Start Huey worker
huey_consumer tasks.worker.huey -v
```

### 5. Access API

- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

---

## 🧪 Testing

### Run All Tests

```bash
# Run tests with coverage
pytest

# Run specific test file
pytest tests/test_api_tickets.py -v

# Run with coverage report
pytest --cov=app --cov=models --cov=services --cov=tasks --cov-report=html
```

### Test Structure

```
tests/
├── conftest.py          # Fixtures (test DB, test client)
├── test_api_tickets.py  # API endpoint tests
├── test_services.py     # Service layer tests
└── test_models.py       # Schema validation tests
```

---

## 🐳 Docker Configuration

### Services

- **postgres**: PostgreSQL 16 database
- **redis**: Redis 7 task queue
- **backend**: FastAPI application
- **worker**: Huey background worker

### Environment Variables

```bash
# Database (⚠️ REQUIRED - no defaults in production)
DB_USER=your_db_user
DB_PASSWORD=your_secure_password
DB_NAME=your_db_name

# Google Gemini API (FREE)
GOOGLE_API_KEY=your_api_key_here
GOOGLE_MODEL=gemini-2.5-flash

# Environment Mode
ENVIRONMENT=production  # or 'development' for MemoryHuey
DEBUG=false             # 'true' enables verbose logging
```

### Development vs Production Mode

**Development Mode** (`ENVIRONMENT=development`):

- Uses **MemoryHuey** (no Redis needed)
- Good for quick local testing
- Tasks run in-memory

**Production Mode** (`ENVIRONMENT=production`):

- Uses **RedisHuey** (requires Redis)
- Reliable task queue
- Better for Docker deployment

---

## 📂 Project Structure

```
triage-recovery-hub-be/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application
│   ├── config.py         # Configuration & env vars
│   └── database.py       # SQLAlchemy setup
├── api/
│   ├── __init__.py
│   └── tickets.py        # Ticket endpoints
├── models/
│   ├── __init__.py
│   ├── ticket.py         # SQLAlchemy models
│   └── schemas.py        # Pydantic schemas
├── services/
│   ├── __init__.py
│   ├── llm.py            # Gemini AI service
│   └── validation.py     # JSON validation
├── tasks/
│   ├── __init__.py
│   ├── worker.py         # Huey configuration
│   └── triage.py         # Background triage task
├── migrations/           # Alembic migrations
│   ├── env.py
│   └── versions/
├── tests/                # Pytest tests
│   ├── conftest.py
│   ├── test_api_tickets.py
│   ├── test_services.py
│   └── test_models.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── alembic.ini
├── pytest.ini
├── .env.example
├── .gitignore
└── README.md
```

---

## 🔧 Tech Stack

| Layer          | Technology        | Why                                  |
| -------------- | ----------------- | ------------------------------------ |
| **Framework**  | FastAPI           | Modern, fast, async Python framework |
| **Database**   | PostgreSQL 16     | Robust relational database           |
| **ORM**        | SQLAlchemy 2.0    | Powerful Python ORM                  |
| **Migrations** | Alembic           | Database version control             |
| **Task Queue** | Huey + Redis      | Lightweight async task processing    |
| **AI**         | Google Gemini API | FREE tier, reliable JSON output      |
| **Validation** | Pydantic v2       | Type-safe data validation            |
| **Testing**    | Pytest            | Comprehensive testing framework      |
| **Container**  | Docker            | Reproducible deployments             |

---

## 🐛 Troubleshooting

### Issue: `GOOGLE_API_KEY not found`

**Solution:** Make sure `.env` file exists and contains:

```bash
GOOGLE_API_KEY=AIzaSyD...
```

### Issue: `Database connection failed`

**Solutions:**

1. Check PostgreSQL is running: `docker-compose ps`
2. Verify DATABASE_URL in `.env`
3. Check logs: `docker-compose logs postgres`

### Issue: `Tasks not processing`

**Solutions:**

1. Check worker is running: `docker-compose logs worker`
2. Verify ENVIRONMENT mode in `.env`
3. If using development mode, no Redis needed
4. If using production mode, check Redis: `docker-compose logs redis`

### Issue: `Tickets stuck in "processing"`

**Possible causes:**

- Gemini API rate limit (60 req/min, 1500/day)
- Invalid API key
- Network issues

**Check worker logs:**

```bash
docker-compose logs worker | grep TRIAGE
```

---

## 📝 License

MIT License - Free to use for commercial projects

---

## 🙏 Acknowledgments

- **Google Gemini API** for free tier access
- **FastAPI** for modern Python web framework
- **Huey** for simple task queue
- **PostgreSQL** for reliable database

---

**Questions?** Check the API documentation at http://localhost:8000/docs
