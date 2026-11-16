# ARCH-002 재검증 세션 — 2026-11-16T07:27:03Z

- 도구: codex
- 담당 별칭: Codex
- 작업 카드: [ARCH-002](../tasks/ARCH-002.md)
- 시작 브랜치: feat/bridge-contract
- 시작 커밋: 9139078
- 종료 상태: 요청 범위 검증 완료

## 이번 범위

이전 세션에서 중단된 GUI 포함 Python 전체 테스트와 미실행 VS Code Host·VSIX 검증을 현재 macOS 작업 브랜치에서 실행한다.

## 실제 변경

- 제품 코드는 변경하지 않았다. 성공한 재검증 결과만 작업 카드와 상태 문서에 반영했다.

## 실행한 검증

- 일반 샌드박스의 최소 `tk.Tk()` 생성은 exit 134. GUI 접근 권한을 부여한 동일 Python에서는 Tcl/Tk 8.6.17 창 생성·종료 성공. 이전 중단 원인은 이 실행 권한 경계로 판단한다.
- `.venv/bin/python -m unittest discover -s tests -v`: 202개 통과, 실패·skip 없음. 가상 C 실행은 기본 12, guarded value paths 6, large AUTOSAR 192, struct paths 6으로 총 216시나리오 통과.
- `VSCODE_EXECUTABLE_PATH='/Applications/Visual Studio Code.app/Contents/MacOS/Code' npm run test:host`: 기록 단계(실제 Python 엔진 후보·함수 검색 포함), 재시작 복원, Restricted Mode 차단 모두 통과. 종료 코드 0.
- `npm run package:vsix`: VSIX 22개 파일, 58.28 KB 생성. 패키지의 실행 JS에 v1 검사가 포함되고 테스트·Python 소스는 포함되지 않은 것을 확인.
- Git 작업 트리 clean, 브랜치와 원격 `9139078` 일치 확인(문서 갱신 전).

## 미검증·문제·결정

- VSIX 패키징 시 LICENSE 파일 없음 경고가 있었으나 패키징은 성공했다. 이번 범위의 실패로 취급하지 않는다.
- 사람이 화면을 직접 조작하는 사용성 확인, 다른 PC 설치, 실제 고객 코드·CT 실행은 현재 자동 검증과 구별한다. 민감한 현장 코드는 반입하지 않았다.
- uv CLI는 이 환경에서 발견되지 않아 잠금 기반 새 환경 재구성은 실행하지 않았다. 의존성 변경은 없다.

## 인수인계

- 다음 첫 행동: PR 검토·병합 여부를 결정한다.
- 미커밋 변경: 이 검증 기록과 카드·상태 문서를 커밋 예정.
- 전달 브랜치: `feat/bridge-contract`; 공유 커밋은 push 후 확인한다.
