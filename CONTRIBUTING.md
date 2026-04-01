# Contributing

## Project Focus

Evalynx is a backend control plane for computational runs. The project is not a simulation engine or analytics notebook; it is the service layer that can submit, execute, track, and reproduce runs across external computational systems.

The current priority is a narrow MVP:

- FastAPI API
- PostgreSQL persistence
- Redis + RQ background execution
- `Project` and `Run` lifecycle
- one real runner integration (`solo-wargame-ai`)
- reproducibility metadata, summaries, metrics, and artifacts

## Development Principles

- Use Python 3.11+.
- Keep layers explicit: API -> services -> repositories -> worker/runner boundary.
- Prefer integrating external computational repos through adapter + subprocess boundaries by default.
- Treat reproducibility as a first-class feature:
  - store raw config and normalized config
  - compute a config hash
  - capture execution command
  - capture source repository path and code version when feasible
- Model run lifecycle explicitly. Status handling is part of the product, not incidental plumbing.
- Keep database-backed state authoritative; avoid hidden in-memory workflow state.

## Delivery Style

- Work in small, reviewable vertical slices.
- Prefer finishing one coherent path end-to-end before starting the next abstraction layer.
- Do not start with auth, permissions, dashboards, plugin systems, or multiple runners unless the active scope explicitly requires them.
- Keep public docs focused on product behavior and engineering choices.

## Testing Expectations

- Add tests alongside the behavior introduced by a change.
- Favor a mix of:
  - unit tests for service and runner logic
  - API tests for request/response contracts
  - integration tests for worker and persistence flow
- Test failure paths, not only happy paths.

## Branching

- Prefer one branch per coherent packet or feature slice.
- Use descriptive branch names such as:
  - `packet-01-repo-bootstrap`
  - `packet-02-run-lifecycle-slice`
  - `feat/runner-summary-storage`
- Keep `main` clean and reviewable.

## Commit Rules

- Make commits small enough to review comfortably.
- Keep one logical change per commit when practical.
- Do not commit broken states to `main`.
- Local exploratory commits are acceptable on a working branch, but clean up noisy history before merge when it improves readability.
- Do not commit local scratch files, environment secrets, machine-specific artifacts, or generated outputs that are not meant to be versioned.
- Run the relevant tests for the affected surface before committing.

Preferred commit message format:

- `feat(api): add health endpoint`
- `build(app): bootstrap FastAPI service`
- `test(worker): cover queued to succeeded flow`
- `refactor(runs): split service and repository logic`
- `docs(readme): clarify MVP scope`

Avoid low-signal messages such as:

- `wip`
- `fix stuff`
- `misc changes`
- `updates`

## Early Non-Goals

- user auth and roles
- compare UI or dashboards
- Telegram or mobile clients
- distributed scheduling
- generalized plugin marketplace behavior

Earn complexity only after the core run lifecycle is working end-to-end.
