"""Deterministic bilingual NL fast-path parser and LLM query compiler for wellmanifest/nl-api-llm."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

try:
    from .nl_api_models import (
        _INTENT_TRIGGERS,
        ApiEndpoint,
        ApiRegistry,
        _check_utf8_str,
    )
except ImportError:
    from nl_api_models import (  # type: ignore[no-redef]
        _INTENT_TRIGGERS,
        ApiEndpoint,
        ApiRegistry,
        _check_utf8_str,
    )

MAX_QUERY_CHARS = 8192
MAX_LOG_LINES = 10000
_PUNCT_RE = re.compile(r"[,.!?'\";:()\[\]{}]")
_SPACE_RE = re.compile(r"\s+")
_ACCOUNT_RE = re.compile(r"(?:dla konta|konto|account)\s+([a-zA-Z0-9_\-]+)")
_SHARE_HOST_RE = re.compile(
    r"(?:na maszynie|na hoscie|host|maszyna)\s+([a-zA-Z0-9_\-]+)"
)
_LOGS_HOST_RE = re.compile(r"(?:z hosta|host|z maszyny|maszyny)\s+([a-zA-Z0-9_\-]+)")
_PORTS_RE = re.compile(r"\b(8\d{3}|3000|8888)\b")
_LINES_RE = re.compile(r"(?<!\d)(\d+)\s*(?:linii|wierszy|lines)\b")

__all__ = [
    "MAX_LOG_LINES",
    "MAX_QUERY_CHARS",
    "ApiExecutionPlan",
    "CompiledAction",
    "LLMQueryCompiler",
    "NLIntentMatcher",
]


@dataclass
class CompiledAction:
    endpointId: str
    parameters: dict[str, Any]
    description: str = ""


@dataclass
class ApiExecutionPlan:
    confidence: float
    strategy: str
    actions: list[CompiledAction]
    rawQuery: str = ""
    sessionId: str | None = None


def _validate_query(raw_query: str) -> None:
    if not isinstance(raw_query, str):
        raise TypeError("query must be a string")
    _check_utf8_str(raw_query)
    if len(raw_query) > MAX_QUERY_CHARS:
        raise ValueError(f"query length exceeds {MAX_QUERY_CHARS} characters")


class NLIntentMatcher:
    """Fast-path deterministic rule-based parser matching Polish & English intents to APIs."""

    def __init__(self, registry: ApiRegistry):
        self.registry = registry
        self._endpoints_by_id = {e.id: e for e in registry.endpoints}
        self._intent_phrases: list[tuple[str, ApiEndpoint]] = []
        for ep in registry.endpoints:
            for intent in ep.nlIntents:
                for phrase in intent.phrases:
                    norm_phrase = self.normalize(phrase)
                    if norm_phrase:
                        self._intent_phrases.append((norm_phrase, ep))

    def normalize(self, text: str) -> str:
        """Removes diacritics and normalizes whitespace and punctuation for tolerant matching."""
        lowered = text.lower().strip().translate({0x0142: "l"})
        folded = "".join(
            ch
            for ch in unicodedata.normalize("NFKD", lowered)
            if not unicodedata.combining(ch)
        )
        cleaned = _PUNCT_RE.sub(" ", folded)
        return _SPACE_RE.sub(" ", cleaned).strip()

    def parse(
        self,
        raw_query: str,
        context: dict[str, Any] | None = None,
    ) -> ApiExecutionPlan:
        _validate_query(raw_query)
        ctx = context or {}
        session_id = str(ctx["sessionId"]) if ctx.get("sessionId") else None
        norm = self.normalize(raw_query)
        if not norm:
            return ApiExecutionPlan(
                confidence=0.0,
                strategy="llm",
                rawQuery=raw_query,
                actions=[],
                sessionId=session_id,
            )

        if any(w in norm for w in _INTENT_TRIGGERS.get("premesh.ports.share", ())):
            account = ctx.get("activeAccount", "prototypowanie")
            host = ctx.get("activeHost", "nvidia")
            m_acc = _ACCOUNT_RE.search(norm)
            if m_acc:
                account = m_acc.group(1)
            m_host = _SHARE_HOST_RE.search(norm)
            if m_host:
                host = m_host.group(1)

            ports = [8100, 8096, 8094]
            port_matches = _PORTS_RE.findall(norm)
            if port_matches:
                ports = [int(p) for p in port_matches]

            return ApiExecutionPlan(
                confidence=1.0,
                strategy="deterministic",
                rawQuery=raw_query,
                sessionId=session_id,
                actions=[
                    CompiledAction(
                        endpointId="premesh.ports.share",
                        parameters={"account": account, "host": host, "ports": ports},
                        description=f"Udostępnienie portów {ports} z hosta {host} do kontenera {account}",
                    )
                ],
            )

        if any(w in norm for w in _INTENT_TRIGGERS.get("premesh.logs.fetch", ())):
            host = ctx.get("activeHost", "nvidia")
            lines = 60
            m_lines = _LINES_RE.search(norm)
            if m_lines:
                raw_digits = m_lines.group(1).lstrip("0") or "0"
                lines = (
                    MAX_LOG_LINES
                    if len(raw_digits) > 5
                    else min(MAX_LOG_LINES, max(1, int(raw_digits)))
                )
            m_host = _LOGS_HOST_RE.search(norm)
            if m_host:
                host = m_host.group(1)

            return ApiExecutionPlan(
                confidence=1.0,
                strategy="deterministic",
                rawQuery=raw_query,
                sessionId=session_id,
                actions=[
                    CompiledAction(
                        endpointId="premesh.logs.fetch",
                        parameters={"host": host, "lines": lines},
                        description=f"Pobranie ostatnich {lines} linii logów z hosta {host}",
                    )
                ],
            )

        if any(
            w in norm for w in _INTENT_TRIGGERS.get("prepanel.scenarios.test_hui", ())
        ):
            account = ctx.get("activeAccount", "prototypowanie")
            host = ctx.get("activeHost", "nvidia")
            return ApiExecutionPlan(
                confidence=1.0,
                strategy="deterministic",
                rawQuery=raw_query,
                sessionId=session_id,
                actions=[
                    CompiledAction(
                        endpointId="prepanel.scenarios.test_hui",
                        parameters={"account": account, "host": host},
                        description="Uruchomienie scenariusza Test Manualny HUI w oknie noVNC",
                    )
                ],
            )

        if any(
            w in norm
            for w in _INTENT_TRIGGERS.get("prepanel.scenarios.connect_scenario", ())
        ):
            account = ctx.get("activeAccount", "prototypowanie")
            host = ctx.get("activeHost", "nvidia")
            return ApiExecutionPlan(
                confidence=1.0,
                strategy="deterministic",
                rawQuery=raw_query,
                sessionId=session_id,
                actions=[
                    CompiledAction(
                        endpointId="prepanel.scenarios.connect_scenario",
                        parameters={"account": account, "host": host},
                        description="Uruchomienie scenariusza Connect-Scenario w noVNC",
                    )
                ],
            )

        if any(w in norm for w in _INTENT_TRIGGERS.get("premesh.system.health", ())):
            return ApiExecutionPlan(
                confidence=1.0,
                strategy="deterministic",
                rawQuery=raw_query,
                sessionId=session_id,
                actions=[
                    CompiledAction(
                        endpointId="premesh.system.health",
                        parameters={},
                        description="Sprawdzenie stanu zdrowia usług premesh i prepanel",
                    )
                ],
            )

        if any(w in norm for w in _INTENT_TRIGGERS.get("premesh.accounts.list", ())):
            host = ctx.get("activeHost", "nvidia")
            return ApiExecutionPlan(
                confidence=1.0,
                strategy="deterministic",
                rawQuery=raw_query,
                sessionId=session_id,
                actions=[
                    CompiledAction(
                        endpointId="premesh.accounts.list",
                        parameters={"host": host},
                        description=f"Pobranie listy kont i kontenerów dla hosta {host}",
                    )
                ],
            )

        for phrase_norm, ep in self._intent_phrases:
            if phrase_norm in norm or norm in phrase_norm:
                return ApiExecutionPlan(
                    confidence=0.9,
                    strategy="deterministic",
                    rawQuery=raw_query,
                    sessionId=session_id,
                    actions=[
                        CompiledAction(
                            endpointId=ep.id,
                            parameters={},
                            description=ep.description or ep.title,
                        )
                    ],
                )

        return ApiExecutionPlan(
            confidence=0.0,
            strategy="llm",
            rawQuery=raw_query,
            actions=[],
            sessionId=session_id,
        )


class LLMQueryCompiler:
    """Compiles free-form or composite natural language queries into API execution DAGs."""

    def __init__(
        self,
        registry: ApiRegistry,
        llm_callable: Callable[[str, list[dict[str, Any]]], dict[str, Any]]
        | None = None,
    ):
        self.registry = registry
        self.llm_callable = llm_callable

    def build_prompt_context(self, query: str) -> list[dict[str, Any]]:
        """Filters API catalog to compact candidate tool schemas to preserve token budgets."""
        q_words = set(query.lower().split())
        candidates: list[dict[str, Any]] = []
        for ep in self.registry.endpoints:
            title_low = ep.title.lower()
            desc_low = ep.description.lower()
            tags_set = set(ep.tags)
            score = 0
            if any(w in title_low for w in q_words):
                score += 2
            if any(w in desc_low for w in q_words):
                score += 1
            if q_words & tags_set:
                score += 2
            if score > 0 or len(candidates) < 10:
                candidates.append(
                    {
                        "id": ep.id,
                        "service": ep.service,
                        "title": ep.title,
                        "description": ep.description,
                        "parameters": [asdict(p) for p in ep.parameters],
                    }
                )
        return candidates

    def compile(
        self,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> ApiExecutionPlan:
        _validate_query(query)
        session_id = (
            str(context["sessionId"]) if context and context.get("sessionId") else None
        )
        if self.llm_callable:
            candidates = self.build_prompt_context(query)
            res = self.llm_callable(query, candidates)
            actions = [
                CompiledAction(
                    endpointId=a["endpointId"],
                    parameters=dict(a.get("parameters", {})),
                    description=a.get("description", ""),
                )
                for a in res.get("actions", [])
            ]
            return ApiExecutionPlan(
                confidence=res.get("confidence", 0.85),
                strategy="llm",
                rawQuery=query,
                actions=actions,
                sessionId=session_id,
            )

        params: dict[str, Any] = {"prompt": query}
        if context:
            params["context"] = context
        return ApiExecutionPlan(
            confidence=0.5,
            strategy="llm",
            rawQuery=query,
            sessionId=session_id,
            actions=[
                CompiledAction(
                    endpointId="prepanel.views.chat",
                    parameters=params,
                    description="Przekierowanie do asystenta Chat LLM z zachowaniem kontekstu",
                )
            ],
        )
