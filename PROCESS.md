# CI/CD Process Documentation

## Overview

Every code change goes through an automated pipeline before it can reach `main`. The pipeline enforces code quality, test coverage, and structured review — and notifies the team on every outcome.

---

## How a Change Flows

```
Developer pushes branch
        │
        ▼
CI runs on the branch (lint → test → notify)
        │
        ▼
Developer opens Pull Request targeting main
        │
        ▼
CI runs again on the PR
        │
   ┌────┴────┐
   │         │
 FAIL       PASS
   │         │
   │    1 reviewer approves
   │         │
   │    Merge (squash or rebase only)
   │         │
   └────►  CI runs once more on main
```

---

## The Pipeline Jobs

### 1. Lint (`Lint (flake8)`)
- Runs `flake8` against `src/` and `tests/`
- Checks for style violations, unused imports, and formatting issues
- **Blocking:** if this fails, the test job does not run

### 2. Unit Tests (`Unit Tests (pytest)`)
- Runs only after lint passes (`needs: lint`)
- Executes all tests under `tests/` (excluding `tests/ci/`)
- Enforces **80% minimum code coverage** — drops below this fail the job
- Uploads a `.coverage` artifact retained for 7 days

### 3. Notify
- Runs **always**, even if lint or test fails (`if: always()`)
- Waits for both jobs to finish before sending
- Dispatches to configured notification channels (see below)

---

## Branch Protection Rules (main)

| Rule | Setting |
|---|---|
| Direct pushes to main | Blocked |
| Required PR approvals | 1 |
| Stale review dismissal | Enabled — new commits invalidate prior approvals |
| Required status checks | `Lint (flake8)` and `Unit Tests (pytest)` must pass |
| Allowed merge methods | Squash and rebase only (no merge commits) |
| Force push | Blocked |

---

## Ways the Process Can Fail

### Pipeline failures
| Failure | Cause | Effect |
|---|---|---|
| Lint fails | Code style violation, unused import, line too long | Test job skipped, PR cannot merge |
| Tests fail | A test assertion fails | PR cannot merge |
| Coverage drops below 80% | New code added without tests | PR cannot merge |
| Notify job fails | A notification channel errors (e.g. bad credentials, network) | Exit code 1, visible in Actions log — does not block merge |

### Configuration failures
| Failure | Cause | Effect |
|---|---|---|
| PR comment notification fails (403) | `GITHUB_TOKEN` missing `pull-requests: write` permission | Notify job exits 1 |
| Email notification fails | Missing or invalid `EMAIL_FROM`, `EMAIL_APP_PASSWORD` secrets | Notify job exits 1 |
| Slack notification fails | Invalid or expired webhook URL | Notify job exits 1 |
| Status checks not recognised | Job name in ruleset doesn't match actual job name in workflow | PRs can never satisfy required checks and are permanently blocked |

### Process failures (human)
| Failure | Cause | Effect |
|---|---|---|
| PR merged without review | Ruleset misconfigured or bypassed by admin | Unreviewed code reaches main |
| Ruleset temporarily disabled | Done to unblock a merge | Protection window opens — coordinate carefully |
| Secrets expire or rotate | App password or webhook URL changes | Notifications silently fail or pipeline errors |
| Token scope too narrow | PAT used for meta-tests lacks `repo` scope | Meta-tests skip entirely |

---

## Notifications

### What triggers a notification
The notify job runs after every CI execution — on PRs, on branch pushes, and on pushes to main.

### Where notifications are sent

| Channel | Trigger | Content | Requires |
|---|---|---|---|
| **GitHub PR comment** | PR runs only | ✅/❌ status + link to run | `GITHUB_TOKEN` (auto-provided) |
| **Email** | Every run | Subject: `CI SUCCESS/FAILURE: CI`, body with run URL | `NOTIFY_EMAIL`, `EMAIL_FROM`, `EMAIL_APP_PASSWORD` secrets |
| **Slack** | Every run | Status message with link to run | `SLACK_WEBHOOK_URL` secret |

### Opt-in behaviour
Each channel is **opt-in via secrets**. If a secret is not set, that channel is silently skipped. The notify job only fails if a channel is configured but errors.

---

## Stakeholders as the Process Evolves

### Today
| Stakeholder | Role |
|---|---|
| Developer | Opens PRs, responds to failures, writes tests |
| Reviewer | Approves PRs — must have write access to the repo |
| Repo admin | Manages rulesets, secrets, and workflow permissions |

### As the project grows

| Stakeholder | When they become relevant |
|---|---|
| **QA / Test engineer** | When test coverage strategy needs to evolve beyond unit tests (e.g. integration, e2e) |
| **Security team** | When secret rotation policy, token scopes, or dependency scanning needs governance |
| **Platform / DevOps** | When self-hosted runners, caching strategy, or parallelism becomes a concern |
| **Tech lead / Architect** | When the 80% coverage threshold, merge strategy, or branching model needs revisiting |
| **Compliance / Legal** | If audit trails of who approved and merged what become a requirement |
| **On-call / Ops** | If notify channels expand to paging systems (PagerDuty, OpsGenie) for main branch failures |

---

## Running the Meta-Tests

The `tests/ci/` directory contains tests that verify the pipeline configuration itself via the GitHub API. They are excluded from the normal CI run and must be run manually.

```bash
export GITHUB_TOKEN=<pat_with_repo_scope>
pytest tests/ci/test_ci_pipeline.py -v
```

These should be re-run after any changes to the ruleset or workflow file.
