# Semantic NL → API profile

Candidate extension, 2026-10-01. Profile `semantic-v1` adopts the `wellmanifest.nl-plan/v1` envelope defined by [wellmanifest/nl-dsl-llm](https://github.com/wellmanifest/nl-dsl-llm), specification `spec/SEMANTIC_NL_PLAN.md`. Pin an approved source revision during adoption; this candidate is not evidence of published deployment.

The profile preserves the original Unicode request and uses multilingual contract retrieval followed by operation-specialized structured generation. It supersedes mandatory phrase/regex matching within semantic-v1; the existing PL/EN dispatcher remains an explicit legacy compatibility profile. Language declarations and `nlIntents` are not semantic admission filters.

`standard/semantic_adapter.py` exports registry endpoint descriptions and typed parameter schemas. Effects are supplied explicitly by the host per endpoint; even `readOnly` alone grants no authority. Stable operation IDs and endpoint binding digests prevent arbitrary operation selection or stale endpoint dispatch. Parameter enums and required fields are retained. The shared planner is injected; this standard introduces no hosted model service or vendor dependency.

Translation returns `ok` with a call or literal sequence, `clarify` with a question, or `unsupported` with a reason. Missing parameters must not be invented. Read-only questions must select inspection rather than mutation. A model/API HTTP success or valid JSON is not proof of semantic correctness or execution.

The API compiler revalidates current public contracts and produces inert driver records with typed arguments and expected contract digests. REST path parameters are percent-encoded as values; query/body/header values remain structured data. Endpoint destinations belong to the host registry. CLI templates are never evaluated by this adapter. CLI, gRPC, WebSocket, MCP and KVM records require separately authorized drivers; the adapter does not claim to implement those transports.

The driver rechecks source, endpoint contract, effects, credentials and policy immediately before each call. It persists ordered dependencies for multi-step work. A changed REST binding invalidates an earlier plan. Clarification and unsupported outcomes have zero executable calls. Conditional programs and references to previous outputs are unsupported in v1.

Conformance checks cover Unicode, required arguments, explicit effects, literal shell metacharacters as data, percent-encoding, clarification and changed bindings. Real-model evaluation must separately measure operation/argument correctness, reversed direction, negation, missing data, unsupported requests and multistep ordering per language, plus p95 latency. No vendor or model quality is guaranteed by conformance.

Consumers install the shared runtime owned by `paxlet-com/dockuri` (`dockuri_nl`) or call `dockuri nl` through bounded JSON stdin/stdout. Runtime deployment must pin the tested source/wheel and embedding revision. Existing API registry and menu contracts remain compatible.

The contract-export tests require pytest only. Optional shared-runtime compiler integration tests require a tested Dockuri 0.5.1 installation and report an explicit skip when absent; a skip does not establish runtime adoption.
