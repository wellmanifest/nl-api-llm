# Ticket 002: Harmonize menu-binding naming convention and result envelope with parent nl-dsl-llm

- **ID**: ticket-002
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28

## Goal and scope

1. Document and standardize the dual naming convention for menu bindings (`menuBinding`/`menu_binding`, `viewRoute`/`view_route`, `interactionType`/`interaction_type`) across `spec/NL_API_LLM_SPECIFICATION.md` and `standard/nl_api_llm.py`.
2. Expand `schemas/api-action-result.schema.json` with optional parent standard compatibility fields (`status`, `errors`, `meta`) aligned with `wellmanifest/nl-dsl-llm`.
3. Update `standard/nl_api_llm.py` `ApiActionResult` to populate `status`, `errors`, and `meta` envelopes seamlessly.
4. Verify conformance test suite and governance checks pass.

## Acceptance criteria

- [x] AC-01: `spec/NL_API_LLM_SPECIFICATION.md` documents both camelCase and snake_case alias support for frontend menu bindings.
- [x] AC-02: `schemas/api-action-result.schema.json` defines optional compatibility properties `status`, `errors`, and `meta`.
- [x] AC-03: `standard/nl_api_llm.py` parses both camelCase and snake_case menu bindings and produces dual-conforming result envelopes.
- [x] AC-04: Pytest conformance test suite passes.
- [x] AC-05: `./project/governance-check.sh` passes cleanly (GOV-PASS).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
