#!/usr/bin/env python3
"""
wellmanifest/nl-api-llm: Universal Natural Language, Multi-Protocol API,
and LLM Orchestration Standard Reference Implementation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


# ============================================================================
# 1. Domain Models & Protocols
# ============================================================================

class ProtocolType(str, Enum):
    REST = "rest"
    CLI = "cli"
    GRPC = "grpc"
    WEBSOCKET = "websocket"
    MCP = "mcp"
    KVM = "kvm"


class InteractionType(str, Enum):
    TRIGGER = "trigger"
    MODAL_FORM = "modal_form"
    VIEW_NAVIGATE = "view_navigate"
    TAB_OPEN = "tab_open"


@dataclass
class ApiParameter:
    name: str
    type: str  # string, integer, number, boolean, array, object
    location: str  # path, query, body, header, flag, arg
    required: bool = True
    default: Any = None
    description: str = ""
    enum: Optional[List[Any]] = None


@dataclass
class RestSpec:
    method: str
    path: str
    contentType: str = "application/json"


@dataclass
class CliSpec:
    commandTemplate: str
    binary: Optional[str] = None


@dataclass
class KvmSpec:
    action: str  # navigate, type, click, screenshot, focus, scenario


@dataclass
class MenuBinding:
    category: str
    group: str
    label: str
    icon: str = "circle"
    order: int = 100
    viewRoute: Optional[str] = None
    interactionType: str = InteractionType.TRIGGER.value
    badge: Optional[str] = None


@dataclass
class NLIntent:
    lang: str  # pl, en
    phrases: List[str]
    patterns: List[str] = field(default_factory=list)


@dataclass
class ApiEndpoint:
    id: str
    service: str
    protocol: str
    title: str
    description: str = ""
    readOnly: bool = True
    roles: List[str] = field(default_factory=lambda: ["admin", "dev", "operator", "viewer"])
    tags: List[str] = field(default_factory=list)
    rest: Optional[RestSpec] = None
    cli: Optional[CliSpec] = None
    kvm: Optional[KvmSpec] = None
    parameters: List[ApiParameter] = field(default_factory=list)
    nlIntents: List[NLIntent] = field(default_factory=list)
    menuBinding: Optional[MenuBinding] = None


@dataclass
class ApiService:
    id: str
    name: str
    protocol: str
    description: str = ""
    baseUrl: Optional[str] = None
    defaultPort: Optional[int] = None


@dataclass
class ApiRegistry:
    schema: str
    version: str
    services: List[ApiService]
    endpoints: List[ApiEndpoint]
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ApiRegistry:
        services = [
            ApiService(
                id=s["id"],
                name=s["name"],
                protocol=s["protocol"],
                description=s.get("description", ""),
                baseUrl=s.get("baseUrl"),
                defaultPort=s.get("defaultPort"),
            )
            for s in data.get("services", [])
        ]

        endpoints = []
        for e in data.get("endpoints", []):
            rest_spec = None
            if "rest" in e and e["rest"]:
                rest_spec = RestSpec(
                    method=e["rest"]["method"],
                    path=e["rest"]["path"],
                    contentType=e["rest"].get("contentType", "application/json"),
                )

            cli_spec = None
            if "cli" in e and e["cli"]:
                cli_spec = CliSpec(
                    commandTemplate=e["cli"]["commandTemplate"],
                    binary=e["cli"].get("binary"),
                )

            kvm_spec = None
            if "kvm" in e and e["kvm"]:
                kvm_spec = KvmSpec(action=e["kvm"]["action"])

            parameters = [
                ApiParameter(
                    name=p["name"],
                    type=p.get("type", "string"),
                    location=p.get("location", "query"),
                    required=p.get("required", False),
                    default=p.get("default"),
                    description=p.get("description", ""),
                    enum=p.get("enum"),
                )
                for p in e.get("parameters", [])
            ]

            nl_intents = [
                NLIntent(
                    lang=n.get("lang", "en"),
                    phrases=n.get("phrases", []),
                    patterns=n.get("patterns", []),
                )
                for n in e.get("nlIntents", [])
            ]

            menu_binding = None
            raw_mb = e.get("menuBinding") or e.get("menu_binding")
            if raw_mb:
                mb = raw_mb
                menu_binding = MenuBinding(
                    category=mb["category"],
                    group=mb.get("group", "General"),
                    label=mb["label"],
                    icon=mb.get("icon", "circle"),
                    order=mb.get("order", 100),
                    viewRoute=mb.get("viewRoute") or mb.get("view_route"),
                    interactionType=mb.get("interactionType") or mb.get("interaction_type", InteractionType.TRIGGER.value),
                    badge=mb.get("badge"),
                )

            endpoints.append(
                ApiEndpoint(
                    id=e["id"],
                    service=e["service"],
                    protocol=e["protocol"],
                    title=e["title"],
                    description=e.get("description", ""),
                    readOnly=e.get("readOnly", True),
                    roles=e.get("roles", ["admin", "dev"]),
                    tags=e.get("tags", []),
                    rest=rest_spec,
                    cli=cli_spec,
                    kvm=kvm_spec,
                    parameters=parameters,
                    nlIntents=nl_intents,
                    menuBinding=menu_binding,
                )
            )

        return cls(
            schema=data.get("schema", "wellmanifest.api-registry/v1"),
            version=data.get("version", "0.1.0"),
            services=services,
            endpoints=endpoints,
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "metadata": self.metadata,
            "services": [asdict(s) for s in self.services],
            "endpoints": [
                {
                    "id": e.id,
                    "service": e.service,
                    "protocol": e.protocol,
                    "title": e.title,
                    "description": e.description,
                    "readOnly": e.readOnly,
                    "roles": e.roles,
                    "tags": e.tags,
                    "rest": asdict(e.rest) if e.rest else None,
                    "cli": asdict(e.cli) if e.cli else None,
                    "kvm": asdict(e.kvm) if e.kvm else None,
                    "parameters": [asdict(p) for p in e.parameters],
                    "nlIntents": [asdict(n) for n in e.nlIntents],
                    "menuBinding": asdict(e.menuBinding) if e.menuBinding else None,
                }
                for e in self.endpoints
            ],
        }


# ============================================================================
# 2. Dynamic Menu & Command Palette Generator
# ============================================================================

class MenuGenerator:
    """Generates structured, searchable frontend navigation menus and command palettes."""

    def __init__(self, registry: ApiRegistry):
        self.registry = registry

    def generate_menu(self, user_role: str = "admin") -> Dict[str, Any]:
        categories_dict: Dict[str, Dict[str, Any]] = {}
        search_index: List[Dict[str, Any]] = []

        # Sort endpoints by menu order
        sorted_endpoints = sorted(
            [e for e in self.registry.endpoints if e.menuBinding],
            key=lambda e: (e.menuBinding.order if e.menuBinding else 999, e.title)
        )

        for ep in sorted_endpoints:
            # RBAC check
            if ep.roles and user_role not in ep.roles and "all" not in ep.roles:
                continue

            mb = ep.menuBinding
            cat_id = mb.category.lower().replace(" ", "_")
            if cat_id not in categories_dict:
                categories_dict[cat_id] = {
                    "id": cat_id,
                    "title": mb.category,
                    "icon": mb.icon,
                    "order": mb.order,
                    "groups": {},
                }

            group_id = mb.group.lower().replace(" ", "_")
            if group_id not in categories_dict[cat_id]["groups"]:
                categories_dict[cat_id]["groups"][group_id] = {
                    "id": group_id,
                    "title": mb.group,
                    "items": [],
                }

            # Collect sample prompts from nlIntents
            sample_prompts = []
            for nli in ep.nlIntents:
                sample_prompts.extend(nli.phrases[:2])

            # Form schema for modal parameters
            form_schema = None
            if mb.interactionType == InteractionType.MODAL_FORM.value or any(p.required for p in ep.parameters):
                form_schema = {
                    "fields": [
                        {
                            "name": p.name,
                            "label": p.name.replace("_", " ").title(),
                            "type": p.type,
                            "required": p.required,
                            "default": p.default,
                            "options": p.enum or [],
                            "description": p.description,
                        }
                        for p in ep.parameters
                    ]
                }

            item_data = {
                "id": f"menu_{ep.id.replace('.', '_')}",
                "endpointId": ep.id,
                "label": mb.label,
                "description": ep.description,
                "icon": mb.icon,
                "order": mb.order,
                "interactionType": mb.interactionType,
                "viewRoute": mb.viewRoute,
                "badge": mb.badge,
                "roles": ep.roles,
                "samplePrompts": sample_prompts,
                "formSchema": form_schema,
            }
            categories_dict[cat_id]["groups"][group_id]["items"].append(item_data)

            # Build search index entry for Command Palette (Ctrl+K)
            keywords = [ep.id, mb.label.lower(), ep.title.lower(), mb.category.lower(), mb.group.lower()]
            keywords.extend(ep.tags)
            for p in ep.parameters:
                keywords.append(p.name)

            search_index.append({
                "id": item_data["id"],
                "endpointId": ep.id,
                "title": mb.label,
                "description": ep.description or ep.title,
                "category": mb.category,
                "group": mb.group,
                "icon": mb.icon,
                "interactionType": mb.interactionType,
                "viewRoute": mb.viewRoute,
                "keywords": list(set(keywords)),
                "prompts": sample_prompts,
            })

        # Format categories as array
        categories = []
        for cat in sorted(categories_dict.values(), key=lambda c: c["order"]):
            groups_list = []
            for grp in cat["groups"].values():
                grp["items"] = sorted(grp["items"], key=lambda i: i["order"])
                groups_list.append(grp)
            cat["groups"] = groups_list
            categories.append(cat)

        return {
            "schema": "wellmanifest.menu-tree/v1",
            "version": self.registry.version,
            "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "categories": categories,
            "searchIndex": search_index,
        }

    def export_html_component(self, menu_data: Dict[str, Any]) -> str:
        """Generates a standalone, searchable HTML/JS menu and command palette component."""
        menu_json = json.dumps(menu_data, indent=2)
        return f"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="UTF-8">
  <title>API Menu & Command Palette (NL-API-LLM)</title>
  <style>
    :root {{
      --bg: #12141a;
      --card-bg: #1a1d26;
      --border: #2e3444;
      --text: #e1e4ea;
      --text-muted: #8b949e;
      --accent: #3b82f6;
      --accent-hover: #60a5fa;
      --badge-bg: #212636;
      --badge-text: #93c5fd;
      --input-bg: #0d0e12;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    body {{ background: var(--bg); color: var(--text); padding: 24px; }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--border); }}
    h1 {{ font-size: 20px; font-weight: 600; display: flex; align-items: center; gap: 10px; }}
    .badge-std {{ font-size: 11px; background: #1e3a8a; color: #93c5fd; padding: 3px 8px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.5px; }}
    .palette-trigger {{ background: var(--card-bg); border: 1px solid var(--border); color: var(--text-muted); padding: 8px 16px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 8px; font-size: 13px; }}
    .kbd {{ background: var(--input-bg); border: 1px solid var(--border); padding: 2px 6px; border-radius: 4px; font-size: 11px; font-family: monospace; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 20px; }}
    .category-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 18px; }}
    .category-title {{ font-size: 15px; font-weight: 600; color: #60a5fa; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }}
    .group-title {{ font-size: 12px; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.5px; margin: 10px 0 6px 0; }}
    .menu-item {{ display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; border-radius: 6px; background: rgba(255,255,255,0.02); margin-bottom: 6px; cursor: pointer; transition: all 0.15s; text-decoration: none; color: inherit; border: 1px solid transparent; }}
    .menu-item:hover {{ background: rgba(59, 130, 246, 0.1); border-color: rgba(59, 130, 246, 0.3); transform: translateX(2px); }}
    .item-label {{ font-size: 13px; font-weight: 500; }}
    .item-desc {{ font-size: 11px; color: var(--text-muted); margin-top: 2px; }}
    .item-badge {{ font-size: 10px; background: var(--badge-bg); color: var(--badge-text); padding: 2px 6px; border-radius: 4px; font-family: monospace; }}
    
    /* Command Palette Modal */
    #palette-modal {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); backdrop-filter: blur(4px); z-index: 9999; justify-content: center; align-items: flex-start; padding-top: 10vh; }}
    #palette-modal.active {{ display: flex; }}
    .palette-box {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; width: 100%; max-width: 640px; box-shadow: 0 20px 40px rgba(0,0,0,0.5); overflow: hidden; }}
    .palette-input {{ width: 100%; padding: 16px; background: var(--input-bg); border: none; border-bottom: 1px solid var(--border); color: var(--text); font-size: 15px; outline: none; }}
    .palette-results {{ max-height: 400px; overflow-y: auto; padding: 8px; }}
    .palette-item {{ padding: 10px 14px; border-radius: 8px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }}
    .palette-item:hover, .palette-item.selected {{ background: rgba(59, 130, 246, 0.2); }}
    .prompt-chip {{ display: inline-block; font-size: 11px; background: #262c3b; color: #cbd5e1; padding: 2px 8px; border-radius: 12px; margin: 2px; cursor: pointer; }}
    .prompt-chip:hover {{ background: #3b82f6; color: white; }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>
        <span>🌐 Universal API Menu</span>
        <span class="badge-std">NL-API-LLM Standard</span>
      </h1>
      <button class="palette-trigger" onclick="openPalette()">
        <span>🔍 Szukaj API lub akcji...</span>
        <span class="kbd">Ctrl+K</span>
      </button>
    </header>

    <div class="grid" id="menu-grid"></div>
  </div>

  <div id="palette-modal" onclick="if(event.target===this)closePalette()">
    <div class="palette-box">
      <input type="text" id="palette-search" class="palette-input" placeholder="Wpisz zapytanie NL lub nazwę akcji (np. 'udostępnij porty', 'logi', 'hui')..." oninput="filterPalette(this.value)">
      <div class="palette-results" id="palette-results"></div>
    </div>
  </div>

  <script>
    const MENU_DATA = {menu_json};

    function renderMenu() {{
      const grid = document.getElementById('menu-grid');
      grid.innerHTML = '';
      MENU_DATA.categories.forEach(cat => {{
        const card = document.createElement('div');
        card.className = 'category-card';
        let groupsHtml = '';
        cat.groups.forEach(grp => {{
          groupsHtml += `<div class="group-title">${{grp.title}}</div>`;
          grp.items.forEach(item => {{
            const badge = item.badge ? `<span class="item-badge">${{item.badge}}</span>` : '';
            groupsHtml += `
              <div class="menu-item" onclick="handleItemClick('${{item.endpointId}}', '${{item.interactionType}}', '${{item.viewRoute || ''}}')">
                <div>
                  <div class="item-label">${{item.label}}</div>
                  <div class="item-desc">${{item.description}}</div>
                </div>
                ${{badge}}
              </div>
            `;
          }});
        }});
        card.innerHTML = `<div class="category-title">📁 ${{cat.title}}</div>${{groupsHtml}}`;
        grid.appendChild(card);
      }});
    }}

    function openPalette() {{
      document.getElementById('palette-modal').classList.add('active');
      const input = document.getElementById('palette-search');
      input.value = '';
      input.focus();
      filterPalette('');
    }}

    function closePalette() {{
      document.getElementById('palette-modal').classList.remove('active');
    }}

    function filterPalette(q) {{
      const qNorm = q.trim().toLowerCase();
      const resultsDiv = document.getElementById('palette-results');
      resultsDiv.innerHTML = '';
      const matches = MENU_DATA.searchIndex.filter(item => {{
        if (!qNorm) return true;
        return item.title.toLowerCase().includes(qNorm) ||
               item.description.toLowerCase().includes(qNorm) ||
               item.category.toLowerCase().includes(qNorm) ||
               item.keywords.some(k => k.toLowerCase().includes(qNorm)) ||
               (item.prompts && item.prompts.some(p => p.toLowerCase().includes(qNorm)));
      }});

      if (matches.length === 0) {{
        resultsDiv.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">Brak wyników dla zapytania.</div>';
        return;
      }}

      matches.slice(0, 15).forEach(m => {{
        const div = document.createElement('div');
        div.className = 'palette-item';
        let chipsHtml = '';
        if (m.prompts) {{
          chipsHtml = m.prompts.map(p => `<span class="prompt-chip" onclick="event.stopPropagation(); executePrompt('${{p}}')">${{p}}</span>`).join('');
        }}
        div.innerHTML = `
          <div>
            <div style="font-size: 13px; font-weight: 500;">${{m.title}} <span style="font-size: 11px; color: var(--text-muted);">[${{m.category}}]</span></div>
            <div style="font-size: 11px; color: var(--text-muted);">${{m.description}}</div>
            ${{chipsHtml ? `<div style="margin-top: 4px;">${{chipsHtml}}</div>` : ''}}
          </div>
          <span class="item-badge">${{m.interactionType}}</span>
        `;
        div.onclick = () => {{
          closePalette();
          handleItemClick(m.endpointId, m.interactionType, m.viewRoute || '');
        }};
        resultsDiv.appendChild(div);
      }});
    }}

    function handleItemClick(endpointId, interactionType, viewRoute) {{
      alert(`[NL-API-LLM Dispatch]\nEndpoint: ${{endpointId}}\nTyp: ${{interactionType}}\nRoute: ${{viewRoute || 'direct API execution'}}`);
    }}

    function executePrompt(promptText) {{
      closePalette();
      alert(`[NL Fast-Path Query]\nTekst: "${{promptText}}"\nKierowanie do planera zapytań NL-API-LLM...`);
    }}

    window.addEventListener('keydown', e => {{
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {{
        e.preventDefault();
        openPalette();
      }}
      if (e.key === 'Escape') {{
        closePalette();
      }}
    }});

    renderMenu();
  </script>
</body>
</html>"""


# ============================================================================
# 3. Deterministic Multilingual NL Fast-Path Parser (Layer 3)
# ============================================================================

@dataclass
class CompiledAction:
    endpointId: str
    parameters: Dict[str, Any]
    description: str = ""


@dataclass
class ApiExecutionPlan:
    confidence: float
    strategy: str  # deterministic, llm
    actions: List[CompiledAction]
    rawQuery: str = ""
    sessionId: Optional[str] = None


class NLIntentMatcher:
    """Fast-path deterministic rule-based parser matching Polish & English intents to APIs in <1ms."""

    def __init__(self, registry: ApiRegistry):
        self.registry = registry
        self._endpoints_by_id = {e.id: e for e in registry.endpoints}

    def normalize(self, text: str) -> str:
        """Removes diacritics and normalizes whitespace and punctuation for tolerant matching."""
        text = text.lower().strip()
        pl_map = {
            'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n',
            'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z'
        }
        for k, v in pl_map.items():
            text = text.replace(k, v)
        text = re.sub(r'[,.!?\'";:()\[\]{}]', ' ', text)
        return re.sub(r'\s+', ' ', text).strip()

    def parse(self, raw_query: str, context: Optional[Dict[str, Any]] = None) -> ApiExecutionPlan:
        ctx = context or {}
        norm = self.normalize(raw_query)

        # 1. Port sharing pattern
        # "udostępnij porty", "port-share", "share ports", "wystaw porty"
        if any(w in norm for w in ["udostepnij porty", "port share", "wystaw porty", "share ports", "przekieruj porty"]):
            account = ctx.get("activeAccount", "prototypowanie")
            host = ctx.get("activeHost", "nvidia")
            m_acc = re.search(r'(?:dla konta|konto|account)\s+([a-zA-Z0-9_\-]+)', norm)
            if m_acc:
                account = m_acc.group(1)
            m_host = re.search(r'(?:na maszynie|host|maszyna)\s+([a-zA-Z0-9_\-]+)', norm)
            if m_host:
                host = m_host.group(1)

            # Extract ports if specified
            ports = [8100, 8096, 8094]
            port_matches = re.findall(r'\b(8\d{3}|3000|8888)\b', norm)
            if port_matches:
                ports = [int(p) for p in port_matches]

            return ApiExecutionPlan(
                confidence=1.0,
                strategy="deterministic",
                rawQuery=raw_query,
                actions=[
                    CompiledAction(
                        endpointId="premesh.ports.share",
                        parameters={"account": account, "host": host, "ports": ports},
                        description=f"Udostępnienie portów {ports} z hosta {host} do kontenera {account}",
                    )
                ]
            )

        # 2. System logs pattern
        # "pobierz logi", "pokaż logi", "fetch logs", "system logs", "daj logi", "logów"
        if any(w in norm for w in ["log", "logi", "logow", "pobierz log", "pokaz log", "fetch log", "system log", "view log"]):
            host = ctx.get("activeHost", "nvidia")
            lines = 60
            m_lines = re.search(r'(\d+)\s*(?:linii|wierszy|lines)', norm)
            if m_lines:
                lines = int(m_lines.group(1))
            m_host = re.search(r'(?:z hosta|host|maszyny)\s+([a-zA-Z0-9_\-]+)', norm)
            if m_host:
                host = m_host.group(1)

            return ApiExecutionPlan(
                confidence=1.0,
                strategy="deterministic",
                rawQuery=raw_query,
                actions=[
                    CompiledAction(
                        endpointId="premesh.logs.fetch",
                        parameters={"host": host, "lines": lines},
                        description=f"Pobranie ostatnich {lines} linii logów z hosta {host}",
                    )
                ]
            )

        # 3. HUI Test scenario
        # "test hui", "uruchom test hui", "run hui test", "c2004 test hui"
        if any(w in norm for w in ["test hui", "hui test", "uruchom test hui", "test-hui"]):
            account = ctx.get("activeAccount", "prototypowanie")
            host = ctx.get("activeHost", "nvidia")
            return ApiExecutionPlan(
                confidence=1.0,
                strategy="deterministic",
                rawQuery=raw_query,
                actions=[
                    CompiledAction(
                        endpointId="prepanel.scenarios.test_hui",
                        parameters={"account": account, "host": host},
                        description="Uruchomienie scenariusza Test Manualny HUI w oknie noVNC",
                    )
                ]
            )

        # 4. Connect Scenario
        # "connect scenario", "uruchom connect scenario", "scenariusz c2004", "edytor scenariuszy"
        if any(w in norm for w in ["connect scenario", "connect-scenario", "scenariusz c2004", "edytor scenariuszy"]):
            account = ctx.get("activeAccount", "prototypowanie")
            host = ctx.get("activeHost", "nvidia")
            return ApiExecutionPlan(
                confidence=1.0,
                strategy="deterministic",
                rawQuery=raw_query,
                actions=[
                    CompiledAction(
                        endpointId="prepanel.scenarios.connect_scenario",
                        parameters={"account": account, "host": host},
                        description="Uruchomienie scenariusza Connect-Scenario w noVNC",
                    )
                ]
            )

        # 5. System Health
        # "health", "status systemu", "healthz", "sprawdz system"
        if any(w in norm for w in ["health", "status systemu", "healthz", "sprawdz system"]):
            return ApiExecutionPlan(
                confidence=1.0,
                strategy="deterministic",
                rawQuery=raw_query,
                actions=[
                    CompiledAction(
                        endpointId="premesh.system.health",
                        parameters={},
                        description="Sprawdzenie stanu zdrowia usług premesh i prepanel",
                    )
                ]
            )

        # 6. Accounts listing
        # "konta", "pokaz konta", "wypisz konta", "list accounts"
        if any(w in norm for w in ["pokaz konta", "wypisz konta", "list accounts", "konta", "konta hub"]):
            host = ctx.get("activeHost", "nvidia")
            return ApiExecutionPlan(
                confidence=1.0,
                strategy="deterministic",
                rawQuery=raw_query,
                actions=[
                    CompiledAction(
                        endpointId="premesh.accounts.list",
                        parameters={"host": host},
                        description=f"Pobranie listy kont i kontenerów dla hosta {host}",
                    )
                ]
            )

        # 7. Fallback search across declared nlIntents in registry
        for ep in self.registry.endpoints:
            for intent in ep.nlIntents:
                for phrase in intent.phrases:
                    if self.normalize(phrase) in norm or norm in self.normalize(phrase):
                        return ApiExecutionPlan(
                            confidence=0.9,
                            strategy="deterministic",
                            rawQuery=raw_query,
                            actions=[
                                CompiledAction(
                                    endpointId=ep.id,
                                    parameters={},
                                    description=ep.description or ep.title,
                                )
                            ]
                        )

        # No deterministic match -> Pass to Layer 4 (LLM fallback)
        return ApiExecutionPlan(
            confidence=0.0,
            strategy="llm",
            rawQuery=raw_query,
            actions=[]
        )


# ============================================================================
# 4. LLM Multi-API Orchestration & Query Compiler (Layer 4)
# ============================================================================

class LLMQueryCompiler:
    """Compiles free-form or composite natural language queries into API execution DAGs."""

    def __init__(self, registry: ApiRegistry, llm_callable: Optional[Callable[[str, List[Dict[str, Any]]], Dict[str, Any]]] = None):
        self.registry = registry
        self.llm_callable = llm_callable

    def build_prompt_context(self, query: str) -> List[Dict[str, Any]]:
        """Filters API catalog to compact candidate tool schemas to preserve token budgets."""
        q_words = set(query.lower().split())
        candidates = []
        for ep in self.registry.endpoints:
            # Score candidate based on keyword overlap
            score = 0
            if any(w in ep.title.lower() for w in q_words):
                score += 2
            if any(w in ep.description.lower() for w in q_words):
                score += 1
            if any(w in ep.tags for w in q_words):
                score += 2
            if score > 0 or len(candidates) < 10:
                candidates.append({
                    "id": ep.id,
                    "service": ep.service,
                    "title": ep.title,
                    "description": ep.description,
                    "parameters": [asdict(p) for p in ep.parameters],
                })
        return candidates

    def compile(self, query: str, context: Optional[Dict[str, Any]] = None) -> ApiExecutionPlan:
        if self.llm_callable:
            candidates = self.build_prompt_context(query)
            res = self.llm_callable(query, candidates)
            actions = [
                CompiledAction(
                    endpointId=a["endpointId"],
                    parameters=a.get("parameters", {}),
                    description=a.get("description", ""),
                )
                for a in res.get("actions", [])
            ]
            return ApiExecutionPlan(
                confidence=res.get("confidence", 0.85),
                strategy="llm",
                rawQuery=query,
                actions=actions,
            )

        # Default fallback heuristic when offline
        return ApiExecutionPlan(
            confidence=0.5,
            strategy="llm",
            rawQuery=query,
            actions=[
                CompiledAction(
                    endpointId="prepanel.views.chat",
                    parameters={"prompt": query},
                    description="Przekierowanie do asystenta Chat LLM z zachowaniem kontekstu",
                )
            ]
        )


# ============================================================================
# 5. Protocol Execution Drivers & Orchestrator (Layer 5)
# ============================================================================

@dataclass
class ApiActionResult:
    success: bool
    endpointId: str
    protocol: str
    timestamp: str
    latencyMs: float
    statusCode: int = 200
    data: Any = None
    error: Optional[Dict[str, Any]] = None
    audit: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    errors: Optional[List[Dict[str, Any]]] = None
    meta: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.status is None:
            self.status = "success" if self.success else "error"
        if self.errors is None and self.error:
            self.errors = [self.error]
        elif self.errors is None:
            self.errors = []
        if self.meta is None:
            self.meta = {"protocol": self.protocol, "latencyMs": self.latencyMs, "endpointId": self.endpointId}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ApiOrchestrator:
    """End-to-end dispatcher orchestrating NL intake, parsing, planning, and execution."""

    def __init__(self, registry: ApiRegistry, mock_mode: bool = False):
        self.registry = registry
        self.mock_mode = mock_mode
        self.fast_matcher = NLIntentMatcher(registry)
        self.llm_compiler = LLMQueryCompiler(registry)
        self.endpoints = {e.id: e for e in registry.endpoints}

    def execute_plan(self, plan: ApiExecutionPlan, caller_role: str = "admin") -> List[ApiActionResult]:
        results = []
        for action in plan.actions:
            t0 = time.time()
            ep = self.endpoints.get(action.endpointId)
            if not ep:
                results.append(ApiActionResult(
                    success=False,
                    endpointId=action.endpointId,
                    protocol="unknown",
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    latencyMs=0.0,
                    statusCode=404,
                    error={"code": "ENDPOINT_NOT_FOUND", "message": f"Endpoint {action.endpointId} is not registered"}
                ))
                continue

            # Role check
            if ep.roles and caller_role not in ep.roles and "all" not in ep.roles:
                results.append(ApiActionResult(
                    success=False,
                    endpointId=action.endpointId,
                    protocol=ep.protocol,
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    latencyMs=0.0,
                    statusCode=403,
                    error={"code": "PERMISSION_DENIED", "message": f"Role '{caller_role}' is not authorized to invoke {ep.id}"}
                ))
                continue

            # Execution simulation / mock dispatch
            latency_ms = round((time.time() - t0) * 1000 + 1.2, 2)
            results.append(ApiActionResult(
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
                }
            ))
        return results

    def query(self, raw_query: str, context: Optional[Dict[str, Any]] = None, caller_role: str = "admin") -> Tuple[ApiExecutionPlan, List[ApiActionResult]]:
        # Fast path
        plan = self.fast_matcher.parse(raw_query, context)
        if plan.confidence < 0.8:
            plan = self.llm_compiler.compile(raw_query, context)

        results = self.execute_plan(plan, caller_role=caller_role)
        return plan, results


# ============================================================================
# 6. Self-Test Suite & CLI Interface
# ============================================================================

def run_self_tests() -> int:
    """Verifies standard conformance across registry, menu generator, and NL parsing."""
    print("=== Running wellmanifest/nl-api-llm Reference Self-Tests ===")
    
    # 1. Create minimal registry
    registry = ApiRegistry(
        schema="wellmanifest.api-registry/v1",
        version="0.1.0",
        services=[
            ApiService(id="premesh", name="Premesh Service Hub", protocol="rest", defaultPort=8081),
            ApiService(id="prepanel", name="Prepanel Desktop Panel", protocol="rest", defaultPort=8180),
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
                    interactionType="modal_form",
                    badge="8100/8096",
                )
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
                    interactionType="trigger",
                )
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
                    NLIntent(lang="pl", phrases=["uruchom test hui", "test manualny hui"]),
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
                )
            )
        ]
    )

    # Test 1: Registry Serialization
    reg_dict = registry.to_dict()
    assert reg_dict["version"] == "0.1.0"
    assert len(reg_dict["endpoints"]) == 3
    print("✓ Check 1: Registry serialization & schema parity passed.")

    # Test 2: Dynamic Menu Generation
    menu_gen = MenuGenerator(registry)
    menu = menu_gen.generate_menu(user_role="admin")
    assert len(menu["categories"]) == 3
    assert len(menu["searchIndex"]) == 3
    print("✓ Check 2: Dynamic menu & search index generation passed.")

    # Test 3: Deterministic Polish NL Parsing
    matcher = NLIntentMatcher(registry)
    plan_pl = matcher.parse("Udostępnij porty na maszynie nvidia dla konta prototypowanie")
    assert plan_pl.confidence == 1.0
    assert plan_pl.strategy == "deterministic"
    assert plan_pl.actions[0].endpointId == "premesh.ports.share"
    assert plan_pl.actions[0].parameters["account"] == "prototypowanie"
    assert plan_pl.actions[0].parameters["host"] == "nvidia"
    print("✓ Check 3: Deterministic Polish NL parsing passed.")

    # Test 4: System Logs Query Parsing
    plan_logs = matcher.parse("Pobierz ostatnie 100 linii logów z hosta nvidia")
    assert plan_logs.confidence == 1.0
    assert plan_logs.actions[0].endpointId == "premesh.logs.fetch"
    assert plan_logs.actions[0].parameters["lines"] == 100
    print("✓ Check 4: Parameterized system logs NL parsing passed.")

    # Test 5: Scenario Trigger Parsing
    plan_hui = matcher.parse("odpal test hui w novnc")
    assert plan_hui.confidence == 1.0
    assert plan_hui.actions[0].endpointId == "prepanel.scenarios.test_hui"
    print("✓ Check 5: Scenarios NL parsing passed.")

    # Test 6: End-to-End Orchestrator Dispatch & RBAC
    orchestrator = ApiOrchestrator(registry, mock_mode=True)
    plan, results = orchestrator.query("wystaw porty dla konta dev", caller_role="admin")
    assert len(results) == 1
    assert results[0].success is True
    assert results[0].statusCode == 200

    # Role denial test
    _, denied_res = orchestrator.query("udostępnij porty", caller_role="guest")
    assert denied_res[0].success is False
    assert denied_res[0].statusCode == 403
    print("✓ Check 6: End-to-end dispatch and RBAC security fence passed.")

    print("\nALL 6/6 SELF-TESTS PASSED CONFORMANCE.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="wellmanifest/nl-api-llm CLI reference driver")
    parser.add_argument("--self-test", action="store_true", help="Run comprehensive conformance tests")
    parser.add_argument("--menu", action="store_true", help="Generate frontend menu from registry file")
    parser.add_argument("--registry", type=str, help="Path to API registry JSON file")
    parser.add_argument("--output-json", type=str, help="Path to save generated menu JSON")
    parser.add_argument("--output-html", type=str, help="Path to save standalone HTML preview")
    parser.add_argument("--query", type=str, help="Parse and dispatch a natural language query")
    parser.add_argument("--role", type=str, default="admin", help="Active caller role for RBAC check")

    args = parser.parse_args()

    if args.self_test:
        sys.exit(run_self_tests())

    if args.menu:
        if not args.registry:
            print("Error: --registry is required when using --menu", file=sys.stderr)
            sys.exit(1)
        with open(args.registry, "r", encoding="utf-8") as f:
            data = json.load(f)
        reg = ApiRegistry.from_dict(data)
        gen = MenuGenerator(reg)
        menu_tree = gen.generate_menu(user_role=args.role)

        if args.output_json:
            with open(args.output_json, "w", encoding="utf-8") as f:
                json.dump(menu_tree, f, indent=2, ensure_ascii=False)
            print(f"Saved menu tree JSON to {args.output_json}")

        if args.output_html:
            html_content = gen.export_html_component(menu_tree)
            with open(args.output_html, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"Saved HTML menu preview to {args.output_html}")

        if not args.output_json and not args.output_html:
            print(json.dumps(menu_tree, indent=2, ensure_ascii=False))
        sys.exit(0)

    if args.query:
        if not args.registry:
            print("Error: --registry is required when using --query", file=sys.stderr)
            sys.exit(1)
        with open(args.registry, "r", encoding="utf-8") as f:
            data = json.load(f)
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
        print(json.dumps(output, indent=2, ensure_ascii=False))
        sys.exit(0)

    parser.print_help()


if __name__ == "__main__":
    main()
