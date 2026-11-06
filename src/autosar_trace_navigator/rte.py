"""Conservative explicit RTE read/write candidates, never a resolved call graph."""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Literal

from tree_sitter import Language, Node, Parser
import tree_sitter_c

from .models import ParseResult, SourceRange


Direction = Literal["read", "write"]


@dataclass(frozen=True)
class RteDiagnostic:
    code: str
    message: str
    location: SourceRange


@dataclass(frozen=True)
class RteHeaderApi:
    name: str
    direction: Direction
    channel: str
    form: Literal["declaration", "macro"]
    expression: str
    location: SourceRange
    uncertainty: tuple[str, ...]


@dataclass(frozen=True)
class RteHeader:
    path: Path
    apis: tuple[RteHeaderApi, ...]
    diagnostics: tuple[RteDiagnostic, ...]


@dataclass(frozen=True)
class RteAccess:
    id: str
    function_id: str | None
    api_name: str
    direction: Direction
    channel: str
    location: SourceRange
    header_locations: tuple[SourceRange, ...]
    uncertainty: tuple[str, ...]


@dataclass(frozen=True)
class RteDataDependency:
    producer_access_id: str
    consumer_access_id: str
    channel: str
    uncertainty: tuple[str, ...]


@dataclass(frozen=True)
class RteResolution:
    accesses: tuple[RteAccess, ...]
    dependencies: tuple[RteDataDependency, ...]
    diagnostics: tuple[RteDiagnostic, ...]


def _walk(node: Node) -> Iterator[Node]:
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


def _api_key(name: str) -> tuple[Direction, str] | None:
    for prefix, direction in (("Rte_Read_", "read"), ("Rte_Write_", "write")):
        if name.startswith(prefix) and len(name) > len(prefix):
            # Preserve the full suffix: port/data names can themselves contain underscores.
            return direction, name[len(prefix):]
    return None


def parse_rte_header(path: str | os.PathLike[str]) -> RteHeader:
    """Read a synthetic/generated-style header without opening includes or expanding macros."""
    source_path = Path(path).resolve(strict=True)
    return inspect_rte_header(source_path.read_bytes(), path=source_path)


def inspect_rte_header(source: bytes, *, path: str | os.PathLike[str]) -> RteHeader:
    """Extract API declarations/macro text; macros remain uninterpreted evidence."""
    source_path = Path(path).resolve()
    tree = Parser(Language(tree_sitter_c.language())).parse(source)
    apis: list[RteHeaderApi] = []
    diagnostics: list[RteDiagnostic] = []

    def location(node: Node) -> SourceRange:
        return SourceRange(source_path, node.start_point.row + 1, node.start_point.column + 1,
                           node.end_point.row + 1, node.end_point.column + 1,
                           node.start_byte, node.end_byte)

    for node in _walk(tree.root_node):
        if node.type == "ERROR" or node.is_missing:
            diagnostics.append(RteDiagnostic("HEADER_SYNTAX_ERROR", "Unparsed RTE header syntax.", location(node)))
        form = None
        name_node = None
        if node.type in {"preproc_def", "preproc_function_def"}:
            name_node = node.child_by_field_name("name")
            form = "macro"
        elif node.type == "function_declarator":
            name_node = node.child_by_field_name("declarator")
            form = "declaration"
        if name_node is None or name_node.type != "identifier":
            continue
        name = name_node.text.decode("utf-8", errors="replace")
        key = _api_key(name)
        if key is None:
            if name.startswith("Rte_"):
                diagnostics.append(RteDiagnostic(
                    "UNSUPPORTED_RTE_API", f"Not an explicit Read/Write API: {name}", location(node)))
            continue
        reasons = ["header_preprocessing_not_performed"]
        if form == "macro":
            reasons.append("header_macro_not_expanded")
        if tree.root_node.has_error:
            reasons.append("header_has_syntax_errors")
        apis.append(RteHeaderApi(name, *key, form,
                                 source[node.start_byte:node.end_byte].decode("utf-8", errors="replace"),
                                 location(node), tuple(reasons)))
    try:
        source.decode("utf-8")
    except UnicodeDecodeError:
        diagnostics.append(RteDiagnostic("NON_UTF8_HEADER", "Invalid UTF-8 displayed with replacement characters.",
                                         location(tree.root_node)))
    return RteHeader(source_path, tuple(apis), tuple(diagnostics))


def resolve_rte(results: Iterable[ParseResult], *, headers: Iterable[RteHeader] = ()) -> RteResolution:
    """Match full name suffixes only; every dependency remains an uncertain candidate.

    No files are read here. Header scope, ARXML wiring, macro expansion, reachability
    and runnable scheduling are not resolved. Multiple producers remain separate.
    Duplicate input paths are rejected rather than creating duplicate relations.
    """
    results = tuple(results)
    headers = tuple(sorted(headers, key=lambda h: h.path.as_posix()))
    if len({r.path for r in results}) != len(results) or len({h.path for h in headers}) != len(headers):
        raise ValueError("Duplicate source/header path in RTE input")
    declarations: dict[str, list[RteHeaderApi]] = {}
    diagnostics = [d for h in headers for d in h.diagnostics]
    for header in headers:
        for api in header.apis:
            declarations.setdefault(api.name, []).append(api)
    accesses: list[RteAccess] = []
    for result in sorted(results, key=lambda r: r.path.as_posix()):
        for call in sorted(result.calls, key=lambda c: c.location.start_byte):
            name = call.callee_name
            key = _api_key(name) if name is not None else None
            if key is None:
                if ((name is not None and name.startswith("Rte_"))
                        or (name is None and "Rte_" in call.callee_expression)):
                    diagnostics.append(RteDiagnostic("UNSUPPORTED_RTE_API",
                        f"Unsupported or indirect RTE expression: {call.callee_expression}", call.location))
                continue
            matches = declarations.get(name, [])
            reasons = [*call.uncertainty, "name_based_access", "header_scope_not_resolved"]
            reasons.extend(reason for api in matches for reason in api.uncertainty)
            if not matches:
                reasons.append("missing_header_declaration")
                diagnostics.append(RteDiagnostic("MISSING_HEADER_API", f"No supplied header declares {name}", call.location))
            elif len(matches) > 1:
                reasons.append("multiple_header_candidates")
                diagnostics.append(RteDiagnostic("AMBIGUOUS_HEADER_API", f"Multiple declarations for {name}", call.location))
            if call.caller_id is None:
                reasons.append("unknown_access_owner")
                diagnostics.append(RteDiagnostic("UNKNOWN_ACCESS_OWNER", "RTE call has no identified function owner.",
                                                 call.location))
            accesses.append(RteAccess(f"{call.location.path.as_posix()}:rte:{call.location.start_byte}",
                                      call.caller_id, name, *key, call.location,
                                      tuple(api.location for api in matches), tuple(dict.fromkeys(reasons))))

    writes: dict[str, list[RteAccess]] = {}
    for access in accesses:
        if access.direction == "write":
            writes.setdefault(access.channel, []).append(access)
    dependencies = []
    for read in accesses:
        if read.direction != "read":
            continue
        producers = writes.get(read.channel, [])
        if not producers:
            diagnostics.append(RteDiagnostic("NO_PRODUCER_CANDIDATE",
                f"No supplied Write access for {read.channel}", read.location))
        if len(producers) > 1:
            diagnostics.append(RteDiagnostic("MULTIPLE_PRODUCER_CANDIDATES",
                f"{len(producers)} Write access sites for {read.channel}", read.location))
        for write in producers:
            reasons = (*write.uncertainty, *read.uncertainty, "name_only_connection",
                       "arxml_not_resolved", "execution_order_not_resolved")
            if len(producers) > 1:
                reasons += ("multiple_producer_candidates",)
            dependencies.append(RteDataDependency(write.id, read.id, read.channel,
                                                  tuple(dict.fromkeys(reasons))))
    return RteResolution(tuple(accesses), tuple(dependencies), tuple(diagnostics))
