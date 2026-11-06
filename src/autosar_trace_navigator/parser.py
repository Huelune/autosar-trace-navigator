"""Extract C syntax without preprocessing, symbol linking, or source writes."""

from collections.abc import Iterable, Iterator
import os
from pathlib import Path

from tree_sitter import Language, Node, Parser
import tree_sitter_c

from .models import (
    Branch, FunctionCall, FunctionDefinition, ParseDiagnostic, ParseResult, SourceRange,
)


def _walk(node: Node) -> Iterator[Node]:
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


def _declaration_name(node: Node | None) -> str | None:
    has_function_declarator = False
    while node is not None:
        if node.type == "function_declarator":
            has_function_declarator = True
        if node.type == "identifier":
            return node.text.decode("utf-8", errors="replace") if has_function_declarator else None
        child = node.child_by_field_name("declarator")
        if child is None and node.type == "parenthesized_declarator" and node.named_children:
            child = node.named_children[0]
        node = child
    return None


def parse_file(
    path: str | os.PathLike[str], *, known_macros: Iterable[str] = (),
) -> ParseResult:
    """Read a file as bytes. I/O errors propagate; syntax errors become diagnostics."""
    source_path = Path(path).resolve(strict=True)
    return parse_source(source_path.read_bytes(), path=source_path, known_macros=known_macros)


def parse_source(
    source: bytes, *, path: str | os.PathLike[str], known_macros: Iterable[str] = (),
) -> ParseResult:
    """Extract syntax from bytes with an explicit (possibly virtual) source path.

    No includes are opened and no preprocessor conditions are evaluated. Local
    macro definitions and caller-supplied macro names are recognized conservatively,
    including definitions after an invocation or inside inactive #if alternatives.
    Direct call names are candidates only, never resolved function identities.
    """
    source_path = Path(path).resolve()
    tree = Parser(Language(tree_sitter_c.language())).parse(source)
    all_nodes = list(_walk(tree.root_node))
    functions: list[FunctionDefinition] = []
    calls: list[FunctionCall] = []
    branches: list[Branch] = []
    diagnostics: list[ParseDiagnostic] = []
    macros = set(known_macros)

    def text(node: Node) -> str:
        return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    def location(node: Node, end: Node | None = None) -> SourceRange:
        last = node if end is None else end
        return SourceRange(source_path, node.start_point.row + 1, node.start_point.column + 1,
                           last.end_point.row + 1, last.end_point.column + 1,
                           node.start_byte, last.end_byte)

    def identity(kind: str, node: Node) -> str:
        return f"{source_path.as_posix()}:{kind}:{node.start_byte}"

    for node in all_nodes:
        if node.type in {"preproc_def", "preproc_function_def"}:
            name = node.child_by_field_name("name")
            if name is not None:
                macros.add(text(name))
        if node.type == "ERROR" or node.is_missing:
            diagnostics.append(ParseDiagnostic(
                "SYNTAX_ERROR", f"Unparsed or missing C syntax: {node.type}", location(node)))

    has_preprocessor = any(node.type.startswith("preproc_") for node in all_nodes)
    if has_preprocessor:
        diagnostics.append(ParseDiagnostic(
            "PREPROCESSOR_NOT_EVALUATED",
            "Includes/macros are not expanded; all conditional alternatives may be present.",
            location(tree.root_node)))
    try:
        source.decode("utf-8")
    except UnicodeDecodeError:
        diagnostics.append(ParseDiagnostic(
            "NON_UTF8_SOURCE", "Invalid UTF-8 is displayed with replacement characters.",
            location(tree.root_node)))

    def uncertainty(node: Node) -> tuple[str, ...]:
        reasons = []
        if has_preprocessor:
            reasons.append("preprocessing_not_performed")
        # A malformed declaration can affect later syntax recovery, too.
        if tree.root_node.has_error:
            reasons.append("file_has_syntax_errors")
        if any(child.type == "identifier" and text(child) in macros for child in _walk(node)):
            reasons.append("unexpanded_macro")
        return tuple(reasons)

    def visit(node: Node, function_id: str | None, parent_id: str | None) -> None:
        if node.type == "function_definition":
            name = _declaration_name(node.child_by_field_name("declarator"))
            body = node.child_by_field_name("body")
            if name is None or body is None:
                diagnostics.append(ParseDiagnostic(
                    "UNRESOLVED_FUNCTION", "Cannot identify function declarator/body.", location(node)))
            else:
                function_id = identity("function", node)
                functions.append(FunctionDefinition(
                    function_id, name, location(node), location(body), uncertainty(node)))
        if node.type == "if_statement":
            visit_chain(node, function_id, parent_id)
            return
        if node.type == "call_expression":
            callee = node.child_by_field_name("function")
            if callee is not None:
                name = text(callee) if callee.type == "identifier" else None
                kind = "macro" if name in macros else ("direct_candidate" if name else "indirect")
                reason = "unexpanded_macro" if kind == "macro" else "unresolved_call_target"
                reasons = tuple(dict.fromkeys((*uncertainty(node), reason)))
                calls.append(FunctionCall(function_id, parent_id, text(node), text(callee), name,
                                          kind, location(node), reasons))
                diagnostics.append(ParseDiagnostic(
                    "MACRO_INVOCATION" if kind == "macro" else "UNRESOLVED_CALL_TARGET",
                    "Macro expansion required." if kind == "macro" else
                    "Syntax candidate only; symbol/function-pointer resolution not performed.",
                    location(node)))
        for child in node.named_children:
            visit(child, function_id, parent_id)

    def visit_chain(node: Node, function_id: str | None, parent_id: str | None) -> None:
        chain_id = identity("branch", node)
        kind = "if"
        while True:
            condition = node.child_by_field_name("condition")
            body = node.child_by_field_name("consequence")
            if condition is None or body is None:
                diagnostics.append(ParseDiagnostic(
                    "INCOMPLETE_BRANCH", "Missing condition or consequence.", location(node)))
                return
            branch_id = identity("branch", node)
            branches.append(Branch(branch_id, function_id, kind, text(condition),
                                   location(node, body), location(body), parent_id, chain_id,
                                   uncertainty(node)))
            visit(condition, function_id, branch_id)
            visit(body, function_id, branch_id)
            alternative = node.child_by_field_name("alternative")
            if alternative is None:
                return
            # else_clause contains comments as named children; ignore them.
            bodies = [child for child in alternative.named_children if child.type != "comment"]
            if not bodies:
                diagnostics.append(ParseDiagnostic(
                    "INCOMPLETE_BRANCH", "Missing else body.", location(alternative)))
                return
            next_body = bodies[0]
            if next_body.type == "if_statement":
                node = next_body
                kind = "else_if"
                continue
            branch_id = identity("branch", alternative)
            branches.append(Branch(branch_id, function_id, "else", None,
                                   location(alternative), location(next_body), parent_id,
                                   chain_id, uncertainty(alternative)))
            visit(next_body, function_id, branch_id)
            return

    visit(tree.root_node, None, None)
    return ParseResult(source_path, tuple(functions), tuple(calls),
                       tuple(sorted(branches, key=lambda branch: branch.location.start_byte)),
                       tuple(sorted(diagnostics, key=lambda item: item.location.start_byte)))
