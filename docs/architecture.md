# 아키텍처

## VS Code 조사 기록 P0

`extensions/branch-investigation`은 TypeScript 확장이다. TreeView/Webview/명령 → InvestigationService →
JSON 저장소와 AnchorResolver/NavigationHistory를 사용한다. 기록은 `.branch-investigation/workspace.json`에 저장하며
기존 Trace 모델·SQLite와 분리한다. P0는 Python 프로세스를 실행하지 않는다.
P1용 TraceAnalysisPort는 기존 Workbench/ProjectSnapshot의 호출·RTE·값·조건 API 재사용 경계이며 기본 비활성이다.
자세한 [설치·설계·검증 안내](../extensions/branch-investigation/README.md)를 참고한다.

## 예정된 데이터 흐름

읽기 전용 C 소스 → scanner → parser → 분석 모델 → storage(SQLite)

- scanner: .c/.h 및 Rte_*.h 파일 발견. 경로 정규화 및 포함/제외 범위 가지치기 담당.
- parser: tree-sitter-c 구문 트리에서 함수 정의, 호출, 분기와 진단 추출.
- models.py: SourceRange, FunctionDefinition, FunctionCall, Branch, ParseDiagnostic.
- rte.py: 별도의 RteAccess, RteDataDependency, RteHeaderApi 및 후보 분석 결과.
- storage: 분석 결과와 탐색 세션의 영속화. 원본 C 소스와 분리.
- rte: RTE 헤더와 명시적 Read/Write 접근을 분석하여 이름 기반 데이터 연결 후보 기록.
- trace: 최초 목표 분기, 탐색 단계, 조사 이유 관리.
- dataflow: 현재 변수/반환값의 공급 후보를 요청 시 분석. 호출·RTE 모델을 참조하되 관계를 합치지 않음.
- access/structflow: 객체·멤버 경로를 보존하고 복사·명시적 별칭·출력 인수·객체 출처 후보를 분석.
- workbench: 입력 예산 내 선택 범위 스냅샷, 함수·호출·RTE 조회 인덱스와 검색 페이지, 조사·저장 액션.
- gui: Tkinter 화면. 워커 분석과 메인 스레드 위젯 갱신을 분리하며 파싱 로직을 포함하지 않음.

FunctionCall은 호출 지점과 호출 대상 표현식을 기록한다. RteDataDependency는
포트/데이터 요소 및 읽기·쓰기 관계를 기록한다. Rte_Read처럼 호출 구문인 경우에도
구문상 호출과 의미상 데이터 의존을 별도로 보존하고 위치로 연결한다.

분기 모델은 if/else if/else의 종류, 조건(else는 없음), 본문 위치,
부모 분기 및 체인 관계를 보존한다. 매크로 확장이나 함수 대상 식별이
확실하지 않으면 원문과 진단, 불확실한 상태를 남긴다. C 전처리기 실행이나
모든 빌드 변형의 의미 분석을 보장하지 않는다.

## 단계

1. 패키지 구조, 환경, 작업 지침과 환경 검증 테스트(완료).
2. 읽기 전용 스캐너와 가상 AUTOSAR fixture, 스캐너 테스트(완료).
3. 함수/호출/분기 파서, 위치 및 불확실성 모델과 테스트(완료).
4. 스캐너·파서 범위의 통합 검증(완료).
5. 사용자 승인에 따른 Trace Manager·SQLite 세션 저장 및 복원(완료).
6. 이름 기반 RTE Resolver와 Trace/SQLite 통합 검증(완료).
7. Tkinter GUI와 실제 위젯·클릭 검증(완료).
8. 선택 범위 분석·검색 중심 GUI와 표시 상한 검증(완료). 증분 캐시는 후속 범위.
9. 변수값 출처 후보·고정 변수 목표·선택 위치 저장 및 후보/이력 코드 미리보기(완료).
10. 외부 연결 전역의 CT 제어 후보 및 구조상 실행 조건의 반복 하위 조사(완료).
11. 분기 입력의 명시적 선택, 현재 소스/비교 코드 분리와 상세 정보 정리(완료).
12. 구조체 멤버·객체 출처 분석, GUI 선택·미리보기와 가상 코드·저장 예제 연결(완료).

현재 패키지 버전과 환경 검증, test/ 가상 AUTOSAR 샘플, 샘플 구조·실행 검증,
scanner.py의 SourceFile/scan_sources 및 parser.py의 parse_file/parse_source API가 존재한다.
models.py는 함수 정의, 호출 구문, 분기, 위치, 진단의 불변 모델을 정의한다.
파서가 함수/호출/분기의 위치와 불확실성을 기록하며 실제 호출 대상 연결과 RTE
데이터 의미 해석은 파서에서 수행하지 않는다. trace.py는 최초 목표 및 조사 경로를 보존하고,
storage.py는 그 불변 세션 스냅샷을 SQLite 트랜잭션으로 저장·복원한다.
함수 호출 조사와 RTE 조사 이동은 별도 relation으로 기록하며 실제 연결은 해석하지 않는다.
SQLite 세션 스키마는 분석 인덱스 저장과 분리한다. rte.py는 호출과 분리된
Read/Write 접근 및 이름 기반 연결 후보를 제공한다. 실제 ARXML wiring과 매크로 확장,
실행 순서는 해석하지 않는다. workbench.py와 gui.py가 위 API를 조합해 목표·조사 경로·이유를
보존하는 로컬 화면을 제공한다. 원본 소스는 변경하지 않는다.
ValueProbe는 현재 사용 위치를, VariableGoal은 첫 변수·목표값을 별도로 보존한다.
ValueResolver는 스냅샷에서 파일별 구문 트리를 필요할 때 구성한다. GUI의 후보 열람은
세션을 수정하지 않고 명시적인 조사 이동/위치 기록만 Workbench 액션을 호출한다.
값 출처는 구문·이름 기반 후보이며 제약 해결이나 조건 충족 증명은 수행하지 않는다.
ExecutionRequirement는 선택 지점의 구조상 조건과 필요한 참/거짓·변수 probe를 제공한다.
호출·RTE와 별개의 값/조건 조사로서 TraceStep의 부모 참조를 사용해 조사 트리를 보존한다.
CT 접근성은 외부 연결 이름을 바탕으로 한 후보이며 static·const는 제외한다.
ConditionInput은 분기 조건의 선택 가능한 식과 위치를 제공한다. 단순 식별자·멤버·역참조와
아직 추적하지 못하는 배열 경로를 구분하며 GUI에서 C 구문을 다시 파싱하지 않는다.
멤버·역참조 세션은 JSON 스냅샷 형식 3이며 단순 변수 형식 1/2 읽기도 유지한다.
GUI의 기준 소스와 단계별 코드는 독립 위젯이며 후보 열람·조사 이동으로 기준 화면을 전환하지 않는다.
기준 파일과 단계 코드의 파일·첫 표시 행·선택 위치를 분리해 다른 파일이나 잘린 표시 범위의 좌표를 혼동하지 않는다.
단계 코드는 현재 조사·후보·이력 중 표시 상태를 명시하며 열람은 세션을 변경하지 않는다.
상세 계약은 [파서 문서](parser.md), [RTE 문서](rte.md)를 참고한다.
