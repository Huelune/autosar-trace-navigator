# ARCH-002 세션 — 2026-11-16T07:09:27Z

- 도구: codex
- 담당 별칭: Codex
- 작업 카드: [ARCH-002](../tasks/ARCH-002.md)
- 시작 브랜치: docs/component-boundaries
- 시작 커밋: f107194
- 작업 브랜치: feat/bridge-contract
- 종료 상태: 계약 검증 완료, GUI 포함 전체 테스트 재실행 필요

## 이번 범위

Python 브리지와 확장 포트의 v1 계약을 문서화하고, 동일한 가상 C fixture로 양쪽 회귀 테스트를 만든다. 사용자 데이터·실제 고객 코드는 사용하지 않았다.

## 실제 변경

- 요청·응답에 `protocolVersion: 1`을 적용했다. 필드 생략 요청·응답은 기존 v1로 허용하고 다른 버전은 거부한다.
- UTF-16 위치, 경로·분석·프로세스 한도, 오류와 불확실성 의미를 문서화했다.
- 실제 격리 Python 프로세스 출력과 확장 파서가 같은 `test/bridge_contract` 기대 응답을 검증한다.

## 실행한 검증

- `.venv/bin/python -m unittest discover -s tests -p 'test_bridge*.py' -v`: 20개 통과.
- `npm ci`: 157개 패키지 설치 완료.
- `npm test`: 확장 단위 테스트 41개 통과.
- `.venv/bin/python -m unittest discover -s tests -v`: 첫 실행에서 기존 응답 키 기대값 불일치 1건을 확인·수정했으나, 이어 `test_execution_values.ExecutionGuiTests`의 Tk 시작 시 프로세스가 exit 134로 중단. 수정 후 전체 재실행은 하지 못했다.

## 미검증·문제·결정

- GUI 포함 전체 Python 테스트와 VS Code Host는 이번 세션에서 통과했다고 기록하지 않는다. Host는 UI·저장 동작 변경이 없어 필수 범위 밖이다.
- 문서/계약 자체는 양쪽 집중 테스트로 검증했으나, GUI 환경이 있는 세션에서 전체 회귀를 재시도해야 한다.

## 인수인계

- 다음 첫 행동: GUI 가능한 macOS 세션에서 전체 Python 테스트를 재실행한다.
- 미커밋 변경: 커밋 전 최종 diff·상태를 확인한다.
- 전달할 브랜치: `feat/bridge-contract`; 공유 커밋은 push 후 확인한다.
