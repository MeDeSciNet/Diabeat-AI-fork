#!/usr/bin/env python3
"""Generate Python (Pydantic v2) and TypeScript types from the JSON Schemas.

The schemas under ``schemas/`` are the single source of truth: no type may be
hand-written in either language. Run ``make schemas`` after editing a schema and
commit the result; CI re-runs this and fails if the tree drifts.

Why not datamodel-code-generator / json-schema-to-typescript (named in the PRD)?
Both would put a network-installed toolchain on the critical path of every
build, and the TS one drags in a full npm dependency tree for four hundred
lines of output. This emitter handles the schema subset the project actually
uses (``$defs``, cross-file ``$ref``, enums, nullable unions, arrays) with no
dependencies, so ``make schemas`` works offline. Swapping it out later only
changes this file.
"""

from __future__ import annotations

import json
import keyword
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SCHEMA_DIR = ROOT / "schemas"
OUT_PY = ROOT / "generated" / "python" / "somno_schemas" / "somno_types.py"
OUT_TS = ROOT / "generated" / "ts" / "somno-types.ts"

# Emission order matters: a definition must appear before it is referenced.
FILE_ORDER = [
    "common.json",
    "signal_chunk.json",
    "psg_annotations.json",
    "swallow_event.json",
    "session.json",
    "nightly_risk.json",
    "alert.json",
    "mattress.json",
    "eval_report.json",
]

PY_PRIMITIVES = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "null": "None",
    "object": "dict[str, Any]",
    "array": "list[Any]",
}
TS_PRIMITIVES = {
    "string": "string",
    "integer": "number",
    "number": "number",
    "boolean": "boolean",
    "null": "null",
    "object": "Record<string, unknown>",
    "array": "unknown[]",
}


class Emitter:
    def __init__(self) -> None:
        self.schemas: dict[str, Any] = {}
        self.py_blocks: list[str] = []
        self.ts_blocks: list[str] = []
        self.emitted: set[str] = set()
        # Definitions discovered while walking a schema (inline titled objects).
        self._pending: list[tuple[str, dict[str, Any], str]] = []

    # ---------------------------------------------------------------- loading
    def load(self) -> None:
        for name in FILE_ORDER:
            self.schemas[name] = json.loads((SCHEMA_DIR / name).read_text())
        extra = sorted(p.name for p in SCHEMA_DIR.glob("*.json") if p.name not in self.schemas)
        if extra:
            raise SystemExit(f"schemas not listed in FILE_ORDER: {extra}")

    def resolve(self, ref: str, current_file: str) -> tuple[str, dict[str, Any], str]:
        """Return (type_name, schema_node, defining_file) for a $ref."""
        file_part, _, pointer = ref.partition("#")
        target_file = file_part or current_file
        node: Any = self.schemas[target_file]
        for part in pointer.strip("/").split("/"):
            if part:
                node = node[part]
        name = node.get("title") or pointer.rsplit("/", 1)[-1]
        return name, node, target_file

    # ------------------------------------------------------------ type naming
    def type_of(self, node: dict[str, Any], file: str, hint: str) -> tuple[str, str]:
        """Return (python_type, ts_type) for a schema node."""
        if "$ref" in node:
            name, target, target_file = self.resolve(node["$ref"], file)
            if not _is_named(target):
                # A $def that is just a constrained primitive (Uuid, say) has no
                # type of its own worth emitting - inline it at the use site.
                return self.type_of(target, target_file, hint)
            self.queue(name, target, target_file)
            return name, name

        if "oneOf" in node or "anyOf" in node:
            options = node.get("oneOf") or node["anyOf"]
            py, ts = zip(*(self.type_of(o, file, hint) for o in options))
            py_set = _dedupe(py)
            ts_set = _dedupe(ts)
            return " | ".join(py_set), " | ".join(ts_set)

        if "enum" in node:
            name = node.get("title")
            if name:
                self.queue(name, node, file)
                return name, name
            literals = ", ".join(json.dumps(v) for v in node["enum"])
            return f"Literal[{literals}]", " | ".join(json.dumps(v) for v in node["enum"])

        t = node.get("type")
        if isinstance(t, list):
            py = _dedupe([PY_PRIMITIVES[x] for x in t])
            ts = _dedupe([TS_PRIMITIVES[x] for x in t])
            return " | ".join(py), " | ".join(ts)

        if t == "array":
            items = node.get("items")
            if items is None:
                return "list[Any]", "unknown[]"
            py, ts = self.type_of(items, file, hint + "Item")
            return f"list[{py}]", f"({ts})[]"

        if t == "object":
            if "properties" in node:
                name = node.get("title") or hint
                self.queue(name, node, file)
                return name, name
            extra = node.get("additionalProperties")
            if isinstance(extra, dict):
                py, ts = self.type_of(extra, file, hint + "Value")
                return f"dict[str, {py}]", f"Record<string, {ts}>"
            return "dict[str, Any]", "Record<string, unknown>"

        if t is None:
            return "Any", "unknown"
        return PY_PRIMITIVES[t], TS_PRIMITIVES[t]

    def queue(self, name: str, node: dict[str, Any], file: str) -> None:
        if name in self.emitted:
            return
        if any(n == name for n, _, _ in self._pending):
            return
        self._pending.append((name, node, file))

    # --------------------------------------------------------------- emitting
    def run(self) -> None:
        self.load()
        for file in FILE_ORDER:
            schema = self.schemas[file]
            for name, node in _top_level_defs(schema):
                if _is_named(node):
                    self.queue(name, node, file)
            while self._pending:
                name, node, owner = self._pending.pop(0)
                self.emit(name, node, owner)

    def emit(self, name: str, node: dict[str, Any], file: str) -> None:
        if name in self.emitted:
            return
        self.emitted.add(name)

        if "enum" in node:
            self.emit_enum(name, node)
            return
        if node.get("type") != "object" or "properties" not in node:
            return

        # Resolve children first so nested definitions are emitted before use.
        fields: list[tuple[str, str, str, bool, str | None]] = []
        required = set(node.get("required", []))
        nested_before = list(self._pending)
        self._pending = []
        for prop, sub in node["properties"].items():
            py, ts = self.type_of(sub, file, name + _pascal(prop))
            fields.append((prop, py, ts, prop in required, sub.get("description")))
        nested = self._pending
        self._pending = nested_before
        for n_name, n_node, n_file in nested:
            self.emit(n_name, n_node, n_file)

        doc = node.get("description")
        py_lines = [f"class {name}(BaseModel):"]
        if doc:
            py_lines.append(f'    """{doc}"""')
            py_lines.append("")
        if not node.get("additionalProperties", True):
            py_lines.append('    model_config = ConfigDict(extra="forbid")')
            py_lines.append("")
        ts_lines = []
        if doc:
            ts_lines.append(f"/** {doc} */")
        ts_lines.append(f"export interface {name} {{")

        for prop, py, ts, req, desc in fields:
            alias = ""
            attr = prop
            if keyword.iskeyword(prop) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", prop):
                attr = re.sub(r"\W", "_", prop) + "_"
                alias = f', alias="{prop}"'
            if req:
                default = f"Field(...{alias})" if alias else None
            else:
                py = f"{py} | None" if "None" not in py.split(" | ") else py
                default = f"Field(default=None{alias})" if alias else "None"
            suffix = f" = {default}" if default else ""
            if desc:
                py_lines.append(f"    # {desc}")
            py_lines.append(f"    {attr}: {py}{suffix}")
            if desc:
                ts_lines.append(f"  /** {desc} */")
            ts_lines.append(f"  {prop}{'' if req else '?'}: {ts};")

        ts_lines.append("}")
        self.py_blocks.append("\n".join(py_lines))
        self.ts_blocks.append("\n".join(ts_lines))

    def emit_enum(self, name: str, node: dict[str, Any]) -> None:
        values = node["enum"]
        doc = node.get("description")
        py = [f"class {name}(str, Enum):"]
        if doc:
            py.append(f'    """{doc}"""')
            py.append("")
        for v in values:
            py.append(f"    {_const(v)} = {json.dumps(v)}")
        ts = []
        if doc:
            ts.append(f"/** {doc} */")
        ts.append(f"export type {name} = {' | '.join(json.dumps(v) for v in values)};")
        ts.append(
            f"export const {name}Values = [{', '.join(json.dumps(v) for v in values)}] as const;"
        )
        self.py_blocks.append("\n".join(py))
        self.ts_blocks.append("\n".join(ts))

    def write(self) -> None:
        header = (
            "// GENERATED FILE - do not edit.\n"
            "// Source: packages/shared-schemas/schemas/*.json\n"
            "// Regenerate with `make schemas`.\n"
        )
        OUT_PY.parent.mkdir(parents=True, exist_ok=True)
        OUT_TS.parent.mkdir(parents=True, exist_ok=True)
        OUT_PY.write_text(
            header.replace("//", "#")
            + "\nfrom __future__ import annotations\n\n"
            "from enum import Enum\n"
            "from typing import Any, Literal\n\n"
            "from pydantic import BaseModel, ConfigDict, Field\n\n\n"
            + "\n\n\n".join(self.py_blocks)
            + "\n"
        )
        OUT_TS.write_text(header + "\n" + "\n\n".join(self.ts_blocks) + "\n")
        (OUT_PY.parent / "__init__.py").write_text(
            "from .somno_types import *  # noqa: F401,F403\n"
        )


def _is_named(node: dict[str, Any]) -> bool:
    """True when a node deserves a type of its own rather than being inlined."""
    return "enum" in node or (node.get("type") == "object" and "properties" in node)


def _top_level_defs(schema: dict[str, Any]):
    if schema.get("type") == "object" and "properties" in schema:
        yield schema.get("title") or schema["$id"].rsplit("/", 1)[-1], schema
    for name, node in schema.get("$defs", {}).items():
        yield node.get("title", name), node


def _dedupe(items) -> list[str]:
    seen: list[str] = []
    for i in items:
        for part in i.split(" | "):
            if part not in seen:
                seen.append(part)
    # `None` sorts last so the Python union reads `X | None`.
    seen.sort(key=lambda x: x in ("None", "null"))
    return seen


def _pascal(s: str) -> str:
    return "".join(p.capitalize() for p in re.split(r"[_\W]+", s) if p)


def _const(value: str) -> str:
    name = re.sub(r"\W", "_", str(value)).upper()
    return f"V_{name}" if not name[0].isalpha() and name[0] != "_" else name


if __name__ == "__main__":
    e = Emitter()
    e.run()
    e.write()
    print(f"wrote {OUT_PY.relative_to(ROOT.parent.parent)}")
    print(f"wrote {OUT_TS.relative_to(ROOT.parent.parent)}")
