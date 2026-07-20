# How to Develop

Everything you need to run EnglishConnect locally, test it, and ship a change. For the big picture, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Prerequisites

- **Docker** — runs PostgreSQL and Redis.
- **Python 3.12** — the backend and services.
- **Node.js 20+** — the React frontend.
- **A GPU** — only if you run the *optional* local STT/TTS stack. The default voice path uses the Azure Realtime API and needs no GPU.

## First-time setup

1. **Create your `.env`.** `start.sh` copies `.env.example` to `.env` on first run, or do it yourself:

   ```bash
   cp .env.example .env
   ```

   Fill in the keys that matter for what you're doing. At minimum the app needs the Postgres/Redis URLs (defaults work with the bundled Docker services) and the Azure OpenAI settings (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`) for the agent and voice. Auth and local-LLM keys are optional.

2. **Start infrastructure and the local services.** `start.sh` brings up Docker, creates Python virtual environments, ingests lesson content on first run, and starts the content service:

   ```bash
   ./start.sh          # infra + services
   ./start.sh infra    # only PostgreSQL + Redis
   ./start.sh services # only local services (infra already up)
   ```

## Running the app

`start.sh` does **not** launch the backend API or the frontend — you run those yourself so they're easy to debug.

**Backend API** (port 8000):

```bash
cd src/backend
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --env-file ../../.env
```

**Frontend** (Vite dev server, port 5173):

```bash
cd src/frontend
npm install          # first time only
npm run dev
```

Open the **Vite URL** (<http://localhost:5173>), not port 8000 — Vite proxies `/api` and `/ws` to the backend. Resize the window across 768px to switch between the mobile and desktop layouts.

**In VS Code:** the `Backend + Frontend` compound launch config starts both with the right working directory, `.env`, and `--reload`.

### Ports

| Service      | Port | Started by                     |
|--------------|------|--------------------------------|
| Frontend     | 5173 | `npm run dev`                  |
| Backend API  | 8000 | `uvicorn` (manual / VS Code)   |
| PostgreSQL   | 5432 | `./start.sh` (Docker)          |
| Redis        | 6379 | `./start.sh` (Docker)          |
| Content MCP  | 8003 | `./start.sh services`          |
| STT (opt.)   | 8001 | manual — local GPU only        |
| TTS (opt.)   | 8002 | manual — local GPU only        |

Stop everything with `./stop.sh`.

## Testing

This project follows **test-driven development** — write a failing test, watch it fail, write the minimum to pass. See the RED-GREEN-REFACTOR section in [CLAUDE.md](CLAUDE.md).

**Backend** (pytest, from the repo root):

```bash
python -m pytest tests/unit/ -v              # unit
python -m pytest tests/integration/ -v       # integration (needs the database)
python -m pytest tests/e2e/ -v               # end-to-end (needs running services)
python -m pytest tests/unit/test_audio_router.py::test_name -v   # a single test
```

`pytest.ini` marks tests `unit`, `integration`, `e2e`, `slow`, and `agent_integration` (the last calls real Azure OpenAI and costs money).

**Frontend** (Vitest):

```bash
cd src/frontend
npm run test:run     # once
npm run test         # watch mode
```

## Content pipeline

Lessons flow from source PDFs to the database to generated audio. `start.sh` ingests content automatically on first run when the database is empty. To run it by hand:

```bash
./start.sh ingest
```

For the full pipeline — new courses, regenerating audio, demo samples — see:

- [documentation/CONTENT-INGESTION-PIPELINE.md](documentation/CONTENT-INGESTION-PIPELINE.md)
- [documentation/HOW-TO-GENERATE-DEMO-SAMPLES.md](documentation/HOW-TO-GENERATE-DEMO-SAMPLES.md)
- [documentation/LOCAL-TTS-VOICES.md](documentation/LOCAL-TTS-VOICES.md)

## Shipping a change

1. Branch from `main`, make the change test-first, and keep the suites green.
2. Open a pull request against `main`. The `test` job runs on every PR.
3. Merge to `main`. That triggers `deploy.yml` (`test → build-and-push → sync-audio → deploy-app`) and ships to Azure Container Apps — no manual deploy step. Expect roughly 25 minutes end to end; the audio sync is the slow part.

Infrastructure changes under `azure/**` are deployed separately by `deploy-infra.yml`.

## Optional: local voice stack

The default voice path is the Azure Realtime API, so you can ignore this unless you want fully local, offline speech. The STT and TTS services need a CUDA GPU and are commented out in `start.sh`; uncomment those blocks and start each service manually. See:

- [documentation/LOCAL-TTS-VOICES.md](documentation/LOCAL-TTS-VOICES.md)
- `src/services/stt/` and `src/services/tts-mcp/` for each service's own README and tests.
