# autosar-trace-navigator

## 목표와 범위
- AUTOSAR Classic C 통합 테스트의 목표 분기, 탐색 경로, 현재 함수 조사 이유를 보존하는 로컬 도구를 개발한다.
- Python, Tkinter, SQLite, tree-sitter-c를 사용한다. 실행 중 인터넷에 의존하지 않는다.
- 실제 고객사 소스는 반입하지 않는다. 테스트에는 직접 작성한 가상 C 코드만 사용한다.
- 사용자 승인에 따라 기존 분석·Trace·SQLite 기능을 Tkinter GUI로 연결한다. 분석 로직은 Tkinter에 의존하지 않고 화면 상태 계층으로 분리한다.
- 대규모 프로젝트에서는 선택 범위만 탐색·파싱하고 함수 검색 결과를 제한한다. 범위 안에서 미발견한 대상을 시스템 전체에 없다고 단정하지 않는다.
- RTE 이름 기반 후보는 실제 연결로 확정하지 않는다. 매크로, 헤더 범위, ARXML·실행 순서 미해석을 명시한다.
- test/parser_cases/는 의도적인 오류·미확장 매크로 사례를 포함하므로 실행용 AUTOSAR 샘플과 분리한다.
- test/large_autosar/는 독립 확장 프로젝트다. 기존 샘플 테스트는 include/src/support 범위를 명시하며 확장 프로젝트는 별도로 검증한다.
- 가상 코드 생성기는 새 출력 폴더만 허용한다. 기존 C/H를 덮어쓰지 않는다.
- test/value_paths/는 목표값 리터럴 없는 계산·실행 조건의 독립 샘플이다. 기존 실행 샘플과 분리해 검증한다.
- test/struct_paths/는 객체·포인터·RTE 출력 인수 추적의 독립 샘플이며 기존 실행 샘플과 분리해 검증한다.
- CT 전역 입력은 외부 연결 이름 기반 후보이며 static·const는 제외한다. 실제 CT 값 변경·조건 충족을 자동 확정하지 않는다.
- 실행 조건의 하위 조사 트리는 실제 프로그램 실행 순서와 구분한다.

## 설계와 코딩 규칙
- src 레이아웃을 사용하고 공개 함수에 타입 힌트와 필요한 설명을 작성한다.
- 분석 대상 .c/.h/Rte_*.h는 읽기 전용이다. 전처리 결과로 원본을 덮어쓰지 않는다.
- 함수 호출 관계와 RTE 데이터 의존 관계를 별도 모델로 유지한다.
- 소스 위치는 파일 경로와 1부터 시작하는 라인 번호로 기록한다.
- 해석 불가능한 매크로와 파싱 오류는 불확실성 및 이유를 기록한다. 확정된 결과로 추정하지 않는다.
- parser, scanner, storage는 GUI에 의존하지 않는다. 향후 trace와 rte 계층을 독립적으로 추가한다.
- SQLite 연결과 파일 입출력은 명시적인 작업에서만 수행한다. import 시 부작용을 만들지 않는다.
- 검증된 작업을 커밋한 뒤 사용자가 명시적으로 금지하지 않으면 현재 작업 브랜치를 원격에 push한다.
- main 직접 push, PR 생성·병합과 배포는 별도 사용자 요청이 있을 때만 수행한다.
- VS Code 확장은 extensions/branch-investigation/의 독립 TypeScript 프로젝트다. P0는 Python을 실행하지 않으며 기존 분석 엔진 재사용은 P1 범위로 별도 승인·검증한다.

## 테스트 규칙
- 표준 unittest를 사용한다: `.venv\Scripts\python -m unittest discover -s tests -v`.
- uv 환경에서는 `python -m uv sync --locked --group test` 후 `python -m uv run --locked --group test python -m unittest discover -s tests -v`를 사용한다.
- 실행·테스트 의존성 변경 시 uv.lock을 갱신하고 오프라인 실행 가능성을 확인한다. Tkinter·SQLite를 pip 의존성으로 추가하지 않는다.
- 테스트 데이터는 사용자 지정 test/ 아래 가상 코드로 구성한다. Python 자동 검증은 tests/에 둔다.
- 스캐너 구현 시 확장자, 중첩 경로, 제외 경로 및 원본 무변경을 검증한다.
- 파서 구현 시 함수 정의/호출, 중첩 if/else if/else, 위치, 매크로 불확실성을 검증한다.
- SQLite 테스트는 임시 DB를 사용하며 사용자 DB를 수정하지 않는다.
- 각 단계에서 실제 실행한 검사와 미검증 항목을 구분하여 보고한다.
- 확장 변경은 해당 폴더에서 npm ci 후 npm test를 실행한다. UI/저장 동작에 영향을 주면 설치된 VS Code의 npm run test:host도 실행하고 미실행 시 이유를 남긴다.
- 작업 기록 생성기만 검증할 때는 python -m unittest discover -s tests -p test_worklog.py -v로 표준 라이브러리 테스트를 실행할 수 있다.

## 커밋 규칙
- docs/ai/commit-convention.md를 따른다. 검증한 작업은 단계별로 자동 커밋한다.
- 여러 커밋은 계획을 먼저 제시하고, 변경별 CHANGELOG 항목을 같은 커밋에 넣는다.
- 관련 없는 사용자 변경은 포함하지 않는다. 사용자 요청 없이 기존 이력을 수정하지 않는다.
- 검증된 커밋은 사용자가 금지하지 않으면 현재 작업 브랜치에 push하고, 실패하면 원인과 미공유 상태를 보고한다.

## 다른 PC·Codex·Claude Code 작업 공유
- 환경 구성은 CONTRIBUTING.md, 작업 공유는 docs/work/README.md를 따른다.
- 시작 시 docs/work/STATUS.md, 배정 작업 카드와 연결된 최신 세션, 실제 Git 상태·코드를 확인한다.
- 승인된 작업에만 착수한다. 계획 카드 생성만으로 후속 구현을 승인받았다고 해석하지 않는다.
- 작업 카드에 범위·담당·상태·최신 인계 링크를, 세션별 새 파일에 변경·실제 검증·미검증·다음 첫 행동을 기록한다.
- 작업 종료/중단 시 기록을 갱신한다. 동시 작업은 담당 범위를 나누고 다른 도구의 세션 기록을 덮어쓰지 않는다.
- 과거 결과를 현재 PC의 검증으로 보고하지 않는다. 로컬 커밋과 원격 공유 상태를 구분한다.
- 공유 기록에는 가상 코드와 비민감 개발 정보만 넣는다. 고객/회사 자료·비밀키·개인 AI 메모리를 반입하지 않는다.

## Notion 프로젝트 기록
- 개발 포트폴리오: https://app.notion.com/p/3b1f5e6cf897818d9b4be7a92ed11508
- 프로젝트 데이터베이스: https://app.notion.com/p/23c44f4364684707837b03ebd3284d27
- 프로젝트 기준 문서: https://app.notion.com/p/415f5e6cf89781fe8869eb64ec3e0e8d
- Project Areas 데이터 소스: collection://6247775a-c846-4a13-b43e-602ccdb8c332
- Work Items 데이터 소스: collection://99f3d9a6-c8bf-477c-8ca7-471e30ee3475
- Dev Logs 데이터 소스: collection://ca5ee476-94be-4d39-9d86-1965b5170bc4
- Portfolio 데이터 소스: collection://ecf3f374-3d2c-457d-a044-05f4e0752139
- 프로젝트별 데이터베이스를 새로 만들지 않고 공용 데이터 소스의 프로젝트 관계로 연결한다.
- 기록 전 실제 스키마와 프로젝트명·저장소·작업명·대표 커밋 중복을 다시 확인한다.
