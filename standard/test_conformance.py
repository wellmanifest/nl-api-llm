"""
Conformance test suite for wellmanifest/nl-api-llm standard.
Verifies registry schema validation, dynamic menu generation, command palette indexing,
bilingual fast-path parsing, entity extraction, and RBAC execution fences.
"""

import json
from pathlib import Path

import pytest

from standard.nl_api_llm import (
    MAX_LOG_LINES,
    MAX_QUERY_CHARS,
    ApiEndpoint,
    ApiOrchestrator,
    ApiParameter,
    ApiRegistry,
    ApiService,
    InteractionType,
    LLMQueryCompiler,
    MenuBinding,
    MenuGenerator,
    NLIntent,
    NLIntentMatcher,
    main,
    read_strict_json,
    write_atomic_text,
)


@pytest.fixture
def sample_registry() -> ApiRegistry:
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
            ApiService(
                id="app",
                name="Platform Application Core",
                protocol="rest",
                defaultPort=8080,
            ),
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
                    ApiParameter(
                        name="email", type="string", location="body", required=True
                    ),
                    ApiParameter(
                        name="password", type="string", location="body", required=True
                    ),
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
        ],
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
    hui_search = next(
        item for item in index if item["endpointId"] == "prepanel.scenarios.test_hui"
    )
    assert "hui" in hui_search["keywords"]
    assert "c2004" in hui_search["keywords"]
    assert hui_search["category"] == "Scenarios"


def test_fast_path_bilingual_nl_matching(sample_registry: ApiRegistry):
    matcher = NLIntentMatcher(sample_registry)

    # Polish query
    plan_pl = matcher.parse(
        "Udostępnij porty na maszynie nvidia dla konta prototypowanie"
    )
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


def test_menu_binding_dual_naming_and_result_envelope():
    # Verify snake_case menu_binding parsing
    raw_data = {
        "schema": "wellmanifest.api-registry/v1",
        "version": "0.1.0",
        "services": [{"id": "svc", "name": "Service", "protocol": "rest"}],
        "endpoints": [
            {
                "id": "svc.action",
                "service": "svc",
                "protocol": "rest",
                "title": "Action",
                "menu_binding": {
                    "category": "work",
                    "group": "Tools",
                    "label": "Execute Action",
                    "view_route": "/work/action",
                    "interaction_type": "view_navigate",
                    "order": 5,
                },
            }
        ],
    }

    registry = ApiRegistry.from_dict(raw_data)
    ep = registry.endpoints[0]
    assert ep.menuBinding is not None
    assert ep.menuBinding.category == "work"
    assert ep.menuBinding.viewRoute == "/work/action"
    assert ep.menuBinding.interactionType == "view_navigate"

    # Verify result envelope harmonization
    orchestrator = ApiOrchestrator(registry, mock_mode=True)
    _, results = orchestrator.query("pobierz", caller_role="admin")
    if results:
        res = results[0]
        res_dict = res.to_dict()
        assert "status" in res_dict
        assert res_dict["status"] in ("success", "error")
        assert "errors" in res_dict
        assert isinstance(res_dict["errors"], list)
        assert "meta" in res_dict
        assert isinstance(res_dict["meta"], dict)


def test_html_component_blocks_script_breakout_and_inline_xss():
    xss_registry = ApiRegistry(
        schema="wellmanifest.api-registry/v1",
        version="0.1.0",
        services=[ApiService(id="svc", name="Svc", protocol="rest")],
        endpoints=[
            ApiEndpoint(
                id="svc.xss",
                service="svc",
                protocol="rest",
                title="</script><script>alert(1)</script>",
                description="<img src=x onerror=alert(2)>",
                nlIntents=[NLIntent(lang="en", phrases=["'); alert(3); //"])],
                menuBinding=MenuBinding(
                    category="<b>Cat</b>",
                    group="<i>Grp</i>",
                    label="</script><svg onload=alert(4)>",
                    badge="<script>5</script>",
                ),
            )
        ],
    )
    gen = MenuGenerator(xss_registry)
    html = gen.export_html_component(gen.generate_menu())
    assert html.count("</script>") == 1
    assert "<script>alert(1)" not in html
    assert "<svg onload=alert(4)>" not in html
    assert "innerHTML = `" not in html
    assert "onclick=" not in html
    assert "\\u003c/script\\u003e" in html


def test_strict_json_io_symlink_traversal_and_atomic_write(
    sample_registry: ApiRegistry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    reg_file = real_dir / "registry.json"
    write_atomic_text(reg_file, json.dumps(sample_registry.to_dict()))
    loaded = read_strict_json(reg_file)
    assert loaded["schema"] == "wellmanifest.api-registry/v1"

    sym_file = tmp_path / "sym_reg.json"
    sym_file.symlink_to(reg_file)
    with pytest.raises(ValueError, match="symlink"):
        read_strict_json(sym_file)
    with pytest.raises(ValueError, match="symlink"):
        write_atomic_text(sym_file, "{}")

    sym_dir = tmp_path / "sym_dir"
    sym_dir.symlink_to(real_dir)
    with pytest.raises(ValueError, match="symlink"):
        read_strict_json(f"{sym_dir}/../real/registry.json")

    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    monkeypatch.chdir(sub_dir)
    with pytest.raises(ValueError, match="symlink"):
        read_strict_json("../sym_dir/registry.json")

    for name, bad_json in [
        ("dup.json", '{"a": 1, "a": 2}'),
        ("nan.json", '{"a": NaN}'),
        ("huge_int.json", '{"a": ' + ("9" * 5000) + "}"),
        ("surrogate.json", '{"a": "\\ud800"}'),
    ]:
        bad_path = real_dir / name
        bad_path.write_text(bad_json, encoding="utf-8")
        with pytest.raises(ValueError):
            read_strict_json(bad_path)

    out_html = real_dir / "menu.html"
    assert (
        main(["--menu", "--registry", str(reg_file), "--output-html", str(out_html)])
        == 0
    )
    assert out_html.is_file()
    assert main(["--menu", "--registry", str(sym_file)]) == 1


def test_query_bounds_huge_log_lines_empty_query_and_module_line_limits(
    sample_registry: ApiRegistry,
):
    matcher = NLIntentMatcher(sample_registry)
    huge_lines_plan = matcher.parse("Pokaż " + ("9" * 5000) + " linii logów")
    assert huge_lines_plan.actions[0].endpointId == "premesh.logs.fetch"
    assert huge_lines_plan.actions[0].parameters["lines"] == MAX_LOG_LINES

    punct_only_plan = matcher.parse("??? !!! ...")
    assert punct_only_plan.confidence == 0.0
    assert punct_only_plan.strategy == "llm"
    assert punct_only_plan.actions == []

    with pytest.raises(ValueError, match="query length exceeds"):
        matcher.parse("a" * (MAX_QUERY_CHARS + 1))

    compiler = LLMQueryCompiler(sample_registry)
    ctx_plan = compiler.compile(
        "custom freeform", context={"sessionId": "s-42", "k": "v"}
    )
    assert ctx_plan.sessionId == "s-42"
    assert ctx_plan.actions[0].parameters["context"] == {"sessionId": "s-42", "k": "v"}

    std_dir = Path(__file__).resolve().parent
    for py_file in sorted(std_dir.glob("*.py")):
        line_count = sum(1 for _ in py_file.open("r", encoding="utf-8"))
        assert line_count < 500, f"{py_file.name} has {line_count} lines (>= 500)"
