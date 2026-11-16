# Python 프로그램과 VS Code 확장 경계 제안

기준: `main@7d99447` (2026-11-16 확인). 이 문서는 구조 선택안이며 코드 이동이나 저장 형식 변경을 승인하지 않는다.

## 현재 구성

| 구성 | 코드·배포 | 의존 관계 |
|---|---|---|
| 분석 엔진 | `src/autosar_trace_navigator/`의 Python 패키지, `uv.lock` | 스캔·파싱·Trace·RTE·값 출처를 제공 |
| 데스크톱 프로그램 | 같은 Python 패키지의 `gui.py`, `storage.py`, Tkinter·SQLite | 분석 엔진을 프로세스 안에서 호출 |
| VS Code 확장 | `extensions/branch-investigation/`의 독립 npm 프로젝트와 VSIX | 수동 기록은 독립 동작. 설정된 경우 `python -I -m autosar_trace_navigator.bridge`를 호출 |
| 연결 계약 | `bridge.py` ↔ `src/adapters/traceAnalysisPort.ts` | stdin 요청 1건과 stdout JSON 응답 1건, 위치·범위·불확실성 검증 |

확장의 JSON 조사 기록과 데스크톱의 SQLite 세션은 서로 다른 모델이다. 같은 조사 기록이라고 가정해 파일을 직접 공유하지 않는다.

## 권장 구조

현재는 한 저장소에서 세 구성의 개발·배포 경계를 명시한다. Python 엔진과 데스크톱 프로그램은 같은 패키지로 유지하고, 확장은 독립 npm 패키지로 유지한다. 두 제품 사이의 재사용은 Python 프로세스의 JSON 계약으로 제한한다.

```text
src/autosar_trace_navigator/
  scanner.py, parser.py, rte.py, dataflow.py, ...  분석 엔진
  bridge.py                                    확장용 명시적 프로세스 경계
  gui.py, ui_style.py, storage.py              데스크톱 화면과 저장
extensions/branch-investigation/
  src/domain/, src/storage/, src/ui/           확장 자체 조사 모델과 UI
  src/adapters/traceAnalysisPort.ts           Python 계약 어댑터
tests/ + test/                                Python 회귀와 공통 가상 C 샘플
extensions/branch-investigation/test/         확장 단위·Host·계약 검증
```

## 단계별 실행안

1. `bridge.py` 요청·응답의 버전, 오류 코드, 위치 단위(UTF-16), 범위·시간·출력 한도와 불확실성 의미를 [브리지 계약 v1](bridge-contract.md)에 고정한다. 양쪽 테스트가 같은 가상 C fixture로 계약을 확인한다.
2. Python 테스트와 확장 단위·Host 테스트를 각각 실행하고, `bridge.py` 또는 어댑터 변경 때는 양쪽 계약 검증을 필수로 한다. VSIX와 Python 패키지의 버전·배포물·변경 이력을 따로 관리한다.
3. 새 기능은 분석 엔진, 데스크톱 UI, 확장 UI 중 소유 위치를 먼저 정한다. 확장이 Python 분석을 재구현하거나 데스크톱이 확장의 JSON 기록을 암묵적으로 읽지 않게 한다. SQLite import가 필요하면 별도 변환 계약과 데이터 손실 검증을 설계한다.
4. 배포 주기·담당자·저장소 접근 권한이 실제로 분리되고, 위 계약 테스트가 독립 실행 가능해지면 저장소 분리를 다시 결정한다. 그때 패키지 설치 경로와 fixture 배포 방식을 함께 설계한다.

## 현재 미병합 브랜치에 적용

- `feat/TASK-019-export`: 확장 UI와 VSIX 변경이다. `main`보다 3커밋 뒤이므로 최신 `main`을 반영해 확장 테스트·Host·VSIX를 재검증한 뒤 별도 PR로 검토한다. 내보낸 파일에 기록된 이유와 상대 경로가 포함되므로 전달 전 확인 안내를 유지한다.
- `codex/agent-docs-layout`: 문서 위치 정리만이 아니라 Python 분석, 브리지, 확장 미리보기 UI, 대형 fixture와 검증을 포함한 7커밋이다. 문서 이동과 제품 변경을 구분해 검토하고, 최신 `main`과 통합한 후 Python·C·Node·Host 계약을 다시 검증한다. 브랜치 이름만으로 문서 전용 변경으로 판단하지 않는다.

## 별도 저장소로 옮길 때의 기준

- 두 구성의 릴리스와 담당자가 독립적으로 운영되어야 한다.
- 확장이 지원할 Python 엔진 버전 범위와 JSON 계약 호환성 정책이 정해져 있다.
- Python 패키지를 별도로 설치한 환경에서 확장 Host와 fixture 계약 테스트가 통과한다.
- 공통 샘플과 문서를 어느 저장소가 소유하고 어떻게 버전 관리할지 정해져 있다.

이 조건이 충족되기 전 저장소만 분리하면 현재 같은 커밋에서 확인하던 브리지와 확장의 호환성 검증이 느슨해진다.
