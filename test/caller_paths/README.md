# 매개변수에서 호출자로 거슬러 가는 예시

독립 합성 구문 샘플이다. `Callers.c`의 `Caller_Check` 안에서 `pedal`을 선택한다.

```text
pedal (두 번째 매개변수)
  <- Caller_Relay: Caller_Check(999u, command)
     <- command <- Caller_Run: Caller_Relay(amount)
        <- amount = Caller_Raw * 2u
        조건: Caller_Enable != 0u 참 필요
  <- Caller_Alternate: Caller_Check(0u, Caller_AlternateRaw + 10u)
  <- Caller_Literal: Caller_Check(7u, 65u)
  <- Caller_FromFunction: Caller_Check(123u, Caller_GetRaw())
     <- Caller_GetRaw 반환값 <- Caller_Raw
```

변수명이 달라도 인수 순서로 대응한다. 첫 번째 인수 999/0/7/123은 pedal의 출처가 아니다.
여러 호출부는 별도 후보이며 실제 호출 맥락은 확정하지 않는다.
함수 포인터·매크로·실행 가능성/CT 제어를 검증하는 실행 샘플은 아니다.
Python 회귀는 tests/test_value_graph.py, 흐름 선택/표시는 확장 단위와 Host에서 검증한다.

함수 반환값을 인수로 전달하는 경우, 전달한 호출부 Caller_FromFunction과 반환값 제공 함수 Caller_GetRaw를 구분해서 표시한다.
