# TASK-007 — 검증된 작업 브랜치 자동 push 정책

- 상태: done
- 담당: Codex
- 브랜치: fix/feature-branch-integration
- 기준 커밋: c9391460d11162ef8f7fbe9ef40e3e9ca551ba9d
- 생성 UTC: 2026-11-11T23:00:52+00:00
- 최신 세션: [Codex 작업 기록](../sessions/20261111T230052Z-codex-auto-push.md)

## 목적과 승인 범위

사용자 요청에 따라 별도 금지 지시가 없으면 검증·커밋한 변경을 현재 작업 브랜치에 자동 push한다.
기존 미공유 통합 브랜치도 원격에 공유하고 Git·Notion 준비 문서의 반영 상태를 실제 상태와 일치시킨다.

## 범위 밖

main 직접 push, PR 생성·병합, 배포, Notion 페이지 생성·수정.

## 완료 조건

- [x] 저장소 `AGENTS.md`에 기본 push 정책과 외부 변경 경계 기록
- [x] `fix/feature-branch-integration` 원격 브랜치 생성 및 upstream 연결
- [x] STATUS·TASK-005·Notion 등록 준비안의 Git 반영 상태 갱신
- [x] PR·main·Portfolio 상태를 실제보다 앞서 기록하지 않음
- [x] 변경 문서 형식과 Git 상태 검증

## 진행과 검증

현재 통합 브랜치를 `origin/fix/feature-branch-integration`에 push하고 운영 규칙과 관련 문서를 갱신했다.

## 인수인계 — 다음 첫 행동

이후 검증된 커밋은 사용자가 금지하지 않으면 같은 작업 브랜치에 자동 push한다.
PR 생성·병합, main 직접 push와 배포는 계속 별도 요청을 확인한다.
