"""Manual investigation history, independent of parsing, storage and GUI."""

from dataclasses import dataclass, replace
from typing import Literal
from uuid import uuid4

from .models import Branch, FunctionDefinition, SourceRange


Relation = Literal["root", "call", "rte_data", "manual"]


@dataclass(frozen=True)
class TraceStep:
    id: str
    parent_id: str | None
    function: FunctionDefinition
    reason: str
    relation: Relation
    evidence: SourceRange | None
    uncertainty: tuple[str, ...]


@dataclass(frozen=True)
class TraceSession:
    id: str
    target_function: FunctionDefinition
    target_branch: Branch
    steps: tuple[TraceStep, ...]
    current_step_id: str


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


def validate_session(session: TraceSession) -> None:
    """Reject broken history references, including loaded/caller-created snapshots."""
    _require_text(session.id)
    if not session.steps or session.target_branch.function_id != session.target_function.id:
        raise ValueError("A session needs a target branch belonging to its target function")
    if session.target_branch.kind not in {"if", "else_if", "else"}:
        raise ValueError("Invalid target branch kind")
    if session.target_branch.location.path != session.target_function.location.path:
        raise ValueError("Target function and branch must use the same source file")
    for span in (session.target_function.location, session.target_function.body_location,
                 session.target_branch.location, session.target_branch.body_location):
        _validate_range(span)
    seen: set[str] = set()
    for index, step in enumerate(session.steps):
        for value in (step.id, step.function.id, step.function.name, step.reason):
            _require_text(value)
        if step.id in seen or step.relation not in {"root", "call", "rte_data", "manual"}:
            raise ValueError("Duplicate step or unsupported investigation relation")
        if index == 0:
            if (step.parent_id is not None or step.relation != "root"
                    or step.function != session.target_function or step.evidence is not None):
                raise ValueError("The first step must represent the original target function")
        elif step.parent_id not in seen or step.relation == "root":
            raise ValueError("Steps must refer to an earlier parent")
        if step.relation in {"call", "rte_data"} and step.evidence is None:
            raise ValueError("Call/RTE investigation steps require an evidence location")
        _validate_range(step.function.location)
        _validate_range(step.function.body_location)
        if step.evidence is not None:
            _validate_range(step.evidence)
        seen.add(step.id)
    if session.current_step_id not in seen:
        raise ValueError("Current step is not part of this session")


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
                         target_function.uncertainty)
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
               uncertainty: tuple[str, ...] = ()) -> TraceStep:
        """Record a user-selected investigation edge, not a proven runtime relation."""
        reasons = tuple(dict.fromkeys((*function.uncertainty, *uncertainty, "user_selected_relation")))
        step = TraceStep(str(uuid4()), self.current_step.id, function, reason, relation,
                         evidence, reasons)
        session = replace(self._session, steps=(*self._session.steps, step), current_step_id=step.id)
        validate_session(session)
        self._session = session
        return step

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
