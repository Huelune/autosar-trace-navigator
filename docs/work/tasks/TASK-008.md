# TASK-008 — Notion 실제 등록·교차 플랫폼 검증·통합 PR

- 상태: in_progress
- 담당: Codex
- 브랜치: fix/feature-branch-integration
- 기준 커밋: c31c706b0f521738794e318858d18aceb0c72237
- 생성 UTC: 2026-11-11T23:33:51+00:00
- 최신 세션: [Codex 작업 기록](../sessions/20261111T233351Z-codex-notion-pr.md)

## 목적과 승인 범위

준비한 Notion 프로젝트·영역·Work Item·Dev Log를 실제로 등록하고 관계를 검증한다.
통합 브랜치의 미완료 검증을 가능한 범위에서 수행하며 발견한 교차 플랫폼 회귀를 수정한 뒤 main 대상 PR을 생성한다.

## 범위 밖

PR 병합, main 직접 push, 배포, 부분 검증 상태의 Portfolio 등록, 실제 고객 코드 검증.

## 완료 조건

- [x] Notion Projects·Project Areas·Work Items·Dev Logs 중복 재조회 및 실제 등록
- [x] 프로젝트 역관계와 각 기록의 속성·본문 재조회
- [x] Portfolio 미등록 근거 유지
- [x] macOS VS Code Host 경로 문제 수정 및 Host 3단계 통과
- [x] Windows 절대 경로 번들 SQLite의 macOS 복원 문제 수정 및 관련 테스트 통과
- [x] 확장 단위 27개와 Python 비-GUI·C 회귀 검증
- [ ] 변경 기록·Notion 링크 커밋 및 원격 push
- [ ] main 대상 PR 생성과 Notion Dev Log 연결
- [ ] PR 상태를 작업 카드·STATUS·세션에 기록

## 진행과 검증

Notion 등록과 교차 플랫폼 수정·검증을 완료했다. 커밋·push·PR 생성 및 기록 갱신을 진행한다.

## 인수인계 — 다음 첫 행동

현재 변경을 커밋·push한 뒤 main 대상 PR을 생성하고, PR URL을 Dev Log와 저장소 기록에 반영한다.
