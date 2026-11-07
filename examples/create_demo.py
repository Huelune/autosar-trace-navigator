"""Create a new tutorial DB using public analysis/trace APIs and fictional sources."""

import argparse
from dataclasses import replace
from pathlib import Path

from autosar_trace_navigator.storage import TraceStore
from autosar_trace_navigator.trace import TraceManager, TraceSession
from autosar_trace_navigator.workbench import ProjectSnapshot, Workbench, analyze_project


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "test/value_paths"
SESSION_IDS = ("example-01-ct-global", "example-02-nested-conditions")


def _start(project: ProjectSnapshot, session_id: str, reason: str) -> Workbench:
    workbench = Workbench()
    workbench.project = project
    function, = project.functions_by_name["ValuePath_Consume"]
    branch, = (b for result in project.results for b in result.branches if b.function_id == function.id)
    workbench.start(function.id, branch.id, reason)
    workbench.set_variable_goal("pedal", "60", branch.location)
    workbench.manager = TraceManager(replace(workbench.session, id=session_id))
    return workbench


def _value(workbench: Workbench, kind: str, reason: str, expression: str | None = None) -> None:
    candidate, = (c for c in workbench.value_candidates() if c.value_kind == kind
                  and (expression is None or c.label == f"{kind}: {expression}"))
    workbench.follow(candidate, reason)


def _condition(workbench: Workbench, variable: str, expression: str, reason: str) -> None:
    candidate, = (c for c in workbench.execution_candidates()
                  if c.probe and c.probe.expression == variable
                  and f"execution_requirement_true: {expression}" in c.uncertainty)
    workbench.follow(candidate, reason)


def _calculation(workbench: Workbench) -> str:
    _value(workbench, "rte_data", "pedal의 RTE 공급 값 next가 어디서 만들어지는지 확인")
    _value(workbench, "expression_operand", "next = RawInput * 2 + 10 계산의 입력 조사",
           "ValuePath_RawInput")
    return workbench.session.current_step_id


def create_demo_database(output: Path) -> tuple[TraceSession, ...]:
    """Write two reviewable sessions to a new DB; never overwrite an existing file."""
    output = output.resolve()
    if output.suffix.lower() not in {".sqlite3", ".db"}:
        raise ValueError("출력은 .sqlite3 또는 .db여야 합니다.")
    if output.exists():
        raise FileExistsError(f"기존 DB는 덮어쓰지 않습니다. 새 파일 이름을 지정하세요: {output}")
    project = analyze_project(SAMPLE, include_paths=("value_paths.c", "value_paths.h"))
    direct = _start(project, SESSION_IDS[0], "예제 01: pedal ≥ 60을 위한 CT 전역 입력 후보 찾기")
    _calculation(direct)
    _value(direct, "ct_global_input",
           "사람이 검토한 입력 계획: ValuePath_RawInput=25 → 25*2+10=60. CT 접근성 별도 확인")

    nested = _start(project, SESSION_IDS[1], "예제 02: 계산과 중첩 조건 조사. 입력 계획 Raw=25, Mode=2, Enable=1")
    calculation = _calculation(nested)
    _value(nested, "ct_global_input", "RawInput=25 입력 계획. 다른 실행 조건은 계산 지점에서 별도 조사")
    nested.select(calculation)
    _condition(nested, "value_path_permit", "(value_path_permit != 0u)",
               "계산에 permit가 필요. static이므로 직접 CT 제어 대신 쓰기 지점 조사")
    _value(nested, "constant", "permit를 1로 만드는 쓰기가 다른 분기 안에 있어 그 조건 조사", "1u")
    _condition(nested, "ValuePath_EnableInput", "(ValuePath_EnableInput == 1u)",
               "permit=1 쓰기를 실행하려면 EnableInput==1이 필요")
    _value(nested, "ct_global_input", "입력 계획: ValuePath_EnableInput=1. PreparePermit 실행 필요. CT 접근성 별도 확인")
    nested.select(calculation)
    _condition(nested, "ValuePath_ModeInput", "(ValuePath_ModeInput == 2u)",
               "별도 조건 조사: Mode==0은 거짓, Mode==2는 참이어야 계산 분기로 진입")
    _value(nested, "ct_global_input", "입력 계획: ValuePath_ModeInput=2. 실제 실행은 PreparePermit → Produce → Consume")
    nested.select(calculation)
    sessions = (direct.session, nested.session)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb"):  # Also refuse a file created since the initial existence check.
        pass
    with TraceStore(output) as store:
        for session in sessions:
            store.save(session)
    return sessions


def main() -> None:
    """Generate the tutorial for this checkout so absolute source locations match."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/tutorial.sqlite3",
                        help="새 DB 경로 (기본: build/tutorial.sqlite3, 기존 파일 덮어쓰기 금지)")
    args = parser.parse_args()
    try:
        sessions = create_demo_database(args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"예제 DB: {args.output.resolve()}")
    for session in sessions:
        print(f"  {session.id}: {len(session.steps)}단계 / {session.steps[0].reason}")


if __name__ == "__main__":
    main()
