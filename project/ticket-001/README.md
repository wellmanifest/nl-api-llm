# Ticket 001: feat(standard): normative specification, schemas, reference implementation, and prepanel-app menu for NL-API-LLM

- **ID**: ticket-001
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-21

`SESSION_EXECUTION_AUTHORIZATION`: user explicitly requested creation of wellmanifest/nl-api-llm standard, API catalog, dynamic menu generator, and reference implementation for clonerd-com/prepanel and app.

## Goal and scope

1. Establish normative specification `spec/NL_API_LLM_SPECIFICATION.md` defining the tripartite NL-API-LLM architecture, universal API registry, dynamic frontend menu generator, and multi-protocol dispatch (REST, CLI/ACLI, gRPC, WebSocket, MCP, KVM).
2. Author JSON schemas under `schemas/` (`api-registry.schema.json`, `menu-tree.schema.json`, `nl-api-query.schema.json`, `api-action-result.schema.json`).
3. Build the Python reference implementation in `standard/nl_api_llm.py` with CLI tooling (`nl-api`), deterministic multilingual fast-path parser (PL/EN), dynamic menu generator, and execution drivers.
4. Construct real-world reference registry and generated menu for `clonerd-com/prepanel` and `clonerd-com/app` in `examples/prepanel_app_registry.json` and `examples/prepanel_app_menu.json`, along with interactive preview in `examples/api_menu_preview.html`.
5. Deliver complete test suite in `standard/test_conformance.py` verifying all layers.

## Acceptance criteria

- [x] AC-01: Normative specification under `spec/` and machine-verifiable JSON schemas under `schemas/` are complete and valid.
- [x] AC-02: Reference implementation `standard/nl_api_llm.py` passes all self-tests.
- [x] AC-03: Real-world catalog and generated menu for `clonerd-com/prepanel` and `clonerd-com/app` accurately index views and endpoints.
- [x] AC-04: Pytest conformance test suite passes 100%.
- [x] AC-05: `./project/governance-check.sh` passes cleanly (GOV-PASS: 0 errors, 0 warnings).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
