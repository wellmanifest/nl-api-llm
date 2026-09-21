# wellmanifest/nl-api-llm

**Standard and Reference Implementation for Universal Natural Language, Multi-Protocol API, and Large Language Model (NL-API-LLM) Architectures.**

## Overview

The `nl-api-llm` standard establishes a unified, deterministic, and safe pattern for discovering, indexing, searching, and controlling heterogeneous project APIs through Natural Language (NL) interfaces, dynamic frontend menus, and LLM-assisted orchestration.

Building on the foundation of `wellmanifest/nl-dsl-llm`, this standard extends tripartite control into multi-protocol API landscapes (REST, CLI/ACLI, gRPC, WebSocket, MCP, KVM):

1. **Universal API Registry & Manifest**: Machine-readable single source of truth (SSOT) cataloging all endpoints, parameters, semantics, and frontend menu bindings across project services.
2. **API-Driven Menu Generator**: Automated generation of hierarchical, searchable, and actionable frontend navigation menus, command palettes (Ctrl+K), and modal interaction forms for any web or desktop application.
3. **Multi-Protocol NL-to-API Dispatcher**: Deterministic rule-based fast path (<1ms) for common multilingual intents (PL/EN) with seamless LLM fallback compilation for free-form queries.
4. **Multi-API Orchestration**: Safe federation across multiple project boundaries (e.g. `prepanel`, `app`, `premesh`, and KVM desktop agents).

## Standard Structure

- `spec/`: Normative architectural specification (`NL_API_LLM_SPECIFICATION.md`).
- `schemas/`: Machine-verifiable JSON schemas for API manifests, menu definitions, and NL queries.
- `src/nl_api_llm/`: Python reference implementation including registry, menu generator, and protocol drivers.
- `examples/`: Reference API manifests and generated menus (e.g. `clonerd-com/prepanel` and `clonerd-com/app`).
- `web/`: Reusable web component (`<api-menu>`) and searchable command palette interface.
- `tests/`: Conformance and integration test suite.

## Governance

Adopts `wellmanifest/new-project` policy-as-code standard.
