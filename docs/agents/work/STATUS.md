# 현재 상태

## 이번 작업

[DOCS-001](tasks/DOCS-001.md): 에이전트 문서와 제품 문서를 분리하고 기록 생성기·링크를 정리한다.
상태와 최신 세션은 작업 카드에서 확인한다. 기준 커밋은 `21e6fcf`, 작업 브랜치는 `codex/agent-docs-layout`이다.
원격 공유 여부는 실제 Git 상태와 최신 세션을 확인한다.

## 최근 제품 작업

| 작업 | 구현과 검증 근거 |
|---|---|
| [TRACE-002](tasks/TRACE-002.md) | 선택 경로·코드 중심 UI와 호출자 인수 예시. [최종 검증](../history/verification/2026-11-15-origin-flow.md) |
| [TRACE-001](tasks/TRACE-001.md) | 전체 출처 미리보기. [검증과 해석 한계](../history/verification/2026-11-14-origin-preview.md) |
| [SCALE-003](tasks/SCALE-003.md) | 분석 과부하 측정. [보고서](../history/verification/2026-11-14-overload.md) |
| [SCALE-002](tasks/SCALE-002.md) | 5,125파일 독립 가상 프로젝트. [생성·사용법](../../../test/mega_autosar/README.md) |

큰 예시의 uint16 캐스트는 미해결이다. 조건 경로의 입력 후보 도달을 값 출처 해결로 해석하지 않는다.
이 표는 이전 작업의 근거이며 이번 PC/세션의 재검증 결과가 아니다. 브랜치 반영 상태는 실제 Git으로 확인한다.

## 이어받기

1. 배정 작업 카드와 최신 세션, 실제 Git 상태·코드를 대조한다.
2. [작업 절차](README.md)에 따라 새 세션을 작성한다. [개선 후보](IMPROVEMENTS.md)는 승인 전 제안이다.
3. 과거 개요가 필요하면 [정리 전 상태 기록](../history/STATUS-2026-11-15.md)을 확인한다.
