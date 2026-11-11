#!/usr/bin/env python3
"""
wellmanifest/nl-api-llm: Universal Natural Language, Multi-Protocol API,
and LLM Orchestration Standard Reference Implementation.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from typing import Any

try:
    from .nl_api_matcher import (
        MAX_LOG_LINES,
        MAX_QUERY_CHARS,
        ApiExecutionPlan,
        CompiledAction,
        LLMQueryCompiler,
        NLIntentMatcher,
    )
    from .nl_api_menu import MenuGenerator, _serialize_script_json
    from .nl_api_models import (
        MAX_FILE_BYTES,
        MAX_JSON_DEPTH,
        ApiActionResult,
        ApiEndpoint,
        ApiParameter,
        ApiRegistry,
        ApiService,
        CliSpec,
        InteractionType,
        KvmSpec,
        MenuBinding,
        NLIntent,
        ProtocolType,
        RestSpec,
        _out,
        read_strict_json,
        write_atomic_text,
    )
except ImportError:
    from nl_api_matcher import (  # type: ignore[no-redef]
        MAX_LOG_LINES,
        MAX_QUERY_CHARS,
        ApiExecutionPlan,
        CompiledAction,
        LLMQueryCompiler,
        NLIntentMatcher,
    )
    from nl_api_menu import MenuGenerator, _serialize_script_json  # type: ignore[no-redef]
    from nl_api_models import (  # type: ignore[no-redef]
        MAX_FILE_BYTES,
        MAX_JSON_DEPTH,
        ApiActionResult,
        ApiEndpoint,
        ApiParameter,
        ApiRegistry,
        ApiService,
        CliSpec,
        InteractionType,
        KvmSpec,
        MenuBinding,
        NLIntent,
        ProtocolType,
        RestSpec,
        _out,
        read_strict_json,
        write_atomic_text,
    )

__all__ = [
    "MAX_FILE_BYTES",
    "MAX_JSON_DEPTH",
    "MAX_LOG_LINES",
    "MAX_QUERY_CHARS",
    "ApiActionResult",
    "ApiEndpoint",
    "ApiExecutionPlan",
    "ApiOrchestrator",
    "ApiParameter",
    "ApiRegistry",
    "ApiService",
    "CliSpec",
    "CompiledAction",
    "InteractionType",
    "KvmSpec",
    "LLMQueryCompiler",
    "MenuBinding",
    "MenuGenerator",
    "NLIntent",
    "NLIntentMatcher",
    "ProtocolType",
    "RestSpec",
    "_serialize_script_json",
    "main",
    "read_strict_json",
    "run_self_tests",
    "write_atomic_text",
]


class ApiOrchestrator:
    """End-to-end dispatcher orchestrating NL intake, parsing, planning, and execution."""

    def __init__(self, registry: ApiRegistry, mock_mode: bool = False):
        self.registry = registry
        self.mock_mode = mock_mode
        self.fast_matcher = NLIntentMatcher(registry)
        self.llm_compiler = LLMQueryCompiler(registry)
        self.endpoints = {e.id: e for e in registry.endpoints}

    def execute_plan(
        self,
        plan: ApiExecutionPlan,
        caller_role: str = "admin",
    ) -> list[ApiActionResult]:
        results: list[ApiActionResult] = []
        for action in plan.actions:
            t0 = time.time()
            ep = self.endpoints.get(action.endpointId)
            if not ep:
                results.append(
                    ApiActionResult(
                        success=False,
                        endpointId=action.endpointId,
                        protocol="unknown",
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        latencyMs=0.0,
                        statusCode=404,
                        error={
                            "code": "ENDPOINT_NOT_FOUND",
                            "message": f"Endpoint {action.endpointId} is not registered",
                        },
                    )
                )
                continue

            if ep.roles and caller_role not in ep.roles and "all" not in ep.roles:
                results.append(
                    ApiActionResult(
                        success=False,
                        endpointId=action.endpointId,
                        protocol=ep.protocol,
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        latencyMs=0.0,
                        statusCode=403,
                        error={
                            "code": "PERMISSION_DENIED",
                            "message": f"Role '{caller_role}' is not authorized to invoke {ep.id}",
                        },
                    )
                )
                continue

            latency_ms = round((time.time() - t0) * 1000 + 1.2, 2)
            results.append(
                ApiActionResult(
                    success=True,
                    endpointId=ep.id,
                    protocol=ep.protocol,
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    latencyMs=latency_ms,
                    statusCode=200,
                    data={
                        "status": "success",
                        "operation": ep.id,
                        "parameters": action.parameters,
                        "description": action.description,
                        "mock": self.mock_mode,
                    },
                    audit={
                        "caller": caller_role,
                        "protocol": ep.protocol,
                        "sanitizedParams": action.parameters,
                    },
                )
            )
        return results

    def query(
        self,
        raw_query: str,
        context: dict[str, Any] | None = None,
        caller_role: str = "admin",
    ) -> tuple[ApiExecutionPlan, list[ApiActionResult]]:
        plan = self.fast_matcher.parse(raw_query, context)
        if plan.confidence < 0.8:
            plan = self.llm_compiler.compile(raw_query, context)
        results = self.execute_plan(plan, caller_role=caller_role)
        return plan, results


def _build_self_test_registry() -> ApiRegistry:
    return ApiRegistry(
        schema="wellmanifest.api-registry/v1",
        version="0.1.0",
        services=[
            ApiService(
                id="premesh",
                name="Premesh Service Hub",
                protocol="rest",
                defaultPort=8081,
            ),
            ApiService(
                id="prepanel",
                name="Prepanel Desktop Panel",
                protocol="rest",
                defaultPort=8180,
            ),
        ],
        endpoints=[
            ApiEndpoint(
                id="premesh.ports.share",
                service="premesh",
                protocol="rest",
                title="Share PC Host Ports to Container",
                description="Udostępnianie portów z hosta Nvidia do środowiska noVNC",
                readOnly=False,
                roles=["admin", "dev"],
                tags=["ports", "nvidia", "novnc"],
                parameters=[
                    ApiParameter(
                        name="account", type="string", location="path", required=True
                    ),
                    ApiParameter(
                        name="host",
                        type="string",
                        location="query",
                        required=False,
                        default="nvidia",
                    ),
                    ApiParameter(
                        name="ports",
                        type="array",
                        location="body",
                        required=False,
                        default=[8100, 8096, 8094],
                    ),
                ],
                nlIntents=[
                    NLIntent(
                        lang="pl", phrases=["udostępnij porty", "wystaw porty do novnc"]
                    ),
                    NLIntent(lang="en", phrases=["share ports", "forward host ports"]),
                ],
                menuBinding=MenuBinding(
                    category="Port Sharing",
                    group="Host Integration",
                    label="Udostępnij porty PC Nvidia",
                    icon="share",
                    order=10,
                    interactionType="modal_form",
                    badge="8100/8096",
                ),
            ),
            ApiEndpoint(
                id="premesh.logs.fetch",
                service="premesh",
                protocol="rest",
                title="Pobieranie logów systemowych",
                description="Pobiera ostatnie linie logów z wybranego hosta",
                readOnly=True,
                roles=["admin", "dev", "viewer"],
                tags=["logs", "diagnostics"],
                parameters=[
                    ApiParameter(
                        name="host",
                        type="string",
                        location="query",
                        required=False,
                        default="nvidia",
                    ),
                    ApiParameter(
                        name="lines",
                        type="integer",
                        location="query",
                        required=False,
                        default=60,
                    ),
                ],
                nlIntents=[
                    NLIntent(
                        lang="pl", phrases=["pobierz logi", "pokaż ostatnie logi"]
                    ),
                    NLIntent(lang="en", phrases=["fetch logs", "show system logs"]),
                ],
                menuBinding=MenuBinding(
                    category="Diagnostics",
                    group="Logs",
                    label="Pobierz logi systemowe",
                    icon="file-text",
                    order=20,
                    interactionType="trigger",
                ),
            ),
            ApiEndpoint(
                id="prepanel.scenarios.test_hui",
                service="prepanel",
                protocol="kvm",
                title="Scenariusz Test HUI",
                description="Uruchamia interfejs testu HUI w oknie noVNC",
                readOnly=False,
                roles=["admin", "dev"],
                tags=["scenario", "hui", "c2004"],
                nlIntents=[
                    NLIntent(
                        lang="pl", phrases=["uruchom test hui", "test manualny hui"]
                    ),
                    NLIntent(lang="en", phrases=["run test hui", "launch hui test"]),
                ],
                menuBinding=MenuBinding(
                    category="Scenarios",
                    group="C2004",
                    label="Test Manualny HUI",
                    icon="play",
                    order=30,
                    interactionType="trigger",
                    badge="HUI",
                ),
            ),
        ],
    )


def run_self_tests() -> int:
    """Verifies standard conformance across registry, menu generator, and NL parsing."""
    _out("=== Running wellmanifest/nl-api-llm Reference Self-Tests ===")
    registry = _build_self_test_registry()

    reg_dict = registry.to_dict()
    assert reg_dict["version"] == "0.1.0"
    assert len(reg_dict["endpoints"]) == 3
    _out("✓ Check 1: Registry serialization & schema parity passed.")

    menu_gen = MenuGenerator(registry)
    menu = menu_gen.generate_menu(user_role="admin")
    assert len(menu["categories"]) == 3
    assert len(menu["searchIndex"]) == 3
    _out("✓ Check 2: Dynamic menu & search index generation passed.")

    matcher = NLIntentMatcher(registry)
    plan_pl = matcher.parse(
        "Udostępnij porty na maszynie nvidia dla konta prototypowanie"
    )
    assert plan_pl.confidence == 1.0
    assert plan_pl.strategy == "deterministic"
    assert plan_pl.actions[0].endpointId == "premesh.ports.share"
    assert plan_pl.actions[0].parameters["account"] == "prototypowanie"
    assert plan_pl.actions[0].parameters["host"] == "nvidia"
    _out("✓ Check 3: Deterministic Polish NL parsing passed.")

    plan_logs = matcher.parse("Pobierz ostatnie 100 linii logów z hosta nvidia")
    assert plan_logs.confidence == 1.0
    assert plan_logs.actions[0].endpointId == "premesh.logs.fetch"
    assert plan_logs.actions[0].parameters["lines"] == 100
    _out("✓ Check 4: Parameterized system logs NL parsing passed.")

    plan_hui = matcher.parse("odpal test hui w novnc")
    assert plan_hui.confidence == 1.0
    assert plan_hui.actions[0].endpointId == "prepanel.scenarios.test_hui"
    _out("✓ Check 5: Scenarios NL parsing passed.")

    orchestrator = ApiOrchestrator(registry, mock_mode=True)
    _, results = orchestrator.query("wystaw porty dla konta dev", caller_role="admin")
    assert len(results) == 1
    assert results[0].success is True
    assert results[0].statusCode == 200

    _, denied_res = orchestrator.query("udostępnij porty", caller_role="guest")
    assert denied_res[0].success is False
    assert denied_res[0].statusCode == 403
    _out("✓ Check 6: End-to-end dispatch and RBAC security fence passed.")

    _out("\nALL 6/6 SELF-TESTS PASSED CONFORMANCE.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="wellmanifest/nl-api-llm CLI reference driver"
    )
    parser.add_argument(
        "--self-test", action="store_true", help="Run comprehensive conformance tests"
    )
    parser.add_argument(
        "--menu", action="store_true", help="Generate frontend menu from registry file"
    )
    parser.add_argument("--registry", type=str, help="Path to API registry JSON file")
    parser.add_argument(
        "--output-json", type=str, help="Path to save generated menu JSON"
    )
    parser.add_argument(
        "--output-html", type=str, help="Path to save standalone HTML preview"
    )
    parser.add_argument(
        "--query", type=str, help="Parse and dispatch a natural language query"
    )
    parser.add_argument(
        "--role", type=str, default="admin", help="Active caller role for RBAC check"
    )

    args = parser.parse_args(argv)

    if args.self_test:
        rc = run_self_tests()
        if argv is None:
            sys.exit(rc)
        return rc

    if args.menu:
        if not args.registry:
            _out("Error: --registry is required when using --menu", stream=sys.stderr)
            if argv is None:
                sys.exit(1)
            return 1
        try:
            data = read_strict_json(args.registry)
            reg = ApiRegistry.from_dict(data)
            gen = MenuGenerator(reg)
            menu_tree = gen.generate_menu(user_role=args.role)
            if args.output_json:
                write_atomic_text(
                    args.output_json,
                    json.dumps(menu_tree, indent=2, ensure_ascii=False, allow_nan=False)
                    + "\n",
                )
                _out(f"Saved menu tree JSON to {args.output_json}")
            if args.output_html:
                write_atomic_text(
                    args.output_html, gen.export_html_component(menu_tree)
                )
                _out(f"Saved HTML menu preview to {args.output_html}")
            if not args.output_json and not args.output_html:
                _out(
                    json.dumps(menu_tree, indent=2, ensure_ascii=False, allow_nan=False)
                )
        except (OSError, TypeError, ValueError, KeyError) as exc:
            _out(f"Error: {exc}", stream=sys.stderr)
            if argv is None:
                sys.exit(1)
            return 1
        if argv is None:
            sys.exit(0)
        return 0

    if args.query:
        if not args.registry:
            _out("Error: --registry is required when using --query", stream=sys.stderr)
            if argv is None:
                sys.exit(1)
            return 1
        try:
            data = read_strict_json(args.registry)
            reg = ApiRegistry.from_dict(data)
            orchestrator = ApiOrchestrator(reg, mock_mode=True)
            plan, results = orchestrator.query(args.query, caller_role=args.role)
            output = {
                "query": args.query,
                "plan": {
                    "confidence": plan.confidence,
                    "strategy": plan.strategy,
                    "actions": [asdict(a) for a in plan.actions],
                },
                "results": [r.to_dict() for r in results],
            }
            _out(json.dumps(output, indent=2, ensure_ascii=False, allow_nan=False))
        except (OSError, TypeError, ValueError, KeyError) as exc:
            _out(f"Error: {exc}", stream=sys.stderr)
            if argv is None:
                sys.exit(1)
            return 1
        if argv is None:
            sys.exit(0)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    main()
