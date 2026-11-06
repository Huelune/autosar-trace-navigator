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

## SQLite 저장·복원

위 예제의 manager를 명시적으로 저장한다. 시작·이동 시 자동 저장은 하지 않는다.

```python
from autosar_trace_navigator.storage import TraceStore

with TraceStore("investigation.sqlite3") as store:
    revision = store.save(manager.session)  # 새 세션, revision=1
    session_id = manager.session.id

with TraceStore("investigation.sqlite3") as store:
    saved = store.load(session_id)
    manager = TraceManager(saved.session)
    # 현재 위치 변경 또는 조사 단계를 추가한 후:
    revision = store.save(manager.session, expected_revision=saved.revision)
    print(store.list_sessions())
```

- `.sqlite3`, `.db` 또는 `:memory:`를 받는다. 부모 폴더는 미리 만들어야 한다.
- DB는 application_id와 schema version으로 식별한다. 세션 ID·리비전·JSON
  스냅샷을 한 행에 저장하며 C/H 본문이나 전체 파싱 인덱스는 저장하지 않는다.
- 목표, 버려진 대안 경로, 현재 커서, 소스 위치, 조사 이유, 불확실성을 복원한다.
  복원은 원본 파일을 다시 열지 않는다. 실제 코드 변경 여부는 별도로 확인해야 한다.
- `save(session)`은 새 세션만 삽입한다. 갱신은 `expected_revision`이 필요하며,
  다른 저장자가 먼저 갱신했거나 세션이 없으면 TraceConflictError가 발생한다.
  충돌 시 자동 덮어쓰기·재시도는 하지 않는다. 최신 내용을 불러와 조사자가 병합한다.
- 저장은 트랜잭션으로 수행한다. 실패 시 이전 행과 다른 세션은 보존된다.
- 미지원 버전이나 다른 DB는 초기화·마이그레이션하지 않는다. 손상된 스냅샷은
  ValueError, 없는 세션은 KeyError, SQLite 입출력 오류는 SQLite 예외로 전달한다.
- `with`를 쓰거나 `close()`로 연결을 닫는다. import만으로 DB를 생성하지 않는다.
- 근거 위치는 사용자가 지정한 조사 근거이며 자동 심볼/RTE 해석을 의미하지 않는다.
