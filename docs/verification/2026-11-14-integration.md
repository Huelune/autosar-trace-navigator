# 최신 main 통합 자동 검증 — 2026-11-14

기준: main `25d6e34`, 통합 브랜치 `codex/integrate-scale-navigation`.
기존 로컬 한도/긴 경로 개선만 선택 이식했다. 최신 함수 검색·결과 캐시·갈래 묶음을 보존했다.
export 브랜치는 포함하지 않았다. 고객 자료와 Computer Use는 사용하지 않았다.

## 실행 환경과 실제 결과

Windows x64, Python 3.14.3, uv 0.13.7, Node 22.23.4, VS Code 1.145.2.
캐시를 이용한 오프라인 uv sync --locked --group test 및 npm ci로 이 통합 체크아웃을 구성했다.

| 검사 | 실제 실행 명령 | 결과 |
|---|---|---|
| Python 전체 | `.venv/Scripts/python -m unittest discover -s tests -v` | 201개 통과, 실패/skip 0 |
| 가상 C 실행 | 위 unittest에 포함된 Zig 컴파일/실행 | 기본 12 + 대형 192 + 계산 조건 6 + 구조체 6 = 216개 통과 |
| 확장 단위 | 확장 폴더 `npm test` | 40개 통과, 실패/skip 0 (승격 실행) |
| VS Code Host | 확장 폴더 `npm run test:host` | record/restart/untrusted 세 단계 통과 |
| 패키지 | 확장 폴더 `npm run package:vsix` | 생성 후 release VSIX 갱신 |
| 산출물 감사 | `python scripts/verification/audit_vsix.py extensions/branch-investigation` | manifest·17개 runtime JS·README 일치, 개발 파일·잘못된 상위 경로 링크 없음 |
| 정적 변경 검사 | `git diff --check` | 통과 |

Host는 실제 Python 후보 조회/함수 검색, 결과 캐시 재사용과 C/H 변경 무효화, 설정 변경 후 한도 오류 및 복구,
취소 시 기록 보존, 단계 검색·일괄 추가·선택 코드 이유, 소스 스크롤·사이드바 유지와 저장 복원을 검증한다.
40단계/19개 대안에서 현재 경로 깊이 ≤2, 전체 갈래 보존, 상단 목표·위치·이유,
현재 단계 찾기/보기 전환의 JSON 무변경, 다른 경로 검색과 원래 코드 재방문을 확인했다.

초기 검증 중 함수명 오기(Consume → Consumer)를 고쳤다. 비승격 Node 단위 실행의 symlink 1개 skip은
승격 전체 실행에서 해소했다. 긴 경로 Host에서 다른 사이드바가 열린 상태의 현재 단계 찾기가 행을 선택하지 못해,
명시적 찾기 명령에서 조사 트리를 먼저 열도록 수정한 후 전체 Host를 통과했다.

## 산출물

`release/branch-investigation-0.1.0.vsix`: 59685 bytes.
SHA-256: `8751881d91183700c55515481cc6827fb35b39657b558dac809a7e68e761dac6`.
감사 스크립트는 설치하거나 UI를 조작하지 않고 압축 내부와 현재 컴파일 결과를 비교한다.

## 미검증과 한계

- 602파일 fixture는 범위/한도와 원본 무변경 회귀 검사다. 실제 회사 프로젝트 성능·매크로·RTE wiring 검증은 아니다.
- 40단계 fixture는 조사 표시 테스트이며 C의 40함수 실행 또는 CT 조건 충족 증명이 아니다.
- 전체 갈래 모드는 원래 분기 계층을 보존하므로 중첩 분기에 따라 깊어질 수 있다. 얕은 깊이 보장은 현재 경로 모드에 적용된다.
- 수동 화면 육안 확인, 사용자 실사용, 새 PC·다른 OS 및 Marketplace 배포는 수행하지 않았다.
- 실행 중 네트워크 의존성을 추가하지 않았다. 이 PC의 오프라인 의존성 캐시를 사용했으며 다른 PC의 캐시 준비를 보장하지 않는다.

[다음 개선 후보](../work/IMPROVEMENTS.md)는 제안이며 구현 승인 전이다.
