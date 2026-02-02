# 🏥 Triage & Recovery Hub - Backend

<div align="center">

[![Đọc bằng tiếng Việt](https://img.shields.io/badge/Lang-Tiếng%20Việt-red?style=for-the-badge&logo=google-translate&logoColor=white)](./README.vi.md)

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Gemini AI](https://img.shields.io/badge/Google%20Gemini-8E75B2?style=for-the-badge&logo=google&logoColor=white)](https://aistudio.google.com/)

![Status](https://img.shields.io/badge/Status-Stable-success?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)
![Cost](https://img.shields.io/badge/Cost-$0_Free-green?style=flat-square)

**Automated Customer Support & Triage System powered by AI**
_Understand instantly - Respond immediately - Zero cost_

Demo Video (TODO) | [Frontend Repo](https://github.com/MangBao/triage-recovery-hub-fe) | [API Docs](http://localhost:8000/docs) | Report Bug (TODO)

</div>

---

## 🌟 Introduction

**Triage & Recovery Hub** is a powerful backend solution automating the customer support workflow. It ingests complaints, utilizes **Google Gemini AI** to analyze sentiment, assess urgency, and automatically draft professional responses, saving up to 80% of support handling time.

### ✨ Key Features

| Feature                   | Description                                                     | Tech                      |
| :------------------------ | :-------------------------------------------------------------- | :------------------------ |
| 🧠 **AI Triage**          | Categorize complaints (Billing, Tech, Feature) & assess urgency | `Google Gemini`           |
| ❤️ **Sentiment Analysis** | Score customer sentiment (1-10) for prioritization              | `Gemini Pro`              |
| ✍️ **Auto-Draft**         | Automatically generate professional drafts                      | `Generative AI`           |
| ⚡ **Real-time Push**     | WebSocket Broadcast for instant UI updates                      | `FastAPI Websockets`      |
| 🕒 **Async Queue**        | Asynchronous processing, non-blocking requests                  | `Huey` + `Redis`          |
| 🛡️ **Secure Design**      | Sensitive data masking, anti-collision, transaction rollbacks   | `Pydantic` + `SQLAlchemy` |

---

## 🏗️ Architecture

```mermaid
graph LR
    User[Client / App] -->|POST Ticket| API[FastAPI Backend]
    User <-->|WebSocket| API
    API -->|Save| DB[(PostgreSQL)]
    API -->|Enqueue| Queue[(Redis)]
    Queue -->|Consume| Worker[Huey Worker]
    Worker -->|Analyze| AI[Google Gemini API]
    AI -->|Result| Worker
    Worker -->|Update| DB
    Worker -->|Pub| Queue
    Queue -->|Sub Update| API
```

### 💡 Engineering Decisions

- **Non-blocking Ingestion**: Decoupled API (FastAPI) from heavy AI processing using **Huey + Redis**. This ensures the API returns `201 Created` in <100ms while AI processes in the background (meeting the "Bottleneck Test").
- **Real-time Architecture**: Implemented **Redis Pub/Sub** to bridge the asynchronous Huey worker and FastAPI WebSocket layer, allowing the worker to "push" updates back to connected clients instantly.
- **AI Safety & Validation**: Implemented strict **Pydantic V2** schemas to parse and validate LLM JSON outputs. If the AI hallucinates invalid data, the system falls back gracefully instead of crashing.
- **Resilience**: Added **Rate Limiting** (SlowAPI) and **Timeouts** to protect against 3rd-party API failures and potential DoS attacks.

---

## 🚀 Quick Start

### 1️⃣ Prerequisites

- **Docker Desktop** & **Docker Compose**
- **Google API Key** (Free): [Get it here](https://aistudio.google.com/)

### 2️⃣ Setup

```bash
# Clone project
git clone https://github.com/MangBao/triage-recovery-hub-be.git
cd triage-recovery-hub-be

# Configure environment
cp .env.example .env
# ⚠️ Open .env file and add your GOOGLE_API_KEY!
```

### 3️⃣ Deploy

Use Docker Compose to launch the full stack (db, redis, backend, worker):

```bash
docker-compose up -d --build
```

> **Note:** The system will automatically create database tables on startup. No manual migration needed.

### 4️⃣ Advanced Verification

Checks Functional, Security, and Load resilience.
**Note:** Scripts now include a safety prompt to prevent accidental API quota consumption. Use `--force` to bypass.

```bash
docker-compose exec backend python tests/full_verification.py
```

| Test Layer              | Checks                                                |
| :---------------------- | :---------------------------------------------------- |
| **1. Unit/Integration** | Code logic, Database models, Services                 |
| **2. Stress Test**      | 6 Business scenarios (Billing, Tech, Multilingual)    |
| **3. Security Audit**   | SQL Injection, XSS, Huge Payloads (10KB), Empty Input |
| **4. Rate Limiting**    | Spam protection check (Limits 30 req/min/IP)          |
| **5. Heavy Load**       | 200 Concurrent Requests (Queue resilience test)       |

### 5️⃣ Manual Verify

- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health) (Basic) | [http://localhost:8000/health/deep](http://localhost:8000/health/deep) (Deep)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📚 API Usage Guide

### 1. Create Ticket (Customer)

Send a complaint request. AI will process it in 3-5 seconds.

```bash
curl -X POST http://localhost:8000/api/tickets \
  -H "Content-Type: application/json" \
  -d '{"customer_complaint": "I was charged twice for order #123! Refund me NOW!"}'
```

### 2. View Result (Agent)

Retrieve ticket details to see AI analysis.

```bash
curl http://localhost:8000/api/tickets/1
```

**Example Response:**

```json
{
  "status": "completed",
  "category": "Billing",
  "urgency": "High",
  "sentiment_score": 2,
  "ai_status": "success",
  "ai_draft_response": "Hello, I sincerely apologize for the double charge..."
}
```

### 3. Real-time Updates (WebSocket)

Connect to receive live updates when tickets change status.

**URL**: `ws://localhost:8000/ws/tickets`

**Client Protocol:**

1. Connect to WebSocket.
2. Send Subscribe Message:
   ```json
   { "action": "subscribe", "ticket_ids": [1, 2, 3] }
   ```
3. Receive Updates:
   ```json
   {
     "type": "ticket_updated",
     "data": { "id": 1, "status": "completed", ... }
   }
   ```

---

## 🛠️ Tech Stack Details

| Component        | Tech                                                                                          | Version       |
| :--------------- | :-------------------------------------------------------------------------------------------- | :------------ |
| **Language**     | ![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)             | `3.11`        |
| **Framework**    | ![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)          | `0.109+`      |
| **Database**     | ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?logo=postgresql&logoColor=white) | `16`          |
| **Worker**       | ![Huey](https://img.shields.io/badge/Huey-Consumers-orange)                                   | `2.4.5`       |
| **Cache/Queue**  | ![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white)                | `7.0`         |
| **LLM Provider** | ![Gemini](https://img.shields.io/badge/Google_Gemini-8E75B2?logo=google&logoColor=white)      | `Pro / Flash` |

---

## 🛡️ Security & Performance

- **Non-root Container**: Runs as `appuser` for security.
- **Fail-safe Transactions**: Automatic `rollback` on DB errors.
- **Timeout Protection**: AI API calls strictly timed out (30s).
- **Input Validation**: XSS prevention and strict Pydantic v2 validation.

---

## 🤝 Contributing

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

<div align="center">
  <p>Made with ❤️ by <a href="https://github.com/MangBao"><b>MangBao</b></a></p>
</div>
