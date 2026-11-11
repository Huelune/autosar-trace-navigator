# TASK-002 — P1 Python 분석 엔진 연결 범위 확정과 구현

- 상태: done
- 담당: dev-b / Claude Code
- 브랜치: feat/repo-analysis-aa2e6b
- 기준 커밋: 7057a38aca5631266d09cb15f510e356a25d29c6
- 생성 UTC: 2026-11-10T15:37:14+00:00
- 최신 세션: [Claude 작업 기록](../sessions/20261111T003557Z-claude-d4a7aab3fa3c4ed690f59b38db37ac41.md)

## 목적과 승인 범위

VS Code에서 기존 Python 분석 엔진의 후보 조회를 재사용한다.
**2026-11-11 사용자가 승인한 1차 범위**: 커서가 있는 함수의 호출 후보와 RTE Writer 후보를 조회하고,
고른 후보만 이유와 함께 하위 단계로 추가한다. 값 출처·실행 조건 후보, 함수 검색, 결과 캐시는 승인 범위가 아니다.
기존 포트는 `extensions/branch-investigation/src/adapters/traceAnalysisPort.ts`이며 Python 분석을 TS로 중복 구현하지 않는다.

## 범위 밖

Tkinter 삽입, 원본 C/H 변경, 실제 RTE wiring/실행 순서 확정, CT 자동 제어,
전체 프로젝트 무제한 파싱, P1의 다른 UI 기능 일괄 구현. 회사 Python 실행 정책 우회.

## 완료 조건

- [x] 승인된 범위·subprocess/JSON DTO 계약과 한도 확정 (사내 PC의 Python 실행 허용 여부는 미확인)
- [x] 기존 analyze_project/ProjectSnapshot/Workbench API 재사용 위치 확인
- [x] 파일/인코딩·UTF-8 바이트 ↔ UTF-16 범위 변환 실패를 "위치 확인 필요"로 보존
- [x] 범위 제한·취소/실패·불확실 후보·원본 무변경을 가상 코드로 검증 (Python 7개, 확장 단위 5개)
- [x] 기존 P0 기록과 독립 동작·관련 Python/확장 회귀 검증 — Python 184개·확장 단위 23개·Host 6단계(엔진 연동 포함) 통과
- [x] 세션에 실제 검증·미검증·다음 행동 기록

## 진행과 검증

1차 범위 구현·커밋(로컬)·Host 검증 완료. 실행 명령·결과·환경과 남은 미검증 항목은 최신 세션에 있다.

## 인수인계 — 다음 첫 행동

1차 범위는 끝났다. 값 출처·실행 조건 후보 연결 등 다음 범위는 승인받은 뒤 새 카드로 나눈다.
사내 PC에서 Python subprocess 사용이 허용되는지는 해당 환경에서 확인한다. 실제 편집기에서 사람이 직접 조작한 확인도 남아 있다.
