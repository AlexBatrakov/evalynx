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
- [x] Retry and lifecycle hardening
- [x] Docker Compose and CI setup
- [x] MVP polish and reviewer onboarding
- [x] Final MVP review and positioning pass

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

The MVP is complete. The next decision is whether to leave Evalynx as a finished backend portfolio artifact or expand deliberately into follow-on areas such as a second runner, comparison workflows, or richer observability.
