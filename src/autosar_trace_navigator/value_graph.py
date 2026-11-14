"""Bounded, read-only value-origin preview; candidate relationships, never execution proof."""

from collections import deque
from dataclasses import dataclass, field
import time

from .models import SourceRange, ValueProbe
from .workbench import ProjectSnapshot


@dataclass
class OriginNode:
    id: str
    kind: str
    expression: str
    function_id: str
    location: SourceRange
    depth: int
    terminal: str = "none"
    required_truth: bool | None = None
    uncertainty: tuple[str, ...] = ()


@dataclass
class OriginGraph:
    nodes: list[OriginNode] = field(default_factory=list)
    edges: list[tuple[str, str, str]] = field(default_factory=list)
    limit_reasons: list[str] = field(default_factory=list)
    cycle_edges: set[tuple[str, str, str]] = field(default_factory=set)


def trace_origins(project: ProjectSnapshot, probe: ValueProbe, *, max_nodes: int = 1000,
                  max_depth: int = 256, max_seconds: int = 20) -> OriginGraph:
    """Expand sources and structural conditions once per probe, sharing repeated sites.

    All supported alternatives are candidates. Limits are explicit, including depth,
    time, fan-out and node/edge counts. Cycles are represented as reference edges.
    External-linkage input candidates stop expansion without asserting CT access.
    """
    for value, ceiling in ((max_nodes, 2000), (max_depth, 256), (max_seconds, 30)):
        if type(value) is not int or not 1 <= value <= ceiling:
            raise ValueError("Origin preview limits must be bounded positive integers")
    resolver = project.value_resolver
    graph = OriginGraph()
    keyed: dict[tuple, OriginNode] = {}
    edge_set = set()
    pending = deque()
    started = time.monotonic()

    def key(p: ValueProbe) -> tuple:
        return (p.function_id, p.kind, p.expression, p.location.path, p.location.start_byte, p.location.end_byte)

    def limited(parent: OriginNode, reason: str) -> None:
        parent.terminal = "limit"
        if reason not in graph.limit_reasons:
            graph.limit_reasons.append(reason)

    def attach(parent: OriginNode, identity: tuple, kind: str, expression: str, owner: str,
               location: SourceRange, relation: str, depth: int, *, terminal: str = "none",
               truth: bool | None = None, uncertainty: tuple[str, ...] = ()) -> tuple[OriginNode | None, bool]:
        if depth > max_depth:
            limited(parent, "depth")
            return None, False
        if len(graph.edges) >= max_nodes * 4:
            limited(parent, "edges")
            return None, False
        node = keyed.get(identity)
        fresh = node is None
        if fresh:
            if len(graph.nodes) >= max_nodes:
                limited(parent, "nodes")
                return None, False
            node = OriginNode(f"n{len(graph.nodes) + 1}", kind, expression, owner, location, depth,
                              terminal, truth, uncertainty)
            graph.nodes.append(node)
            keyed[identity] = node
        edge = (parent.id, node.id, relation)
        if edge not in edge_set:
            edge_set.add(edge)
            graph.edges.append(edge)
        return node, fresh

    root = OriginNode("n1", "probe", probe.expression, probe.function_id, probe.location, 0)
    graph.nodes.append(root)
    keyed[("probe", *key(probe))] = root
    pending.append((root, probe))

    def conditions(parent: OriginNode, site: SourceRange) -> None:
        for requirement in resolver.conditions(site):
            identity = ("condition", requirement.function_id, requirement.location.start_byte,
                        requirement.required_truth)
            node, fresh = attach(parent, identity, "condition", requirement.expression,
                                 requirement.function_id, requirement.location, "condition", parent.depth + 1,
                                 truth=requirement.required_truth, uncertainty=requirement.uncertainty)
            if node is None or not fresh:
                continue
            if not requirement.variables:
                node.terminal = "review"
            for variable in requirement.variables:
                child, new = attach(node, ("probe", *key(variable)), "probe", variable.expression,
                                    variable.function_id, variable.location, "condition", node.depth + 1)
                if child is not None and new:
                    pending.append((child, variable))

    while pending:
        if time.monotonic() - started >= max_seconds:
            for node, _ in pending:
                limited(node, "time")
            break
        node, current = pending.popleft()
        if node.depth >= max_depth:
            limited(node, "depth")
            continue
        try:
            sources = resolver.sources(current)
        except ValueError:
            node.terminal = "unresolved"
            node.uncertainty = ("unsupported_value_probe",)
            continue
        if not sources:
            node.terminal = "unresolved"
        for source in sources[:64]:
            if time.monotonic() - started >= max_seconds:
                limited(node, "time")
                break
            identity = ("source", source.function_id, source.kind, source.expression,
                        source.location.path, source.location.start_byte, source.location.end_byte,
                        key(source.next_probe) if source.next_probe else None)
            relation = ("rte_data" if "name_only_connection" in source.uncertainty else
                        "call" if source.kind == "return_value" else "value")
            terminal = ("ct_input" if source.kind == "ct_global_input" else
                        "constant" if source.kind == "constant" else
                        "none" if source.next_probe else
                        "review" if source.kind == "expression" else "unresolved")
            child, fresh = attach(node, identity, source.kind, source.expression, source.function_id,
                                  source.location, relation, node.depth + 1,
                                  terminal=terminal, uncertainty=source.uncertainty)
            if child is None or not fresh:
                continue
            conditions(child, source.location)
            if source.next_probe is not None and terminal != "ct_input":
                following = source.next_probe
                next_node, new = attach(child, ("probe", *key(following)), "probe", following.expression,
                                        following.function_id, following.location, relation, child.depth + 1)
                if next_node is not None and new:
                    pending.append((next_node, following))
        if len(sources) > 64:
            limited(node, "sources")
        if node is root:
            conditions(root, current.location)
    # Mark back edges in the candidate graph, without recursive Python calls.
    outgoing = {}
    for edge in graph.edges:
        outgoing.setdefault(edge[0], []).append(edge)
    color = {root.id: 1}
    stack = [(root.id, iter(outgoing.get(root.id, ())))]
    while stack:
        parent, children = stack[-1]
        edge = next(children, None)
        if edge is None:
            color[parent] = 2
            stack.pop()
        elif color.get(edge[1]) == 1:
            graph.cycle_edges.add(edge)
            node = graph.nodes[int(parent[1:]) - 1]
            if node.terminal == "none":
                node.terminal = "cycle"
                node.uncertainty += ("candidate_cycle_not_runtime_proof",)
        elif edge[1] not in color:
            color[edge[1]] = 1
            stack.append((edge[1], iter(outgoing.get(edge[1], ()))))
    return graph
