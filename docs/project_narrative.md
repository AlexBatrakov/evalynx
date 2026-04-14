# Project Narrative

## One-Sentence Positioning

Evalynx is a backend control plane for computational runs.

## Problem Statement

It provides a structured way to submit, execute, track, and reproduce jobs that would otherwise be managed through ad-hoc scripts, logs, and files.

## Backend Skills Signal

It demonstrates API design, relational data modeling, background job processing, execution lifecycle management, external system integration, and reproducibility-focused backend engineering.

## Longer Framing

Many technical projects already have strong computational cores but weak service boundaries. Computation may be reproducible in principle, yet execution metadata is incomplete, result discovery is manual, and run comparison depends on scattered files or ad-hoc scripts.

Evalynx addresses that gap by introducing a backend service layer around those workflows. The platform is designed to persist run metadata, execute jobs asynchronously, expose lifecycle state, and retain structured outputs such as summaries, metrics, and artifact references.

The finished MVP keeps that story intentionally narrow: one strong vertical slice, one real runner integration, and a backend-first implementation that emphasizes lifecycle reliability over breadth. In practical terms, it proves an end-to-end flow from API request to queued job, worker execution, persisted attempt history, and reproducibility-aware result storage.

The default reviewer path uses a built-in `stub` runner through Docker Compose so the async lifecycle is easy to validate quickly, while the real external integration story remains the host-based `solo_wargame` adapter.

## Resume-Style Description

Built Evalynx, a FastAPI/PostgreSQL/Redis backend control plane for submitting, executing, tracking, and reproducing computational runs with asynchronous job handling, attempt-aware execution history, structured result storage, and reproducibility-focused metadata.
