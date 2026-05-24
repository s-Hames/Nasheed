# Nasheed Streaming & Search API (Backend MVP)

A lightweight, production-style, async-first Python backend built with **FastAPI** to query, score, and extract direct playable audio streams for Islamic Nasheeds from YouTube. It filters out non-nasheed content (e.g. DJ remixes, reverb versions, pop music) using custom scoring rules.

---

## Technical Stack

- **Framework**: Python 3.12+, FastAPI (ASGI)
- **Server**: Uvicorn
- **Extractor**: `yt-dlp` (asynchronously integrated via thread pools)
- **Database**: SQLite with `SQLAlchemy` (Asyncio ORM using `aiosqlite`)
- **Validation**: Pydantic v2
- **Containerization**: Docker

---

## Features

1. **YouTube Search integration**: Leverages `yt-dlp`'s flat playlists extractor to query metadata (video ID, title, channel name, thumbnail, duration, and upload date) with zero-blocking overhead.
2. **Nasheed Suitability Filter**:
   - **Boost words (+10 pts)**: `nasheed`, `no music`, `vocals only`, `islamic`.
   - **Blacklist words (-100 pts / auto-reject)**: `remix`, `dj`, `slowed`, `reverb`, `lofi`, `edit`, `status`, `music video`.
   - **Trusted Channels (+20 pts)**: Search hits from channels like `Muhammad Al Muqit`, `Labbayk`, `Ahmed Bukhatir`, etc. receive an automatic score boost.
   - **Threshold rejection**: Filters and rejects any video scoring below `SCORE_THRESHOLD` (default is `0`).
3. **Playable Stream Extraction**: Direct extraction of the high-quality audio stream link (M4A/WebM audio format) from YouTube IDs without proxying the heavy binary stream payload through the backend server.
4. **Trending System**: Keeps a registry of cataloged nasheeds, tracking their total plays. `/trending` returns items sorted by most played to least played.
5. **Basic Rate Limiting**: In-memory IP-based sliding window rate limiter protects endpoints against heavy automated crawling.
6. **Structured API Responses**: Standard success envelopes and friendly, schema-driven, non-sensitive error formats.

---

## Directory Structure

```text
app/
├── main.py                  # App entry point, lifecycle hooks & middleware setup
├── api/
│   ├── deps.py              # Database session injection dependency
│   ├── endpoints/
│   │   ├── health.py        # /health endpoint
│   │   ├── search.py        # /search and /trending endpoints
│   │   ├── stream.py        # /stream/{video_id} endpoint
│   │   └── video.py         # /video/{video_id} metadata endpoint
│   └── middleware/
│       └── rate_limit.py    # Sliding window IP-based rate limiting
├── core/
│   ├── config.py            # Pydantic Settings configuration from env variables
│   └── exceptions.py        # Custom exceptions and global handlers
├── database/
│   ├── base.py              # Declarative Base
│   └── session.py           # Async SQLAlchemy sessionmaker
├── models/
│   ├── video.py             # Video cataloging (YouTube metadata + play count)
│   ├── search_history.py    # Search queries hit logs
│   └── trusted_channel.py   # Seeding table for verified channels
├── schemas/
│   ├── health.py            # Pydantic models for health endpoint
│   ├── search.py            # Envelope, streaming and search query models
│   └── video.py             # Pydantic models for Video catalog items
└── utils/
    └── logger.py            # Centralized logging configuration
```

---

## Getting Started (Local Run)

### 1. Prerequisites
- Python 3.12 or higher.
- `ffmpeg` installed on your operating system (recommended for yt-dlp compatibility).

### 2. Installation
Clone the repository, create a virtual environment, and install dependencies:

```bash
# Create environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 3. Setup Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default configuration values:
```env
DATABASE_URL=sqlite+aiosqlite:///./nasheed.db
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
SCORE_THRESHOLD=0
RATE_LIMIT_PER_MINUTE=60
```

### 4. Run the Server
Startup the application using Uvicorn:
```bash
uvicorn app.main:app --reload
```
The server will start at `http://127.0.0.1:8000`. You can visit Swagger API Docs at `http://127.0.0.1:8000/docs`.

---

## Docker Execution

Build and run the container locally:

```bash
# Build the Docker image
docker build -t nasheed-backend .

# Run the container
docker run -p 8000:8000 --env-file .env nasheed-backend
```

---

## API Documentation Reference

All endpoints return a standardized JSON envelope:
- **Success**: `{"success": true, "data": ...}`
- **Failure**: `{"success": false, "error": {"code": "...", "message": "...", "details": {...}}}`

### 1. API Health Check
- **Endpoint**: `GET /health`
- **Response**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "database": "healthy"
  }
}
```

### 2. Search Nasheeds
- **Endpoint**: `GET /search?q={query}`
- **Parameters**: `q` (string, required) - search term.
- **Response**: Returns matching, sorted, and scored nasheeds.
```json
{
  "success": true,
  "data": [
    {
      "youtube_id": "dQw4w9WgXcQ",
      "title": "Beautiful Islamic Vocals - Quran Recitation Nasheed",
      "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
      "duration": 240,
      "channel": "Islam Vocals",
      "score": 20,
      "upload_date": "20231024",
      "id": 1,
      "play_count": 0,
      "created_at": "2026-05-24T14:32:00",
      "updated_at": "2026-05-24T14:32:00"
    }
  ]
}
```

### 3. Retrieve Audio Stream URL
- **Endpoint**: `GET /stream/{video_id}`
- **Parameters**: `video_id` (string, 11-char YouTube ID).
- **Response**: Returns direct audio streaming link from YouTube.
```json
{
  "success": true,
  "data": {
    "video_id": "dQw4w9WgXcQ",
    "stream_url": "https://rr3---sn-4g57kned.googlevideo.com/videoplayback?expire=..."
  }
}
```

### 4. Fetch Video Metadata
- **Endpoint**: `GET /video/{video_id}`
- **Response**: Returns cataloged metadata of a video. If not cataloged yet, details are lazily fetched, filtered, and saved.
```json
{
  "success": true,
  "data": {
    "youtube_id": "dQw4w9WgXcQ",
    "title": "Beautiful Islamic Vocals - Quran Recitation Nasheed",
    "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
    "duration": 240,
    "channel": "Islam Vocals",
    "score": 20,
    "upload_date": "20231024",
    "id": 1,
    "play_count": 5,
    "created_at": "2026-05-24T14:32:00",
    "updated_at": "2026-05-24T14:35:10"
  }
}
```

### 5. Get Trending Nasheeds
- **Endpoint**: `GET /trending?limit=15`
- **Response**: Returns cataloged videos sorted by `play_count` and `score` descending.
```json
{
  "success": true,
  "data": [
    {
      "youtube_id": "dQw4w9WgXcQ",
      "title": "Beautiful Islamic Vocals - Quran Recitation Nasheed",
      "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
      "duration": 240,
      "channel": "Islam Vocals",
      "score": 20,
      "upload_date": "20231024",
      "id": 1,
      "play_count": 105,
      "created_at": "2026-05-24T14:32:00",
      "updated_at": "2026-05-24T14:40:00"
    }
  ]
}
```
