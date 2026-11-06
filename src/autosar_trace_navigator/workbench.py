"""UI-independent project snapshots and investigation actions."""

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterable

from .models import FunctionDefinition, ParseResult, SourceRange
from .parser import parse_source
from .rte import RteResolution, inspect_rte_header, resolve_rte
from .scanner import scan_sources
from .storage import TraceStore
from .trace import TraceManager, TraceSession


@dataclass(frozen=True)
class ProjectSnapshot:
    root: Path
    sources: tuple[tuple[Path, bytes], ...]
    results: tuple[ParseResult, ...]
    rte: RteResolution

    @property
    def functions(self) -> tuple[FunctionDefinition, ...]:
        return tuple(function for result in self.results for function in result.functions)


@dataclass(frozen=True)
class InvestigationCandidate:
    function: FunctionDefinition | None
    label: str
    relation: str
    evidence: SourceRange
    uncertainty: tuple[str, ...]


def analyze_project(root: str | Path, *, exclude_paths: Iterable[str | Path] = ()) -> ProjectSnapshot:
    """Read each source once so parser, header inspector and preview use the same bytes."""
    base = Path(root).resolve(strict=True)
    sources = scan_sources(base, exclude_paths=exclude_paths)
    snapshots = tuple((source.path, source.path.read_bytes()) for source in sources)
    results = tuple(parse_source(data, path=path) for path, data in snapshots)
    rte_paths = {source.path for source in sources if source.is_rte_header}
    headers = tuple(inspect_rte_header(data, path=path) for path, data in snapshots if path in rte_paths)
    return ProjectSnapshot(base, snapshots, results, resolve_rte(results, headers=headers))


class Workbench:
    """Keep save metadata unchanged on failure; candidate selection never resolves symbols."""

    def __init__(self) -> None:
        self.project: ProjectSnapshot | None = None
        self.manager: TraceManager | None = None
        self.database: Path | None = None
        self.revision: int | None = None
        self.dirty = False
        self.restored = False

    @property
    def session(self) -> TraceSession:
        if self.manager is None:
            raise ValueError("먼저 목표 분기를 선택해 조사를 시작하세요.")
        return self.manager.session

    def start(self, function_id: str, branch_id: str, reason: str) -> None:
        if self.project is None:
            raise ValueError("먼저 소스 폴더를 분석하세요.")
        function = next((f for f in self.project.functions if f.id == function_id), None)
        branch = next((b for r in self.project.results for b in r.branches if b.id == branch_id), None)
        if function is None or branch is None:
            raise ValueError("현재 분석에서 목표 함수와 분기를 찾지 못했습니다.")
        manager = TraceManager.start(function, branch, reason=reason)
        self.manager = manager
        self.database = None
        self.revision = None
        self.restored = False
        self.dirty = True

    def candidates(self) -> tuple[InvestigationCandidate, ...]:
        if self.manager is None or self.project is None:
            return ()
        current = self.manager.current_step.function
        if current not in self.project.functions:
            return ()
        candidates = []
        for result in self.project.results:
            for call in result.calls:
                if call.caller_id != current.id:
                    continue
                matches = [f for f in self.project.functions if f.name == call.callee_name]
                if call.kind != "direct_candidate":
                    matches = []
                reasons = (*call.uncertainty, "name_only_call_candidate")
                if len(matches) > 1:
                    reasons += ("multiple_function_candidates",)
                for function in matches or [None]:
                    candidates.append(InvestigationCandidate(
                        function, call.callee_expression, "call", call.location, reasons))
        by_id = {access.id: access for access in self.project.rte.accesses}
        by_function = {function.id: function for function in self.project.functions}
        for dependency in self.project.rte.dependencies:
            read = by_id[dependency.consumer_access_id]
            if read.function_id == current.id:
                write = by_id[dependency.producer_access_id]
                candidates.append(InvestigationCandidate(
                    by_function.get(write.function_id), dependency.channel, "rte_data",
                    write.location, dependency.uncertainty))
        return tuple(candidates)

    def follow(self, candidate: InvestigationCandidate, reason: str) -> None:
        if self.manager is None or candidate not in self.candidates() or candidate.function is None:
            raise ValueError("조사할 함수가 확인되지 않았거나 현재 단계의 후보가 아닙니다.")
        self.manager.follow(candidate.function, reason=reason, relation=candidate.relation,
                            evidence=candidate.evidence, uncertainty=candidate.uncertainty)
        self.dirty = True

    def back(self) -> None:
        self.session
        self.manager.back()
        self.dirty = True

    def select(self, step_id: str) -> None:
        old = self.session.current_step_id
        self.manager.select(step_id)
        self.dirty = self.dirty or old != step_id

    def save(self, path: str | Path) -> None:
        session = self.session
        database = Path(path).resolve()
        expected = self.revision if database == self.database else None
        with TraceStore(database) as store:
            revision = store.save(session, expected_revision=expected)
        self.database, self.revision, self.dirty = database, revision, False

    def restore(self, path: str | Path, session_id: str) -> None:
        database = Path(path).resolve(strict=True)
        with TraceStore(database) as store:
            saved = store.load(session_id)
        manager = TraceManager(saved.session)
        self.manager = manager
        self.database, self.revision = database, saved.revision
        self.dirty, self.restored = False, True
