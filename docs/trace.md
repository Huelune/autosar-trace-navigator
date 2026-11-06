# Trace Manager

GUI 없이 목표 분기와 조사 경로를 기록하는 API다. 소스 파일은 수정하지 않으며,
호출 대상 또는 RTE 공급자를 자동으로 찾거나 실행 가능성을 판정하지 않는다.

```python
from autosar_trace_navigator.parser import parse_file
from autosar_trace_navigator.trace import TraceManager

result = parse_file("test/src/BrakeControl.c")
entry = next(f for f in result.functions if f.name == "BrakeControl_10ms")
target = next(b for b in result.branches if b.condition == "(mode == BRAKE_ASSIST)")
manager = TraceManager.start(entry, target, reason="보조제동 분기 조건 조사")
callee = next(f for f in result.functions if f.name == "EvaluateBrakeMode")
call = next(c for c in result.calls if c.callee_name == callee.name)
manager.follow(callee, reason="mode의 계산 조건 확인", relation="call",
               evidence=call.location, uncertainty=call.uncertainty)
print(manager.session.target_branch.condition)
print([(s.function.name, s.reason) for s in manager.current_path])
manager.back()
```

- 세션의 최초 목표 함수와 분기는 수정하지 않고 불변 스냅샷으로 유지한다.
- `current_path`는 최초 목표에서 현재 단계까지의 경로다.
  `session.steps`는 되돌아가기 전 경로와 대안 경로까지 생성 순서로 보존한다.
- `follow`는 현재 단계의 자식 단계를 생성하며 조사 이유를 필수로 받는다.
  `call`, `rte_data`는 근거 위치도 필수다. `manual`은 일반 조사 이동이다.
  이 구분은 조사자가 선택한 관계이며 실제 데이터 의존성을 확정하는 것이 아니다.
- 반복 함수 조사도 허용하며 단계 ID를 별도로 부여한다. 경로에 순환 참조는 없다.
- `select(step_id)`는 기록된 어느 단계로든 이동한다. 최초 단계의 `back()`이나
  잘못된 이동·빈 이유는 ValueError이며 기존 상태는 변경하지 않는다.
- 사용자 선택으로 추가한 단계에는 `user_selected_relation`을 기록하고 파서 및
  호출부에서 전달한 불확실성도 유지한다.
- 스냅샷은 함수·분기 메타데이터와 위치이며 원본 전체 코드를 복사하지 않는다.
  파일 수정 후 위치가 유효한지 자동으로 확인하거나 재연결하지 않는다.
