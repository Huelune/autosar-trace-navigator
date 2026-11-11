# 프로젝트 현재 상태

## 이어받을 때

이 문서는 저장소 기반 공유를 구성한 시점의 요약이다. 이후 세부 진행 상태는 작업 카드·최신 세션·실제 코드를 확인한다.
기준 구현 커밋은 `a84ffeb`, 새 체크아웃 준비 수정은 `7057a38`이다. 현재 HEAD와 원격 공유 여부는 `git log`와 Git 상태로 확인한다.
원래 PC의 build 산출물·로컬 조사 JSON·AI 대화는 복제되지 않으며 개발을 이어가는 데 필수 자료로 삼지 않는다.
**[원본 구현 지시서](../branch-investigation/05_Codex_VSCode확장_구현지시서.md)**를 먼저 읽어 제품 목적·요구사항·완료 기준을 확인한다.
처음 공유할 때 미추적 파일이라는 이유로 제외한 것은 인계에 필요한 명세를 누락한 판단 오류였다.
[TASK-003](tasks/TASK-003.md)에서 원문을 그대로 포함하고 [구현을 이어받는 순서](../branch-investigation/README.md)를 추가했다.

## Git 반영 경계

- 원격 `main`의 현재 기준은 `03c30531eb10210c65d0fd088a0510279f7851ea`이다.
- Python 분석 연결, 후속 VS Code UX, 교차 플랫폼 조사 DB 복원과 macOS Host 검증 수정은
  [PR #1](https://github.com/Huelune/autosar-trace-navigator/pull/1)로 main에 병합됐다.
- 기능 브랜치와 통합 브랜치는 이력 근거이며 현재 제공 기능의 기준은 원격 main이다.

## main에 구현된 것

| 영역 | 현재 구현 | 확인할 곳 |
|---|---|---|
| Python 엔진 | 범위 스캔·tree-sitter C 파싱·함수/분기·호출·RTE 후보·값/구조체/출력 인수 역추적 | `src/autosar_trace_navigator/`, [아키텍처](../architecture.md) |
| Tkinter/SQLite | 목표·조사 이력·라인·후보 미리보기, 고정 기준 소스와 단계별 코드, 저장/복원 | [사용법](../user-guide.md), [구조체 예시](../structs.md) |
| uv 환경 | 잠금 파일, 실행/테스트 의존성, Zig C 실행, 캐시 기반 오프라인 설치 | [uv 안내](../uv.md) |
| VS Code P0 | 코드 선택·목표/이유·트리·상세·소스 재방문·스니펫·근거·원자 JSON/복구·VSIX | [확장 README](../../extensions/branch-investigation/README.md), [P0 결과](../branch-investigation/P0_구현_검증결과.md) |
| 작업 공유 | 공통 AGENTS/CLAUDE 지침, 새 PC 환경 안내, 작업 카드·세션·생성기 | [시작 안내](../../CONTRIBUTING.md), [기록 절차](README.md) |

VS Code 확장은 기본 설정에서 Python을 실행하지 않는다. Python 경로를 설정하면 커서 변수의 값 출처, 커서 위치의 실행 조건,
커서 함수의 호출·RTE Writer 후보를 기존 엔진에서 조회해 고른 후보를 단계로 추가할 수 있다(TASK-002, TASK-004).
함수 검색과 결과 캐시는 미연결이다.
호출과 RTE 관계는 별개이며, 후보/조사 경로를 실제 wiring·프로그램 실행 순서·CT 값 제어 성공으로 해석하지 않는다.

## 검증 근거

- **공유 구성 작업(TASK-001)**: 새 체크아웃 복사본의 오프라인 `npm ci`, 확장 단위 테스트 18개, VSIX 생성 통과.
  새 .venv의 오프라인 uv 설치 후 전체 Python **177개(기록 생성기 6개 포함)**, C 시나리오 **216개** 통과, 실패/skip 없음.
  환경·명령·제한은 [TASK-001](tasks/TASK-001.md)의 연결 세션 참조.
- **이전 P0 작업의 기록**: Windows x64 / Node 22.23.4 / VS Code 1.145.2, 단위 18개·Host 기록/재시작/Restricted Mode·native UI·패키지 설치 검증.
  상세는 [당시 결과 보고서](../branch-investigation/P0_구현_검증결과.md). 이번에 Host/native UI를 재실행한 결과는 아니다.
- **이전 uv 작업의 기록**: Windows x64 / Python 3.14.3에서 전체 Python 171개 및 C 시나리오 216개 통과, 오프라인 새 환경 구성 확인.
  이후 기록 테스트 6개가 추가됐고 위 새 환경에서 177개로 재검증했다. 과거 171개와 현재 결과를 구분한다.
- 다른 PC의 실제 설치, 회사 Claude Code 지침 로딩, 다른 OS, 실제 CT/고객 코드 검증은 하지 않았다.
- **명세 누락 정정(TASK-003)**: 원문 SHA256 보존·로컬 링크 68개·Git 스테이징/배포 아카이브의 원문 포함 확인 통과.
  실행 코드는 변경하지 않았다. 원격 공유 커밋은 카드의 연결 세션과 Git 이력으로 확인한다.
- **Notion 등록·통합 검증(TASK-008)**: 확장 단위 27개, VS Code Host record·restart·Restricted Mode 및 7개 시나리오,
  Python 비-GUI 122개와 추가 환경·값·구조체·튜토리얼 20개, 시스템 Clang 기반 C 216개 통과.
  macOS Tk GUI 전체와 Zig 0.15.2 C 경로는 미검증이므로 프로젝트 검증 상태는 부분 검증을 유지한다.

## 작업 목록과 남은 일

| 카드 | 범위 | 최초 등록 상태 |
|---|---|---|
| [TASK-001](tasks/TASK-001.md) | 저장소 기반 환경 구성·공통 지침·작업/세션 기록 | 완료 (세부 인계는 카드) |
| [TASK-002](tasks/TASK-002.md) | P1 Python 분석 포트 연결 | 완료, PR #1로 main 반영 |
| [TASK-003](tasks/TASK-003.md) | 원본 구현 지시서 누락 공유 복구 | 완료 (검증·공유는 연결 세션) |
| [TASK-004](tasks/TASK-004.md) | 확장의 값 출처·실행 조건 후보 연결 | 완료, PR #1로 main 반영 |
| [TASK-005](tasks/TASK-005.md) | 기능 브랜치와 main 인계 통합 | 완료, [PR #1](https://github.com/Huelune/autosar-trace-navigator/pull/1)로 main 반영 |
| [TASK-006](tasks/TASK-006.md) | Notion 프로젝트·작업 이력 등록 준비 | 완료, main 반영 |
| [TASK-007](tasks/TASK-007.md) | 검증된 작업 브랜치 자동 push 정책 | 완료, main 반영 |
| [TASK-008](tasks/TASK-008.md) | Notion 실제 등록·교차 플랫폼 검증·통합 PR | 완료, PR #1로 main 반영 |

P1의 다른 후보는 검색/필터, 일괄 스니펫, 위치 복구 후보, 기존 SQLite 읽기 import다.
이들은 지금 구현하도록 승인된 범위가 아니다. 요청받은 항목만 별도 카드로 나누고 완료 조건부터 정한다.
P2 그래프·성능 확대와 CT 자동 조작은 현재 작업에 포함하지 않는다.

Notion 기록을 실행할 때는 [등록 준비안](../notion-registration.md)에 따라 현재 공용 데이터 소스 스키마와 중복을 다시 확인한다.
TASK-005는 Projects·Project Areas·Work Items·Dev Logs에 등록하고 Dev Log를 `main 반영`으로 갱신했다.
전체 검증이 아닌 부분 검증 상태이므로 Portfolio는 생성하지 않았다.

다른 PC의 첫 행동은 [CONTRIBUTING](../../CONTRIBUTING.md)에 따라 환경과 대상 커밋을 확인하고,
담당 카드로 **새 세션**을 시작하는 것이다. 과거 세션을 자신의 수행 기록으로 덮어쓰지 않는다.
