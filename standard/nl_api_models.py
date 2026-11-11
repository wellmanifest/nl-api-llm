"""Domain models, protocols, and bounded regular-file/JSON I/O for wellmanifest/nl-api-llm."""

from __future__ import annotations

import errno
import json
import math
import os
import stat
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_JSON_DEPTH = 64

__all__ = [
    "MAX_FILE_BYTES",
    "MAX_JSON_DEPTH",
    "_INTENT_TRIGGERS",
    "ApiActionResult",
    "ApiEndpoint",
    "ApiParameter",
    "ApiRegistry",
    "ApiService",
    "CliSpec",
    "InteractionType",
    "KvmSpec",
    "MenuBinding",
    "NLIntent",
    "ProtocolType",
    "RestSpec",
    "_check_no_symlink_ancestors",
    "_check_utf8_str",
    "_load_intent_triggers",
    "_out",
    "read_strict_json",
    "write_atomic_text",
]


def _out(msg: str, stream: Any = None) -> None:
    target = sys.stdout if stream is None else stream
    target.write(f"{msg}\n")


def _check_utf8_str(value: str) -> None:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("lone UTF-16 surrogate in string is forbidden") from exc


def _check_no_symlink_ancestors(
    path: str | Path, *, include_self: bool = False
) -> Path:
    raw_path = os.fspath(path)
    path_obj = Path(raw_path)
    raw_parts = path_obj.parts if include_self else path_obj.parts[:-1]
    if path_obj.is_absolute():
        cur = Path(path_obj.anchor)
        walk_parts = raw_parts[1:]
    else:
        cwd = Path.cwd()
        if len(cwd.parts) > 2 and cwd.is_symlink():
            raise ValueError(f"symlink ancestor is forbidden: {cwd}")
        for anc in cwd.parents:
            if len(anc.parts) > 2 and anc.is_symlink():
                raise ValueError(f"symlink ancestor is forbidden: {anc}")
        cur = cwd
        walk_parts = raw_parts
    for part in walk_parts:
        if part in ("", "."):
            continue
        cur = cur / part
        if part != ".." and len(cur.parts) > 2 and cur.is_symlink():
            raise ValueError(f"symlink ancestor is forbidden: {cur}")
    abs_path = Path(os.path.abspath(raw_path))
    if include_self and abs_path.is_symlink():
        raise ValueError(f"symlink path is forbidden: {path_obj}")
    if any(anc.is_symlink() for anc in abs_path.parents if len(anc.parts) > 2):
        raise ValueError(f"symlink ancestor is forbidden: {path_obj}")
    return abs_path


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, val in pairs:
        if key in obj:
            raise ValueError(f"duplicate JSON key: {key!r}")
        obj[key] = val
    return obj


def _reject_constant(token: str) -> Any:
    raise ValueError(f"non-finite JSON constant {token!r} is forbidden")


def _parse_finite_float(token: str) -> float:
    parsed = float(token)
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite JSON number {token!r} is forbidden")
    return parsed


def _parse_finite_int(token: str) -> int:
    digits = token.removeprefix("-")
    if len(digits) > 309:
        raise ValueError("JSON integer magnitude exceeds finite range")
    parsed = int(token)
    try:
        ok = math.isfinite(float(parsed))
    except OverflowError:
        ok = False
    if not ok:
        raise ValueError("JSON integer magnitude exceeds finite range")
    return parsed


def read_strict_json(path: str | Path, *, max_bytes: int = MAX_FILE_BYTES) -> Any:
    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")
    raw_path = os.fspath(path)
    _check_no_symlink_ancestors(raw_path, include_self=False)
    lst = os.lstat(raw_path)
    if stat.S_ISLNK(lst.st_mode):
        raise ValueError(f"symlink JSON input is forbidden: {raw_path}")
    if not stat.S_ISREG(lst.st_mode):
        raise ValueError(f"JSON input must be a regular file: {raw_path}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(raw_path, flags)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise ValueError(f"symlink JSON input is forbidden: {raw_path}") from exc
        raise
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise ValueError(f"JSON input must be a regular file: {raw_path}")
        if (st.st_dev, st.st_ino) != (lst.st_dev, lst.st_ino):
            raise ValueError(f"JSON input inode changed during open: {raw_path}")
        if st.st_size > max_bytes:
            raise ValueError(f"JSON input exceeds {max_bytes} bytes: {raw_path}")
        chunks = bytearray()
        while True:
            chunk = os.read(fd, min(65536, max_bytes + 1 - len(chunks)))
            if not chunk:
                break
            chunks.extend(chunk)
            if len(chunks) > max_bytes:
                raise ValueError(f"JSON input exceeds {max_bytes} bytes: {raw_path}")
    finally:
        os.close(fd)
    text = bytes(chunks).decode("utf-8")
    _check_utf8_str(text)
    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_unique_pairs,
            parse_constant=_reject_constant,
            parse_float=_parse_finite_float,
            parse_int=_parse_finite_int,
        )
    except RecursionError as exc:
        raise ValueError(f"JSON nesting depth exceeds {MAX_JSON_DEPTH}") from exc
    stack: list[tuple[Any, int]] = [(parsed, 0)]
    while stack:
        cur, depth = stack.pop()
        if depth > MAX_JSON_DEPTH:
            raise ValueError(f"JSON nesting depth exceeds {MAX_JSON_DEPTH}")
        if isinstance(cur, dict):
            for k, v in cur.items():
                if not isinstance(k, str):
                    raise TypeError("JSON object keys must be strings")
                _check_utf8_str(k)
                stack.append((v, depth + 1))
        elif isinstance(cur, list):
            for v in cur:
                stack.append((v, depth + 1))
        elif isinstance(cur, str):
            _check_utf8_str(cur)
    return parsed


def write_atomic_text(path: str | Path, content: str) -> None:
    if not isinstance(content, str):
        raise TypeError("content must be a string")
    _check_utf8_str(content)
    raw_path = os.fspath(path)
    abs_dest = _check_no_symlink_ancestors(raw_path, include_self=True)
    if abs_dest.exists() and not abs_dest.is_file():
        raise ValueError(f"output destination is not a regular file: {raw_path}")
    parent = abs_dest.parent
    if not parent.is_dir():
        raise ValueError(f"output parent directory does not exist: {parent}")
    fd, tmp_name = tempfile.mkstemp(prefix=".nl-api-", dir=str(parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, abs_dest)
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def _load_intent_triggers() -> dict[str, list[str]]:
    profile_path = Path(__file__).resolve().with_name("semantic-profile.json")
    data = read_strict_json(profile_path)
    return {str(k): list(v) for k, v in (data.get("intent_triggers") or {}).items()}


_INTENT_TRIGGERS: dict[str, list[str]] = _load_intent_triggers()


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
    type: str
    location: str
    required: bool = True
    default: Any = None
    description: str = ""
    enum: list[Any] | None = None


@dataclass
class RestSpec:
    method: str
    path: str
    contentType: str = "application/json"


@dataclass
class CliSpec:
    commandTemplate: str
    binary: str | None = None


@dataclass
class KvmSpec:
    action: str


@dataclass
class MenuBinding:
    category: str
    group: str
    label: str
    icon: str = "circle"
    order: int = 100
    viewRoute: str | None = None
    interactionType: str = InteractionType.TRIGGER.value
    badge: str | None = None


@dataclass
class NLIntent:
    lang: str
    phrases: list[str]
    patterns: list[str] = field(default_factory=list)


@dataclass
class ApiEndpoint:
    id: str
    service: str
    protocol: str
    title: str
    description: str = ""
    readOnly: bool = True
    roles: list[str] = field(
        default_factory=lambda: ["admin", "dev", "operator", "viewer"]
    )
    tags: list[str] = field(default_factory=list)
    rest: RestSpec | None = None
    cli: CliSpec | None = None
    kvm: KvmSpec | None = None
    parameters: list[ApiParameter] = field(default_factory=list)
    nlIntents: list[NLIntent] = field(default_factory=list)
    menuBinding: MenuBinding | None = None


@dataclass
class ApiService:
    id: str
    name: str
    protocol: str
    description: str = ""
    baseUrl: str | None = None
    defaultPort: int | None = None


@dataclass
class ApiRegistry:
    schema: str
    version: str
    services: list[ApiService]
    endpoints: list[ApiEndpoint]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApiRegistry:
        if not isinstance(data, dict):
            raise TypeError("ApiRegistry data must be a dict")
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
        endpoints: list[ApiEndpoint] = []
        for e in data.get("endpoints", []):
            rest_spec = (
                RestSpec(
                    method=e["rest"]["method"],
                    path=e["rest"]["path"],
                    contentType=e["rest"].get("contentType", "application/json"),
                )
                if e.get("rest")
                else None
            )
            cli_spec = (
                CliSpec(
                    commandTemplate=e["cli"]["commandTemplate"],
                    binary=e["cli"].get("binary"),
                )
                if e.get("cli")
                else None
            )
            kvm_spec = KvmSpec(action=e["kvm"]["action"]) if e.get("kvm") else None
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
            raw_mb = e.get("menuBinding") or e.get("menu_binding")
            menu_binding = (
                MenuBinding(
                    category=raw_mb["category"],
                    group=raw_mb.get("group", "General"),
                    label=raw_mb["label"],
                    icon=raw_mb.get("icon", "circle"),
                    order=raw_mb.get("order", 100),
                    viewRoute=raw_mb.get("viewRoute") or raw_mb.get("view_route"),
                    interactionType=raw_mb.get("interactionType")
                    or raw_mb.get("interaction_type", InteractionType.TRIGGER.value),
                    badge=raw_mb.get("badge"),
                )
                if raw_mb
                else None
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

    def to_dict(self) -> dict[str, Any]:
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


@dataclass
class ApiActionResult:
    success: bool
    endpointId: str
    protocol: str
    timestamp: str
    latencyMs: float
    statusCode: int = 200
    data: Any = None
    error: dict[str, Any] | None = None
    audit: dict[str, Any] | None = None
    status: str | None = None
    errors: list[dict[str, Any]] | None = None
    meta: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.status is None:
            self.status = "success" if self.success else "error"
        if self.errors is None and self.error:
            self.errors = [self.error]
        elif self.errors is None:
            self.errors = []
        if self.meta is None:
            self.meta = {
                "protocol": self.protocol,
                "latencyMs": self.latencyMs,
                "endpointId": self.endpointId,
            }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
