# Viral Gaming News – Backend Service

A production-ready FastAPI service that continuously collects gaming news from RSS feeds and Reddit, detects viral topics related to hybrid-casual and mobile gaming, and stores results in PostgreSQL.

---

## Architecture

```
backend/
├── app/
│   ├── main.py              # FastAPI app + lifespan (startup/shutdown)
│   ├── config.py            # Settings loaded from environment / .env
│   ├── database.py          # SQLAlchemy engine, session factory, Base
│   ├── models/
│   │   └── news.py          # ViralGamingNews ORM model
│   ├── services/
│   │   ├── rss_fetcher.py   # Fetch & parse RSS feeds
│   │   ├── reddit_fetcher.py# Fetch hot posts from subreddits via PRAW
│   │   ├── keyword_filter.py# Filter articles by target keywords
│   │   └── virality_engine.py # Deduplicate + compute virality score
│   ├── scheduler/
│   │   └── job_runner.py    # APScheduler background job (runs every 10 min)
│   └── routes/
│       └── news.py          # GET /news, GET /news/{id}
├── requirements.txt
├── Dockerfile
└── .env.example
```

---

## Prerequisites

- Python 3.12+
- PostgreSQL 14+ running locally or via Docker
- Reddit OAuth app credentials (read-only script app)

---

## Setup

### 1. Install dependencies

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your DATABASE_URL and Reddit credentials
```

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/viral_news` | PostgreSQL DSN |
| `REDDIT_CLIENT_ID` | – | Reddit OAuth client ID |
| `REDDIT_SECRET` | – | Reddit OAuth secret |
| `REDDIT_USER_AGENT` | `viral-news-bot/1.0` | Reddit API user-agent string |
| `FETCH_INTERVAL_MINUTES` | `10` | Scheduler interval |
| `VIRALITY_THRESHOLD` | `7.0` | Minimum score to store an article |
| `REDDIT_POST_LIMIT` | `25` | Posts fetched per subreddit per run |

### 3. Create the database

```bash
# Using psql
createdb viral_news

# Or with Docker
docker run -d \
  -e POSTGRES_DB=viral_news \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:16-alpine
```

### 4. Run database migrations

Tables are created automatically on first startup via SQLAlchemy's `create_all`. No separate migration step is needed for a fresh database.

### 5. Start the API server

```bash
uvicorn app.main:app --reload
```

The server will start on [http://localhost:8000](http://localhost:8000).

On startup it immediately runs one ingestion pass, then schedules subsequent runs every 10 minutes.

---

## API Endpoints

### `GET /health`
Liveness probe.

```json
{"status": "ok"}
```

### `GET /news`
Returns paginated viral gaming news (newest first).

Query params:
- `page` (int, default 1)
- `page_size` (int, default 20, max 100)
- `min_score` (float, default 0.0)

```json
{
  "total": 42,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": "uuid",
      "title": "...",
      "source": "Pocket Gamer",
      "url": "https://...",
      "summary": "...",
      "virality_score": 9.5,
      "created_at": "2025-03-05T10:00:00Z"
    }
  ]
}
```

### `GET /news/{id}`
Returns a single article by UUID. Returns `404` if not found.

---

## Running with Docker

```bash
# Build image
docker build -t viral-news-backend .

# Run (assumes PostgreSQL is accessible at host.docker.internal)
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:5432/viral_news \
  -e REDDIT_CLIENT_ID=xxx \
  -e REDDIT_SECRET=xxx \
  viral-news-backend
```

---

## Virality Scoring

```
score = source_count × 3 + reddit_upvotes × 0.01 + recency_weight
```

| Component | Max contribution | Notes |
|---|---|---|
| `source_count × 3` | unbounded | Number of sources covering same story |
| `reddit_upvotes × 0.01` | unbounded | Upvotes on Reddit posts |
| `recency_weight` | 5.0 | Linear decay over 24 hours |

Articles with `score >= 7.0` (configurable) are stored as viral.

---

## Reddit App Setup

1. Go to [https://www.reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Click **create another app**
3. Choose **script**
4. Copy the client ID (under the app name) and secret into `.env`
