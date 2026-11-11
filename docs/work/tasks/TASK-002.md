# TASK-002 — P1 Python 분석 엔진 연결 범위 확정과 구현

- 상태: in_progress
- 담당: dev-b / Claude Code
- 브랜치: feat/repo-analysis-aa2e6b
- 기준 커밋: 7057a38aca5631266d09cb15f510e356a25d29c6
- 생성 UTC: 2026-11-10T15:37:14+00:00
- 최신 세션: [Claude 작업 기록](../sessions/20261111T003557Z-claude-d4a7aab3fa3c4ed690f59b38db37ac41.md)

## 목적과 승인 범위

VS Code에서 기존 Python 분석 엔진의 후보 조회를 재사용하는 P1 후속 후보.
**계획 카드이며 이번 공유 구성 요청으로 구현을 승인받은 것은 아니다.**
배정받으면 사용자가 원하는 최초 조회 범위(함수 검색/호출/RTE/값/조건 중 무엇)를 확정하고 이 카드를 좁힌다.
기존 포트는 `extensions/branch-investigation/src/adapters/traceAnalysisPort.ts`이며 Python 분석을 TS로 중복 구현하지 않는다.

## 범위 밖

Tkinter 삽입, 원본 C/H 변경, 실제 RTE wiring/실행 순서 확정, CT 자동 제어,
전체 프로젝트 무제한 파싱, P1의 다른 UI 기능 일괄 구현. 회사 Python 실행 정책 우회.

## 완료 조건

- [ ] 승인된 범위·Python 실행 환경·subprocess/JSON DTO 계약과 한도 확정
- [ ] 기존 analyze_project/ProjectSnapshot/Workbench API 재사용 위치 확인
- [ ] 파일/인코딩·UTF-8 바이트 ↔ UTF-16 범위 변환 실패를 불확실성으로 보존
- [ ] 범위 제한·취소/실패·불확실 후보·원본 무변경을 가상 코드로 검증
- [ ] 기존 P0 기록과 독립 동작·관련 Python/확장 회귀 검증
- [ ] 세션에 실제 검증·미검증·다음 행동 기록

## 진행과 검증

미착수. 실행 명령·결과·환경은 세션에도 남긴다.

## 인수인계 — 다음 첫 행동

사용자가 이 작업을 배정하면 먼저 포트와 기존 Python API를 읽고 최소 연동 범위와 완료 기준을 제안한다.
사내 PC에서 Python subprocess 사용이 허용되는지도 해당 환경에서 확인한다.
