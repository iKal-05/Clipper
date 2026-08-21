# Clipper — Implementation Guide

Acuan implementasi untuk aplikasi Clipper. Wajib dibaca sebelum menulis/mengubah kode. Spec fungsional ada di [PROJECT.md](PROJECT.md).

Stack, struktur, dependensi, konvensi, dan urutan milestone di sini.

## 1. Stack

| Layer | Teknologi |
|---|---|
| Backend | Python 3.11+, FastAPI, uvicorn[standard], Pydantic v2 |
| AI/ML (opsional) | openai-whisper (base default), mediapipe, opencv-python-headless, scipy, scikit-learn |
| Video | ffmpeg/ffprobe (sistem binary), ffmpeg-python, yt-dlp |
| Frontend | Vite, React 18, TypeScript 5 |
| UI | Tailwind CSS, shadcn/ui, lucide-react |
| Realtime | WebSocket (FastAPI) |
| Persistence | JSONL per job (append-only log + snapshot) |
| Test | pytest (backend), vitest (frontend) |
| Lint/format | ruff (backend), eslint + prettier (frontend) |
| OS target | Windows 11 |

### Dependensi backend (`api/pyproject.toml`)

Runtime: `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `yt-dlp`, `numpy`, `scipy`, `scikit-learn`, `Pillow`, `ffmpeg-python`, `httpx`, `python-multipart`, `psutil`, `opencv-python-headless`. Emojiextra `ai`: `openai-whisper`, `mediapipe`. Test: `pytest`, `pytest-asyncio`. Lint/format: `ruff`.

### Dependensi frontend (`web/package.json`)

`vite`, `react`, `react-dom`, `typescript`, `tailwindcss`, `postcss`, `autoprefixer`, `class-variance-authority`, `clsx`, `tailwind-merge`, `lucide-react`, `@radix-ui/react-*`. Test: `vitest`, `@testing-library/react`, `jsdom`. Lint/format: `eslint`, `@typescript-eslint/*`, `eslint-plugin-react-hooks`, `eslint-config-prettier`, `prettier`.

### External

- ffmpeg/ffprobe binary. Install via `scripts/install-ffmpeg.ps1` (`winget install Gyan.FFmpeg`).
- Whisper model weights cached di `%LOCALAPPDATA%/clipper/models/`.

## 2. Struktur folder

```
Clipper/
├── docs/
│   ├── PROJECT.md            # source of truth untuk requirement
│   └── IMPLEMENTATION.md     # dokumen ini
├── api/                      # FastAPI backend + pipeline
│   ├── pyproject.toml
│   ├── ruff.toml
│   ├── app/
│   │   ├── main.py           # FastAPI app, CORS, lifespan
│   │   ├── config.py         # pydantic-settings
│   │   ├── deps.py           # DI helper
│   │   ├── routes/
│   │   │   ├── jobs.py
│   │   │   ├── clips.py
│   │   │   └── ws.py
│   │   ├── models/
│   │   │   ├── job.py
│   │   │   ├── clip.py
│   │   │   ├── moment.py
│   │   │   ├── asset.py
│   │   │   └── progress.py
│   │   ├── services/
│   │   │   ├── job_manager.py    # in-memory + JSONL persistence
│   │   │   ├── pipeline_runner.py
│   │   │   ├── progress_bus.py  # WS pub/sub
│   │   │   └── cleanup.py
│   │   └── pipeline/
│   │       ├── __init__.py       # stage registry + StageContext
│   │       ├── download.py
│   │       ├── transcribe.py
│   │       ├── analyze.py
│   │       ├── score.py
│   │       ├── cut.py
│   │       ├── reframe.py
│   │       ├── subtitle.py
│   │       ├── render.py
│   │       └── assets.py
│   └── tests/
│       ├── conftest.py
│       ├── test_url.py
│       ├── test_score.py
│       └── test_keywords.py
├── web/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── components.json
│   ├── .eslintrc.cjs
│   ├── .prettierrc
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css
│       ├── lib/
│       │   ├── api.ts
│       │   ├── ws.ts
│       │   └── utils.ts
│       ├── types/
│       │   └── api.ts
│       ├── components/
│       │   ├── ui/               # shadcn primitives
│       │   ├── JobForm.tsx
│       │   ├── ProgressPanel.tsx
│       │   ├── ClipGrid.tsx
│       │   ├── ClipCard.tsx
│       │   ├── ClipPlayer.tsx
│       │   ├── TrimHandles.tsx
│       │   └── AssetPanel.tsx
│       ├── pages/
│       │   ├── HomePage.tsx
│       │   └── JobPage.tsx
│       └── hooks/
│           ├── useJobSocket.ts
│           └── useSelection.ts
├── shared/
│   ├── schemas/
│   │   ├── job.schema.json
│   │   ├── clip.schema.json
│   │   ├── moment.schema.json
│   │   ├── asset.schema.json
│   │   └── progress.schema.json
│   └── README.md
├── scripts/
│   ├── dev.ps1
│   ├── install-ffmpeg.ps1
│   ├── clean.ps1
│   └── verify.ps1
├── .gitignore
├── .editorconfig
├── README.md
└── LICENSE
```

Runtime artifacts (gitignored) di `api/storage/jobs/<job_id>/`:
`source.mp4`, `audio.wav`, `transcript.json`, `analysis.json`, `moments.json`, `candidates.json`, `log.jsonl`, `clips/clip_<n>.mp4`, `clips/clip_<n>.json`, `assets/<clip_id>/`.

## 3. API contract

Semua JSON. Pydantic v2 model di `api/app/models/`. JSON Schema di `shared/schemas/`. Type mirror ke `web/src/types/api.ts`.

### REST

| Method | Path | Body/Param | Response |
|---|---|---|---|
| GET | `/api/health` | — | `{status:"ok"}` |
| POST | `/api/jobs` | `JobCreate` | `Job` |
| GET | `/api/jobs/{id}` | — | `Job` |
| GET | `/api/jobs/{id}/clips` | — | `Clip[]` |
| POST | `/api/jobs/{id}/clips/select` | `SelectClips` | `Asset[]` (async: 202 + jobId) |
| GET | `/api/clips/{clip_id}/video` | — | `video/mp4` (Range) |
| GET | `/api/clips/{clip_id}/thumbnail` | — | `image/jpeg` |
| GET | `/api/jobs/{id}/assets` | — | `Asset[]` |
| GET | `/api/jobs/{id}/log` | — | streamed `log.jsonl` |
| DELETE | `/api/jobs/{id}` | — | 204, cleanup storage |

`JobCreate = {url, max_clip_seconds=60, max_clips=8, moment_filters?, min_score?, whisper_model="base", use_cloud_model=false}`

### WebSocket `/api/jobs/{id}/stream`

Server → client frames:
```ts
type ProgressEvent =
  | {type:"stage"; stage:string; status:"started"|"finished"; pct:number}
  | {type:"log"; level:"info"|"warn"|"error"; msg:string}
  | {type:"clips_ready"; count:number}
  | {type:"done"}
  | {type:"error"; message:string};
```

### Data shapes

- `Job{id, url, status: queued|downloading|transcribing|analyzing|scoring|cutting|reframing|rendering|done|error, current_stage, pct, prefs, error?, created_at}`
- `Clip{id, job_id, start, end, duration, moment_labels[], score, thumbnail_path, video_path}`
- `Moment{label, start, end, score, evidence}`
- `Asset{clip_id, title, hook, description, hashtags[], platform_tags[], thumbnail_path, keywords[]}`

## 4. Pipeline stage contracts

Setiap stage: `async def run(ctx: StageContext) -> StageResult`. `ctx` bawa `job_id`, `storage_dir`, `prefs`, `progress_cb`, `log`. Stage baca/tulis file di `api/storage/jobs/<job_id>/`.

| Stage | Input | Output | Signature |
|---|---|---|---|
| download | url | source.mp4, audio.wav, meta.json | `download(url, out_dir, progress_cb) -> MediaMeta` |
| transcribe | audio.wav | transcript.json | `transcribe(audio_path, model="base", lang=None) -> Transcript` |
| analyze | source.mp4 | analysis.json | `analyze(media, chunk_sec=300, overlap_sec=5) -> Analysis` |
| score | transcript + analysis | moments.json | `score_moments(transcript, analysis, prefs) -> Moment[]` |
| cut | moments + prefs | candidates.json (top-N ≤60s, cap 15) | `pick_candidates(moments, max_clips, max_sec, min_score) -> Candidate[]` |
| reframe | source + face_tracks + candidates | per-candidate transform JSON | `compute_reframe(source, face_tracks, candidates) -> ReframePlan[]` |
| subtitle | transcript + candidates | per-candidate subs.ass | `slice_subs(transcript, candidates) -> SubtitleFiles` |
| render | reframe + subs + zoom | clips/clip_<n>.mp4 | `render_clip(plan, subs, zoom, out_path) -> Path` |
| assets | clip + transcript + moments | assets.json | `generate_assets(clip, transcript, moments) -> Asset` |

Zoom: deteksi local score peak di dalam clip → ffmpeg `zoompan` keyframes 1.0→1.2 sepanjang 1.5s di sekitar peak. Reframe fallback: tidak ada face track → center-crop + blur pad.

Moment labels (minimal): Aha, Insight, Fakta mengejutkan, Lucu, Emosional, Inspiratif, Kontroversial, Viral, Hook, Retensi.

## 5. Milestone

Setiap milestone shippable & testable.

- **M1 — Scaffold.** Folder, pyproject, package.json, ruff.toml, tsconfig, vite/tailwind/shadcn init, .gitignore, README, dokumen ini. Healthcheck ok, Vite render "Clipper".
- **M2 — Backend hello-world.** CORS localhost:5173, in-memory JobManager + JSONL, WS echo, progress_bus.
- **M3 — Frontend hello-world.** Vite app, HomePage (URL input), JobPage (WS badge), shadcn Button + Input.
- **M4 — Download stage.** yt-dlp + WS progress. test_url.py. Manual: 10-min TED talk.
- **M5 — Transcribe stage.** Whisper base, chunked. transcript.json.
- **M6 — Analyze + score.** cv2 frame diff, motion, mediapipe face, scipy audio energy/pitch/laughter. score.py TF-IDF + prosody + visual. test_score, test_keywords.
- **M7 — Cut + reframe + render.** Top-N selection, reframe JSON, ffmpeg pipeline. Verify 9:16, H.264/AAC, 720×1280, ≥4 Mbps.
- **M8 — Subtitle overlay.** ASS, WCAG AA contrast (white text, black outline + 4px shadow), ±200ms sync.
- **M9 — Asset generation.** Heuristic templates + TF-IDF top-K. Title (≤100), hook (≤15), description (≤5000, CTA), ≤15 hashtags, platform tags, thumbnail (best frame + PIL overlay), 5–10 keywords.
- **M10 — UI grid + selection + trim + cloud-stub.** ClipGrid, ClipCard, inline video, checkboxes, TrimHandles, Confirm → /clips/select, AssetPanel, cloud-model toggle (no-op, default off).
- **M11 — Polish.** Stage error boundaries + retry, structured log.jsonl, cache cleanup endpoint, psutil RAM monitor, chunked long-video path.

v1 scope: skip upload queue. Cloud model opt-in = stub (disabled by default, no API call).

## 6. Konvensi kode

### Python (ruff)

`ruff.toml`:
```toml
target-version = "py311"
line-length = 100

[lint]
select = ["E", "F", "W", "I", "B", "UP", "SIM", "RUF", "ASYNC"]
ignore = ["E501"]
```
Format: `ruff format`. Import sorted (`I`). Naming: snake_case module/function, PascalCase class, SCREAMING_SNAKE constant.

### TypeScript (eslint + prettier)

eslint: `eslint:recommended`, `plugin:@typescript-eslint/recommended`, `plugin:react-hooks/recommended`, `prettier`. Prettier: `{singleQuote:true, semi:true, printWidth:100}`. Naming: camelCase var, PascalCase component, kebab-case folder.

### General

- Folder kebab-case, file `.py` snake_case, file `.tsx` PascalCase component, `.ts` helper camelCase.
- Tiap stage module satu tanggung jawab, no cross-stage import kecuali via `ctx`/data file.
- Service layer (`services/`) orkestrasi, pipeline (`pipeline/`) eksekusi murni.
- Input validation di route (Pydantic) trust boundary.
- Tidak ada data audio/video keluar ke layanan eksternal kecuali user opt-in `use_cloud_model=true` (v1: stub no-op).

## 7. Performance & acceptance

Chunked: `analyze.py` pakai `cv2.VideoCapture` per-frame (video tidak di-load semua). Chunk 300s overlap 5s. Whisper sekali di audio penuh (fp16/int8). Render stream via ffmpeg pipe, tanpa raw frame intermediate di Python. RAM ≤2GB: (1) satu frame per waktu, (2) flush analysis JSON per chunk, (3) `del arr; gc.collect()` per stage.

`scripts/verify.ps1 <job_id>`:
1. ffprobe clip → assert H.264, AAC, 720×1280, bitrate ≥4 Mbps, fps 24–60.
2. Sample 10 subtitle timestamp → drift vs transcript ≤±200ms.
3. MediaPipe @1fps → face-center ≥80% frame.
4. Wall-clock ≤7 min untuk input 15 min.
5. Peak RSS via psutil ≤2GB.

## 8. Task tracking

Milestone progress track via task list (TaskCreate/TaskUpdate) per sesi. Saat mulai milestone, set task `in_progress`; selesai → `completed`.
