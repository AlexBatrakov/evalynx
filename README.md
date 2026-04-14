# Evalynx

Backend control plane for reproducible computational runs.

Evalynx is a backend-first platform for submitting, executing, tracking, and reproducing runs across external computational systems such as simulations and analytics pipelines. The project focuses on the service layer around computation rather than the computation engines themselves.

## Why Evalynx Exists

Many technical projects already have strong computational cores but weak execution management around them. In practice, that usually means:

- jobs are launched through ad-hoc scripts
- execution metadata is incomplete or inconsistent
- results are scattered across logs, files, and local folders
- comparing runs requires manual reconstruction
- failures are hard to diagnose and retries are poorly tracked

Evalynx addresses that gap with a backend control plane that can:

- accept structured run requests through an API
- persist run metadata in a relational model
- execute jobs asynchronously
- expose lifecycle states such as `queued`, `running`, `succeeded`, and `failed`
- retain summaries, metrics, and artifact references
- capture reproducibility metadata such as normalized config and execution provenance

## What This Project Demonstrates

Evalynx is designed as a backend portfolio project, with emphasis on:

- API design and request validation
- relational data modeling and migrations
- background job processing
- execution lifecycle management
- integration with external systems through explicit adapters
- reproducibility-focused backend engineering

## MVP Scope

The initial MVP is intentionally narrow and aims to prove one strong vertical slice:

- FastAPI application
- PostgreSQL persistence
- Redis + RQ background execution
- `Project` and `Run` lifecycle management
- one real runner integration
- stored summaries, metrics, artifacts, and failure information
- retry support for failed runs

The first integrated real runner is `solo-wargame-ai`, chosen because it already has strong reproducibility surfaces and does not depend on private personal data.

## Planned User Flow

The MVP is centered around one main workflow:

1. Create a project.
2. Submit a run with a runner type and config.
3. Persist the run as `queued`.
4. Execute the run asynchronously through a worker.
5. Store terminal state, summary data, metrics, and artifact references per execution attempt.
6. Inspect the latest run state and attempt history through the API.
7. Retry failed runs without erasing prior failure context.

## Documentation Map

- [Architecture](docs/architecture.md)
- [Project narrative](docs/project_narrative.md)
- [Public roadmap](ROADMAP.md)
- [Contribution guide](CONTRIBUTING.md)

## Run It Locally

There are two intended local paths:

- Reviewer quickstart: Docker Compose plus the built-in `stub` runner. This is the fastest way to validate the asynchronous lifecycle with no external checkout.
- Host development with the real runner: a local Python environment plus the same Dockerized PostgreSQL and Redis services, with a local checkout of `solo-wargame-ai`.

### Reviewer Quickstart

Requirements:

- Docker Desktop or Docker Engine with Compose support

Setup:

1. Copy the example environment if you want a local `.env`: `cp .env.example .env`
2. Start infrastructure: `docker compose up -d postgres redis`
3. Apply migrations: `docker compose run --rm migrate`
4. Start the API and worker: `docker compose up -d api worker`
5. Confirm the API is healthy: `curl http://localhost:8000/health`

If you want a clean demo state, run `docker compose down -v` before repeating the example requests below. The sample IDs assume a fresh database; otherwise, use the IDs returned by your own API responses.

Create a project:

```bash
curl -X POST http://localhost:8000/projects \
  -H 'Content-Type: application/json' \
  -d '{"name":"Reviewer Demo"}'
```

Submit a successful async stub run:

```bash
curl -X POST http://localhost:8000/runs \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id": 1,
    "runner_type": "stub",
    "config": {
      "scenario": "compose-demo-success"
    }
  }'
```

Submit a failing run that can be retried:

```bash
curl -X POST http://localhost:8000/runs \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id": 1,
    "runner_type": "stub",
    "config": {
      "should_fail": true,
      "failure_message": "Reviewer demo failure"
    }
  }'
```

Inspect the lifecycle and retry the failed run:

```bash
curl http://localhost:8000/runs/1
curl http://localhost:8000/runs/2
curl -X POST http://localhost:8000/runs/2/retry
curl http://localhost:8000/runs/2
docker compose logs -f worker
```

Expected reviewer outcomes:

- the health endpoint returns `status: "ok"`
- the first stub run reaches `succeeded` and persists a summary
- the second stub run reaches `failed` with a stored failure message
- retrying the failed run increments `attempt_count` and `current_attempt_number`

Artifacts written by the stack are stored under `./artifacts`.

Shut the stack down with:

```bash
docker compose down
```

If you also want to remove the PostgreSQL volume:

```bash
docker compose down -v
```

### Host Development With The Real Runner

Requirements:

- Python 3.11+
- Docker Desktop or Docker Engine with Compose support
- a local checkout of [`solo-wargame-ai`](https://github.com/AlexBatrakov/solo-wargame-ai) when you want the real runner path

Setup:

1. Copy the environment template: `cp .env.example .env`
2. Start PostgreSQL and Redis: `docker compose up -d postgres redis`
3. Create a virtual environment: `python -m venv .venv`
4. Activate it: `source .venv/bin/activate`
5. Install dependencies: `pip install -e '.[dev]'`
6. Export or edit the required env vars:
   - `EVALYNX_DATABASE_URL=postgresql+psycopg://evalynx:evalynx@localhost:5432/evalynx`
   - `EVALYNX_REDIS_URL=redis://localhost:6379/0`
   - `EVALYNX_SOLO_WARGAME_REPO_PATH=/absolute/path/to/solo-wargame-ai`
   - `EVALYNX_SOLO_WARGAME_PYTHON_COMMAND=/absolute/path/to/solo-wargame-ai/.venv/bin/python`
   - `EVALYNX_ARTIFACT_ROOT=./artifacts`
7. Apply migrations: `alembic upgrade head`
8. Start the API: `uvicorn app.main:app --reload`
9. Start the worker in a second shell: `python -m app.workers.entrypoint`
10. Run tests: `python -m pytest`

For the first real runner family, `POST /runs` accepts `runner_type: "solo_wargame"` with a logical config shaped like:

```json
{
  "project_id": 1,
  "runner_type": "solo_wargame",
  "config": {
    "mission_path": "configs/missions/mission_01_secure_the_woods_1.toml",
    "policy": {
      "kind": "builtin",
      "name": "heuristic"
    },
    "seed_spec": {
      "kind": "range",
      "start": 0,
      "stop": 4
    },
    "write_episode_rows": true
  }
}
```

Evalynx materializes the upstream request file, allocates the artifact directory, invokes the external CLI through a subprocess adapter, and persists summary, metrics, execution metadata, artifacts, warnings, and structured error details back onto the run record and its current attempt snapshot.

Failed runs can be retried through `POST /runs/{id}/retry`. Run detail responses keep the latest run snapshot easy to inspect while also exposing bounded attempt history, and `solo_wargame` artifacts are now written into per-attempt directories under each run.

## Current Status

Evalynx is at a finished MVP milestone.

A reviewer can now:

- run the Docker Compose stack locally
- create a project and submit runs through the API
- observe asynchronous execution through Redis + RQ worker processing
- inspect persisted summaries, metrics, artifacts, and attempt history
- retry failed runs without overwriting prior failure context
- exercise the real `solo_wargame` integration from a host-based app and worker when the external repository is available

The public docs, Compose workflow, and CI checks are aligned around that reviewer-facing backend story.
