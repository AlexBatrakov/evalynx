# Evalynx

Evalynx is a backend control plane for computational runs.

The project provides a service layer for submitting, executing, tracking, and reproducing runs across external computational systems such as simulations and analytics pipelines. The goal is to build a backend-first platform around run lifecycle management rather than another standalone compute engine.

## Why This Project Exists

Many technical workflows already have strong computational cores but weak service boundaries:

- jobs are launched through ad-hoc scripts
- execution metadata is incomplete
- results are scattered across logs and files
- comparing runs is manual and error-prone

Evalynx addresses that gap by introducing:

- a consistent API for run submission
- persistent run metadata
- asynchronous execution
- structured summaries, metrics, and artifacts
- reproducibility-focused execution records

## MVP Focus

The initial MVP is intentionally narrow. It aims to demonstrate one solid backend vertical slice:

- FastAPI API
- PostgreSQL persistence
- Redis + RQ background jobs
- `Project` and `Run` lifecycle management
- one real external runner integration
- reproducibility metadata, result summaries, and artifact references

The first planned real runner is `solo-wargame-ai`.

## Repository Guide

Project conventions and contribution rules live in [CONTRIBUTING.md](CONTRIBUTING.md).

## Public Roadmap

High-level milestones live in [ROADMAP.md](ROADMAP.md).

## Architecture

The current public MVP architecture is described in [docs/architecture.md](docs/architecture.md).

## Status

Early development. The repository is currently being bootstrapped around a backend-oriented MVP.
