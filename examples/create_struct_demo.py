"""Create fictional structure/member/pointer investigations for this checkout."""

import argparse
from dataclasses import replace
from pathlib import Path

from autosar_trace_navigator.storage import TraceStore
from autosar_trace_navigator.trace import TraceSession
from autosar_trace_navigator.workbench import Workbench, analyze_project


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "test/struct_paths"
SCOPE = ("consumer.c", "producer.c", "rte_stub.c", "struct_paths.h", "Rte_StructPaths.h")
SESSION_IDS = ("struct-01-a-through-rte", "struct-02-pointer-member", "struct-03-global-object")


def start_struct_investigation(function_name: str, expression: str) -> Workbench:
    """Start the selected sample threshold branch without modifying any source."""
    workbench = Workbench()
    workbench.project = analyze_project(SAMPLE, include_paths=SCOPE)
    function, = workbench.project.functions_by_name[function_name]
    branch, = (b for result in workbench.project.results for b in result.branches
               if b.function_id == function.id and b.condition and expression + " >=" in b.condition)
    workbench.start(function.id, branch.id, f"{expression} → 60을 위한 객체와 멤버 출처 조사")
    workbench.set_variable_goal(expression, "60", branch.location)
    return workbench


def follow_source(workbench: Workbench, kind: str, expression: str | None = None,
                  reason: str = "같은 객체와 멤버의 공급 근거 확인") -> None:
    """Follow one explicitly identified demo candidate, refusing changed/ambiguous fixtures."""
    candidate, = (c for c in workbench.value_candidates() if c.value_kind == kind
                  and (expression is None or c.probe is not None and c.probe.expression == expression))
    workbench.follow(candidate, reason)


def _trace_supply(workbench: Workbench) -> None:
    for kind in ("rte_data", "return_value", "return", "output_parameter", "return_value", "return", "output_parameter"):
        follow_source(workbench, kind)
    follow_source(workbench, "expression_operand", "Struct_RawInput",
                  "입력 계획(사람 검토): RawInput=25이면 25*2+10=60. 이 쓰기의 EnableInput 조건도 조사")


def _enable_branch(workbench: Workbench) -> None:
    calculation = workbench.session.current_step_id
    follow_source(workbench, "ct_global_input", reason="RawInput=25 제어 후보. CT 접근성과 초기화 시점 확인 필요")
    workbench.select(calculation)
    condition, = (c for c in workbench.execution_candidates() if c.probe and c.probe.expression == "Struct_EnableInput")
    workbench.follow(condition, "out->a 계산을 실행하려면 EnableInput==1 필요")
    follow_source(workbench, "ct_global_input", reason="입력 계획 EnableInput=1. RTE 읽기 성공과 공급자 선행 실행도 확인")
    workbench.select(calculation)


def create_struct_database(output: Path) -> tuple[TraceSession, ...]:
    """Write three new sample sessions with local absolute locations; never overwrite a DB."""
    output = output.resolve()
    if output.suffix.lower() not in {".sqlite3", ".db"}:
        raise ValueError("출력은 .sqlite3 또는 .db여야 합니다.")
    if output.exists():
        raise FileExistsError(f"기존 파일은 덮어쓰지 않습니다: {output}")
    ordinary = start_struct_investigation("Struct_Consume", "a")
    follow_source(ordinary, "assignment", "b.a", "a의 공급 식 b.a에서 구조체 객체와 같은 멤버를 함께 조사")
    local_object = ordinary.session.current_step_id
    _trace_supply(ordinary)
    _enable_branch(ordinary)
    calculation = ordinary.session.current_step_id
    ordinary.select(local_object)
    follow_source(ordinary, "object_origin", reason="b 객체 자체의 출처도 확인. 로컬 객체이므로 실제 값 준비는 RTE 공급 경로에서 조사")
    ordinary.select(calculation)

    pointer = start_struct_investigation("Struct_ConsumePointer", "p->a")
    follow_source(pointer, "parameter_input", "local.a", "호출자의 &local로 포인터 대상 후보를 찾고 같은 a 멤버를 유지")
    _trace_supply(pointer)
    _enable_branch(pointer)

    global_object = start_struct_investigation("Struct_ConsumeGlobal", "Struct_ExternalState.a")
    follow_source(global_object, "object_origin", reason="멤버 a를 가진 외부 전역 객체 자체를 찾아 CT 접근성 확인")
    follow_source(global_object, "ct_global_input",
                  reason="객체 제어 후보: Struct_ExternalState.a=60 준비를 검토. 전체 구조체 배치·다른 멤버·CT 접근성은 별도 확인")
    sessions = tuple(replace(w.session, id=session_id) for w, session_id in
                     zip((ordinary, pointer, global_object), SESSION_IDS))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb"):
        pass
    with TraceStore(output) as store:
        for session in sessions:
            store.save(session)
    return sessions


def main() -> None:
    """Generate the DB used by the Korean structure walkthrough."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/struct_tutorial.sqlite3")
    args = parser.parse_args()
    try:
        sessions = create_struct_database(args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"구조체 예제 DB: {args.output.resolve()}")
    for session in sessions:
        print(f"  {session.id}: {len(session.steps)} steps")


if __name__ == "__main__":
    main()
