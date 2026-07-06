# Agent Validation Contract

Audit date: 2026-07-06 UTC

## Command Matrix

| Command | Purpose | Notes |
| --- | --- | --- |
| `make agent-doctor` | Report local validation and offload readiness. | Metadata only; never prints secret values. |
| `make agent-fast` | Cheap and offline by default validation gate. | Runs dependency sync, static checks, and focused docs/package truth. |
| `make agent-gate` | pre-PR gate. | Matches the substantive suite protected CI consumes. |
| `make agent-full` | Heavier validation gate. | Extends `agent-gate` with container smoke. |
| `make agent-fix` | Deterministic local fixes. | Formatting only. |
| `make agent-affected` | Diff-aware router. | Docs-only changes route to `agent-fast`; source, workflow, package, lockfile, or unknown changes route to `agent-gate`. |

## Offload Policy

- `agent-fast` is cheap and offline by default.
- `agent-gate` and `agent-full` run locally unless offload is requested.
- Offload is explicit and fail-closed.
- `AGENT_REMOTE_HOST` enables explicit remote-host offload. The helper probes
  `ssh`; if the probe or remote command setup fails, the run fails closed.
- `AGENT_USE_DAGGER=1` enables explicit Dagger offload. The helper probes
  `dagger` and requires `AGENT_DAGGER_COMMAND`; if either is missing, the run
  fails closed.
- hosted fallback is not allowed. An unavailable offload target never becomes a
  green hosted runner pass.

## Workflow Posture

Every workflow is classified in-file with a `localci-workflow-classification`
header:

- `protected-evidence`: lightweight hosted proof that consumes the `make agent-*`
  contract.
- `manual-only`: operator-triggered workflow kept for explicit orchestration.
- `offloaded`: workflow that delegates to an external owned surface.
- `retired`: preserved only to document a replaced workflow family.

## Examples

```bash
make agent-doctor
make agent-fast
make agent-gate
make agent-full
AGENT_REMOTE_HOST=tailnet-validator make agent-gate
AGENT_USE_DAGGER=1 AGENT_DAGGER_COMMAND='dagger call validate --mode gate' make agent-full
```
