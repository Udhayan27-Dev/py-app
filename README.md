# PlanMyStudy 📚🤖

An intelligent, full-stack study plan generator and exam timetable manager built with **Django**, **PostgreSQL**, **MongoDB Atlas**, and an integrated **AI Support Assistant** powered by Anthropic's Claude API.

> **Live Deployment Link:** [https://planmystudy.onrender.com](https://planmystudy.onrender.com) *(Placeholder for production URL on Render)*

---

## 🌟 Overview

Preparing for examinations is stressful when students don't know how to distribute their study time across subjects of varying difficulty or leave enough buffer for final revision. 

**PlanMyStudy** solves this problem by:
1. **Mathematical Schedule Optimization**: Proportionally weights daily study hours (Hard subjects receive 3x allocation, Medium 2x, Easy 1x).
2. **Mandatory 2-Day Pre-Exam Revision Buffer**: Automatically reserves the final 48 hours strictly for timed mock tests, formula recall, and mental rest (never study new material on revision days).
3. **24/7 AI Support Assistant**: Floating on every page (including 404/500 errors). Uses PostgreSQL FAQs and error codes as its verified knowledge source. If it cannot answer, it automatically logs a support ticket and provides the user with a ticket reference number.
4. **Resilient Third-Party Integrations**: Fetches daily motivational quotes from ZenQuotes with a 3-second timeout and 1-hour cache, gracefully falling back to curated local quotes so the website never crashes.
5. **Dual Database Architecture**: Combines relational consistency in PostgreSQL for core business data with document agility in MongoDB Atlas for chat telemetry and feedback.

---

## 🏗️ Architecture: PostgreSQL vs. MongoDB Atlas

PlanMyStudy leverages a hybrid storage design:

```
                                  +-----------------------------+
                                  |     Django Application      |
                                  +--------------+--------------+
                                                 |
                       +-------------------------+-------------------------+
                       |                                                   |
                       v                                                   v
         +---------------------------+                       +---------------------------+
         |   PostgreSQL (Django ORM)  |                       | MongoDB Atlas (pymongo)   |
         +---------------------------+                       +---------------------------+
         | • Study Plans & Timetables|                       | • Conversational Logs     |
         | • FAQ Knowledge Base      |                       | • User Feedback (👍 / 👎) |
         | • Error Codes Catalog     |                       | • Latency Metrics         |
         | • Support Tickets         |                       +---------------------------+
         | • User Authentication     |
         +---------------------------+
```

### 1. PostgreSQL (Primary Relational Database via Django ORM)
- **Entities:** `auth_user`, `FAQ`, `ErrorCode`, `StudyPlan`, `SupportTicket`.
- **Why PostgreSQL?**
  - **Relational Integrity & Ownership**: Enforces strict user ownership of study plans via foreign keys (`user_id`).
  - **ACID Guarantees**: Ensures transactions like ticket status transitions (`open` &rarr; `in_progress` &rarr; `closed`) are atomic and reliable.
  - **Structured Search**: Powers categorized FAQ directory searches and ErrorCode lookups.

### 2. MongoDB Atlas (NoSQL Telemetry & Feedback via PyMongo)
- **Collections:** `chat_logs`, `feedback`.
- **Why MongoDB Atlas?**
  - **High Write Throughput**: Chat messages and thumbs up/down ratings are logged asynchronously without locking relational tables.
  - **Schema Flexibility**: Stores varying conversation payloads, model metadata, latency benchmarks (`response_time_ms`), and optional user session contexts.
  - **Built-in Fallback**: If MongoDB Atlas is unreachable or unconfigured during local development, an in-memory queue preserves telemetry and prevents site interruptions.

---

## 🔑 Environment Variables Reference

| Variable | Required | Default / Example | Purpose |
| :--- | :---: | :--- | :--- |
| `SECRET_KEY` | **Yes** | `django-insecure-...` | Django cryptographic signing key. Generated automatically in Render. |
| `DEBUG` | **Yes** | `False` (Production) / `True` (Dev) | Enables or disables Django debug mode and detailed stack traces. |
| `DEBUG_ROUTES` | No | `False` | Enables `/debug/error/<code>/` for demonstration error inspection. |
| `ALLOWED_HOSTS` | **Yes** | `.onrender.com,localhost,127.0.0.1` | Comma-separated allowed domain names and host headers. |
| `DATABASE_URL` | **Yes** | `postgresql://user:pass@host:5432/db` | PostgreSQL connection string (defaults to local SQLite if omitted). |
| `MONGO_URI` | No | `mongodb+srv://user:pass@cluster0.xxx.mongodb.net/` | MongoDB Atlas connection string for chat logs and user feedback. |
| `MONGO_DB_NAME` | No | `planmystudy_db` | MongoDB database name. |
| `ANTHROPIC_API_KEY` | No | `sk-ant-api03-...` | Anthropic Claude API key for server-side chat reasoning. |

---

## 🚀 Local Development Setup

### 1. Clone & Set Up Virtual Environment
```bash
git clone <repository_url>
cd python-full

# Create Python 3.12+ virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` to supply your credentials or keep defaults for local SQLite development.

### 3. Run Migrations & Seed Data
```bash
python manage.py migrate
python manage.py seed_data
```
The `seed_data` command populates:
- 14 comprehensive FAQs across Planning, Techniques, Account Security, and General topics.
- 8 Error Codes (400, 401, 403, 404, 429, 500, 503, and application-specific `SP-4221`).

### 4. Create an Admin / Staff Account
```bash
python manage.py createsuperuser
```

### 5. Run the Development Server
```bash
python manage.py runserver 0.0.0.0:8000
```
Visit `http://localhost:8000/` in your browser.

### 6. Run Automated Tests
```bash
python manage.py test
```

---

## ☁️ Step-by-Step Deployment Guide (Free Tiers)

### Part 1: Set Up MongoDB Atlas (Free M0 Cluster)
1. Sign up or log into [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
2. Click **Create a Deployment** &rarr; select **M0 Free Cluster** (Shared).
3. Under **Security & Access**:
   - Create a database user (e.g., `planuser` with a secure password).
   - Under **Network Access**, add IP Address `0.0.0.0/0` (Allow access from anywhere) so Render instances can connect.
4. Click **Connect** &rarr; choose **Drivers** (Python / PyMongo) &rarr; copy the SRV connection string:
   ```
   mongodb+srv://planuser:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
   Save this for `MONGO_URI`.

---

### Part 2: Set Up Managed PostgreSQL on Render (Free Tier)
1. Log into your [Render Dashboard](https://dashboard.render.com).
2. Click **New +** &rarr; select **PostgreSQL**.
3. Fill in details:
   - **Name:** `planmystudy-db`
   - **Database:** `planmystudy`
   - **User:** `planmystudy_user`
   - **Region:** Choose Oregon or Frankfurt (pick same region for web service).
   - **Plan:** Free
4. Click **Create Database**.
5. Once provisioned, copy the **Internal Database URL** (for Render web service) or **External Database URL**.

---

### Part 3: Deploy PlanMyStudy Web Service on Render
1. In the Render Dashboard, click **New +** &rarr; **Web Service**.
2. Connect your Git repository.
3. Configure the settings:
   - **Name:** `planmystudy`
   - **Language:** `Python 3`
   - **Region:** (Same as your PostgreSQL database)
   - **Branch:** `main`
   - **Build Command:** `./build.sh`
   - **Start Command:** `gunicorn planmystudy_project.wsgi:application --bind 0.0.0.0:$PORT`
   - **Plan:** Free
4. In **Environment Variables**, add:
   - `PYTHON_VERSION`: `3.12.8`
   - `DEBUG`: `False`
   - `DEBUG_ROUTES`: `False`
   - `SECRET_KEY`: *(Click "Generate" or provide random string)*
   - `ALLOWED_HOSTS`: `.onrender.com`
   - `DATABASE_URL`: *(Select "From Database" &rarr; `planmystudy-db` / `connectionString`)*
   - `MONGO_URI`: *(Paste your MongoDB Atlas SRV connection string)*
   - `MONGO_DB_NAME`: `planmystudy_db`
   - `ANTHROPIC_API_KEY`: *(Your Anthropic API key)*
5. Click **Create Web Service**.
6. Render will automatically execute `build.sh` (installing dependencies, collecting static files, applying migrations, and running `seed_data`).
7. Open the live URL and verify the health check at `/health/`!

---

## 💡 Proposed Improvement

> **"Let users log daily progress and automatically re-balance the remaining plan when they fall behind."**

### How it will work:
1. **Interactive Check-ins**:
   - Each study slot in `/my-plans/` includes a status toggle: `Completed`, `Partially Done`, or `Missed`.
   - Students check off study blocks or log the actual minutes spent.
2. **Automated Re-balancing Algorithm**:
   - If a student marks a 2-hour hard subject session as `Missed`, the scheduler recalculates the remaining study days.
   - It redistributes the deficit across upcoming study sessions, preserving the mandatory 2-day revision lock while maintaining sustainable daily study limits.
   - If the exam date is too close to comfortably absorb the missed hours, the AI Assistant proactively alerts the student with prioritized topic recommendations.

---

## 🛡️ Security Best Practices Implemented
- **No Hardcoded Secrets**: All keys, URLs, and configurations load strictly from environment variables.
- **CSRF Protection**: Applied across all POST endpoints (`/login/`, `/register/`, `/generate/`, `/api/chat/`, `/api/feedback/`).
- **Production Cookie Hardening**: `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, `HttpOnly=True`, `SameSite='Lax'`.
- **Layered Rate Limiting**:
  - `POST /login/`: Maximum 5 attempts/minute per IP (returns 429).
  - `POST /api/chat/`: Maximum 20 queries/minute per IP (returns JSON 429).
- **Ownership Verification**: Strict multi-tenant data isolation—users can only view, edit, or delete their own study schedules; unauthorized access triggers HTTP 403.
- **Staff-Gated Dashboard**: `/staff/tickets/` strictly restricted to accounts with `is_staff=True`.
- **Defensive API Calls**: 3-second timeout on ZenQuotes with 1-hour cache and resilient fallback; 10-second timeout on Anthropic Claude API with automatic keyword-matching fallback.

---

## 📄 License
This project is licensed under the MIT License.
