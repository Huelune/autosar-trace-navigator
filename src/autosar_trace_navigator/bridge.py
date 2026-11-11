"""One JSON request on stdin, one JSON response on stdout; no Tkinter, SQLite or network.

Run as ``python -I -m autosar_trace_navigator.bridge``. The response carries error
codes only: exception text may hold paths or source values and is never written.
"""

from pathlib import Path
import json
import sys

from .models import FunctionDefinition, SourceRange, ValueProbe
from .workbench import AnalysisLimitError, ProjectSnapshot, analyze_project, function_candidates

MAX_REQUEST_BYTES = 1024 * 1024
MAX_CANDIDATES = 200
MAX_TEXT_CHARS = 20000
MAX_NOTE_CHARS = 200


class BridgeError(Exception):
    """A handled failure; args[0] is a stable code, not a message."""


def _location(project: ProjectSnapshot, sources: dict[Path, bytes], span: SourceRange) -> dict:
    """Zero-based lines and UTF-16 columns for the editor.

    Columns and text are null when the bytes are not valid UTF-8: the editor may
    decode that file differently, so the caller must not jump to a guessed column.
    """
    data = sources[span.path]
    result = {"path": span.path.relative_to(project.root).as_posix(),
              "startLine": span.start_line - 1, "endLine": span.end_line - 1,
              "startCharacter": None, "endCharacter": None, "text": None}
    try:
        columns = [len(data[offset - column + 1:offset].decode("utf-8").encode("utf-16-le")) // 2
                   for offset, column in ((span.start_byte, span.start_column), (span.end_byte, span.end_column))]
        text = data[span.start_byte:span.end_byte].decode("utf-8")
    except UnicodeDecodeError:
        return result
    if len(text) <= MAX_TEXT_CHARS:
        result.update(startCharacter=columns[0], endCharacter=columns[1], text=text)
    return result


def _signature(sources: dict[Path, bytes], function: FunctionDefinition) -> SourceRange:
    """Declaration up to the body: a whole function is too large to keep as one step."""
    whole, body = function.location, function.body_location
    head = sources[whole.path][whole.start_byte:body.start_byte].rstrip()
    last = head.rfind(b"\n")
    return SourceRange(whole.path, whole.start_line, whole.start_column, whole.start_line + head.count(b"\n"),
                       len(head) - last if last >= 0 else whole.start_column + len(head),
                       whole.start_byte, whole.start_byte + len(head))


def _cursor(data: bytes, path: Path, line: int, character: int) -> SourceRange | None:
    """Zero-width byte position of an editor line and UTF-16 column; None if it cannot be trusted."""
    lines = data.split(b"\n")
    if line >= len(lines):
        return None
    try:
        units = lines[line].decode("utf-8").encode("utf-16-le")
        if character * 2 > len(units):
            return None
        column = len(units[:character * 2].decode("utf-16-le").encode("utf-8"))
    except UnicodeError:  # not UTF-8, or the column splits a surrogate pair
        return None
    offset = sum(len(item) + 1 for item in lines[:line]) + column
    return SourceRange(path, line + 1, column + 1, line + 1, column + 1, offset, offset)


def _notes(project: ProjectSnapshot, reasons: tuple[str, ...]) -> list[str]:
    """Engine reasons for the editor; an absolute declaration path becomes workspace-relative."""
    result = []
    for reason in reasons:
        if reason.startswith("declaration: "):
            where, _, line = reason[len("declaration: "):].rpartition(":")
            try:
                reason = f"declaration: {Path(where).relative_to(project.root).as_posix()}:{line}"
            except ValueError:
                reason = "declaration: outside_analysis_root"
        result.append(reason[:MAX_NOTE_CHARS])
    return result


def _site_candidates(project: ProjectSnapshot, sources: dict[Path, bytes],
                     site: SourceRange) -> tuple[str | None, list[str], list[dict]]:
    """Value sources of the access under the cursor, then structural conditions to reach it."""
    resolver = project.value_resolver
    variable, notes, candidates = None, [], []

    def entry(relation: str, label: str, owner: str, reasons: tuple[str, ...], evidence: SourceRange,
              goal: SourceRange, truth: bool | None = None) -> dict:
        return {"relation": relation, "label": label, "functionName": project.functions_by_id[owner].name,
                "uncertainty": _notes(project, reasons), "requiredTruth": truth,
                "evidence": _location(project, sources, evidence), "target": _location(project, sources, goal)}

    access = resolver.access_at(site)
    if access is not None and not access.supported:
        notes.append("access_path_not_supported")
    elif access is not None:
        variable = access.expression
        owner = next(function for function in project.functions if function.location.path == site.path
                     and function.location.start_byte <= site.start_byte < function.location.end_byte)
        try:
            found = resolver.sources(ValueProbe(owner.id, access.expression, access.location))
        except ValueError:
            found = ()
            notes.append("value_sources_not_available")
        for source in found:
            goal = source.location
            if source.next_probe is not None:
                goal = (_signature(sources, project.functions_by_id[source.next_probe.function_id])
                        if source.next_probe.kind == "return" else source.next_probe.location)
            candidates.append(entry("value", f"{source.kind}: {source.expression}", source.function_id,
                                    source.uncertainty, source.location, goal))
    for requirement in resolver.conditions(site):
        candidates.append(entry("execution_condition", requirement.expression, requirement.function_id,
                                requirement.uncertainty, requirement.location, requirement.location,
                                requirement.required_truth))
    return variable, notes, candidates


def related(request: object) -> dict:
    """Candidates for the function containing a line, plus cursor-specific ones when a column is given.

    Order: value sources of the variable under the cursor, structural execution
    conditions of the cursor, then the function's call and RTE supplier candidates.
    """
    if not isinstance(request, dict):
        raise BridgeError("invalid_request")
    root, file, line, includes = (request.get(key) for key in ("root", "file", "line", "includePaths"))
    character = request.get("character")
    if (not isinstance(root, str) or not isinstance(file, str) or type(line) is not int or line < 0
            or not (character is None or (type(character) is int and character >= 0))
            or not isinstance(includes, list) or not all(isinstance(item, str) for item in includes)
            or not Path(root).is_absolute()):
        raise BridgeError("invalid_request")
    try:
        project = analyze_project(root, include_paths=includes)
        target = (project.root / file).resolve()
    except AnalysisLimitError:
        raise BridgeError("analysis_limit") from None
    except (OSError, ValueError):
        raise BridgeError("scope_not_readable") from None
    sources = dict(project.sources)
    if target not in sources:
        raise BridgeError("file_not_in_scope")
    inside = [function for function in project.functions if function.location.path == target
              and function.location.start_line <= line + 1 <= function.location.end_line]
    if not inside:
        return {"ok": True, "function": None, "variable": None, "notes": [], "candidates": [], "truncated": False}
    function = min(inside, key=lambda item: item.location.end_byte - item.location.start_byte)
    variable, notes, candidates = None, [], []
    if character is not None:
        site = _cursor(sources[target], target, line, character)
        if site is None:
            notes.append("cursor_position_not_resolved")
        else:
            variable, notes, candidates = _site_candidates(project, sources, site)
    for candidate in function_candidates(project, function):
        goal = None
        if candidate.relation == "rte_data":
            goal = candidate.evidence
        elif candidate.function is not None:
            goal = _signature(sources, candidate.function)
        candidates.append({
            "relation": candidate.relation, "label": candidate.label,
            "functionName": candidate.function.name if candidate.function else None,
            "uncertainty": _notes(project, candidate.uncertainty), "requiredTruth": None,
            "evidence": _location(project, sources, candidate.evidence),
            "target": _location(project, sources, goal) if goal else None})
    return {"ok": True, "function": {"name": function.name}, "variable": variable, "notes": notes,
            "candidates": candidates[:MAX_CANDIDATES], "truncated": len(candidates) > MAX_CANDIDATES}


def main() -> int:
    """Exit 0 for a result or a handled error code, 1 for an unexpected failure."""
    status = 0
    try:
        raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
        if len(raw) > MAX_REQUEST_BYTES:
            raise BridgeError("invalid_request")
        try:
            request = json.loads(raw)
        except ValueError:
            raise BridgeError("invalid_request") from None
        response = related(request)
    except BridgeError as error:
        response = {"ok": False, "error": error.args[0]}
    except Exception:  # noqa: BLE001 - the traceback could expose paths or source text
        response, status = {"ok": False, "error": "internal"}, 1
    sys.stdout.write(json.dumps(response))  # ASCII-only output, independent of console encoding
    return status


if __name__ == "__main__":
    raise SystemExit(main())
