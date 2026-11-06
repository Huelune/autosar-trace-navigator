"""UI-independent project snapshots and investigation actions."""

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from collections.abc import Iterable, Mapping
from collections import defaultdict
from types import MappingProxyType

from .models import FunctionCall, FunctionDefinition, ParseResult, SourceRange, ValueProbe
from .dataflow import ValueResolver
from .parser import parse_source
from .rte import RteAccess, RteDataDependency, RteResolution, inspect_rte_header, resolve_rte
from .scanner import scan_sources
from .storage import TraceStore
from .trace import TraceManager, TraceSession


@dataclass(frozen=True)
class ProjectSnapshot:
    root: Path
    sources: tuple[tuple[Path, bytes], ...]
    results: tuple[ParseResult, ...]
    rte: RteResolution
    scope: tuple[Path, ...] = ()

    @cached_property
    def value_resolver(self) -> ValueResolver:
        return ValueResolver(self)

    @cached_property
    def functions(self) -> tuple[FunctionDefinition, ...]:
        return tuple(function for result in self.results for function in result.functions)

    @cached_property
    def functions_by_id(self) -> Mapping[str, FunctionDefinition]:
        return MappingProxyType({function.id: function for function in self.functions})

    @cached_property
    def functions_by_name(self) -> Mapping[str, tuple[FunctionDefinition, ...]]:
        index = defaultdict(list)
        for function in self.functions:
            index[function.name].append(function)
        return MappingProxyType({name: tuple(items) for name, items in index.items()})

    @cached_property
    def calls_by_owner(self) -> Mapping[str | None, tuple[FunctionCall, ...]]:
        index = defaultdict(list)
        for result in self.results:
            for call in result.calls:
                index[call.caller_id].append(call)
        return MappingProxyType({owner: tuple(items) for owner, items in index.items()})

    @cached_property
    def rte_by_owner(self) -> Mapping[str | None, tuple[tuple[RteAccess, RteDataDependency], ...]]:
        by_id = {access.id: access for access in self.rte.accesses}
        index = defaultdict(list)
        for dependency in self.rte.dependencies:
            read = by_id[dependency.consumer_access_id]
            write = by_id[dependency.producer_access_id]
            index[read.function_id].append((write, dependency))
        return MappingProxyType({owner: tuple(items) for owner, items in index.items()})

    @cached_property
    def search_index(self) -> tuple[tuple[FunctionDefinition, str], ...]:
        return tuple((function, f"{function.name} {function.location.path.relative_to(self.root).as_posix()}".casefold())
                     for function in self.functions)

    def search_functions(self, query: str, *, offset: int = 0, limit: int = 100) -> "FunctionPage":
        """Explicit token search by name/path; never materialize all matching rows."""
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 500:
            raise ValueError("Invalid search page: offset >= 0 and 1 <= limit <= 500 required")
        tokens = query.casefold().split()
        matches = []
        total = 0
        if tokens:
            for function, searchable in self.search_index:
                if all(token in searchable for token in tokens):
                    if offset <= total < offset + limit:
                        matches.append(function)
                    total += 1
        return FunctionPage(tuple(matches), total, offset, limit)


@dataclass(frozen=True)
class FunctionPage:
    functions: tuple[FunctionDefinition, ...]
    total: int
    offset: int
    limit: int


class AnalysisLimitError(ValueError):
    """The chosen scope exceeds an explicit workload budget; no partial result returned."""


@dataclass(frozen=True)
class InvestigationCandidate:
    function: FunctionDefinition | None
    label: str
    relation: str
    evidence: SourceRange
    uncertainty: tuple[str, ...]
    probe: ValueProbe | None = None
    selected_location: SourceRange | None = None
    value_kind: str | None = None


def analyze_project(root: str | Path, *, exclude_paths: Iterable[str | Path] = (),
                    include_paths: Iterable[str | Path] = (), max_files: int = 500,
                    max_source_bytes: int = 32 * 1024 * 1024,
                    max_file_bytes: int = 4 * 1024 * 1024) -> ProjectSnapshot:
    """Read each source once so parser, header inspector and preview use the same bytes."""
    base = Path(root).resolve(strict=True)
    if any(type(value) is not int or value < 1 for value in (max_files, max_source_bytes, max_file_bytes)):
        raise ValueError("Analysis budgets must be positive integers")
    includes = tuple(include_paths)
    sources = scan_sources(base, exclude_paths=exclude_paths, include_paths=includes)
    if len(sources) > max_files:
        raise AnalysisLimitError(f"선택 범위에 파일 {len(sources)}개: 제한 {max_files}개. 분석 범위를 줄이세요.")
    snapshots = []
    size = 0
    for source in sources:
        remaining = min(max_file_bytes, max_source_bytes - size)
        with source.path.open("rb") as stream:
            data = stream.read(remaining + 1)
        if len(data) > remaining:
            raise AnalysisLimitError("선택 범위의 소스 크기 제한을 초과했습니다. 분석 범위를 줄이세요.")
        size += len(data)
        snapshots.append((source.path, data))
    snapshots = tuple(snapshots)
    results = tuple(parse_source(data, path=path) for path, data in snapshots)
    rte_paths = {source.path for source in sources if source.is_rte_header}
    headers = tuple(inspect_rte_header(data, path=path) for path, data in snapshots if path in rte_paths)
    scope = tuple(sorted({(base / path).resolve() for path in includes}, key=lambda p: p.as_posix())) or (base,)
    return ProjectSnapshot(base, snapshots, results, resolve_rte(results, headers=headers), scope)


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
        if self.project.functions_by_id.get(current.id) != current:
            return ()
        candidates = []
        for call in self.project.calls_by_owner.get(current.id, ()):
            matches = self.project.functions_by_name.get(call.callee_name, ()) if call.kind == "direct_candidate" else ()
            reasons = (*call.uncertainty, "name_only_call_candidate")
            if not matches:
                reasons += ("not_resolved_in_analysis_scope",)
            if len(matches) > 1:
                reasons += ("multiple_function_candidates",)
            for function in matches or [None]:
                candidates.append(InvestigationCandidate(
                    function, call.callee_expression, "call", call.location, reasons))
        for write, dependency in self.project.rte_by_owner.get(current.id, ()):
            candidates.append(InvestigationCandidate(
                self.project.functions_by_id.get(write.function_id), dependency.channel, "rte_data",
                write.location, dependency.uncertainty))
        return tuple(candidates)

    def follow(self, candidate: InvestigationCandidate, reason: str) -> None:
        if (self.manager is None or candidate.function is None
                or candidate not in (*self.candidates(), *self.value_candidates())):
            raise ValueError("조사할 함수가 확인되지 않았거나 현재 단계의 후보가 아닙니다.")
        self.manager.follow(candidate.function, reason=reason, relation=candidate.relation,
                            evidence=candidate.evidence, uncertainty=candidate.uncertainty,
                            probe=candidate.probe, selected_location=candidate.selected_location)
        self.dirty = True

    def value_candidates(self) -> tuple[InvestigationCandidate, ...]:
        if self.manager is None or self.project is None or self.manager.current_step.probe is None:
            return ()
        step = self.manager.current_step
        if self.project.functions_by_id.get(step.function.id) != step.function:
            return ()
        sources = self.project.value_resolver.sources(step.probe)
        return tuple(InvestigationCandidate(
            self.project.functions_by_id.get(source.function_id), f"{source.kind}: {source.expression}",
            "rte_data" if "name_only_connection" in source.uncertainty else "value", source.location,
            source.uncertainty, source.next_probe,
            source.next_probe.location if source.next_probe else source.location, source.kind)
            for source in sources)

    def set_variable_goal(self, variable: str, target_value: str, location: SourceRange) -> None:
        self.session
        self.manager.set_variable_goal(variable, target_value, location)
        self.dirty = True

    def inspect_variable(self, variable: str, location: SourceRange) -> None:
        self.session
        self.manager.inspect_variable(variable, location)
        self.dirty = True

    def record_location(self, location: SourceRange) -> None:
        self.session
        self.manager.record_location(location)
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
