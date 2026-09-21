"""
Conformance test suite for wellmanifest/nl-api-llm standard.
Verifies registry schema validation, dynamic menu generation, command palette indexing,
bilingual fast-path parsing, entity extraction, and RBAC execution fences.
"""

import json
from pathlib import Path
import pytest
from standard.nl_api_llm import (
    ApiEndpoint,
    ApiParameter,
    ApiRegistry,
    ApiService,
    MenuBinding,
    MenuGenerator,
    NLIntent,
    NLIntentMatcher,
    ApiOrchestrator,
    InteractionType,
)


@pytest.fixture
def sample_registry() -> ApiRegistry:
    return ApiRegistry(
        schema="wellmanifest.api-registry/v1",
        version="0.1.0",
        services=[
            ApiService(id="premesh", name="Premesh Service Hub", protocol="rest", defaultPort=8081),
            ApiService(id="prepanel", name="Prepanel Desktop Panel", protocol="rest", defaultPort=8180),
            ApiService(id="app", name="Platform Application Core", protocol="rest", defaultPort=8080),
        ],
        endpoints=[
            ApiEndpoint(
                id="premesh.ports.share",
                service="premesh",
                protocol="rest",
                title="Share PC Host Ports to Container",
                description="Udostępnianie portów z hosta Nvidia do kontenera noVNC",
                readOnly=False,
                roles=["admin", "dev"],
                tags=["ports", "nvidia", "novnc"],
                parameters=[
                    ApiParameter(name="account", type="string", location="path", required=True),
                    ApiParameter(name="host", type="string", location="query", required=False, default="nvidia"),
                    ApiParameter(name="ports", type="array", location="body", required=False, default=[8100, 8096, 8094]),
                ],
                nlIntents=[
                    NLIntent(lang="pl", phrases=["udostępnij porty", "wystaw porty do novnc"]),
                    NLIntent(lang="en", phrases=["share ports", "forward host ports"]),
                ],
                menuBinding=MenuBinding(
                    category="Port Sharing",
                    group="Host Integration",
                    label="Udostępnij porty PC Nvidia",
                    icon="share",
                    order=10,
                    interactionType=InteractionType.MODAL_FORM.value,
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
                    ApiParameter(name="host", type="string", location="query", required=False, default="nvidia"),
                    ApiParameter(name="lines", type="integer", location="query", required=False, default=60),
                ],
                nlIntents=[
                    NLIntent(lang="pl", phrases=["pobierz logi", "pokaż ostatnie logi"]),
                    NLIntent(lang="en", phrases=["fetch logs", "show system logs"]),
                ],
                menuBinding=MenuBinding(
                    category="Diagnostics",
                    group="Logs",
                    label="Pobierz logi systemowe",
                    icon="file-text",
                    order=20,
                    interactionType=InteractionType.TRIGGER.value,
                ),
            ),
            ApiEndpoint(
                id="prepanel.scenarios.test_hui",
                service="prepanel",
                protocol="kvm",
                title="Scenariusz Test HUI",
                description="Uruchamia interfejs testu manualnego HUI w oknie noVNC",
                readOnly=False,
                roles=["admin", "dev"],
                tags=["scenario", "hui", "c2004"],
                nlIntents=[
                    NLIntent(lang="pl", phrases=["uruchom test hui", "test manualny hui"]),
                    NLIntent(lang="en", phrases=["run test hui", "launch hui test"]),
                ],
                menuBinding=MenuBinding(
                    category="Scenarios",
                    group="C2004",
                    label="Test Manualny HUI",
                    icon="play",
                    order=30,
                    interactionType=InteractionType.TRIGGER.value,
                    badge="HUI",
                ),
            ),
            ApiEndpoint(
                id="app.auth.login",
                service="app",
                protocol="rest",
                title="Logowanie użytkownika",
                description="Uwierzytelnienie w aplikacji głównej",
                readOnly=False,
                roles=["admin", "dev", "viewer", "guest"],
                tags=["auth", "identity"],
                parameters=[
                    ApiParameter(name="email", type="string", location="body", required=True),
                    ApiParameter(name="password", type="string", location="body", required=True),
                ],
                nlIntents=[
                    NLIntent(lang="pl", phrases=["zaloguj się", "logowanie"]),
                    NLIntent(lang="en", phrases=["login", "sign in"]),
                ],
                menuBinding=MenuBinding(
                    category="Identity",
                    group="Authentication",
                    label="Logowanie do platformy",
                    icon="lock",
                    order=5,
                    interactionType=InteractionType.MODAL_FORM.value,
                ),
            ),
        ]
    )


def test_registry_serialization(sample_registry: ApiRegistry):
    data = sample_registry.to_dict()
    assert data["schema"] == "wellmanifest.api-registry/v1"
    assert data["version"] == "0.1.0"
    assert len(data["services"]) == 3
    assert len(data["endpoints"]) == 4

    # Roundtrip from dict
    restored = ApiRegistry.from_dict(data)
    assert len(restored.endpoints) == 4
    assert restored.endpoints[0].id == "premesh.ports.share"


def test_dynamic_menu_generation(sample_registry: ApiRegistry):
    gen = MenuGenerator(sample_registry)
    menu = gen.generate_menu(user_role="admin")

    assert menu["schema"] == "wellmanifest.menu-tree/v1"
    assert "categories" in menu
    assert len(menu["categories"]) == 4

    # Check categories ordering
    cat_titles = [c["title"] for c in menu["categories"]]
    assert "Identity" in cat_titles
    assert "Port Sharing" in cat_titles
    assert "Diagnostics" in cat_titles
    assert "Scenarios" in cat_titles

    # Verify form schema generation for modal forms
    port_item = None
    for cat in menu["categories"]:
        if cat["title"] == "Port Sharing":
            port_item = cat["groups"][0]["items"][0]
    assert port_item is not None
    assert port_item["interactionType"] == "modal_form"
    assert port_item["formSchema"] is not None
    assert len(port_item["formSchema"]["fields"]) == 3


def test_command_palette_search_index(sample_registry: ApiRegistry):
    gen = MenuGenerator(sample_registry)
    menu = gen.generate_menu(user_role="admin")

    index = menu["searchIndex"]
    assert len(index) == 4

    # Check search keywords
    hui_search = next(item for item in index if item["endpointId"] == "prepanel.scenarios.test_hui")
    assert "hui" in hui_search["keywords"]
    assert "c2004" in hui_search["keywords"]
    assert hui_search["category"] == "Scenarios"


def test_fast_path_bilingual_nl_matching(sample_registry: ApiRegistry):
    matcher = NLIntentMatcher(sample_registry)

    # Polish query
    plan_pl = matcher.parse("Udostępnij porty na maszynie nvidia dla konta prototypowanie")
    assert plan_pl.confidence == 1.0
    assert plan_pl.strategy == "deterministic"
    assert plan_pl.actions[0].endpointId == "premesh.ports.share"
    assert plan_pl.actions[0].parameters["account"] == "prototypowanie"
    assert plan_pl.actions[0].parameters["host"] == "nvidia"

    # English query
    plan_en = matcher.parse("Share ports for account dev on host localhost")
    assert plan_en.confidence == 1.0
    assert plan_en.actions[0].endpointId == "premesh.ports.share"
    assert plan_en.actions[0].parameters["account"] == "dev"
    assert plan_en.actions[0].parameters["host"] == "localhost"


def test_entity_extraction_ports_and_logs(sample_registry: ApiRegistry):
    matcher = NLIntentMatcher(sample_registry)

    # Custom ports extraction
    plan_custom_ports = matcher.parse("udostępnij porty 8100 8096 na hoscie nvidia")
    assert plan_custom_ports.actions[0].parameters["ports"] == [8100, 8096]

    # Lines extraction
    plan_logs = matcher.parse("Pokaż 120 linii logów z maszyny nvidia")
    assert plan_logs.actions[0].endpointId == "premesh.logs.fetch"
    assert plan_logs.actions[0].parameters["lines"] == 120
    assert plan_logs.actions[0].parameters["host"] == "nvidia"


def test_rbac_security_fencing(sample_registry: ApiRegistry):
    orchestrator = ApiOrchestrator(sample_registry, mock_mode=True)

    # Admin access allowed
    _, admin_res = orchestrator.query("uruchom test hui", caller_role="admin")
    assert admin_res[0].success is True
    assert admin_res[0].statusCode == 200

    # Viewer denied on mutating action
    _, viewer_res = orchestrator.query("uruchom test hui", caller_role="viewer")
    assert viewer_res[0].success is False
    assert viewer_res[0].statusCode == 403
    assert viewer_res[0].error["code"] == "PERMISSION_DENIED"

    # Viewer allowed on read_only logs
    _, logs_res = orchestrator.query("pobierz logi", caller_role="viewer")
    assert logs_res[0].success is True
    assert logs_res[0].statusCode == 200


def test_html_component_export(sample_registry: ApiRegistry):
    gen = MenuGenerator(sample_registry)
    menu = gen.generate_menu()
    html = gen.export_html_component(menu)

    assert "<!DOCTYPE html>" in html
    assert "NL-API-LLM Standard" in html
    assert "Ctrl+K" in html
    assert "premesh.ports.share" in html
