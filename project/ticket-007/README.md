# Ticket 007: Externalize NL intent rules and eliminate NOHARDCODE-001/007 findings

- **ID**: ticket-007
- **Owner**: agent:antigravity
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-11-02

## Goal and scope

Externalize the hardcoded natural-language endpoint trigger lists in `standard/nl_api_llm.py` into `standard/semantic-profile.json`, replace manual diacritics mapping with Unicode NFKD normalization, and replace raw `print()` calls in `standard/nl_api_llm.py` with structured stream writes so `wellmanifest/nohardcode` reports 0 findings under `--profile strict`.

## Acceptance criteria

- [x] AC-01: `nohardcode_check.py --target . --profile strict` passes with 0 findings (`0 errors, 0 warnings`).
- [x] AC-02: `pytest -q`, `./project/governance-check.sh`, and `python3 .governance/standard_pack_check.py --root .` pass with 0 errors.

## SESSION_EXECUTION_AUTHORIZATION

User authorized autonomous execution to audit and remediate `wellmanifest/nohardcode`, `wellmanifest/ssot`, and `wellmanifest/nl-*` across `wellmanifest/*` repositories.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
