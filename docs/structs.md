# 구조체 멤버와 객체 출처 추적

분석 API는 `b.a`, `b.inner.a`, `p->a`, `*out`을 단순 변수와 구분해 추적한다.
멤버 이름 a만으로 다른 객체를 연결하지 않는다. 배열 인덱스·포인터 연산은 해석하지 않는다.
GUI의 분기 변수 목록과 소스 더블클릭으로 전체 멤버 경로를 선택할 수 있다.
`(*p).a`는 같은 접근 경로인 `p->a`로 표시하되 원본 선택 범위는 그대로 보존한다.

## 예제 DB로 열어보기

1. 프로젝트 루트에서 `.venv\Scripts\python examples\create_struct_demo.py`를 실행한다.
   새 `build/struct_tutorial.sqlite3`를 만든다. 이미 있으면 `--output build/struct-02.sqlite3`처럼 새 이름을 지정한다.
   동봉된 `examples/struct_tutorial.sqlite3`는 작성 당시 경로를 사용하므로 다른 설치 경로에서는 다시 생성한다.
2. GUI를 실행하고 **세션 불러오기**로 DB를 연다. 다음 세션을 선택할 수 있다.

   | 세션 ID | 내용 |
   |---|---|
   | `struct-01-a-through-rte` | a → b.a → RTE 공급 → 계산 입력, EnableInput 조건과 객체 대안 포함 14단계 |
   | `struct-02-pointer-member` | p->a → 호출자의 local.a → 같은 공급 경로와 조건, 13단계 |
   | `struct-03-global-object` | 전역 멤버 → 객체 자체 → CT 접근 후보, 3단계 |

3. **루트 폴더 선택**에서 `test/struct_paths`를 선택하고 아래 범위를 분석한다.
   `struct_paths.h;Rte_StructPaths.h;producer.c;consumer.c;rte_stub.c`
   DB에는 원본 소스가 포함되지 않아 코드 비교와 후보 탐색에는 이 분석이 필요하다.
4. **전체 조사 이력**에서 처음의 a 또는 p->a 단계를 선택해 코드를 미리 본다.
   **선택한 이력 단계로 이동**으로 이동하면 값 출처의 **조사 연결**에서 다음 멤버를 확인할 수 있다.
   후보를 선택해 오른쪽 코드를 확인한 후 **선택 출처 조사**로 진행한다.
5. 계산 지점의 RawInput 경로와 EnableInput 조건은 서로 다른 하위 조사다.
   한쪽을 보고 다른 쪽으로 돌아가도 최초 `a → 60` 또는 `p->a → 60` 목표가 유지된다.
   객체 자체를 찾는 대안도 멤버값 공급 경로와 구분해서 남는다.

새로 조사하려면 `Struct_Consume`의 `a >= (6u * 10u)` 분기를 선택하고 a의 원하는 값을 60으로 설정한다.
`Struct_ConsumeMember`에서는 `Rte_Read_Struct_A(&b.a)`로 채우는 멤버 자체를 조사할 수 있다.

## 예제의 값 준비 경로

```text
Struct_Consume: a >= (6u * 10u)
  a = b.a
  ← Rte_Read_Struct_State(&b)
  ← Struct_Produce: Rte_Write_Struct_State(&built)
  ← Struct_BuildState: state.a
  ← Struct_Fill: out->a, *out = Struct_MakeState()
  ← Struct_MakeState: made.a
  ← Struct_SetMember: out->a = Struct_RawInput * 2u + 10u
       조건: Struct_EnableInput == 1u
```

6개 애플리케이션 함수를 조사하며 RTE 데이터 관계는 함수 호출 관계와 별개다.
사람이 검토한 입력 계획은 RawInput=25, EnableInput=1, ReadStatus=0으로 준비하고
공급자를 소비자보다 먼저 실행하는 것이다. 계산 결과는 25*2+10=60이다.
도구가 수식을 자동으로 풀거나 CT 제어·실행 순서를 확정한 결과는 아니다.
독립 C 하네스에서 입력·조건·읽기 상태를 바꾼 6개 시나리오를 실행한다.

## 보존하는 관계

- `b.a = input`: 같은 객체의 같은 멤버에 대한 쓰기와 계산 입력을 조사한다.
- `b = other`: `b.a`에서 `other.a`로 멤버 경로를 유지한다.
- `State b = {.a = input}`: 명시적 지정 초기화만 같은 멤버에 대응한다.
  필드 순서와 typedef 배치를 알아야 하는 위치 기반 초기화·생략 필드의 0 초기화는 확정하지 않는다.
- `p = &b`, `q = p`, `q->a = input`: 최대 4단계의 명시적 포인터 대입을 후보로 연결한다.
  여러 조건부 재지정은 모두 후보이며 어느 정의가 도달하는지 증명하지 않는다.
- 구조체·포인터 반환: `$return.a` 또는 `$return->a` probe가 반환하는 객체의 같은 경로로 이어진다.
- `Rte_Read_State(&b)` / `Rte_Read_Field(&b.a)`: 전체 객체·단일 멤버의 RTE 공급 값을 분리한다.
  명시적 포인터 인수 Read(p), Write(&src)도 후보로 다루지만 RTE payload 형식·배포 연결은 미확정이다.
- `Fill(&b)`와 함수 인수 `State *out`: `out->a` 쓰기 후보와 호출자의 `b.a`를 연결한다.
  `Set(&b.a)`의 `*out` 쓰기와 구조체 값 인수도 지원한다. 함수 실행·출력 인수 의미·호출 컨텍스트는 확정하지 않는다.
- 선택 범위의 다른 파일에서 전역 객체의 멤버를 쓰는 함수도 이름 기반 후보로 제공한다.
  static 객체와 같은 이름의 로컬 객체는 다른 파일의 전역으로 합치지 않는다.

`object_origin`은 **객체 자체를 찾기 위한 별도 후보**다. `b.a`에서 `b`로 이동해 선언·입력 경계를
조사할 수 있다. 객체 출처를 찾았다는 것이 a의 값이 준비됐다는 뜻은 아니다. 외부 전역 b의 CT 후보도
실제 구조체 배치·멤버 변경 가능성·CT 접근성 확인이 필요하다. 포인터 값 p의 변경 가능성을
가리키는 객체 `p->a`의 직접 제어 가능성과 혼동하지 않는다.

## 위치와 불확실성

모든 후보는 현재 분석 스냅샷의 파일·행과 근거를 보존한다. 직접 쓰기는 해당 쓰기 지점이며,
객체 복사에서 합성한 `other.a` probe는 RHS 객체 other의 실제 사용 위치에 걸린다.
함수 출력 포인터는 해당 함수 본문 끝을 조사 시작 위치로 사용한다. 이는 실행 완료를 뜻하지 않는다.
함수 밖 전역 초기화는 사용 위치에 걸고 `initializer_declaration`에 선언 파일·행을 별도로 기록한다.

대표 불확실성은 `member_type_layout_not_verified`, `aggregate_member_projection`,
`pointer_identity_not_proven`, `alias_candidates_not_reaching_definitions`,
`call_context_not_bound`, `global_linkage_not_proven`, `rte_payload_shape_not_proven`이다.
알 수 없는 포인터 대상은 `pointer_target_not_resolved` 경계로 남는다.
union 중첩 배치, 임의 별칭, 배열, 포인터 산술, 함수 포인터, 매크로 확장, 실제 도달 정의나
조건 충족을 해석한 결과가 아니다. 원본 C/H는 수정하지 않는다.

## 저장 호환성

멤버·역참조 또는 투영된 반환값을 사용하는 세션은 **JSON 스냅샷 형식 3**으로 저장한다.
기존 단순 변수 세션은 형식 2로 저장하고, 형식 1/2를 계속 읽는다. SQLite 테이블 스키마는 1이다.
이전 앱이 형식 3을 거부하므로 멤버 투영을 일반 반환값으로 잘못 해석하는 것을 막는다.

## 검증

`tests/test_structflow.py`는 객체 이름 분리, 복사·초기화, 명시적 별칭·불명 포인터,
RTE 객체/멤버, 함수의 구조체 포인터 인수/출력, 파일 간 전역 쓰기와 static/로컬 제외, SQLite 복원을 검증한다.
`tests/test_struct_sample.py`는 위의 6개 함수 경로, 실제 Tk 선택·미리보기·이동, 예제 DB 복원과
원본 C/H 해시·수정 시각 보존을 추가로 검증한다. 헤더 가드 안 extern 선언도 후보로 찾는다.
가상 소스만 사용하며 CT 제품이나 ECU 실행을 검증하지 않는다.
