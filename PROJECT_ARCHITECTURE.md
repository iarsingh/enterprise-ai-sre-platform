# enterprise-ai-sre-platform — project architecture

[README](README.md) · [Interview questions and answers](INTERVIEW_QA.md)

## Purpose and scope

This is a local laptop proof. It does not call a hosted model and it does not apply production changes.

This document describes files and symbols in this checkout. Deployment templates and statements in the original overview are distinguished from a verified running environment.

## Component diagram

```mermaid
flowchart LR
    M0["src/entsre/__init__.py"]
    M1["src/entsre/agent.py"]
    M2["src/entsre/main.py"]
    M3["src/entsre/ops.py"]
    M2 -->|imports| M1
    M2 -->|imports| M3
```

For Python repositories, arrows show resolved local imports, not network calls or deployment order. Otherwise the diagram is a repository component map; containment arrows do not assert runtime integration.

## Components and responsibilities

| Component | Responsibility |
| --- | --- |
| [`src/entsre/main.py`](src/entsre/main.py) | HTTP handlers: `GET /healthz`, `POST /agent/run` |
| [`src/entsre/ops.py`](src/entsre/ops.py) | HTTP handlers: `GET /readyz`, `POST /workspaces`, `GET /workspaces`, `POST /workspaces/{workspace_id}/jobs`, `GET /jobs/{job_id}` |
| [`src/entsre/agent.py`](src/entsre/agent.py) | Functions: `run` |
| [`requirements.txt`](requirements.txt) | Implementation or supporting configuration |
| [`src/entsre/__init__.py`](src/entsre/__init__.py) | Implementation or supporting configuration |
| [`Dockerfile`](Dockerfile) | Container build/service configuration |
| [`Makefile`](Makefile) | Implementation or supporting configuration |
| [`docker-compose.yml`](docker-compose.yml) | Container build/service configuration |
| [`tests/test_agent.py`](tests/test_agent.py) | Executable checks and regression examples |
| [`tests/test_ops.py`](tests/test_ops.py) | Executable checks and regression examples |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | GitHub Actions job definitions |
| [`README.md`](README.md) | Project explanations or operating notes |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Project explanations or operating notes |

## Existing design and operating guides

These checked-in guides provide the project’s detailed design, operational context, or deployment view:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Request interface

| Method and path | Handler | Source |
| --- | --- | --- |
| `GET /healthz` | `healthz` | [`src/entsre/main.py`](src/entsre/main.py#L10) |
| `POST /agent/run` | `post_run` | [`src/entsre/main.py`](src/entsre/main.py#L15) |
| `GET /readyz` | `readyz` | [`src/entsre/ops.py`](src/entsre/ops.py#L44) |
| `POST /workspaces` | `create_workspace` | [`src/entsre/ops.py`](src/entsre/ops.py#L49) |
| `GET /workspaces` | `list_workspaces` | [`src/entsre/ops.py`](src/entsre/ops.py#L66) |
| `POST /workspaces/{workspace_id}/jobs` | `create_job` | [`src/entsre/ops.py`](src/entsre/ops.py#L73) |
| `GET /jobs/{job_id}` | `get_job` | [`src/entsre/ops.py`](src/entsre/ops.py#L96) |
| `POST /jobs/{job_id}/approve` | `approve_job` | [`src/entsre/ops.py`](src/entsre/ops.py#L105) |
| `GET /audit` | `audit` | [`src/entsre/ops.py`](src/entsre/ops.py#L122) |
| `GET /metrics` | `metrics` | [`src/entsre/ops.py`](src/entsre/ops.py#L138) |

The table lists literal route decorators found in the inspected Python modules. Router prefixes and middleware can add behavior; check the linked handler and application setup before calling an endpoint.

## Implementation walkthrough

### `run(goal, payload)`

Source: [`src/entsre/agent.py`](src/entsre/agent.py#L9).

Calls visible in this function: `InputError`, `any`, `float`, `goal.lower`, `goal.strip`, `isinstance`, `payload.get`.

```python
def run(goal, payload):
    if not isinstance(goal, str) or not goal.strip():
        raise InputError("goal is empty")
    if any(word in goal.lower() for word in WRITES):
        return {"refused": True, "reason": "This agent only reads or plans. It does not write.", "tools": [], "wrote": False, "applied": False}
    result = "freeze" if float(payload.get("burn", 0)) >= 2 else "watch"
    return {"refused": False, "tools": TOOLS, "recommend": result, "wrote": False, "applied": False}
```

## Validation and failure paths

| Explicit exception | Source |
| --- | --- |
| `InputError('goal is empty')` | [`src/entsre/agent.py`](src/entsre/agent.py#L11) |
| `HTTPException(status_code=422, detail=str(exc))` | [`src/entsre/main.py`](src/entsre/main.py#L19) |
| `HTTPException(status_code=404, detail='workspace not found')` | [`src/entsre/ops.py`](src/entsre/ops.py#L77) |
| `HTTPException(status_code=404, detail='job not found')` | [`src/entsre/ops.py`](src/entsre/ops.py#L100) |
| `HTTPException(status_code=404, detail='job not found')` | [`src/entsre/ops.py`](src/entsre/ops.py#L109) |
| `HTTPException(status_code=403, detail='production apply is disabled in this lab')` | [`src/entsre/ops.py`](src/entsre/ops.py#L113) |

These are explicit exceptions in the inspected source, rather than a claim that every failure is handled. Follow the calling handler to see whether the exception becomes an HTTP response or propagates.

## Data and state

- [`src/entsre/agent.py`](src/entsre/agent.py) defines module-level containers: `TOOLS`.
- [`src/entsre/ops.py`](src/entsre/ops.py) defines module-level containers: `_WORKSPACES`, `_JOBS`, `_AUDIT`, `_METRICS`.

Module-level dictionaries/lists live in a Python process. They can be fixtures or mutable state; inspect writes before treating them as persistent storage. A production extension would need to define persistence and concurrency behavior explicitly.

## Data flow and design decisions

### What is the input-to-output contract of `run`

In [`src/entsre/agent.py`](src/entsre/agent.py#L9), `run(goal, payload)` receives the inputs. The function computes these intermediate values:

- `result = 'freeze' if float(payload.get('burn', 0)) >= 2 else 'watch'`

Its result is defined by:

- `{'refused': False, 'tools': TOOLS, 'recommend': result, 'wrote': False, 'applied': False}`
- `{'refused': True, 'reason': 'This agent only reads or plans. It does not write.', 'tools': [], 'wrote': False, 'applied': False}`

### Which decision rules or boundary conditions should an interviewer challenge

The implementation in [`src/entsre/agent.py`](src/entsre/agent.py#L9) branches on:

- `not isinstance(goal, str) or not goal.strip()`
- `any((word in goal.lower() for word in WRITES))`

A useful extension is a table-driven test that covers each condition just below, at, and above its boundary where applicable. These expressions are the current rules; changing them changes behavior and should be justified by the project’s acceptance criteria.

### What does the operations plane add, and where is its limit

[`src/entsre/ops.py`](src/entsre/ops.py) declares `GET /readyz`, `POST /workspaces`, `GET /workspaces`, `POST /workspaces/{workspace_id}/jobs`, `GET /jobs/{job_id}`, `POST /jobs/{job_id}/approve`, `GET /audit`, `GET /metrics`. Inspect the application’s `include_router` call for its URL prefix.

Its state containers are `_WORKSPACES`, `_JOBS`, `_AUDIT`, `_METRICS`. The job-approval handler defines whether a target is accepted or refused; check that branch and the associated tests instead of treating a recorded job as a successful infrastructure apply.

## Setup and verification

The following commands are derived from the checked-in dependency/test contracts. Execute them from the repository root; the block prepares a local environment, not a cloud deployment.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

Python dependencies: [`requirements.txt`](requirements.txt).

Test entry points: [`tests/test_agent.py`](tests/test_agent.py), [`tests/test_ops.py`](tests/test_ops.py).

Automation definitions: [`.github/workflows/ci.yml`](.github/workflows/ci.yml). Read their triggers and job steps to determine what CI actually runs.

## Operating boundaries and design review

Before turning this checkout into a customer deployment, establish the input contract, data ownership, access controls, failure response, evaluation criteria, and rollback owner. Repository fixtures and unit tests demonstrate local behavior; they do not establish throughput, uptime, compliance, or business impact.

A useful architecture review starts with the linked implementation: identify where input enters, where a decision is made, which state can change, and which external dependency can fail. Add a deployment view only for infrastructure that is actually configured and exercised.
