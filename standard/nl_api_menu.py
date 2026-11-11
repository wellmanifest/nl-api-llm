"""Dynamic menu and XSS-hardened command palette HTML generator for wellmanifest/nl-api-llm."""

from __future__ import annotations

import json
import time
from typing import Any

try:
    from .nl_api_models import ApiRegistry, InteractionType
except ImportError:
    from nl_api_models import ApiRegistry, InteractionType  # type: ignore[no-redef]

__all__ = ["MenuGenerator", "_serialize_script_json"]


def _serialize_script_json(data: Any) -> str:
    """Serialize JSON safely for inline <script> blocks without </script> or line-sep breakouts."""
    raw = json.dumps(data, indent=2, allow_nan=False)
    return (
        raw.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


class MenuGenerator:
    """Generates structured, searchable frontend navigation menus and command palettes."""

    def __init__(self, registry: ApiRegistry):
        self.registry = registry

    def generate_menu(self, user_role: str = "admin") -> dict[str, Any]:
        categories_dict: dict[str, dict[str, Any]] = {}
        search_index: list[dict[str, Any]] = []

        sorted_endpoints = sorted(
            [e for e in self.registry.endpoints if e.menuBinding],
            key=lambda e: (e.menuBinding.order if e.menuBinding else 999, e.title),
        )

        for ep in sorted_endpoints:
            if ep.roles and user_role not in ep.roles and "all" not in ep.roles:
                continue

            mb = ep.menuBinding
            assert mb is not None
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

            sample_prompts: list[str] = []
            for nli in ep.nlIntents:
                sample_prompts.extend(nli.phrases[:2])

            form_schema = None
            if mb.interactionType == InteractionType.MODAL_FORM.value or any(
                p.required for p in ep.parameters
            ):
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

            keywords = [
                ep.id,
                mb.label.lower(),
                ep.title.lower(),
                mb.category.lower(),
                mb.group.lower(),
            ]
            keywords.extend(ep.tags)
            for p in ep.parameters:
                keywords.append(p.name)

            search_index.append(
                {
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
                }
            )

        categories: list[dict[str, Any]] = []
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

    def export_html_component(self, menu_data: dict[str, Any]) -> str:
        """Generates a standalone, XSS-hardened searchable HTML/JS menu and command palette."""
        menu_json = _serialize_script_json(menu_data)
        return f"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="UTF-8">
  <title>API Menu &amp; Command Palette (NL-API-LLM)</title>
  <style>
    :root {{
      --bg: #12141a;
      --card-bg: #1a1d26;
      --border: #2e3444;
      --text: #e1e4ea;
      --text-muted: #8b949e;
      --accent: #3b82f6;
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
        <span>Universal API Menu</span>
        <span class="badge-std">NL-API-LLM Standard</span>
      </h1>
      <button class="palette-trigger" type="button" id="open-palette-btn">
        <span>Szukaj API lub akcji...</span>
        <span class="kbd">Ctrl+K</span>
      </button>
    </header>
    <div class="grid" id="menu-grid"></div>
  </div>
  <div id="palette-modal">
    <div class="palette-box">
      <input type="text" id="palette-search" class="palette-input" placeholder="Wpisz zapytanie NL lub nazwe akcji...">
      <div class="palette-results" id="palette-results"></div>
    </div>
  </div>
  <script>
    const MENU_DATA = {menu_json};

    function el(tag, className, text) {{
      const node = document.createElement(tag);
      if (className) node.className = className;
      if (text !== undefined && text !== null) node.textContent = String(text);
      return node;
    }}

    function renderMenu() {{
      const grid = document.getElementById('menu-grid');
      grid.replaceChildren();
      (MENU_DATA.categories || []).forEach(cat => {{
        const card = el('div', 'category-card');
        card.appendChild(el('div', 'category-title', cat.title));
        (cat.groups || []).forEach(grp => {{
          card.appendChild(el('div', 'group-title', grp.title));
          (grp.items || []).forEach(item => {{
            const row = el('div', 'menu-item');
            const left = document.createElement('div');
            left.appendChild(el('div', 'item-label', item.label));
            left.appendChild(el('div', 'item-desc', item.description));
            row.appendChild(left);
            if (item.badge) row.appendChild(el('span', 'item-badge', item.badge));
            row.addEventListener('click', () => handleItemClick(item.endpointId, item.interactionType, item.viewRoute || ''));
            card.appendChild(row);
          }});
        }});
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
      resultsDiv.replaceChildren();
      const matches = (MENU_DATA.searchIndex || []).filter(item => {{
        if (!qNorm) return true;
        return String(item.title || '').toLowerCase().includes(qNorm) ||
               String(item.description || '').toLowerCase().includes(qNorm) ||
               String(item.category || '').toLowerCase().includes(qNorm) ||
               (item.keywords || []).some(k => String(k).toLowerCase().includes(qNorm)) ||
               (item.prompts || []).some(p => String(p).toLowerCase().includes(qNorm));
      }});
      if (matches.length === 0) {{
        const empty = el('div', '', 'Brak wynikow dla zapytania.');
        empty.style.padding = '20px';
        empty.style.textAlign = 'center';
        resultsDiv.appendChild(empty);
        return;
      }}
      matches.slice(0, 15).forEach(m => {{
        const div = el('div', 'palette-item');
        const info = document.createElement('div');
        info.appendChild(el('div', 'item-label', `${{m.title}} [${{m.category}}]`));
        info.appendChild(el('div', 'item-desc', m.description));
        if (m.prompts && m.prompts.length) {{
          const chips = document.createElement('div');
          m.prompts.forEach(p => {{
            const chip = el('span', 'prompt-chip', p);
            chip.addEventListener('click', ev => {{ ev.stopPropagation(); executePrompt(p); }});
            chips.appendChild(chip);
          }});
          info.appendChild(chips);
        }}
        div.appendChild(info);
        div.appendChild(el('span', 'item-badge', m.interactionType));
        div.addEventListener('click', () => {{
          closePalette();
          handleItemClick(m.endpointId, m.interactionType, m.viewRoute || '');
        }});
        resultsDiv.appendChild(div);
      }});
    }}

    function handleItemClick(endpointId, interactionType, viewRoute) {{
      alert(`[NL-API-LLM Dispatch]\\nEndpoint: ${{endpointId}}\\nTyp: ${{interactionType}}\\nRoute: ${{viewRoute || 'direct API execution'}}`);
    }}

    function executePrompt(promptText) {{
      closePalette();
      alert(`[NL Fast-Path Query]\\nTekst: "${{promptText}}"`);
    }}

    document.getElementById('open-palette-btn').addEventListener('click', openPalette);
    document.getElementById('palette-modal').addEventListener('click', e => {{ if (e.target.id === 'palette-modal') closePalette(); }});
    document.getElementById('palette-search').addEventListener('input', e => filterPalette(e.target.value));
    window.addEventListener('keydown', e => {{
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {{ e.preventDefault(); openPalette(); }}
      if (e.key === 'Escape') closePalette();
    }});
    renderMenu();
  </script>
</body>
</html>"""
