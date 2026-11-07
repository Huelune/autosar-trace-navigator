"""Manual investigation history, independent of parsing, storage and GUI."""

from dataclasses import dataclass, replace
from typing import Literal
from uuid import uuid4

from .models import Branch, FunctionDefinition, SourceRange, ValueProbe
from .access import parse_access_path, parse_return_path


Relation = Literal["root", "call", "rte_data", "manual", "value"]


@dataclass(frozen=True)
class VariableGoal:
    function_id: str
    variable: str
    target_value: str
    location: SourceRange


@dataclass(frozen=True)
class TraceStep:
    id: str
    parent_id: str | None
    function: FunctionDefinition
    reason: str
    relation: Relation
    evidence: SourceRange | None
    uncertainty: tuple[str, ...]
    selected_location: SourceRange | None = None
    probe: ValueProbe | None = None


@dataclass(frozen=True)
class TraceSession:
    id: str
    target_function: FunctionDefinition
    target_branch: Branch
    steps: tuple[TraceStep, ...]
    current_step_id: str
    variable_goal: VariableGoal | None = None


def _require_text(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Identifiers and investigation reasons must not be blank")


def _validate_range(span: SourceRange) -> None:
    if not span.path.is_absolute():
        raise ValueError("Source paths must be absolute")
    positions = (span.start_line, span.start_column, span.end_line, span.end_column)
    if any(type(value) is not int or value < 1 for value in positions):
        raise ValueError("Source lines and columns must be positive integers")
    if ((span.end_line, span.end_column) < (span.start_line, span.start_column)
            or type(span.start_byte) is not int or type(span.end_byte) is not int
            or not 0 <= span.start_byte <= span.end_byte):
        raise ValueError("Invalid source range")


def _validate_function(function: FunctionDefinition) -> None:
    _require_text(function.id)
    _require_text(function.name)
    _validate_range(function.location)
    _validate_range(function.body_location)
    if (function.location.path != function.body_location.path
            or not function.location.start_byte <= function.body_location.start_byte
            <= function.body_location.end_byte <= function.location.end_byte):
        raise ValueError("Function body must belong to its source definition")


def _validate_site(function: FunctionDefinition, location: SourceRange) -> None:
    _validate_range(location)
    if (location.path != function.location.path or not function.location.start_byte
            <= location.start_byte <= location.end_byte <= function.location.end_byte):
        raise ValueError("선택 위치가 조사 함수 범위 밖입니다.")


def _validate_probe(function: FunctionDefinition, probe: ValueProbe) -> None:
    _validate_site(function, probe.location)
    if probe.function_id != function.id or probe.kind not in {"variable", "return"}:
        raise ValueError("Invalid value probe owner/kind")
    if probe.kind == "variable" and parse_access_path(probe.expression) is None:
        raise ValueError("변수 또는 지원하는 구조체 멤버 경로를 입력하세요.")
    if probe.kind == "return" and parse_return_path(probe.expression) is None:
        raise ValueError("Invalid return/member projection")
    _require_text(probe.expression)


def validate_session(session: TraceSession) -> None:
    """Reject broken history references, including loaded/caller-created snapshots."""
    _require_text(session.id)
    _require_text(session.target_branch.id)
    _validate_function(session.target_function)
    if not session.steps or session.target_branch.function_id != session.target_function.id:
        raise ValueError("A session needs a target branch belonging to its target function")
    if session.target_branch.kind not in {"if", "else_if", "else"}:
        raise ValueError("Invalid target branch kind")
    if ((session.target_branch.kind == "else" and session.target_branch.condition is not None)
            or (session.target_branch.kind != "else" and not session.target_branch.condition)):
        raise ValueError("Invalid target condition")
    if session.target_branch.location.path != session.target_function.location.path:
        raise ValueError("Target function and branch must use the same source file")
    for span in (session.target_function.location, session.target_function.body_location,
                 session.target_branch.location, session.target_branch.body_location):
        _validate_range(span)
    branch = session.target_branch
    body = session.target_function.body_location
    if (branch.body_location.path != branch.location.path
            or not body.start_byte <= branch.location.start_byte <= branch.body_location.start_byte
            <= branch.body_location.end_byte <= branch.location.end_byte <= body.end_byte):
        raise ValueError("Target branch must lie within its function body")
    seen: set[str] = set()
    for index, step in enumerate(session.steps):
        for value in (step.id, step.function.id, step.function.name, step.reason):
            _require_text(value)
        if step.id in seen or step.relation not in {"root", "call", "rte_data", "manual", "value"}:
            raise ValueError("Duplicate step or unsupported investigation relation")
        if index == 0:
            if (step.parent_id is not None or step.relation != "root"
                    or step.function != session.target_function or step.evidence is not None):
                raise ValueError("The first step must represent the original target function")
        elif step.parent_id not in seen or step.relation == "root":
            raise ValueError("Steps must refer to an earlier parent")
        if step.relation in {"call", "rte_data", "value"} and step.evidence is None:
            raise ValueError("Call/RTE investigation steps require an evidence location")
        _validate_function(step.function)
        if step.evidence is not None:
            _validate_range(step.evidence)
        if step.selected_location is not None:
            _validate_site(step.function, step.selected_location)
        if step.probe is not None:
            _validate_probe(step.function, step.probe)
        seen.add(step.id)
    if session.current_step_id not in seen:
        raise ValueError("Current step is not part of this session")
    if session.variable_goal is not None:
        goal = session.variable_goal
        owner = next((s.function for s in session.steps if s.function.id == goal.function_id), None)
        if owner is None:
            raise ValueError("Variable goal owner is not in investigation history")
        _validate_probe(owner, ValueProbe(goal.function_id, goal.variable, goal.location))
        _require_text(goal.target_value)


class TraceManager:
    """Maintain an immutable snapshot and a cursor without discarding old branches."""

    def __init__(self, session: TraceSession):
        validate_session(session)
        self._session = session

    @classmethod
    def start(cls, target_function: FunctionDefinition, target_branch: Branch,
              *, reason: str) -> "TraceManager":
        """Start at a parser-selected target, preserving its complete syntax snapshot."""
        root = TraceStep(str(uuid4()), None, target_function, reason, "root", None,
                         target_function.uncertainty, target_branch.location)
        return cls(TraceSession(str(uuid4()), target_function, target_branch, (root,), root.id))

    @property
    def session(self) -> TraceSession:
        return self._session

    @property
    def current_step(self) -> TraceStep:
        return next(step for step in self._session.steps if step.id == self._session.current_step_id)

    @property
    def current_path(self) -> tuple[TraceStep, ...]:
        """Return root-to-cursor steps; abandoned alternatives remain in session.steps."""
        steps = {step.id: step for step in self._session.steps}
        path = []
        current: TraceStep | None = self.current_step
        while current is not None:
            path.append(current)
            current = steps[current.parent_id] if current.parent_id else None
        return tuple(reversed(path))

    def follow(self, function: FunctionDefinition, *, reason: str, relation: Relation = "manual",
               evidence: SourceRange | None = None,
               uncertainty: tuple[str, ...] = (), selected_location: SourceRange | None = None,
               probe: ValueProbe | None = None) -> TraceStep:
        """Record a user-selected investigation edge, not a proven runtime relation."""
        reasons = tuple(dict.fromkeys((*function.uncertainty, *uncertainty, "user_selected_relation")))
        step = TraceStep(str(uuid4()), self.current_step.id, function, reason, relation,
                         evidence, reasons, selected_location or (probe.location if probe else function.location), probe)
        session = replace(self._session, steps=(*self._session.steps, step), current_step_id=step.id)
        validate_session(session)
        self._session = session
        return step

    def _replace_current(self, **changes) -> None:
        step = replace(self.current_step, **changes)
        session = replace(self._session, steps=tuple(step if s.id == step.id else s for s in self._session.steps))
        validate_session(session)
        self._session = session

    def record_location(self, location: SourceRange) -> None:
        """Record explicit user selection; previewing code alone does not call this."""
        self._replace_current(selected_location=location)

    def set_variable_goal(self, variable: str, target_value: str, location: SourceRange) -> None:
        """Pin the first variable/value objective while intermediate probes may change."""
        function = self.current_step.function
        goal = VariableGoal(function.id, variable, target_value, location)
        if self.session.variable_goal is not None and self.session.variable_goal != goal:
            raise ValueError("최초 변수 목표는 고정됩니다. 다른 목표는 새 조사로 시작하세요.")
        probe = ValueProbe(function.id, variable, location)
        step = replace(self.current_step, probe=probe, selected_location=location)
        session = replace(self.session, variable_goal=goal,
                          steps=tuple(step if s.id == step.id else s for s in self.session.steps))
        validate_session(session)
        self._session = session

    def inspect_variable(self, variable: str, location: SourceRange) -> None:
        """Change only the current value probe, keeping the original variable goal."""
        if self.session.variable_goal is None:
            raise ValueError("먼저 변수 목표값을 설정하세요.")
        self._replace_current(probe=ValueProbe(self.current_step.function.id, variable, location),
                              selected_location=location)

    def select(self, step_id: str) -> None:
        """Move to a previously recorded step without deleting history."""
        if not any(step.id == step_id for step in self._session.steps):
            raise ValueError("Unknown investigation step")
        self._session = replace(self._session, current_step_id=step_id)

    def back(self) -> None:
        """Move to the parent. At the root, fail without modifying the session."""
        parent = self.current_step.parent_id
        if parent is None:
            raise ValueError("Already at the target function")
        self.select(parent)
