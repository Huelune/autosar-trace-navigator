# 계산과 실행 조건을 따로 조사하는 가상 사례

GUI 루트를 이 폴더로 선택하고 `value_paths.c;value_paths.h`를 분석한다.
`ValuePath_Consume`의 분기를 목표로 시작하고 변수 `pedal`, 최초 목표값 `60`을 지정한다.
C 코드에는 `60` 리터럴이 없다. `VALUE_PATH_TARGET` 매크로도 도구가 확장하지 않는다.

1. 값 출처의 RTE 공급 후보를 따라 ValuePath_Produce의 `next`를 조사한다.
2. `ValuePath_RawInput * 2u + 10u` 계산식의 피연산자 RawInput을 선택한다.
3. 외부 연결 이름의 전역 RawInput은 **CT 전역 제어 후보**다. 빌드·CT에서 접근 가능한지는 확인해야 한다.
4. 계산 지점의 **실행 조건**에서 ModeInput 조건과 내부 permit 조건을 별도로 조사한다.
   else-if에 도달하려면 앞의 `ModeInput == 0u`는 거짓, 현재 `ModeInput == 2u`는 참이어야 한다.
5. permit은 static이므로 CT 제어 후보가 아니다. `permit = 1u` 쓰기 후보로 이동하면
   이를 실행하는 `EnableInput == 1u` 분기를 다시 조사할 수 있다.
6. EnableInput 전역 후보까지 조사한 뒤 이력에서 계산 지점으로 돌아가 ModeInput도 조사한다.
   조사 트리의 다른 자식 경로로 보존되며 실제 호출·실행 순서를 나타내지 않는다.

다음 값은 수식을 사람이 검토하여 정한 가상 CT 입력 구성이다. 도구가 자동 역산한 값은 아니다.

| CT 제어 후보 | 입력 예 | 목적 |
|---|---:|---|
| ValuePath_RawInput | 25 | 25 × 2 + 10으로 목표값 생성 |
| ValuePath_ModeInput | 2 | 계산이 있는 else-if 진입 |
| ValuePath_EnableInput | 1 | static permit을 설정하는 분기 진입 |

하네스는 permit 준비 → 공급자 → 소비자 순서로 실행한다. 6개 시나리오는
위 구성의 성공, RawInput 부족, EnableInput 불충족, ModeInput의 두 불충족 값과
임계값 초과를 각각 확인한다. 실제 CT 연결이나 ECU 실행을 검증하는 코드는 아니다.
