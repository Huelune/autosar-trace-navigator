# 구조체와 RTE 출력 인수의 가상 AUTOSAR 코드

직접 작성한 독립 샘플이다. 실제 고객사 소스나 생성된 RTE 구현을 사용하지 않는다.
`Rte_StructPaths.h`와 `rte_stub.c`는 테스트용 인터페이스와 메모리 스텁이다.

| 파일 | 역할 |
|---|---|
| struct_paths.h | 구조체와 외부 제어 입력 선언 |
| Rte_StructPaths.h | 전체 객체·단일 멤버의 Read/Write 선언 |
| producer.c | 5개 함수의 생성 경로, 조건부 멤버 계산과 RTE 공급 |
| consumer.c | 일반 변수·포인터 멤버·멤버 출력 인수·전역 객체 소비 |
| rte_stub.c | 읽기 상태 및 객체·멤버의 테스트 버퍼 |
| harness.c | 값·실행 조건·읽기 실패를 바꾸는 6개 실행 시나리오 |

`Struct_Consume → Struct_Produce → Struct_BuildState → Struct_Fill → Struct_MakeState → Struct_SetMember`의
6개 함수에 걸쳐 값 공급 근거를 조사한다. 소비자와 공급자 사이는 RTE 데이터 후보이며 호출 관계가 아니다.
`a = b.a`, `Rte_Read_Struct_State(&b)`, `Rte_Read_Struct_A(&b.a)`,
`Struct_ConsumePointer(&local)`, `*out = Struct_MakeState()` 형태를 포함한다.

목표는 a 또는 멤버 a의 값 60이다. 실제 계산은 `Struct_RawInput * 2u + 10u`이며
`Struct_EnableInput == 1u` 안에서 실행된다. 입력 계획 RawInput=25, EnableInput=1, ReadStatus=0과
공급자 선행 실행은 사람이 확인한 계획이다. 정적 도구가 자동으로 제약을 풀었다는 뜻은 아니다.

GUI 분석에는 이 폴더를 루트로 아래 5개 파일만 지정한다.

```text
struct_paths.h;Rte_StructPaths.h;producer.c;consumer.c;rte_stub.c
```

하네스는 별도 실행 검증용이다. 기존 test/include·src·support 샘플과 함께 링크하지 않는다.

```powershell
.venv\Scripts\python -m unittest discover -s tests -p test_struct_sample.py -v
.venv\Scripts\python examples\create_struct_demo.py
```

[GUI와 저장 예제 안내](../../docs/structs.md)를 참고한다. 원본 C/H는 읽기만 한다.
