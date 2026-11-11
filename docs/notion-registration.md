# Notion 등록 준비안

이 문서는 `autosar-trace-navigator`의 프로젝트 문서와 개발 작업 이력을 개발 포트폴리오 Notion에
중복 없이 등록하기 위한 실행 기준이다. 2026-11-12 KST에 실제 데이터 소스 스키마와 기존 항목을 조회해 작성했다.
아직 Notion 페이지를 생성하거나 수정하지 않았다.

## 등록 대상과 운영 구조

현재 개발 포트폴리오는 프로젝트별 데이터베이스를 새로 만들지 않고 다음 공용 데이터 소스를 관계로 연결한다.

| 용도 | Notion 위치 | 데이터 소스 |
|---|---|---|
| 개발 포트폴리오 허브 | [개발 포트폴리오](https://app.notion.com/p/3b1f5e6cf897818d9b4be7a92ed11508) | 해당 없음 |
| 프로젝트 기준 문서 | [Projects](https://app.notion.com/p/23c44f4364684707837b03ebd3284d27) | `collection://01f3c0b6-6b82-4748-8fdf-f4e4cabbd25c` |
| 기능·기술 영역 | [Project Areas](https://app.notion.com/p/d301442da9b64b18b44e64f6d6acc710) | `collection://6247775a-c846-4a13-b43e-602ccdb8c332` |
| 승인 작업 | [Work Items](https://app.notion.com/p/e3098566658d477d8f1e4c6d41d61d63) | `collection://99f3d9a6-c8bf-477c-8ca7-471e30ee3475` |
| 완료 작업 이력 | [Dev Logs](https://app.notion.com/p/92da26d1e1ea4b6c894c50941a0da011) | `collection://ca5ee476-94be-4d39-9d86-1965b5170bc4` |
| 대표 성과 | [Portfolio](https://app.notion.com/p/b0d5ab90097746a3b7e500ff8471332f) | `collection://ecf3f374-3d2c-457d-a044-05f4e0752139` |

## 중복 조회 결과

다음 조건을 각 데이터 소스에서 조회했으며 일치 항목이 없었다.

- Projects: 프로젝트명 `autosar-trace-navigator`, 저장소 URL `https://github.com/Huelune/autosar-trace-navigator.git`
- Work Items: 작업명 `기능 브랜치와 main 인계 통합`, 프로젝트명을 포함한 기존 작업
- Dev Logs: 작업명 `기능 브랜치와 main 인계 통합`, 대표 커밋 `58811b4`
- Project Areas: 아래에 제안한 다섯 영역명

등록 직전에는 동일 조건을 다시 조회한다. 이름 또는 저장소 URL이 일치하면 새 페이지를 만들지 않고 기존 페이지를 갱신한다.

## 1. Projects 등록안

### 속성

| 속성 | 값 |
|---|---|
| 프로젝트명 | `autosar-trace-navigator` |
| 한줄 소개 | AUTOSAR Classic C 통합 테스트의 목표 분기와 조사 맥락을 보존하는 로컬 분석·탐색 도구 |
| 상태 | 진행 중 |
| 프로젝트 유형 | 데스크톱 앱 |
| 프로젝트 영역 | 개발 도구, 데이터 처리, GUI/UX, 문서화 |
| 기술 | Python, Git, GitHub |
| 기본 브랜치 | `main` |
| 저장소 | `https://github.com/Huelune/autosar-trace-navigator` |
| 시작일 | 2026-11-06 |
| 최근 기준일 | 2026-11-12 |
| 검증 상태 | 부분 검증 |
| 현재 기준 | `main 076c155 / 원격 통합 브랜치 58811b4` |
| 보관 | 해제 |

`현재 기준`은 원격 통합 브랜치와 main을 의도적으로 분리한다. 통합 브랜치 기능을 `main`의 현재 제공 기능으로 기록하지 않는다.
Notion의 현재 기술 선택지에 Tkinter, tree-sitter, TypeScript가 없으므로 임의 옵션을 만들지 않고 본문에서 설명한다.

### 본문 초안

#### 프로젝트 개요

AUTOSAR Classic C 통합 테스트에서 목표 분기, 탐색 경로, 현재 함수를 조사하는 이유를 보존하는 로컬 도구다.
Python 분석 엔진과 Tkinter/SQLite 조사 UI, 독립적인 VS Code 조사 기록 확장으로 구성된다.

#### 목표와 해결하려는 문제

- 대규모 C 코드에서 선택한 범위만 탐색하고 조사 맥락을 잃지 않게 한다.
- 함수 호출과 RTE 데이터 의존을 구분하고 불확실한 후보를 확정 사실처럼 표시하지 않는다.
- 조사 목표, 이유, 코드 위치, 근거, 방문 이력을 로컬에서 저장·복원한다.

#### 사용자와 주요 흐름

AUTOSAR Classic C 통합 테스트를 준비하는 개발자·테스터가 프로젝트 범위를 선택하고 목표 함수나 분기를 분석한다.
후보를 따라가며 조사 이유와 근거를 기록하고, 저장한 세션이나 VS Code 조사 트리에서 소스를 다시 방문한다.

#### 기능 범위와 제외 범위

- 포함: C/H 범위 스캔, 함수·분기·호출 분석, RTE 후보, 값·구조체·출력 인수 역추적, 로컬 조사 기록, 가상 샘플 검증.
- 제외: 실제 wiring 자동 확정, ARXML·실행 순서 완전 해석, CT 값 자동 조작, 고객사 소스 반입, 실행 중 인터넷 의존.
- 함수 검색 결과와 파싱은 선택 범위 기준이며 범위 밖 부재를 단정하지 않는다.

#### 아키텍처와 책임

- Python 엔진: scanner, parser, trace, rte, dataflow, access, structflow, workbench 계층.
- Tkinter/SQLite: 분석 로직과 분리된 화면 상태, 조사 이력과 세션 저장·복원.
- VS Code 확장: `extensions/branch-investigation/`의 독립 TypeScript 프로젝트. 수동 기록은 Python 없이 동작하고,
  관련 후보 조회만 명시적으로 설정된 Python 엔진을 사용한다.
- 분석 대상 C/H와 `Rte_*.h`는 읽기 전용이며 import 시 파일·DB 부작용을 만들지 않는다.

#### 데이터와 외부 연동

분석 대상 소스, SQLite 조사 DB, VS Code 로컬 JSON을 로컬에서만 처리한다. 네트워크 서비스나 실서버 API는 사용하지 않는다.
함수 호출 관계와 RTE 데이터 의존 관계는 별도 모델로 유지한다.

#### 저장소와 문서

- 저장소: [GitHub](https://github.com/Huelune/autosar-trace-navigator)
- 시작: `README.md`, `CONTRIBUTING.md`
- 구조: `docs/architecture.md`
- 사용: `docs/user-guide.md`, `extensions/branch-investigation/README.md`
- 현재 상태와 작업 근거: `docs/work/STATUS.md`, `docs/work/tasks/`, `docs/work/sessions/`

#### 현재 main 제공 기능

`main@076c155`는 원본 VS Code 구현 명세와 저장소 기반 인계 정정을 포함한다. Python 분석 연결과 후속 VS Code UX,
로컬 통합 결과는 아직 `main`에 병합되지 않았으므로 현재 제공 기능으로 기록하지 않는다.

#### 설정과 실행

Python은 `uv.lock` 기반 환경과 기존 pip 설치 방식을 지원한다. GUI와 분석 엔진은 오프라인 실행을 전제로 한다.
VS Code 확장은 `release/branch-investigation-0.1.0.vsix`로 설치할 수 있으며 Python 후보 조회는 사용자 설정이 필요하다.

#### 테스트와 완료 기준

- Python 표준 `unittest`, 가상 C 실행 시나리오, 확장 TypeScript 단위 테스트와 VS Code Host 시나리오를 구분한다.
- SQLite 검증은 임시 DB를 사용하고 실제 사용자 DB를 수정하지 않는다.
- 현재 로컬 통합 검증: 확장 단위 27개, Python 비-GUI 122개, 가상 C 시나리오 216개 통과, VSIX 무결성 확인.
- macOS Tk GUI 전체 실행, Zig 경로, 실제 VS Code 수동 UI는 이번 기준에서 미검증이다.

#### 보안과 데이터 취급

실제 고객사 소스, 서버 주소, 자격 증명, 토큰, 사용자·조직 식별자, 비공개 업무 데이터는 저장소와 Notion에 기록하지 않는다.
테스트와 예시는 직접 작성한 가상 C 코드와 익명화된 구조만 사용한다.

#### 상태와 기준

- 기본 브랜치: `main`
- main 기준: `076c155`
- 활성 원격 통합 브랜치: `origin/fix/feature-branch-integration` (대표 통합 커밋 `58811b4`)
- Git 반영: 원격 브랜치에 push됐으며 PR·main 반영 전이다.
- 최근 검증일: 2026-11-11
- 검증 상태: 부분 검증

#### 알려진 제한과 다음 우선순위

- macOS Tk와 Zig 호환성, 실제 VS Code 수동 UI, 다른 PC 설치 정책은 추가 확인이 필요하다.
- 다음 우선순위는 통합 diff 검토 후 승인된 경우 PR 생성이다.
- 검색/필터, 일괄 스니펫, 위치 복구 후보, 기존 SQLite 읽기 import, P2 그래프·성능 확대는 승인되지 않은 후보이며
  현재 제공 기능이나 확정 백로그로 기록하지 않는다.

## 2. Project Areas 등록안

Projects 페이지를 만든 뒤 아래 영역을 생성하고 모두 해당 프로젝트와 연결한다.

| 영역명 | 분류 | 설명 | 활성 |
|---|---|---|---|
| AUTOSAR Trace · 분석 엔진 | Domain | C 범위 스캔, 파싱, 호출·분기·RTE·값·구조체 흐름 분석 | 설정 |
| AUTOSAR Trace · 조사 UI | UI | Tkinter GUI와 VS Code 조사 트리·상세·소스 재방문 | 설정 |
| AUTOSAR Trace · 저장·복원 | Data | SQLite 세션과 VS Code 로컬 JSON 기록·복구 | 설정 |
| AUTOSAR Trace · 검증·가상 샘플 | Test | unittest, Host 검증, 가상 AUTOSAR C 시나리오 | 설정 |
| AUTOSAR Trace · 배포·인계 | Operations | uv·VSIX 배포와 Git·작업 카드 기반 인수인계 | 설정 |

## 3. Work Items 등록안

| 속성 | 값 |
|---|---|
| 작업명 | 기능 브랜치와 main 인계 통합 |
| 상태 | 완료 |
| 우선순위 | P1 |
| 작업 유형 | 운영 |
| 완료 기준 | main 명세·인계를 보존하면서 기능 브랜치를 통합하고, 작업 번호·문서·VSIX를 정리해 관련 회귀 검증을 통과한다. |
| 검증 근거 | 확장 27개, Python 비-GUI 122개, 가상 C 216개 통과. VSIX 생성·압축 무결성·문서 링크 확인. macOS Tk·Zig·수동 UI는 미검증. |
| 기간 | 2026-11-11 |
| Portfolio 후보 | 해제 |
| 프로젝트 | 생성한 `autosar-trace-navigator` Projects 페이지 |
| 영역 | 배포·인계, 검증·가상 샘플 |

## 4. Dev Logs 등록안

### 속성

| 속성 | 값 |
|---|---|
| 작업명 | 기능 브랜치와 main 인계 통합 |
| 한줄 요약 | 기능 브랜치의 Python·VS Code 변경을 main의 명세·인계와 로컬 통합하고 문서·VSIX·작업 기록을 정리했다. |
| 작업 유형 | 운영 |
| 검증 상태 | 부분 검증 |
| 검증 방식 | 자동 테스트, 오프라인 실행, 문서 검토 |
| 반영 상태 | 원격 브랜치 |
| 브랜치 | `fix/feature-branch-integration` |
| 대표 커밋 | `58811b4b1953e20493ae355db70e6fcadec73381` |
| PR | 비움 |
| 기술 | Python, Git, GitHub |
| 작업 기간 | 2026-11-11 |
| 완료일 | 2026-11-11 |
| 프로젝트 | 생성한 `autosar-trace-navigator` Projects 페이지 |
| 영역 | 배포·인계, 검증·가상 샘플 |
| 관련 Work Item | 위 Work Items 페이지 |

### 본문 초안

#### 목표

원격 기능 브랜치의 Python 분석 연결·VS Code UX 변경을 최신 main의 원본 명세·인계 정정과 통합한다.

#### 주요 작업

- 원격 기능 브랜치를 보존한 별도 로컬 브랜치에서 main을 병합했다.
- 중복된 작업 번호를 정리하고 완료 작업과 명세 복구 작업의 역할을 분리했다.
- 확장 README의 Python 실행 조건과 VSIX 내부에서 깨지는 링크를 실제 동작에 맞게 수정했다.
- 현재 소스와 문서로 설치용 VSIX를 다시 생성했다.

#### 핵심 결정

- 함수 호출과 RTE 의존, 추정 후보와 확정 사실의 경계를 유지했다.
- 원격 통합 브랜치 push를 main 반영으로 과장하지 않았다.
- 기능 커밋 일부만 떼지 않고 절대 경로 가림 수정을 포함한 전체 이력을 유지한다.

#### 검증 근거

- 확장 `npm test`: 27개 통과.
- Python 비-GUI 회귀: 122개 통과.
- 시스템 Clang 기반 가상 C 실행: 216개 통과.
- VSIX 재생성 및 `unzip -t`, 패키지 README 링크 확인, `git diff --check` 통과.
- macOS Tk 전체 테스트, Zig 경로, 실제 VS Code 수동 UI는 완료하지 못해 부분 검증으로 기록한다.

#### 커밋·PR

- 브랜치: `fix/feature-branch-integration`
- 대표 커밋: `58811b4b1953e20493ae355db70e6fcadec73381`
- 반영 상태: 원격 브랜치
- PR: 없음

#### 사용자 영향

통합 브랜치에서 main의 명세·인계와 기능 브랜치의 분석·조사 UX를 함께 검토할 수 있고, 설치용 VSIX의 설명과 링크가
현재 동작에 맞는다. 원격 main 사용자는 PR이 병합되기 전까지 영향을 받지 않는다.

#### 남은 과제

통합 diff를 검토한 뒤 사용자가 요청하면 PR을 생성한다. macOS Tk·Zig와 실제 VS Code 수동 UI는
별도 환경 검증이 필요하다.

## Portfolio 처리

이번 작업은 `원격 브랜치`이고 `부분 검증`이므로 Portfolio 항목을 만들지 않는다. PR 병합과 요구 범위 검증이 끝난 뒤
대표 성과로 볼 근거가 생겼을 때만 기존 항목을 조회하고 연결한다.

## 실제 등록 순서

1. 모든 대상 데이터 소스의 스키마와 선택 옵션을 다시 조회한다.
2. 프로젝트명과 저장소 URL로 Projects 중복을 재확인하고 프로젝트 기준 문서를 생성하거나 갱신한다.
3. 다섯 영역명을 재조회하고 Project Areas를 생성하거나 기존 항목을 프로젝트에 연결한다.
4. Projects의 Project Areas 관계를 연결한다.
5. 작업명과 프로젝트 관계로 Work Items 중복을 재확인하고 등록한다.
6. 작업명과 대표 커밋으로 Dev Logs 중복을 재확인하고 프로젝트·영역·Work Item 관계를 연결한다.
7. Portfolio는 생성하지 않는다.
8. 생성·갱신한 각 페이지를 다시 읽어 속성, 본문, 관계, Git 반영 상태를 검증한다.
9. 실제 Projects 페이지와 공용 데이터베이스 위치를 저장소 `AGENTS.md`에 기록한다.

## 등록 후 확인 체크리스트

- [ ] 동일 프로젝트명 또는 저장소 URL의 중복 페이지가 없다.
- [ ] `main`과 원격 통합 브랜치가 서로 다른 기준으로 적혔다.
- [ ] Work Item과 Dev Log가 Projects 및 올바른 Project Areas에 연결됐다.
- [ ] Dev Log의 반영 상태가 `원격 브랜치`, 검증 상태가 `부분 검증`이다.
- [ ] PR 속성이 비어 있고 Portfolio 항목이 생성되지 않았다.
- [ ] 고객·회사 자료, 자격 증명, 실제 서버·사용자 식별자가 포함되지 않았다.
- [ ] 프로젝트 본문과 저장소 `STATUS.md`, TASK-005 세션의 수치가 일치한다.
- [ ] 생성·수정된 Notion 페이지를 다시 읽어 저장 성공을 확인했다.
