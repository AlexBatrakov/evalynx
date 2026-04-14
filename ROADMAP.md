# Roadmap

This roadmap tracks public milestones for Evalynx. It intentionally stays high-level and product-facing.

## Completed Foundation Work

- [x] Project foundation and contribution guide
- [x] Public architecture and project narrative docs
- [x] Initial GitHub repository setup

## MVP Milestones

- [x] FastAPI service bootstrap
- [x] Run lifecycle vertical slice
- [x] Background worker execution flow
- [x] First real runner integration
- [ ] Retry and lifecycle hardening
- [ ] Docker Compose and CI setup
- [ ] MVP polish and reviewer onboarding

## MVP Outcome

The MVP is complete when a reviewer can:

- start the stack locally
- create a project
- submit a run through the API
- observe asynchronous execution and lifecycle changes
- inspect stored run summaries, metrics, and artifact references
- retry failed runs

## Direction Beyond MVP

Potential follow-on areas after the MVP:

- additional runner integrations
- run comparison workflows
- richer observability
- scheduling and automation

## Current Focus

The next milestone is lifecycle hardening: adding retry support, attempt-aware execution tracking, and stronger failure diagnostics now that the first real runner path is in place.
