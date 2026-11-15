# 작업 안내

Codex·Claude Code·사람이 공유하는 개발 지침과 진행 기록을 이 폴더에서 관리한다.
제품 사용법은 루트 README와 일반 docs 문서에 둔다. 이 폴더도 Git으로 공유되며 비공개 저장 공간은 아니다.

## 시작할 때 읽는 순서

1. [공통 규칙](rules.md): 설계·검증·커밋·원격 공유 기준.
2. [현재 상태](work/STATUS.md): 진행 중인 작업과 최신 인계 위치.
3. 배정된 `work/tasks/<ID>.md`와 그 카드의 최신 세션.
4. 실제 Git 상태·코드. VS Code 작업은 [원본 명세와 구현 결과](vscode.md)도 확인한다.

기록 전체를 매번 읽지 않는다. 다른 작업 카드나 과거 기록은 현재 작업과 관련될 때 확인한다.
진행 기록과 실제 Git/코드가 다르면 현재 확인한 사실을 새 세션에 남긴다.

## 기록 위치

| 위치 | 용도 |
|---|---|
| [CHANGELOG.md](CHANGELOG.md) | 문서·작업 절차 등 개발 운영 변경 요약 |
| [work/README.md](work/README.md) | 카드·세션 작성과 인수인계 절차 |
| `work/tasks/`, `work/sessions/` | 해야 할 일과 실제로 한 일 |
| [work/manual-checks.md](work/manual-checks.md) | 다른 PC에서 확인할 항목 |
| [history/CHANGELOG.md](history/CHANGELOG.md) | 정리 전 상세 변경 이력 원문 |
| `history/verification/` | 실제 검증 보고서와 측정 결과 |
| [policies/commit-convention.md](policies/commit-convention.md) | 커밋 규칙 |
| [tool-setup.md](tool-setup.md), [vscode.md](vscode.md) | 도구별 지침 불러오기와 확장 작업 진입 안내 |
| [integrations/notion-registration.md](integrations/notion-registration.md) | 기존 Notion 등록 기준과 결과 |

제품 동작이 바뀌면 루트 `CHANGELOG.md`에 사용자 관점의 요약을 남긴다.
작업 절차·인계 문서만 바뀌면 이 폴더의 `CHANGELOG.md`에 남긴다. 상세 명령·수치·미검증은 세션 또는 검증 보고서에 둔다.
기존 세션의 내용과 원본 구현 지시서를 요약으로 대체하거나 삭제하지 않는다.

## 기존 경로에서 이어받기

`docs/work/` → `docs/agents/work/`, `docs/ai/` → `docs/agents/policies/`,
`docs/verification/` → `docs/agents/history/verification/`로 이동했다.
루트 `todo.md`는 `work/manual-checks.md`, 상세 규칙은 `rules.md`에서 이어간다.
기존 `docs/verification.md`와 VS Code P0 검증 보고서도 `history/verification/`에 보존한다.
작업 생성 명령은 그대로다: `python scripts/worklog.py list`, `new`, `start`.
새 카드·세션은 새 경로에만 생성한다.
