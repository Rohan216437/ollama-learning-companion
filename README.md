# AI Learning Companion

Paste a YouTube URL, get an AI-generated study guide: summary, key points, glossary,
flashcards, and a practice quiz — exportable as a PDF.

## Stack
- **Frontend:** HTML5, CSS3 (custom design system), Bootstrap 5, vanilla JS
- **Backend:** Python Flask
- **Database:** SQLite by default, swappable for MySQL via `DATABASE_URL`
- **AI:** Local Ollama (`POST /api/chat`)
- **Transcript:** `youtube-transcript-api`
- **PDF export:** ReportLab

## Setup

```bash
cd ai-learning-companion
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
```

### Ollama Setup

1. Install and start Ollama (if not already running):
   ```bash
   ollama serve
   ```
2. Verify Ollama is running:
   ```bash
   curl http://localhost:11434
   # or
   ollama list
   ```
3. Pull the required model:
   ```bash
   ollama pull llama3.1:8b
   ```

### Configuration (.env)

The following settings are configurable via environment variables in `.env`:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_TIMEOUT=300
OLLAMA_TEMPERATURE=0.2
OLLAMA_MAX_TRANSCRIPT_CHARS=45000
```

Start the application:
```bash
python app.py
```

Visit **http://localhost:5000**.

## How it works
1. `POST /api/analyze` — takes a YouTube URL, extracts the video id, pulls metadata
   (title/channel/thumbnail via YouTube's oEmbed endpoint) and the transcript
   (`youtube_transcript_api`).
2. The transcript is sent to local Ollama with a prompt requesting strict JSON containing
   a summary, key points, glossary, quiz, and flashcards.
3. Results are stored in the `video_analyses` table (SQLite/MySQL/PostgreSQL) and rendered on
   `/result/<id>` with tabs for each section.
4. `/export/<id>/pdf` renders the same data into a formatted PDF with ReportLab.

## Project structure
```
app.py                   # Flask app + routes
config.py                # Env-driven configuration
models.py                # SQLAlchemy models
services/
  youtube_service.py     # URL parsing, metadata, transcript fetch
  ollama_service.py      # Ollama HTTP API -> structured JSON + validation
  pdf_service.py         # ReportLab PDF builder
templates/               # Jinja2 + Bootstrap 5 templates
static/css/style.css     # Custom design system
static/js/               # analyze.js (async form), quiz.js (interactive quiz)
```

## Migrating to MySQL / PostgreSQL
Set `DATABASE_URL` in `.env`, e.g.:
```
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/learning_companion
```
Install a driver (`pip install pymysql` or `psycopg2-binary`) and restart — `db.create_all()` will
create the tables automatically.

## Notes
- Videos without captions/transcripts (disabled or auto-captions off) cannot be
  processed — this is a YouTube-side limitation, not a bug.
- Transcripts are truncated to ~45k characters before being sent to Ollama to stay
  within a safe prompt budget for very long videos.
