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

The first planned real runner is `solo-wargame-ai`, chosen because it already has strong reproducibility surfaces and does not depend on private personal data.

## Planned User Flow

The MVP is centered around one main workflow:

1. Create a project.
2. Submit a run with a runner type and config.
3. Persist the run as `queued`.
4. Execute the run asynchronously through a worker.
5. Store terminal state, summary data, metrics, and artifact references.
6. Inspect the completed or failed run through the API.

## Documentation Map

- [Architecture](docs/architecture.md)
- [Project narrative](docs/project_narrative.md)
- [Public roadmap](ROADMAP.md)
- [Contribution guide](CONTRIBUTING.md)

## Local Development

Evalynx now includes a minimal runnable FastAPI bootstrap with a `/health` endpoint.

Requirements:

- Python 3.11+

Setup:

1. Create a virtual environment: `python -m venv .venv`
2. Activate it: `source .venv/bin/activate`
3. Install dependencies: `pip install -e '.[dev]'`
4. Start the service: `uvicorn app.main:app --reload`
5. Run tests: `pytest`

## Current Status

The repository is in early development.

The current foundation now includes:

- project framing
- architecture and roadmap docs
- contribution guide
- git and GitHub setup
- FastAPI service bootstrap
- configuration scaffold
- pytest-based test harness
- `GET /health`

The next implementation milestone is the run lifecycle vertical slice: initial persistence, run creation flow, queue submission, and the first stubbed asynchronous execution path.
