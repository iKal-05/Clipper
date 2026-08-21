# Clipper

Local desktop web app for Windows 11 that turns a YouTube URL into ready-to-upload vertical shorts (9:16, ≤60s) with auto-reframe, subtitles, Ken Burns zoom, and supporting assets (title, hook, description, hashtags, tags, thumbnail, keywords).

See [docs/PROJECT.md](docs/PROJECT.md) for the full spec and [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) for stack, structure, milestones, and conventions.

## Quick start

Prereqs: Python 3.11+, Node 20+, ffmpeg in PATH, Windows 11.

```powershell
# 1. Install ffmpeg (skip if already installed)
pwsh scripts/install-ffmpeg.ps1

# 2. Backend (base install — for AI extras use: pip install -e "api[ai]")
python -m pip install -e api

# 3. Frontend
cd web
npm install
cd ..

# 4. Run both servers (api on :8000, web on :5173)
pwsh scripts/dev.ps1
```

Open http://localhost:5173.

## Project layout

```
api/    FastAPI backend, pipeline stages, services
web/    Vite + React frontend, Tailwind + shadcn/ui
shared/ JSON Schemas shared between api and web
docs/   PROJECT.md (spec) + IMPLEMENTATION.md (this build plan)
scripts dev/install/clean/verify PowerShell helpers
```

## Development

- Python: `ruff format api` and `ruff check api`; `pytest api/tests`.
- TypeScript: `cd web && npm run lint`, `npm run format`, `npm run test`.
