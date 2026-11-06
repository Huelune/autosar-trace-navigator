"""On-demand, conservative value-source candidates over analyzed source bytes."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import TYPE_CHECKING
from collections.abc import Iterator

from tree_sitter import Language, Node, Parser
import tree_sitter_c

from .models import SourceRange, ValueProbe

if TYPE_CHECKING:
    from .workbench import ProjectSnapshot


@dataclass(frozen=True)
class ValueSource:
    function_id: str
    kind: str
    expression: str
    location: SourceRange
    next_probe: ValueProbe | None
    uncertainty: tuple[str, ...]


@dataclass(frozen=True)
class ExecutionRequirement:
    function_id: str
    expression: str
    required_truth: bool
    location: SourceRange
    variables: tuple[ValueProbe, ...]
    uncertainty: tuple[str, ...]


def _walk(node: Node) -> Iterator[Node]:
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.named_children))


def _name(node: Node | None) -> str | None:
    while node is not None:
        if node.type == "identifier":
            return node.text.decode("utf-8", errors="replace")
        node = node.child_by_field_name("declarator")
    return None


class ValueResolver:
    """Candidate source sites only: no alias analysis, reaching definitions or solver."""

    def __init__(self, project: "ProjectSnapshot") -> None:
        self.project = project
        self._trees = {}
        self._bytes = dict(project.sources)

    def _root(self, path: Path) -> Node:
        if path not in self._trees:
            self._trees[path] = Parser(Language(tree_sitter_c.language())).parse(self._bytes[path])
        return self._trees[path].root_node

    def _function(self, function_id: str) -> Node:
        definition = self.project.functions_by_id[function_id]
        return next(node for node in _walk(self._root(definition.location.path))
                    if node.type == "function_definition" and node.start_byte == definition.location.start_byte)

    def _location(self, path: Path, node: Node) -> SourceRange:
        return SourceRange(path, node.start_point.row + 1, node.start_point.column + 1,
                           node.end_point.row + 1, node.end_point.column + 1, node.start_byte, node.end_byte)

    def conditions(self, site: SourceRange) -> tuple[ExecutionRequirement, ...]:
        """Structural if/else prerequisites, including false preceding arms of a chain."""
        owner = next((fn for fn in self.project.functions if fn.location.path == site.path
                      and fn.body_location.start_byte <= site.start_byte < fn.body_location.end_byte
                      and site.end_byte <= fn.body_location.end_byte), None)
        if owner is None:
            return ()
        branches = [branch for result in self.project.results for branch in result.branches
                    if branch.function_id == owner.id]
        containing = [branch for branch in branches
                      if branch.body_location.start_byte <= site.start_byte < branch.body_location.end_byte
                      and site.end_byte <= branch.body_location.end_byte]
        requirements = []
        seen = set()
        nodes = {node.start_byte: node for node in _walk(self._function(owner.id))
                 if node.type == "if_statement"}
        for selected in containing:
            chain = [branch for branch in branches if branch.chain_id == selected.chain_id
                     and branch.location.start_byte <= selected.location.start_byte and branch.condition]
            for branch in chain:
                truth = branch.id == selected.id
                if (branch.id, truth) in seen:
                    continue
                seen.add((branch.id, truth))
                syntax = nodes.get(branch.location.start_byte)
                condition = syntax.child_by_field_name("condition") if syntax else None
                if condition is None:
                    continue
                variables = []
                for identifier in _walk(condition):
                    if identifier.type != "identifier":
                        continue
                    parent = identifier.parent
                    if parent.type == "call_expression" and parent.child_by_field_name("function") == identifier:
                        continue
                    # Member/pointer outputs are not same-spelled local variable uses.
                    if any(ancestor.type in {"field_expression", "pointer_expression", "subscript_expression"}
                           for ancestor in _ancestors(identifier, condition)):
                        continue
                    name = identifier.text.decode("utf-8", errors="replace")
                    if not any(probe.expression == name for probe in variables):
                        variables.append(ValueProbe(owner.id, name, self._location(site.path, identifier)))
                requirements.append(ExecutionRequirement(
                    owner.id, branch.condition, truth, self._location(site.path, condition), tuple(variables),
                    tuple(dict.fromkeys((*owner.uncertainty, *branch.uncertainty, "structural_conditions_only",
                                         "earlier_exit_loop_switch_not_resolved", "condition_satisfiability_not_proven")))))
        return tuple(requirements)

    def sources(self, probe: ValueProbe) -> tuple[ValueSource, ...]:
        """Find source candidates for a simple variable or all returns of a function."""
        function = self.project.functions_by_id.get(probe.function_id)
        if function is None or probe.location.path != function.location.path:
            raise ValueError("현재 분석에 추적 함수가 없습니다.")
        if (not function.location.start_byte <= probe.location.start_byte
                <= probe.location.end_byte <= function.location.end_byte):
            raise ValueError("추적 위치가 함수 범위 밖입니다.")
        if probe.kind not in {"variable", "return"}:
            raise ValueError("지원하지 않는 값 추적 종류입니다.")
        if probe.kind == "variable" and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", probe.expression):
            raise ValueError("현재 버전은 단순 변수 이름만 직접 추적합니다.")
        node = self._function(function.id)
        path = function.location.path
        result = []
        common = tuple(dict.fromkeys((*function.uncertainty, "value_source_candidate",
                                     "control_flow_not_proven", "alias_and_scope_not_resolved")))

        def add(owner: str, kind: str, expression: str, site: SourceRange,
                next_probe: ValueProbe | None = None, extra: tuple[str, ...] = ()) -> None:
            result.append(ValueSource(owner, kind, expression, site, next_probe,
                                      tuple(dict.fromkeys((*common, *self.project.functions_by_id[owner].uncertainty, *extra)))))

        def expression_sources(expression: Node, owner: str, kind: str, site: SourceRange,
                               extra: tuple[str, ...] = ()) -> None:
            original = expression.text.decode("utf-8", errors="replace")
            while expression.type in {"parenthesized_expression", "cast_expression"}:
                child = expression.child_by_field_name("value")
                if child is None:
                    child = next((c for c in expression.named_children if c.type != "comment"), None)
                if child is None:
                    break
                expression = child
            point = self._location(self.project.functions_by_id[owner].location.path, expression)
            if expression.type == "identifier":
                add(owner, kind, original, site, ValueProbe(owner, expression.text.decode(), point), extra)
            elif expression.type in {"number_literal", "char_literal", "string_literal", "true", "false", "null"}:
                add(owner, "constant", original, site, extra=(*extra, "constant_source_not_constraint_solution"))
            elif expression.type == "call_expression":
                callee = expression.child_by_field_name("function")
                name = callee.text.decode() if callee is not None and callee.type == "identifier" else None
                calls = self.project.calls_by_owner.get(owner, ())
                syntax = next((c for c in calls if c.location.start_byte == expression.start_byte), None)
                matches = self.project.functions_by_name.get(name, ()) if syntax and syntax.kind == "direct_candidate" else ()
                for destination in matches:
                    add(destination.id, "return_value", original, site,
                        ValueProbe(destination.id, "$return", destination.location, "return"),
                        (*extra, "name_only_call_candidate", "call_context_not_bound"))
                if not matches:
                    add(owner, "unresolved_call", original, site,
                        extra=(*extra, "macro_or_external_call_not_resolved"))
                # For macros/unknown calls, expose argument variables without expanding their meaning.
                if not matches:
                    arguments = expression.child_by_field_name("arguments")
                    if arguments is not None:
                        for argument in arguments.named_children:
                            if argument.type == "identifier":
                                add(owner, "call_argument", argument.text.decode(), site,
                                    ValueProbe(owner, argument.text.decode(), self._location(point.path, argument)),
                                    (*extra, "call_transformation_not_resolved"))
            else:
                add(owner, "expression", original, site, extra=(*extra, "expression_not_inverted"))
                # Compound member/pointer expressions are boundaries, not same-spelled local identifiers.
                if expression.type in {"binary_expression", "unary_expression", "conditional_expression"}:
                    seen = set()
                    for child in _walk(expression):
                        if (child.type == "identifier" and child.text not in seen
                                and not (child.parent.type == "call_expression"
                                         and child.parent.child_by_field_name("function") == child)
                                and not any(ancestor.type in {"field_expression", "pointer_expression", "subscript_expression"}
                                            for ancestor in _ancestors(child, expression))):
                            seen.add(child.text)
                            add(owner, "expression_operand", child.text.decode(), site,
                                ValueProbe(owner, child.text.decode(), self._location(point.path, child)),
                                (*extra, "expression_not_inverted"))

        if probe.kind == "return":
            for current in _walk(node):
                if current.type == "return_statement":
                    expression = next((c for c in current.named_children if c.type != "comment"), None)
                    if expression is not None:
                        expression_sources(expression, function.id, "return", self._location(path, current))
        else:
            variable = probe.expression
            locals_found = False
            for current in _walk(node):
                if current.type in {"init_declarator", "parameter_declaration", "declaration"}:
                    if _name(current.child_by_field_name("declarator")) == variable:
                        locals_found = True
                if current.end_byte > probe.location.start_byte:
                    continue
                if current.type == "init_declarator" and _name(current.child_by_field_name("declarator")) == variable:
                    value = current.child_by_field_name("value")
                    if value is not None:
                        expression_sources(value, function.id, "initializer", self._location(path, current))
                elif current.type == "assignment_expression":
                    left, right = current.child_by_field_name("left"), current.child_by_field_name("right")
                    if left is not None and left.type == "identifier" and left.text.decode() == variable and right is not None:
                        operator = current.child_by_field_name("operator")
                        extra = ("compound_assignment_requires_previous_value",) if operator and operator.text != b"=" else ()
                        expression_sources(right, function.id, "assignment", self._location(path, current), extra)
                elif current.type == "update_expression" and any(c.type == "identifier" and c.text.decode() == variable
                                                                   for c in current.named_children):
                    add(function.id, "update", current.text.decode(), self._location(path, current),
                        extra=("increment_requires_previous_value",))
                elif current.type == "call_expression":
                    arguments = current.child_by_field_name("arguments")
                    if arguments is None:
                        continue
                    output = any(a.type == "pointer_expression" and re.sub(rb"\s+", b"", a.text) == b"&" + variable.encode()
                                 for a in arguments.named_children)
                    if not output:
                        continue
                    read = next((a for a in self.project.rte.accesses if a.direction == "read"
                                 and a.function_id == function.id and a.location.start_byte == current.start_byte), None)
                    if read is None:
                        add(function.id, "possible_output_argument", current.text.decode(), self._location(path, current),
                            extra=("output_argument_semantics_not_resolved",))
                        continue
                    matched = False
                    for write, dependency in self.project.rte_by_owner.get(function.id, ()):
                        if dependency.consumer_access_id != read.id or write.function_id is None:
                            continue
                        matched = True
                        writer = self.project.functions_by_id[write.function_id]
                        write_node = next((n for n in _walk(self._function(writer.id))
                                           if n.type == "call_expression" and n.start_byte == write.location.start_byte), None)
                        args = write_node.child_by_field_name("arguments") if write_node else None
                        if args and args.named_children:
                            expression_sources(args.named_children[0], writer.id, "rte_data", write.location,
                                               dependency.uncertainty)
                    if not matched:
                        add(function.id, "missing_rte_producer", current.text.decode(), read.location,
                            extra=(*read.uncertainty, "no_producer_in_analysis_scope"))

            declarator = node.child_by_field_name("declarator")
            while declarator is not None and declarator.type != "function_declarator":
                declarator = declarator.child_by_field_name("declarator")
            parameters = declarator.child_by_field_name("parameters") if declarator else None
            parameter_index = next((index for index, parameter in enumerate(parameters.named_children)
                                    if _name(parameter.child_by_field_name("declarator")) == variable), None) if parameters else None
            if parameter_index is not None:
                for parsed in self.project.results:
                    for call in parsed.calls:
                        if call.callee_name != function.name or call.kind != "direct_candidate" or call.caller_id is None:
                            continue
                        caller = self.project.functions_by_id[call.caller_id]
                        call_node = next((n for n in _walk(self._function(caller.id))
                                          if n.type == "call_expression" and n.start_byte == call.location.start_byte), None)
                        arguments = call_node.child_by_field_name("arguments") if call_node else None
                        if arguments and len(arguments.named_children) > parameter_index:
                            expression_sources(arguments.named_children[parameter_index], caller.id, "parameter_input",
                                               call.location, ("name_only_caller_candidate", "call_context_not_bound"))
            if not locals_found:
                declarations = []
                for declaration_path in self._bytes:
                    if declaration_path != path and declaration_path.suffix.lower() != ".h":
                        continue
                    for declaration in self._root(declaration_path).named_children:
                        if declaration.type == "declaration" and any(
                            _name(child.child_by_field_name("declarator") if child.type == "init_declarator" else child) == variable
                            for child in declaration.named_children
                            if not any(part.type == "function_declarator" for part in _walk(child))
                        ):
                            declarations.append((declaration_path, declaration))
                if declarations and not any(
                    child.type in {"storage_class_specifier", "type_qualifier"} and child.text in {b"static", b"const"}
                    for _, declaration in declarations for child in declaration.named_children
                ):
                    declaration_path, declaration = declarations[0]
                    add(function.id, "ct_global_input", variable, probe.location, extra=(
                        "external_linkage_name_candidate", "ct_accessibility_not_verified",
                        "header_visibility_not_verified", f"declaration: {declaration_path}:{declaration.start_point.row + 1}"))
                # Deliberately file-local lookup; do not merge same-spelled globals in other files.
                global_known = any(n.type == "declaration" and n.parent.type != "compound_statement"
                                   and any(_name(c.child_by_field_name("declarator") if c.type == "init_declarator" else c) == variable
                                           for c in n.named_children)
                                   for n in self._root(path).named_children)
                if global_known:
                    for other in self.project.functions:
                        if other.location.path != path or other.id == function.id:
                            continue
                        for assignment in _walk(self._function(other.id)):
                            if assignment.type != "assignment_expression":
                                continue
                            left, right = assignment.child_by_field_name("left"), assignment.child_by_field_name("right")
                            if left is not None and left.type == "identifier" and left.text.decode() == variable and right is not None:
                                expression_sources(right, other.id, "global_write", self._location(path, assignment),
                                                   ("file_local_global_name_candidate", "execution_order_not_resolved"))
            if not result:
                add(function.id, "input_boundary", variable, probe.location,
                    extra=("no_supported_source_in_analysis_scope",))
        return tuple(sorted(result, key=lambda s: (s.location.path.as_posix(), -s.location.start_byte, s.expression)))


def _ancestors(node: Node, stop: Node) -> Iterator[Node]:
    parent = node.parent
    while parent is not None and parent != stop:
        yield parent
        parent = parent.parent
