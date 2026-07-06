# Coverage Evidence

Audit date: 2026-07-06 UTC
Phase plan: `plans/phase-plan-v9-COVERAGE.md`

## Baseline

Baseline command: `make coverage-baseline`
coverage.xml generation: `Coverage XML written to file coverage.xml`
Terminal missing-line summary: `TOTAL 44667 statements, 34945 missed, 16144 branches, 436 partials, 17.31% coverage`
Existing threshold posture: `pytest.ini` still carries `--cov-fail-under=35`; COVERAGE did not replace it with `--cov-fail-under=80`.

## Guard And Ownership

Guard result: `make coverage-artifact-guard` passed before baseline generation and the generated outputs remained unstaged.
Coverage ownership: `make agent-full` owns routine coverage generation through the local/offloaded `make coverage` target.
Generated artifact policy: `coverage.xml`, `coverage.json`, `.coverage*`, and `htmlcov/` are ignored runtime outputs and must not be tracked or staged.

## Hosted Posture

Workflow upload decision: ordinary `pull_request` runs stay on `make agent-gate`; `.github/workflows/ci-cd-pipeline.yml` does not add Codecov or coverage artifact upload.
README badge decision: badge remains deferred until a trusted event produces real uploaded evidence.

## Threshold Decision

threshold ramp deferred: the 2026-07-06 local/offloaded baseline is `17.31%`, so `--cov-fail-under=80` is not enforced in this phase.

## Verification Commands

Verification commands used for COVERAGE:

```bash
uv run pytest tests/test_coverage_artifact_guard.py tests/test_coverage_command_contract.py tests/test_coverage_workflow_posture.py tests/test_ignore_patterns.py tests/docs/test_coverage_docs.py -q --no-cov
make coverage-baseline
```
