"""Conservative member projections and explicit pointer/object source candidates."""

from dataclasses import replace

from .access import AccessPath
from .dataflow import ValueResolver, ValueSource, _access, _name, _unwrap, _walk
from .models import SourceRange, ValueProbe


class _Members:
    def __init__(self, resolver, probe: ValueProbe, target: AccessPath):
        self.r = resolver
        self.probe = probe
        self.target = target
        self.project = resolver.project
        self.function = self.project.functions_by_id[probe.function_id]
        self.result = []
        self.flags = (*self.function.uncertainty, "value_source_candidate", "control_flow_not_proven",
                      "alias_and_scope_not_resolved", "member_type_layout_not_verified")

    def emit(self, owner, kind, text, site, probe=None, flags=()):
        self.result.append(ValueSource(owner, kind, text, site, probe,
                                       tuple(dict.fromkeys((*self.flags, *self.project.functions_by_id[owner].uncertainty, *flags)))))

    def site(self, owner, node):
        return self.r._location(self.project.functions_by_id[owner].location.path, node)

    def project_value(self, expression, owner, kind, site, tail, flags=()):
        """Project a whole-object source without dropping or guessing member names."""
        expression = _unwrap(expression)
        flags = (*flags, "aggregate_member_projection")
        if not tail.members and not tail.dereference:
            for source in self.r._expression_sources(expression, owner, kind, site, (*self.flags, *flags)):
                if source.next_probe is not None:
                    function = self.project.functions_by_id[source.next_probe.function_id]
                    if not function.location.start_byte <= source.next_probe.location.start_byte <= function.location.end_byte:
                        source = replace(source, next_probe=replace(source.next_probe, location=site))
                self.result.append(source)
            return
        if expression.type == "pointer_expression" and expression.child_by_field_name("operator").text == b"&":
            argument = expression.child_by_field_name("argument")
            if argument is not None:
                steps = tail.members
                if steps and steps[0][0] == "->":
                    steps = ((".", steps[0][1]), *steps[1:])
                self.project_value(argument, owner, kind, site, AccessPath("value", steps),
                                   (*flags, "explicit_address_binding_candidate", "pointer_identity_not_proven"))
                return
        base = _access(expression)
        if base is not None:
            if tail.dereference:
                projected = AccessPath(base.root, dereference=True) if not base.members and not base.dereference else None
            elif base.dereference and tail.members and tail.members[0][0] == ".":
                projected = AccessPath(base.root, (("->", tail.members[0][1]), *tail.members[1:]))
            elif not base.dereference:
                projected = AccessPath(base.root, (*base.members, *tail.members))
            else:
                projected = None
            if projected:
                location = self.site(owner, expression)
                function = self.project.functions_by_id[owner]
                if not function.location.start_byte <= location.start_byte <= location.end_byte <= function.location.end_byte:
                    location = site
                self.emit(owner, kind, projected.expression, site,
                          ValueProbe(owner, projected.expression, location), flags)
                return
        if expression.type == "initializer_list" and tail.members and tail.members[0][0] == ".":
            for pair in expression.named_children:
                if pair.type != "initializer_pair":
                    continue
                if any(d.type.endswith("_designator") and d.type != "field_designator" for d in pair.named_children):
                    continue
                designators = tuple((".", d.named_children[0].text.decode()) for d in pair.named_children
                                    if d.type == "field_designator" and d.named_children)
                value = pair.child_by_field_name("value")
                if designators and tail.members[:len(designators)] == designators and value is not None:
                    self.project_value(value, owner, kind, site, AccessPath("value", tail.members[len(designators):]), flags)
                    return
        if expression.type == "call_expression" and not tail.dereference:
            syntax = next((c for c in self.project.calls_by_owner.get(owner, ())
                           if c.location.start_byte == expression.start_byte and c.kind == "direct_candidate"), None)
            matches = self.project.functions_by_name.get(syntax.callee_name, ()) if syntax else ()
            for function in matches:
                returned = "$return" + "".join(op + name for op, name in tail.members)
                self.emit(function.id, "return_value", expression.text.decode() + returned[len("$return"):], site,
                          ValueProbe(function.id, returned, function.location, "return"),
                          (*flags, "name_only_call_candidate", "call_context_not_bound"))
            if matches:
                return
        self.emit(owner, "member_boundary", expression.text.decode(), site,
                  flags=(*flags, "aggregate_source_shape_not_resolved"))

    def local_declarations(self, owner, root):
        return [n for n in _walk(self.r._function(owner))
                if n.type in {"init_declarator", "parameter_declaration", "declaration"}
                and _name(n.child_by_field_name("declarator")) == root]

    def global_declarations(self, path, root):
        return list(self.r._global_declarations(path, root))

    @staticmethod
    def is_static(declarations):
        return any(c.type == "storage_class_specifier" and c.text == b"static"
                   for declaration in declarations for c in declaration.named_children)

    def alias_paths(self, owner, path, before, seen=()):
        """Bounded explicit &object / pointer-copy aliases, retaining every candidate."""
        if not path.indirect or path.root in seen or len(seen) >= 4:
            return ()
        results = []
        for node in _walk(self.r._function(owner)):
            if node.end_byte > before:
                continue
            if node.type == "init_declarator" and _name(node.child_by_field_name("declarator")) == path.root:
                value = node.child_by_field_name("value")
            elif node.type == "assignment_expression" and _access(node.child_by_field_name("left")) == AccessPath(path.root):
                value = node.child_by_field_name("right")
            else:
                continue
            if value is None:
                continue
            value = _unwrap(value)
            address = value.type == "pointer_expression" and value.child_by_field_name("operator").text == b"&"
            base = _access(value.child_by_field_name("argument")) if address else _access(value)
            if base is None or base.dereference:
                continue
            members = path.members
            if address:
                if members and members[0][0] == "->":
                    members = ((".", members[0][1]), *members[1:])
                projected = AccessPath(base.root, (*base.members, *members))
            else:
                if base.members:  # Pointer-valued fields need type/alias analysis.
                    continue
                projected = AccessPath(base.root, members, path.dereference)
            results.append(projected)
            results.extend(self.alias_paths(owner, projected, node.start_byte, (*seen, path.root)))
        return tuple(dict.fromkeys(results))

    def assignment(self, owner, node, flags=()):
        left, right = node.child_by_field_name("left"), node.child_by_field_name("right")
        access = _access(left)
        if access is None or right is None:
            return
        for candidate in (access, *self.alias_paths(owner, access, node.start_byte)):
            tail = self.target.relative_to(candidate)
            if tail is None:
                continue
            extra = (*flags, "explicit_alias_candidate", "alias_candidates_not_reaching_definitions") if candidate != access else flags
            operator = node.child_by_field_name("operator")
            if operator is not None and operator.text != b"=":
                extra = (*extra, "compound_assignment_requires_previous_value")
            self.project_value(right, owner, "member_write", self.site(owner, node), tail, extra)

    def parameter_info(self, owner):
        declarator = self.r._function(owner).child_by_field_name("declarator")
        while declarator is not None and declarator.type != "function_declarator":
            declarator = declarator.child_by_field_name("declarator")
        parameters = declarator.child_by_field_name("parameters") if declarator else None
        return tuple(parameters.named_children) if parameters else ()

    def output_call(self, owner, node):
        arguments = node.child_by_field_name("arguments")
        if arguments is None:
            return
        for index, argument in enumerate(arguments.named_children):
            argument = _unwrap(argument)
            address = argument.type == "pointer_expression" and argument.child_by_field_name("operator").text == b"&"
            base = _access(argument.child_by_field_name("argument")) if address else _access(argument)
            if base is None:
                continue
            tail = self.target.relative_to(base)
            if tail is None or (not address and not tail.indirect):
                continue
            site = self.site(owner, node)
            read = next((a for a in self.project.rte.accesses if a.function_id == owner and a.direction == "read"
                         and a.location.start_byte == node.start_byte), None)
            if read:
                payload_tail = tail
                if not address:
                    steps = tail.members
                    if steps and steps[0][0] == "->":
                        steps = ((".", steps[0][1]), *steps[1:])
                    payload_tail = AccessPath("value", steps)
                matched = False
                for write, dependency in self.project.rte_by_owner.get(owner, ()):
                    if dependency.consumer_access_id != read.id or write.function_id is None:
                        continue
                    writer = next((n for n in _walk(self.r._function(write.function_id))
                                   if n.type == "call_expression" and n.start_byte == write.location.start_byte), None)
                    args = writer.child_by_field_name("arguments") if writer else None
                    if args and args.named_children:
                        matched = True
                        payload = args.named_children[0]
                        projection = payload_tail
                        payload_path = _access(payload)
                        if payload_path and not payload_path.members and projection.members and projection.members[0][0] == ".":
                            declarations = self.local_declarations(write.function_id, payload_path.root)
                            declarations += self.global_declarations(write.location.path, payload_path.root)
                            if any(n.type == "pointer_declarator" for d in declarations for n in _walk(d)):
                                projection = AccessPath("value", (("->", projection.members[0][1]), *projection.members[1:]))
                        self.project_value(payload, write.function_id, "rte_data", write.location, projection,
                                           (*dependency.uncertainty, "rte_payload_shape_not_proven"))
                if not matched:
                    self.emit(owner, "missing_rte_producer", node.text.decode(), site,
                              flags=(*read.uncertainty, "no_producer_in_analysis_scope"))
                continue
            syntax = next((c for c in self.project.calls_by_owner.get(owner, ())
                           if c.location.start_byte == node.start_byte and c.kind == "direct_candidate"), None)
            matched = False
            for function in self.project.functions_by_name.get(syntax.callee_name, ()) if syntax else ():
                parameters = self.parameter_info(function.id)
                if len(parameters) <= index:
                    continue
                parameter = parameters[index]
                name = _name(parameter.child_by_field_name("declarator"))
                if name is None or not any(n.type == "pointer_declarator" for n in _walk(parameter)):
                    continue
                if tail.members:
                    steps = tail.members
                    if steps[0][0] == ".":
                        steps = (("->", steps[0][1]), *steps[1:])
                    output = AccessPath(name, steps)
                else:
                    output = AccessPath(name, dereference=True)
                end = function.body_location
                location = SourceRange(end.path, end.end_line, end.end_column, end.end_line, end.end_column,
                                       end.end_byte, end.end_byte)
                matched = True
                self.emit(function.id, "output_parameter", output.expression, site,
                          ValueProbe(function.id, output.expression, location),
                          flags=("possible_output_parameter_write", "name_only_call_candidate", "call_context_not_bound"))
            if not matched:
                self.emit(owner, "possible_output_argument", node.text.decode(), site,
                          flags=("output_argument_semantics_not_resolved",))

    def run(self):
        owner = self.function.id
        node = self.r._function(owner)
        if self.probe.kind == "return":
            for statement in _walk(node):
                if statement.type == "return_statement" and statement.named_children:
                    self.project_value(statement.named_children[0], owner, "return", self.site(owner, statement), self.target)
        else:
            for statement in _walk(node):
                if statement.end_byte > self.probe.location.start_byte:
                    continue
                if statement.type == "assignment_expression":
                    self.assignment(owner, statement)
                elif statement.type == "init_declarator" and _name(statement.child_by_field_name("declarator")) == self.target.root:
                    value = statement.child_by_field_name("value")
                    if value is not None:
                        self.project_value(value, owner, "member_initializer", self.site(owner, statement),
                                           AccessPath("value", self.target.members, self.target.dereference))
                elif statement.type == "call_expression":
                    self.output_call(owner, statement)
            for index, parameter in enumerate(self.parameter_info(owner)):
                if _name(parameter.child_by_field_name("declarator")) != self.target.root:
                    continue
                for parsed in self.project.results:
                    for call in parsed.calls:
                        if call.callee_name != self.function.name or call.kind != "direct_candidate" or call.caller_id is None:
                            continue
                        caller = next((n for n in _walk(self.r._function(call.caller_id))
                                       if n.type == "call_expression" and n.start_byte == call.location.start_byte), None)
                        args = caller.child_by_field_name("arguments") if caller else None
                        if args and len(args.named_children) > index:
                            self.project_value(args.named_children[index], call.caller_id, "parameter_input", call.location,
                                               AccessPath("value", self.target.members, self.target.dereference),
                                               ("name_only_caller_candidate", "call_context_not_bound"))
            if not self.local_declarations(owner, self.target.root):
                own = self.global_declarations(self.function.location.path, self.target.root)
                headers = [d for p in self.r._bytes if p.suffix.lower() == ".h"
                           for d in self.global_declarations(p, self.target.root)]
                if own or headers:
                    for other in self.project.functions:
                        if other.id == owner or self.local_declarations(other.id, self.target.root):
                            continue
                        if other.location.path != self.function.location.path:
                            if self.is_static((*own, *headers)) or self.is_static(self.global_declarations(other.location.path, self.target.root)):
                                continue
                        for statement in _walk(self.r._function(other.id)):
                            if statement.type == "assignment_expression":
                                self.assignment(other.id, statement, ("name_only_global_candidate", "global_linkage_not_proven",
                                                                     "execution_order_not_resolved"))
                    for declaration in own:
                        for child in declaration.named_children:
                            if child.type == "init_declarator" and _name(child.child_by_field_name("declarator")) == self.target.root:
                                value = child.child_by_field_name("value")
                                if value is not None:
                                    # A global declaration is outside the function: keep a use-site anchor.
                                    self.project_value(value, owner, "member_initializer", self.probe.location,
                                                       AccessPath("value", self.target.members, self.target.dereference),
                                                       ("global_initializer_source",
                                                        f"initializer_declaration: {self.function.location.path}:{child.start_point.row + 1}"))
            if not self.result:
                self.emit(owner, "member_boundary", self.target.expression, self.probe.location,
                          flags=("pointer_target_not_resolved" if self.target.indirect else "no_supported_member_source",))
            self.emit(owner, "object_origin", self.target.root, self.probe.location,
                      ValueProbe(owner, self.target.root, self.probe.location),
                      ("object_origin_not_member_value", "pointer_value_not_pointee_control" if self.target.indirect else "root_object_candidate"))
        return tuple(sorted(dict.fromkeys(self.result), key=lambda s: (s.location.path.as_posix(), -s.location.start_byte, s.expression)))


def member_sources(resolver: ValueResolver, probe: ValueProbe, target: AccessPath) -> tuple[ValueSource, ...]:
    """Resolve member/value projections only within the selected analysis snapshot."""
    return _Members(resolver, probe, target).run()
