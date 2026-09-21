# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-21

### Added
- Initial standard baseline for wellmanifest/nl-api-llm:
  - Normative specification for Universal Natural Language, Multi-Protocol API, and LLM Orchestration (`spec/NL_API_LLM_SPECIFICATION.md`).
  - Machine-verifiable JSON schemas for API Registries, Menu trees, and NL queries (`schemas/`).
  - Python reference implementation `nl_api_llm` with Universal API Registry, API-driven Menu Generator, and NL-to-API dispatcher (`src/nl_api_llm/`).
  - Prepanel & App reference API catalog and interactive menu generation for `clonerd-com/prepanel` and `clonerd-com/app` (`examples/`).
  - Interactive Web Component command palette and menu view (`web/api-menu.html`, `web/api-menu.js`).
  - Conformance test suite (`tests/`).
