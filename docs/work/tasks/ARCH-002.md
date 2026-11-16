# ARCH-002 — Python–VS Code 브리지 계약 v1 고정

- 상태: done
- 담당: Codex
- 브랜치: feat/bridge-contract
- 기준 커밋: f107194
- 최신 세션: [Codex 재검증 기록](../sessions/20261116T072703Z-codex-bridge-validation.md)

## 목적과 승인 범위

ARCH-001의 후속으로 브리지 요청·응답을 명문화하고 Python·확장 양쪽에서 같은 가상 코드와 기대 응답으로 계약을 검증한다.

## 범위 밖

제품/확장 저장소 분리, SQLite↔확장 JSON 변환, UI·저장 동작 변경, PR·병합·배포.

## 완료 조건

- [x] 버전·오류·위치·한도·불확실성 계약 문서화
- [x] 공통 가상 C fixture와 양쪽 계약 테스트
- [x] 지원하지 않는 버전 거부, 구버전 생략 호환
- [x] 브리지 관련 Python 테스트와 확장 단위 테스트
- [x] 전체 Python GUI 포함 테스트
- [x] VS Code Host 기록·재시작·Restricted Mode와 VSIX 패키징

## 진행과 검증

[브리지 계약](../../bridge-contract.md)과 [최신 재검증 세션](../sessions/20261116T072703Z-codex-bridge-validation.md)을 확인한다. GUI 접근 권한을 부여한 macOS 환경에서 Python 전체 202개(가상 C 216시나리오 포함), VS Code Host 세 단계와 VSIX 패키징을 검증했다.

## 인수인계 — 다음 첫 행동

이 브랜치의 PR 검토·병합 여부를 결정한다. 다른 PC 설치·고객 코드·실제 CT 검증은 별도의 현장 검증이다.
