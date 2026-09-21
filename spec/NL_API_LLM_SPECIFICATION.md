# Wellmanifest Standard: NL-API-LLM Architecture Specification

- **Standard ID**: `wellmanifest/nl-api-llm`
- **Version**: `0.1.0`
- **Status**: `Draft / Candidate`
- **Authors**: Wellmanifest Architecture Workgroup
- **Parent Standard**: `wellmanifest/nl-dsl-llm`

---

## 1. Executive Summary & Architectural Motivation

Modern distributed software ecosystems consist of heterogeneous APIs spanning multiple protocols:
- **REST / HTTP**: OpenAPI endpoints, JSON payloads, URL templates, and HTTP methods.
- **CLI / Shell / ACLI**: Terminal commands, options, flags, and subprocess streams.
- **gRPC / Protobuf**: Remote procedure calls, strongly typed protobuf messages, and bidirectional streaming.
- **WebSocket / AsyncAPI / SSE**: Real-time asynchronous event streams.
- **MCP (Model Context Protocol)**: Agentic tool definitions and prompt templates.
- **RFB / VNC / KVM**: Desktop GUI actions, canvas interactions, and automated screen navigation.

While `wellmanifest/nl-dsl-llm` formalized the intake, parsing, and execution boundary for a single Domain-Specific Language (DSL), real-world web frontends and multi-service systems require interacting with dozens of distinct APIs across different services. 

### Key Problems Addressed:
1. **API Fragmentation**: Frontends frequently hardcode endpoints, creating drift between backend capabilities and user navigation.
2. **Missing Universal Menus**: Adding a new backend endpoint requires manually modifying frontend navigation trees, route tables, and action buttons across disparate applications.
3. **Conversational AI Inefficiency**: Providing LLMs with full raw API specifications (e.g. massive OpenAPI JSON files) exhausts context windows, increases token latency, and introduces hallucinated parameters.
4. **Natural Language Disconnect**: Users want to express goals naturally in Polish or English (e.g. *"Udostępnij porty PC nvidia"* or *"Pobierz logi systemowe"*), without knowing which specific microservice, port, or HTTP verb is responsible.

### The NL-API-LLM Solution:
The **NL-API-LLM Standard** establishes a layered, fail-closed architecture that:
- Maintains a **Universal API Registry (SSOT)** cataloging all endpoints, protocols, parameters, and frontend bindings.
- **Generates Dynamic Menus and Command Palettes (Ctrl+K)** automatically for any frontend, directly from the API registry.
- Provides a **Deterministic Fast-Path NL Matcher** (< 1ms latency, 0 token cost, bilingual PL/EN support).
- Leverages **LLM Fallback Compilation** for free-form queries, mapping natural intent into strictly validated API execution plans.
- Executes operations via **Pluggable Protocol Drivers** (REST, CLI, gRPC, MCP, KVM) with unified response envelopes and audit logging.

```
                         ┌─────────────────────────────────────────┐
                         │           Incoming Requests             │
                         │  (Frontend UI / Chat LLM / CLI / Agent) │
                         └────────────────────┬────────────────────┘
                                              │
                         Is input direct Menu Action or NL?
                                              │
                          ┌───────────────────┴───────────────────┐
                          │ NL Query                              │ Menu / Action ID
                          ▼                                       │
             ┌─────────────────────────┐                          │
             │ Layer 1: Rule-Based NL  │                          │
             │ Fast-Path Parser        │                          │
             │ (PL/EN Synonyms & Regex)│                          │
             └────────────┬────────────┘                          │
                          │                                       │
                  Pattern matched?                                │
                  ├── YES ──────────────────┐                     │
                  │                         ▼                     │
                  │             ┌───────────────────────┐         │
                  └── NO ──────►│ Layer 2: LLM Fallback │         │
                                │ Orchestration Compiler│         │
                                │ (NL -> API Plan)      │         │
                                └───────────┬───────────┘         │
                                            │                     │
                                            ▼                     ▼
                                 ┌───────────────────────────────────┐
                                 │ Layer 3: Universal API Registry   │
                                 │ - Endpoint & Parameter Validation │
                                 │ - Role & Security Fencing         │
                                 │ - Multi-API Federation DAG        │
                                 └──────────────────┬────────────────┘
                                                    │
             ┌──────────────────────────────────────┼──────────────────────────────────────┐
             ▼                                      ▼                                      ▼
┌─────────────────────────┐            ┌─────────────────────────┐            ┌─────────────────────────┐
│ Layer 4: REST Driver    │            │ Layer 4: CLI Driver     │            │ Layer 4: KVM/MCP Driver │
│ (HTTP/1.1, HTTP/2)      │            │ (Shell, acli, subproc)  │            │ (RFB, xdotool, Stdio)   │
└────────────┬────────────┘            └────────────┬────────────┘            └────────────┬────────────┘
             │                                      │                                      │
             └──────────────────────────────────────┼──────────────────────────────────────┘
                                                    │
                                                    ▼
                                 ┌───────────────────────────────────┐
                                 │ Unified API Response Envelope     │
                                 │ (Status, Data, Audit Trail, UI)   │
                                 └──────────────────┬────────────────┘
                                                    │
                                                    ▼
                                 ┌───────────────────────────────────┐
                                 │ Dynamic Frontend Menu Generator   │
                                 │ - Hierarchical Nav Trees          │
                                 │ - Command Palette (Ctrl+K)        │
                                 │ - Parameter Modal Forms           │
                                 └───────────────────────────────────┘
```

---

## 2. Core Architectural Layers

### 2.1 Layer 1: Universal API Registry (SSOT)

The Universal API Registry is the canonical catalog of all callable services, endpoints, commands, and operations across a project.

#### Requirements:
1. **Multi-Protocol Declarations**:
   - `protocol`: One of `rest`, `cli`, `grpc`, `websocket`, `mcp`, `kvm`.
   - `service`: Identifier of the owning subsystem (e.g. `prepanel`, `app`, `premesh`, `desktop`).
   - `id`: Globally unique operation identifier (e.g. `premesh.ports.share`, `app.auth.login`, `prepanel.scenarios.test_hui`).
2. **Endpoint Specification**:
   - For `rest`: `method` (`GET`, `POST`, `PUT`, `DELETE`, `PATCH`), `path` (with RFC 6570 URI templates like `/api/accounts/{account}/port-share`).
   - For `cli`: `command` template (e.g. `prepanel serve {port}`).
   - For `grpc`: `service_name`, `method_name`, `package`.
   - For `kvm`: `action` (`navigate`, `type`, `click`, `screenshot`, `focus`).
3. **Parameter Schema**:
   - Strongly typed parameters with location (`path`, `query`, `body`, `header`, `flag`, `arg`).
   - Types: `string`, `integer`, `float`, `boolean`, `array`, `object`.
   - Constraints: `required`, `default`, `enum`, `pattern`, `description`.
4. **Semantics & Fencing**:
   - `read_only`: Boolean flag indicating idempotent, side-effect-free reading.
   - `roles`: Access control requirements (e.g. `["admin", "dev"]`).
   - `tags`: Domain taxonomy for classification and filtering.
5. **Frontend Menu Binding (`menu_binding`)**:
   - `category`: Top-level navigation category (e.g. `Accounts`, `KVM Desktop`, `Scenarios`, `Diagnostics`).
   - `group`: Sub-group within category.
   - `label`: Human-readable display label (multilingual dict or localized string).
   - `icon`: Icon identifier for frontend rendering.
   - `order`: Numeric sort priority.
   - `view_route`: Target route or view URL if navigation is involved.
   - `interaction_type`: One of:
     - `trigger`: Immediate one-click action execution.
     - `modal_form`: Displays parameter collection form before dispatch.
     - `view_navigate`: Navigates to frontend view/URL.
     - `tab_open`: Opens in separate tab or external viewer.

### 2.2 Layer 2: API-Driven Menu & Command Palette Generator

The menu generator is an automated compiler that ingests the Universal API Registry and produces structured navigation hierarchies, search indices, and interactive forms for frontends.

#### Capabilities:
1. **Tree Synthesis**:
   - Groups operations by `category` and `group`.
   - Filters entries dynamically based on user session role (RBAC).
   - Automatically assigns shortcuts, icons, and display badges.
2. **Command Palette Indexing**:
   - Builds an inverted search index over operation IDs, labels, descriptions, and natural language aliases.
   - Supports fuzzy matching and quick filtering for `Ctrl+K` palettes.
3. **Form Schema Generation**:
   - Operations requiring parameters with `interaction_type: "modal_form"` emit standard JSON form definitions (labels, inputs, selects, validation rules).
4. **Multi-Format Export**:
   - `JSON`: Machine-readable tree for client-side frameworks (`React`, `Vue`, `Svelte`, `Vanilla JS`).
   - `HTML/Web Component`: Standalone `<api-menu>` custom element with zero external dependencies.
   - `TypeScript`: Strongly typed definitions (`menu.d.ts`).

### 2.3 Layer 3: Deterministic Multilingual NL Fast-Path Parser

Before invoking expensive LLM calls, all incoming user queries pass through the local deterministic parser.

- **Latency**: < 1ms.
- **Cost**: 0 tokens.
- **Languages**: Native Polish (PL) and English (EN) root verbs and entities.
- **Normalization**:
  - Lowercasing, punctuation stripping, diacritics-tolerant matching.
  - Verb Synonym Table:
    - *Launch/Execute*: `uruchom`, `odpal`, `włącz`, `wykonaj`, `start`, `run`, `launch`, `execute`.
    - *Share/Forward*: `udostępnij`, `przekieruj`, `wystaw`, `share`, `forward`, `expose`.
    - *Fetch/Read*: `pobierz`, `pokaż`, `wyświetl`, `logi`, `get`, `fetch`, `show`, `view`, `logs`.
    - *Navigate/Open*: `otwórz`, `przejdź`, `idź do`, `nawiguj`, `open`, `goto`, `navigate`.
- **Entity Extraction**:
  - Regex-based extraction of accounts (`prototypowanie`, `dev`), hosts (`nvidia`, `localhost`), ports (`6084`, `8100`), scenario names (`test-hui`, `connect-scenario`).
- **Confidence**: Emits confidence `1.0` on complete match; lower confidence falls through to Layer 4.

### 2.4 Layer 4: LLM Multi-API Orchestration & Query Compiler

When a natural language query is complex, ambiguous, or spans multiple actions:
1. **Context Filtering**: Instead of sending all APIs, Layer 4 filters candidates based on domain tags and semantic embeddings to keep prompt tokens minimal.
2. **Plan Compilation**: Compiles the query into an `ApiExecutionPlan`:
   - Single Action: direct mapping with extracted arguments.
   - Multi-Action DAG: sequence of dependent API calls (e.g. 1. Share port -> 2. Launch scenario in noVNC -> 3. Fetch logs).
3. **Fail-Closed Validation**: The compiled plan is strictly validated against the API Registry schema before any network call.

### 2.5 Layer 5: Universal Protocol Drivers

Protocol drivers isolate execution mechanics:
1. **`RestDriver`**: Handles HTTP/HTTPS dispatch, URL parameter substitution, JSON query encoding, timeouts, and error code normalization.
2. **`CliDriver`**: Spawns asynchronous subprocesses, escapes shell arguments, and captures standard streams.
3. **`KvmDriver`**: Interacts with container X11 displays, RFB sockets, and native `xdotool` automation.
4. **`McpDriver`**: Dispatches calls via Model Context Protocol JSON-RPC.

---

## 3. Reference Implementations

The reference implementation demonstrates the standard on real-world repositories:
- **`clonerd-com/prepanel`**: Frontend management panel, noVNC desktop sessions, host port sharing, scenario executions, and system log streams.
- **`clonerd-com/app`**: Complete platform application covering accounts, authentication, runtime records, sync, teams, and local identity.

---

## 4. Conformance Criteria

A conforming implementation of `wellmanifest/nl-api-llm` MUST:
1. Validate all API manifests against `schemas/api-registry.schema.json`.
2. Generate valid menu trees conforming to `schemas/menu-tree.schema.json`.
3. Provide a deterministic NL matcher that resolves standard operations in < 10ms with 0 LLM calls.
4. Normalize all execution results into the standard response envelope (`schemas/api-action-result.schema.json`).
5. Guarantee role-based permission fences prior to dispatching any mutating API action.
