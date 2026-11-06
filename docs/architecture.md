# 아키텍처

## 예정된 데이터 흐름

읽기 전용 C 소스 → scanner → parser → 분석 모델 → storage(SQLite)

- scanner: .c/.h 및 Rte_*.h 파일 발견. 경로 정규화 및 제외 규칙 담당.
- parser: tree-sitter-c 구문 트리에서 함수 정의, 호출, 분기와 진단 추출.
- model: SourceLocation(path, line), FunctionDefinition, FunctionCall,
  Branch, ParseDiagnostic, RteDataDependency를 독립 타입으로 정의할 예정.
- storage: 분석 결과와 탐색 세션의 영속화. 원본 C 소스와 분리.
- rte(후속): 생성된 RTE 헤더와 접근 표현식을 분석하여 데이터 의존 관계 해석.
- trace(후속): 최초 목표 분기, 탐색 단계, 조사 이유 관리.
- gui(후속): Tkinter 화면. 분석 계층을 호출하며 파싱 로직을 포함하지 않음.

FunctionCall은 호출 지점과 호출 대상 표현식을 기록한다. RteDataDependency는
포트/데이터 요소 및 읽기·쓰기 관계를 기록한다. Rte_Read처럼 호출 구문인 경우에도
구문상 호출과 의미상 데이터 의존을 별도로 보존하고 위치로 연결한다.

분기 모델은 if/else if/else의 종류, 조건(else는 없음), 본문 위치,
부모 분기 및 체인 관계를 보존할 예정이다. 매크로 확장이나 함수 대상 식별이
확실하지 않으면 원문과 진단, 불확실한 상태를 남긴다. C 전처리기 실행이나
모든 빌드 변형의 의미 분석을 보장하지 않는다.

## 단계

1. 패키지 구조, 환경, 작업 지침과 환경 검증 테스트(완료).
2. 읽기 전용 스캐너와 가상 AUTOSAR fixture, 스캐너 테스트(완료).
3. 함수/호출/분기 파서, 위치 및 불확실성 모델과 테스트(완료).
4. 위 범위의 통합 검증(완료). Trace Manager, RTE Resolver, GUI와 DB 스키마 구현은 후속 범위.

현재 패키지 버전과 환경 검증, test/ 가상 AUTOSAR 샘플, 샘플 구조·실행 검증,
scanner.py의 SourceFile/scan_sources 및 parser.py의 parse_file/parse_source API가 존재한다.
models.py는 함수 정의, 호출 구문, 분기, 위치, 진단의 불변 모델을 정의한다.
파서가 함수/호출/분기의 위치와 불확실성을 기록하며 실제 호출 대상 연결과 RTE
데이터 의미 해석은 수행하지 않는다. 나머지 storage/rte/trace/gui는 후속 설계다.
상세 계약은 [파서 문서](parser.md)를 참고한다.
