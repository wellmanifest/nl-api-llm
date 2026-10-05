# Ticket 005: standardize standard adoption and pytest configuration

- **ID**: ticket-005
- **Owner**: agent:gemini
- **Status**: IN_PROGRESS
- **Workflow state**: VALIDATION
- **Created**: 2026-10-05

## Goal and scope

Standardize adoption of `wellmanifest/nl-dsl-llm@0.1.0` in `pyproject.toml` under `[tool.wellmanifest]` and align pytest configuration (`testpaths`, `python_files`, `pythonpath`) to guarantee seamless testing across the `wellmanifest/nl-*` standards family.

## Acceptance criteria

- [x] AC-01: `pyproject.toml` declares formal standard adoption `adopts = ["wellmanifest/nl-dsl-llm@0.1.0"]` under `[tool.wellmanifest]`.
- [x] AC-02: `pyproject.toml` configures `testpaths`, `python_files`, and `pythonpath` under `[tool.pytest.ini_options]`.
- [x] AC-03: Full test suite passes directly with `pytest` (12/12 passed).
- [x] AC-04: `./project/governance-check.sh` passes with 0 errors and 0 warnings.

## SESSION_EXECUTION_AUTHORIZATION

User: "scalaj integruj , zadbaj o standaryzacje zaleznosci na poziomie wellmanifest/nl-*standardow".

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
