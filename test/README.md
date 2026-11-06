# 가상 AUTOSAR 다단계 추적 샘플

직접 작성한 AUTOSAR Classic 스타일 코드입니다. 실제 고객사 코드, 생성기 산출물,
AUTOSAR 전체 스택은 사용하지 않습니다. Rte_*.h는 생성 헤더 형태를 흉내 낸 파일이며
support/Rte_Stub.c는 동기식 메모리 버퍼 기반 테스트 대역입니다.

## 목표와 호출 경로

목표: `src/BrakeControl.c`의 `BrakeControl_10ms` 안에 있는
`else if (mode == BRAKE_ASSIST)` 분기를 통과하기.

```text
BrakeControl_10ms
  → EvaluateBrakeMode       #1: mode가 결정되는 이유
  → IsAssistRequested      #2: 보조제동 요청 조건
  → IsSpeedEligible        #3: 속도 자격 조건
  → GetValidatedSpeed      #4: 유효 범위 판정
  → DecodeSpeed            #5: 원시값 변환과 invalid sentinel
  → ReadRawSpeed           #6: 입력값 획득
  → Rte_Read_Speed_Raw         RTE 경계(추가 호출)
```

세 개의 C 파일에 걸친 애플리케이션 함수 7개, 함수 사이 이동 6단계입니다.
조사 중에는 최초 목표를 유지한 채 위 질문을 각 단계의 조사 이유로 기록할 수 있습니다.

## RTE 데이터 경로 (위 호출 경로와 별개)

```text
IoHwAb_ReadSpeedRaw → SensorAcquisition_10ms → Rte_Write_Speed_Raw
                                              ↓ speed_buffer
                                         Rte_Read_Speed_Raw → ReadRawSpeed

IoHwAb_ReadPedalPercent → SensorAcquisition_10ms → Rte_Write_Pedal_Percent
                                                   ↓ pedal_buffer
                                    Rte_Read_Pedal_Percent → IsAssistRequested
```

소비자가 공급자 Runnable을 직접 호출하지 않습니다. 테스트 하네스가 공급자를 먼저
실행한 후 소비자를 실행합니다. 이를 호출 관계와 데이터 의존 관계를 분리하는 예제로 사용합니다.

목표 입력: speed raw=300, pedal=60, 두 RTE read 상태=E_OK.
속도는 정수 나눗셈 `raw / 10`으로 변환되며 30~250 km/h, 페달은 60~100%일 때
목표에 도달합니다. raw=65535, 읽기 실패, 범위 초과는 FAULT입니다.
2509는 250으로 잘리므로 유효하며 2510부터 범위를 초과합니다.

`RAW_TO_KPH(raw)`는 함수처럼 보이는 매크로입니다. tree-sitter 구문만으로
이를 실제 함수 호출로 확정하면 안 됩니다. 현재 검증은 구문 형태만 확인하며,
제품 파서는 별도 tests/test_parser.py에서 매크로 불확실성과 위치를 검증합니다.
RTE 의미 해석 기능은 아직 구현하지 않았습니다.

## 실행

루트에서 다음 명령을 실행합니다.

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
```

Python 테스트는 모든 C/H 구문, 6단계 호출 경로, 목표 else-if 및 중첩 분기,
별도 RTE 공급자, 매크로 구문을 검증합니다. 별도의 C 하네스는 12개 시나리오에서
출력 모드와 쓰기 횟수를 검증합니다. 컴파일 경고는 오류로 처리합니다.
완전한 분기 커버리지 측정이나 실제 ECU 동작 검증을 의미하지 않습니다.

실행 검증에는 C99 컴파일러가 필요합니다. PATH의 Zig/GCC/Clang 또는 이 프로젝트의
`.venv/c-tools/ziglang/zig.exe`를 사용합니다. 없으면 C 실행 테스트만 skip됩니다.
Windows에서 이번에 사용한 테스트 전용 컴파일러 준비 명령:

```powershell
.venv\Scripts\python -m pip install --target .venv/c-tools ziglang==0.15.2
```

오프라인 PC에는 해당 OS용 컴파일러도 미리 준비해야 합니다. 테스트 실행 중 다운로드는
수행하지 않습니다. 빌드 및 캐시는 build/에 저장되며 C/H 입력 파일을 수정하지 않습니다.

| C 시나리오 | raw | pedal | 예상 |
|---|---:|---:|---|
| 목표 경계 | 300 | 60 | ASSIST |
| 속도 미달 | 299 | 60 | NORMAL |
| 페달 미달 | 300 | 59 | NORMAL |
| 속도 상한 | 2500 | 100 | ASSIST |
| 정수 변환 | 2509 | 60 | ASSIST |
| 속도 초과 | 2510 | 60 | FAULT |
| invalid sentinel | 65535 | 60 | FAULT |
| 속도 RTE 실패 | 300 | 60 | FAULT |
| 페달 RTE 실패 | 300 | 60 | FAULT |
| 페달 초과 | 300 | 101 | FAULT |
| 초기값 | 0 | 0 | NORMAL |
| 공급자 실행 전/후 | 300 | 60 | NORMAL → ASSIST |

## 이번 검증 결과 (2026-11-06)

- Windows x64 / Python 3.14.3 / Zig 0.15.2의 C 컴파일러 사용.
- `-std=c99 -Wall -Wextra -Werror -pedantic` 컴파일 및 실행 성공.
- Python 테스트 10개 통과(환경 4개, 샘플 구문·구조 5개, C 실행 1개), skip 없음.
- C 하네스 시나리오 12개 모두 통과.
- Codex 샌드박스에서는 컴파일러 파일 접근 오류가 발생하여 동일 명령을
  권한 제한 밖에서 실행해 검증했다. 코드나 테스트 조건을 완화하지 않았다.
