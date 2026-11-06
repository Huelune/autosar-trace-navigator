# 확장 가상 AUTOSAR 샘플

`test/large_autosar/`는 기존 보조제동 샘플과 별개의 독립 C99 프로젝트다.

| 항목 | 기본 샘플 |
|---|---:|
| 가상 SWC | 24 |
| C 파일 / H 파일 | 122 / 49 |
| 파서가 추출한 함수 정의 | 424 |
| if/else-if/else 분기 | 665 |
| RTE 접근 / 데이터 연결 후보 | 172 / 52 |
| 실제 실행한 C 시나리오 | 192 |

함수 정의 수에는 전처리 대안도 포함된다. 고객 코드, 실제 ECU 또는 벤더 생성물은 아니다.
Brake·Steering·Battery 등의 이름은 탐색 연습용이며 실제 각 도메인의 제어 동작을 구현하지 않는다.

## GUI에서 조사하기

1. 루트를 `test/large_autosar/`로 선택한다.
2. 범위는 `swc/Brake_000;shared`를 입력하고 선택 범위 분석을 누른다(8개 C/H).
3. `Brake_000_10ms`를 검색하고 `(mode == MODE_ACTIVE)` else-if를 목표로 시작한다.
4. Evaluate → Decide → Eligible → Validated → Decode → Read를 따라간다.
5. RTE 탭에서 Brake_000_Signal_Raw 공급자 후보를 확인한다.

모듈별 threshold는 manifest.json에 있으며 목표 입력은 raw=threshold×10,
demand=60, 두 RTE read 상태=E_OK다. 공급자 Runnable을 먼저 실행해야 버퍼에 입력이 전달된다.

Control/Decision/Signal만 범위에 넣으면 공급자가 미확인이다. Producer.c를 범위에
추가하면 공급자 후보가 생기며 원래 목표·경로는 유지된다. Brake_000에는 백업
쓰기 지점도 있어 공급자 후보가 둘이다. 실제 선택·실행 순서는 자동 확정하지 않는다.

`swc;shared`로 넓히면 다른 모듈의 동명 static Normalize 24개가 이름 기반 후보로
나타난다. C 언어에서는 별도 번역 단위의 static 함수가 구분되지만 현재 도구는
이를 확정 연결하지 않으므로 불확실성을 검토하는 사례다.

일부 Rte_*.h의 Read API는 함수 형태 매크로나 객체 형태 alias다. 일부 진단 코드는
조건부 대안을, 진단 함수는 switch·loop 내부 if·else-if를 포함한다.
Rte_Impl_*는 현재 Resolver의 지원 범위 밖이므로 헤더 진단이 나오는 것은 의도적이다.

## 새 변형 생성

```powershell
.venv\Scripts\python test\generate_large_autosar.py --output build\autosar_80_swc --components 80
```

출력 폴더는 존재하지 않아야 한다. 생성기는 기존 C/H를 덮어쓰지 않는다.
1~256 SWC를 지원하고 같은 옵션의 텍스트 내용은 재현된다(경로·타임스탬프를 삽입하지 않음).
80 SWC 변형은 563파일로 기본 500파일 제한을 넘는다. 전체 `.`은 거부되고
`swc/Brake_000;shared` 같은 선택 범위로는 분석할 수 있다.

## 검증

```powershell
.venv\Scripts\python -m unittest discover -s tests -p test_large_autosar.py -v
```

9개 테스트가 구조·각 SWC의 6단계 경로·동명/조건부 함수·RTE 모호성·검색 페이지·
범위 확장 후 세션 저장/복원·생성기 재현성·덮어쓰기 거부·80 SWC 예산 제한·
C 컴파일 및 실행을 검증한다. 원본 fixture의 해시와 수정 시각 불변도 검사한다.

C 122개를 `-std=c99 -Wall -Wextra -Werror -pedantic`으로 함께 컴파일하고,
24 SWC마다 목표 경계·신호 미달·요청 미달·신호 범위 초과·invalid sentinel·요청 범위 초과·
신호 읽기 실패·요청 읽기 실패 8개씩 192개 시나리오의 모드와 출력 횟수를 확인했다.
Zig의 샌드박스 접근 오류가 발생해 전체 검증은 일반 실행 환경에서 완료했다.

80 SWC 변형은 생성·예산 거부·범위 분석만 검증했으며 해당 변형의 C 전체 실행은 하지 않았다.
수백만 줄 프로젝트의 성능 보장이나 실차·전체 분기 커버리지 검증을 뜻하지 않는다.
