# Evalynx Architecture

## Overview

Evalynx is a backend platform for managing computational runs. It acts as a control plane around external computation systems rather than owning the computation logic itself.

The MVP architecture is designed around one core concern: a reliable run lifecycle.

```text
Client
  ->
FastAPI API
  ->
Service Layer
  ->
PostgreSQL
  ->
Redis + RQ
  ->
Worker
  ->
Runner Adapter
  ->
External Computational System
```

## Core Domain

The central domain object is `Run`.

A run represents:

- a selected runner type
- a submitted configuration
- a persistent lifecycle state
- execution attempts
- structured outputs such as summaries, metrics, and artifacts

The MVP also includes `Project` as the container for related runs.

## MVP Components

### API Layer

The API is responsible for:

- request validation
- run creation and retrieval
- project creation and retrieval
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

PostgreSQL is the source of truth for:

- projects
- runs
- run attempts
- metrics
- artifact references

### Queue and Worker

Redis and RQ handle asynchronous execution. Workers are responsible for:

- picking up queued runs
- marking attempts as running
- invoking a runner adapter
- persisting terminal results
- recording failure information

### Runner Boundary

Evalynx integrates with external systems through runner adapters.

The default MVP preference is an adapter plus subprocess boundary rather than deeply embedding external project internals into the application runtime. This keeps the integration surface explicit and makes reproducibility metadata easier to capture.

## Reproducibility

Reproducibility is a first-class product concern.

The MVP should capture:

- raw submitted config
- normalized config
- config hash
- execution command
- source repository path
- code version or commit when feasible

## Initial API Surface

Planned MVP endpoints:

- `POST /projects`
- `GET /projects`
- `POST /runs`
- `GET /runs`
- `GET /runs/{id}`
- `GET /projects/{id}/runs`
- `POST /runs/{id}/retry`
- `GET /health`

## Initial Runner Strategy

The first real runner target is `solo-wargame-ai`.

It is a good first integration because it already has reproducible execution surfaces and does not depend on private personal data. A wearable analytics public-demo path remains a strong candidate for a later second runner.

## Non-Goals For Early Development

The early MVP does not aim to include:

- user authentication and authorization
- dashboards or frontend clients
- multiple production-grade runners at once
- generalized plugin systems
- distributed scheduling
- cloud artifact storage

The initial goal is a credible backend execution platform with one strong vertical slice.
