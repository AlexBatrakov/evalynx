# Evalynx Architecture

## Overview

Evalynx is a backend platform for managing computational runs. It acts as a control plane around external computation systems rather than owning the computation logic itself.

The MVP architecture is designed around one core concern: a reliable and inspectable run lifecycle.

```text
Client
  ->
FastAPI API
  ->
Service Layer
  ->                 \
PostgreSQL            Redis + RQ
                        ->
                      Worker
                        ->
                    Runner Adapter
                        ->
              External Computational System
```

## Architectural Intent

Evalynx is meant to make execution observable and reproducible, not merely to trigger scripts. The backend is therefore responsible for:

- durable lifecycle state
- consistent result storage
- clear failure reporting
- retry semantics
- provenance capture for later inspection

## Core Domain

The central domain object is `Run`.

A run represents:

- a selected runner type
- a submitted configuration
- a persistent lifecycle state
- one or more execution attempts
- structured outputs such as summaries, metrics, and artifacts

The MVP also includes `Project` as the container for related runs.

## MVP Components

### API Layer

The API is responsible for:

- request validation
- project creation and retrieval
- run creation and retrieval
- retry entry points
- exposing lifecycle state to clients

### Service Layer

The service layer coordinates:

- config normalization
- run persistence
- queue submission
- status transitions
- result storage

### Persistence Layer

The persistence layer is the source of truth for:

- projects
- runs
- structured terminal runner results

Lifecycle state should remain database-backed and queryable rather than hidden inside worker-local execution flow.

Packet 04 extends the `Run` model beyond lifecycle state so a completed run can retain:

- a compact summary
- result metrics
- execution metadata
- artifact manifests
- warnings
- structured error details

These surfaces are intentionally stored as clear JSON-backed fields on `Run` for the first real runner integration instead of being exploded into several new relational tables too early. SQLite is suitable for local development in the current repository, while PostgreSQL remains the intended MVP deployment target.

### Queue and Worker

Workers are responsible for:

- picking up queued runs
- marking attempts as running
- invoking a runner adapter
- persisting terminal results from the runner contract
- recording failure information

The long-term target remains Redis + RQ. The current vertical slice uses an explicit in-process queue/worker seam so the lifecycle is already separated from the request path without over-expanding early infrastructure work.

### Runner Boundary

Evalynx integrates with external systems through runner adapters.

The default MVP preference is an adapter plus subprocess boundary rather than deeply embedding external project internals into the application runtime. This keeps the integration surface explicit, reduces coupling, and makes reproducibility metadata easier to capture.

The current real adapter is `solo_wargame`, which:

- validates and normalizes a narrower Evalynx-side config
- materializes an upstream `episode_batch` request file
- allocates an Evalynx-managed artifact directory
- invokes `solo_wargame_ai.cli.episode_batch_runner --request-file ...`
- treats the upstream stdout JSON payload as the source of truth for structured result persistence

## Run Lifecycle

The intended lifecycle for the MVP is:

1. receive a run request
2. validate and normalize config
3. persist the run as `queued`
4. enqueue background execution
5. mark the active attempt as `running`
6. invoke the selected runner adapter
7. store summary data, metrics, and artifact references
8. mark the run as `succeeded` or `failed`

This lifecycle is a product concern, not just an implementation detail. Much of the value of Evalynx comes from making these states explicit and queryable.

## Reproducibility

Reproducibility is a first-class product concern.

The MVP should capture:

- raw submitted config
- normalized config
- config hash
- execution command
- source repository path
- code version or commit when feasible

The long-term goal is to make it easy to answer questions such as:

- what exactly ran?
- which config produced this result?
- which code version was used?
- what failed, and on which attempt?

## Initial API Surface

Current Packet 04 endpoints:

- `POST /projects`
- `GET /projects`
- `POST /runs`
- `GET /runs`
- `GET /runs/{id}`
- `GET /projects/{id}/runs`
- `GET /health`

Planned later MVP endpoint:

- `POST /runs/{id}/retry`

## Initial Data Model

The early MVP is expected to revolve around:

- `Project`
- `Run`
- `RunAttempt`
- `RunMetric`
- `RunArtifact`

## Current Runner Strategy

The first real runner integration is `solo-wargame-ai` through its bounded `episode_batch` JSON contract.

It is a good first integration because it already has reproducible execution surfaces and does not depend on private personal data. The Evalynx-side config intentionally stays narrower than the full transport payload so clients provide logical inputs such as mission path, builtin policy, seed spec, and whether episode rows should be written, while Evalynx fills transport-only fields such as schema version, operation, and artifact directory.

A wearable analytics public-demo path remains a strong candidate for a later second runner.

## Planned Code Layout

The repository is expected to evolve toward a structure similar to:

```text
app/
  api/
  core/
  db/
  repositories/
  runners/
  schemas/
  services/
  workers/
tests/
docs/
```

## Non-Goals For Early Development

The early MVP does not aim to include:

- user authentication and authorization
- dashboards or frontend clients
- multiple production-grade runners at once
- generalized plugin systems
- distributed scheduling
- cloud artifact storage

The initial goal is a credible backend execution platform with one strong vertical slice.
