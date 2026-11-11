# Codex 구현 지시서 — AUTOSAR Trace 기반 VS Code Branch Investigation Workspace

이 문서 전체를 기존 AUTOSAR Trace 저장소를 연 Codex에 전달한다. 다른 문서를 읽지 않아도 구현을 시작할 수 있도록 작성했다.

## 1. 이번 요청의 결과물

**기존 별도 프로그램의 화면을 개선하는 작업이 아니다. 새 결과물은 VS Code 확장이다.**

현재 AUTOSAR Trace의 Python 분석 엔진은 인터페이스를 통해 재사용한다. Tkinter 창을 VS Code에 삽입하거나 기존 프로그램 전체를 재작성하지 않는다. 사용자는 VS Code 안에서 조사 세션을 만들고, 코드 선택을 저장하고, 조사 트리를 클릭하여 이유를 확인하고 실제 소스로 이동한다. 기존 프로그램 창을 따로 실행할 필요가 없어야 한다.

이 문서는 계획 수립 요청을 넘어 **P0 확장의 실제 구현·검증·패키징**을 요청한다. 저장소 진단과 짧은 작업계획을 제시한 다음 구현을 진행하라. 이미 허용된 가역적 개발 작업마다 확인을 반복하지 말고 기본값으로 진행한다. 환경의 쓰기 권한·설치 승인 정책은 그대로 따른다. 완료하지 못한 UI나 검증을 완료했다고 보고하지 않는다.

## 2. 배경과 사용자 문제

사용자는 AUTOSAR C 소스(.c/.h), 생성 Rte_*.h, Rte_Read/Write 연계를 따라가며 SureSoft CT 2025 단위·통합 테스트에서 목표 분기를 통과시킬 입력·조건을 조사한다. 함수·분기 경로가 길고 앞뒤 이동·대체 경로 탐색이 많아, 조사 목적·현재 위치·가정·확인 결과를 잃기 쉽다.

기존 Trace는 함수와 RTE 연결 후보 탐색에 유용하다. 새 제품의 중심은 **사용자의 조사 흐름을 기록하고 재방문하는 것**이다. 그래프는 후순위다. 조사 트리 순서를 실제 실행 순서로 표현하지 않는다.

## 3. 기존 저장소와 확인된 사실

로컬 저장소 후보: `E:\01.Projects\autosar-trace-navigator`.

2026-11-10 진단 기준 커밋: `06f707e73f38bd3f7a737564eaeb4f7c9db484fd`. 당시 작업 트리 변경 출력은 없었다. **이는 과거 확인값이다. 작업 시작 시 현재 상태와 최신 지침을 다시 확인한다.**

| 실제 파일 | 확인한 기능과 재사용 원칙 |
|---|---|
| `src/autosar_trace_navigator/trace.py` | TraceManager, TraceSession, TraceStep에 목표·부모·이유·선택 위치·대체 경로가 있다. 새 기록을 위해 이 모델을 무작정 재설계하지 않는다. |
| `src/autosar_trace_navigator/workbench.py` | analyze_project, ProjectSnapshot.search_functions, Workbench.candidates/value_candidates/execution_candidates를 제공한다. GUI 독립 포트에서 호출한다. |
| `src/autosar_trace_navigator/models.py` | SourceRange는 1부터 시작하는 행과 바이트 열, 끝 exclusive다. VS Code는 0부터 시작하는 행·UTF-16 열이므로 변환이 필요하다. |
| `src/autosar_trace_navigator/storage.py` | TraceStore에 SQLite 저장·복원·revision 충돌 검사가 있다. DB schema version 1과 JSON snapshot format 1/2/3은 다른 개념이다. 기존 DB를 자동 변경하지 않는다. |
| `src/autosar_trace_navigator/rte.py` | RTE 연결은 별도 데이터 의존 후보다. 이름 기반 후보를 실제 wiring/실행 보장으로 해석하지 않는다. |
| `AGENTS.md`, `docs/architecture.md` | 가상 C 테스트, 소스 읽기 전용, GUI 독립 계층, 로컬 실행 원칙이 있다. 최신 내용을 먼저 읽는다. |

기존 Trace 모델은 함수·분기 모델을 요구하므로, 파일도 함수도 없는 수동 스니펫을 가짜 FunctionDefinition으로 만들어 넣지 않는다. 신규 조사 기록은 독립 도메인으로 두고 기존 엔진과 DTO로 연결한다.

이전 작업에서 제공한 `starter/investigation_bridge.py`는 기존 공개 API를 호출하는 첫 시제품이다. analyze/search/branches/candidates 테스트 5개만 통과했으며 **VS Code 확장, 값 출처 포트, 설치 가능한 완성품이 아니다.** 첨부돼 있다면 참고하되 누락돼도 P0는 구현할 수 있어야 한다. 엔진 코드를 복제하는 근거로 사용하지 않는다.

이전 환경에서는 Python 가상환경과 Node가 있었고 npm은 PATH에서 발견되지 않았다. 현재 도구를 다시 확인하고 발견 가능한 승인된 도구를 사용한다. 도구가 없으면 권한 정책에 따라 설치하거나, 가능한 구현과 검증을 마친 후 정확한 차단 항목을 보고한다.

## 4. 가장 먼저 완성할 두 흐름

### 흐름 A — 코드 선택 → 조사단계 저장

1. VS Code에서 가상 C/H 파일의 코드 범위를 선택한다.
2. 우클릭 ‘현재 조사에 추가’ 또는 `Ctrl+Alt+I`를 실행한다.
3. 명령 시작 순간의 문서 URI·문서 버전·선택 범위·선택 문자열을 캡처한다. 입력창을 띄운 뒤 활성 편집기를 다시 읽어 다른 코드를 저장하지 않는다.
4. 현재 목표가 없으면 목표 이름과 설명을 받고, 선택 위치를 수동 목표 분기 앵커로 사용한다. P0에서 파서로 분기 자동 식별을 요구하지 않는다.
5. 선택 이유만 필수로 입력한다. 취소·빈 이유는 Step을 생성하지 않는다. 목표 생성도 취소하면 부분 저장하지 않는다.
6. 현재 조사단계의 자식으로 저장하고 트리·상세를 갱신한다. 현재 단계가 없으면 루트 단계로 저장한다.
7. 코드 위치·스니펫·부모·순번·이유는 자동 캡처하고 나머지 정보는 나중에 수정할 수 있다.

### 흐름 B — 조사단계 클릭 → 이유 확인 → 소스 이동

1. 왼쪽 Investigation TreeView에서 단계를 클릭한다.
2. 상세 Webview에 선택 이유를 가장 먼저 표시한다.
3. 당시 목표 분기, 가정, 필요 조건, 도출 조건, 관찰, 결과, 다음 할 일, 저장 당시 스니펫·파일·범위를 표시한다.
4. 검증된 앵커라면 실제 VS Code 파일을 열고 해당 범위로 이동·강조한다.
5. 위치를 검증할 수 없으면 기록·스니펫은 정상 표시하고 ‘위치 확인 필요’ 또는 ‘연결된 파일 없음’을 명시한다. 옛 행 번호로 자동 이동하지 않는다.
6. 단순 클릭·복귀는 새 조사단계나 분석 관계를 만들지 않는다.

**위 두 흐름이 Extension Development Host에서 실제로 동작하는 것이 P0의 핵심 완료 조건이다.**

## 5. P0 범위와 화면

TypeScript VS Code Extension으로 구현한다. Python 프로세스 없이도 P0 전체가 동작해야 한다. 별도 웹 서버·독립 데스크톱 프로그램은 만들지 않는다.

- 왼쪽: Activity Bar의 Branch Investigation 뷰. 목표별 세션과 순번 있는 조사단계를 부모·자식 트리로 표시한다. 형제는 대체 경로이며 접기/펼치기를 지원한다.
- 중앙: 기존 소스 편집기. 이동 범위만 표시하고 원본 코드는 수정하지 않는다.
- 오른쪽: 상세 Webview. 이유·당시 목표·조건·결과·다음 할 일·스니펫을 조회·수정한다. 사용자 UI는 한국어로 제공한다.
- 상태: 조사 중 / 확인 / 보류 / 제외. 보류·제외 경로는 트리와 저장소에 유지한다.
- 별도 탐색 이력: 이전 위치 복귀 / 앞으로. 상위 조사로 이동과 구분한다.
- 최소 수동 스니펫 입력: 여러 줄 입력창에 Ctrl+V로 붙여넣어 이유와 함께 한 단계로 저장한다. 파일 미연결 상태로 저장할 수 있다. P0에서 자동 분류·일괄 단계화는 하지 않는다.
- 자동 저장·재시작 복구·저장 실패 안내를 제공한다.

기본값은 단일 workspace folder, 로컬 file URI, 단일 작성 창이다. 다중 루트·원격 URI는 자동 추측하지 않고 지원 범위를 안내한다. 로컬 file URI의 snippet-only 기록은 허용한다. 다른 종류의 문서 내용도 수동 붙여넣기로 기록할 수 있지만 위치 열기는 지원하지 않는다.

## 6. 아키텍처와 디렉터리 기본안

```text
extensions/branch-investigation/
  package.json
  tsconfig.json
  .vscode/launch.json
  .vscode/tasks.json
  src/
    extension.ts
    domain/model.ts
    domain/validation.ts
    domain/investigationService.ts
    storage/jsonStore.ts
    navigation/anchorResolver.ts
    navigation/history.ts
    ui/investigationTree.ts
    ui/detailsPanel.ts
    ui/snippetInput.ts
    adapters/traceAnalysisPort.ts
  test/
  README.md
docs/branch-investigation/
```

역할 분리:

```text
TreeView / Webview / Commands
          ↓
InvestigationService ──→ JSON InvestigationRepository
          ↓ (P1, 기본 비활성)
TraceAnalysisPort → 승인된 Python subprocess → 기존 Workbench/ProjectSnapshot

Source Navigation → AnchorResolver + NavigationHistory
```

설명·제품 UI·README는 한국어로 작성한다. UI는 조사 서비스와 기록 저장소를 사용하고, P1에서만 기존 Python 분석에 연결한다. 소스 이동은 별도 방문 이력으로 관리한다.

확장의 소스 위치는 VS Code UTF-16 기준으로 저장한다. Python의 바이트 위치는 P1 adapter 경계에서 원본 바이트·인코딩을 고려해 변환하고, 모호한 변환을 성공으로 처리하지 않는다. 기존 소스 인코딩을 알 수 없으면 이유를 표시한다.

## 7. 핵심 데이터 계약

아래 필드를 기준으로 실제 타입·검증을 구현한다. ID는 UUID, 시간은 UTC ISO 문자열, 편집기 범위 끝은 exclusive다.

| 모델 | 필수 개념 |
|---|---|
| InvestigationGoal | id, 제목, 목표 BranchTarget, createdAt/updatedAt |
| BranchTarget | anchorId, branch kind(if/else_if/else/manual), 조건식·필요 진릿값(선택) |
| InvestigationStep | id, goalId, parentStepId, sequence, reason, 당시 goalSnapshot, hypothesis, observation, requiredConditions, derivedConditions, result, nextAction, status, codeAnchorId, snippet, 시각 |
| CodeNode | id, repositoryId, identityKey, symbol(선택). 함수·코드 실체의 공유 식별자 |
| CodeAnchor | id, codeNodeId, fileUri/relativePath/symbol/revision(선택), range(선택), textFingerprint, 주변 문맥, 위치 상태 |
| NavigationEvent | id, goalId/stepId(선택), from/to anchor, action(select_step/open_source/back/forward), 시각 |
| RelationEdge | id, fromStepId, toStepId, type(call/read/write/data_dependency/manual), 근거, uncertainty |
| Evidence | id, text, kind(source_fact/hypothesis/ct_observed), anchorId(선택), CT 실행 라벨·관찰 시각·메모(실측일 때 필수) |
| WorkspaceDocument | schemaVersion, revision, 위 모델 목록, currentGoalId/currentStepId |

한 함수를 여러 번 조사해도 가능한 경우 CodeNode는 공유하되 Step과 방문 이벤트는 각각 저장한다. P0는 파서 없이 함수 경계를 알 수 없으므로 동일 파일·정확히 동일한 범위·fingerprint에 대해서만 보수적으로 코드를 공유한다. 범위가 다르면 임시 code site identity를 사용한다. P1에서 symbol을 확인한 뒤 기존 기록을 잃지 않는 연결/병합 절차를 제공한다. 단순히 snippet 문자열이 같다는 이유로 서로 다른 파일의 노드를 합치지 않는다.

Step sequence는 목표 안에서 증가하는 생성 순번이다. 부모 선택은 같은 목표의 이전 Step만 허용하고 순환을 금지한다. Step 상태 ‘확인’이 CT 실측 확인을 의미하지는 않는다. CT 실측은 별도 Evidence로만 기록한다. 원본 분석 사실과 사용자 가설을 혼합하지 않는다.

## 8. 명령 계약

접두어는 `branchInvestigation.`을 사용한다.

| 명령 | 의미 |
|---|---|
| createGoal / switchGoal | 목표 생성 / 현재 목표 전환 |
| addSelection | 선택 코드를 이유와 함께 현재 조사에 추가 |
| addSnippet | Ctrl+V 가능한 여러 줄 입력 → 한 스니펫 단계 생성 |
| openStep / editStep | 상세 조회·소스 이동 / 조사 정보 수정 |
| setStatus | 보류·제외 포함 상태 수정 |
| goParent | 부모 조사단계 선택 |
| navigateBack / navigateForward | 저장된 방문 이력 커서 이동 |
| repairAnchor | P0는 파일·범위 수동 재연결, P1은 후보 복구 |

키 바인딩은 확장 뷰 또는 C/H 편집기 문맥으로 한정하고 사용자 변경을 허용한다. 선택 없음·조사 없음·지원 안 되는 URI에는 설명 있는 안내를 보여 준다. 전체 VS Code의 Ctrl+V를 가로채지 않는다.

## 9. 저장과 앵커 정책

신규 저장 위치: 프로젝트 로컬 `.branch-investigation/workspace.json`. 기존 SQLite와 분리한다. Git 제외 권장 안내를 제공하고 저장소 지침에 맞는 경우 제외 설정을 추가한다. 자동 내보내기·동기화·클라우드 저장 기능을 만들지 않는다.

변경은 직렬 큐에서 검증한 복제본에 적용한다. 동일 디렉터리 임시 파일→flush/fsync→원자 교체, 마지막 정상 backup, revision 검사, 단일 writer 잠금을 구현한다. 잠금은 배타적으로 획득하고 기존 잠금을 임의 삭제하지 않는다. 비정상 종료 잠금은 소유 프로세스 확인 또는 사용자가 명시적으로 복구하는 절차를 제공한다. 동시 작성 감지 시 조용히 덮어쓰지 않는다. 실제 OS 파일 교체 동작을 검증한다.

저장 실패 시 dirty·오류를 표시하고 재시도를 지원한다. 손상 JSON은 보존하고 backup 복구 선택을 제공한다. 미래 schemaVersion을 임의 수정하지 않는다. 이력 보존 개수·파일 크기에 현실적인 한도를 정하고 UI가 멈추지 않게 한다.

P0 앵커는 저장 범위의 현재 텍스트와 fingerprint가 일치할 때만 자동 이동한다. 파일 없음·불일치·수동 스니펫은 이동 불가 상태로 보여 주고 사용자가 직접 재연결할 수 있다. P1은 동일 파일의 스니펫·주변 문맥 검색으로 후보를 제안하되 유일 후보여도 확인 후 앵커를 갱신한다. 기존 snippet과 당시 목표를 덮어쓰지 않는다. 편집기에 미저장 변경이 있으면 디스크가 아닌 열린 문서 텍스트로 위치를 검증한다.

실제 파일 이동과 단계 선택을 방문 이력에 남긴다. back/forward 처리 중 기록을 재삽입해 무한 루프를 만들지 않는다. 복귀 후 다른 위치로 이동하면 forward 분기를 정리한다. 탐색 이력을 데이터 출처 관계로 변환하지 않는다.

## 10. 보안·현장 제약

고객사 원격 PC의 소스/CT 자료를 다른 PC로 복사하거나 AI에 전달할 수 없다. 이 확장은 승인 PC 안에서만 로컬 실행·저장해야 한다. 개발은 기존 가상 소스로 수행한다.

- 네트워크 호출·AI·텔레메트리·클립보드 감시·보안 우회·고객 코드 반출 기능 없음.
- Workspace Trust에 맞게 미신뢰 workspace에서 활성 작업을 제한한다.
- Webview CSP·nonce·HTML escape·메시지 allowlist와 runtime validation 적용. 코드·경로를 명령이나 HTML로 실행하지 않는다.
- 분석·기록 파일 경로는 workspace realpath 경계를 확인한다. 심볼릭 링크로 경계를 벗어나는 접근을 자동 허용하지 않는다.
- Python 연동은 P1 기본 비활성, 명시적으로 설정한 승인 인터프리터만 shell=false argv로 실행. stdin/stdout JSON, 요청 ID, 크기 제한, timeout·취소 적용. 로컬 TCP 서버를 만들지 않는다.
- 원본 C/H는 읽기 전용. 고객 코드·스니펫을 출력 로그·원격 오류 수집에 포함하지 않는다.
- VS Code 사용 가능 여부, 오프라인 VSIX 설치 정책, Python 실행 승인, 로컬 저장/보존 정책은 **현장 배포 전 확인 항목**이다. 이 항목을 사용자에게 전부 물어본 뒤 개발을 시작하는 방식은 피한다.
- AI가 필요 없는 로컬 런타임과, 개발 단계의 Codex 사용을 구별한다. 고객 소스를 Codex에 제공하라고 안내하지 않는다.

## 11. 단계별 진행과 완료 기준

### P0 — 이번에 실제 구현할 범위

1. **진단·확장 뼈대**: 지침/현재 변경/도구 확인, TypeScript 빌드와 F5 Extension Development Host 구성. 확장 뷰·명령 등록.
2. **도메인·저장**: 데이터 모델·runtime validation·JSON 저장·복구·단일 writer 제한. 사용자 DB를 사용하지 않는 테스트.
3. **선택 저장 E2E**: 목표 생성→C/H 선택→이유→Step 저장→트리 표시. 취소 시 무변경.
4. **클릭·소스 이동 E2E**: 상세·이유·당시 목표·스니펫, 앵커 확인과 실제 범위 강조. 없는 파일도 기록 조회 가능.
5. **조사 계속하기**: 메모·조건·결과·다음 할 일 편집, 보류·제외, 부모 복귀, 대체 형제 생성, 독립 방문 back/forward, 수동 스니펫 붙여넣기.
6. **복원·검증·배포물**: 재시작·오류 복구 검증, README, 오프라인 설치용 VSIX와 수동 확인 절차. 패키징 도구를 사용할 수 없으면 소스 구현 완료와 VSIX 미생성을 구별한다.

첫 단계의 계획만 제시하고 멈추지 말고 가능한 P0 작업을 완료한다. 기존 프로젝트 지침이 자동 커밋을 요구하면 검증한 변경만 그 규칙에 따라 커밋하며 원격 푸시는 하지 않는다.

### P1 — P0 이후 계획, 이번 완료 주장에 포함하지 말 것

- 함수명/경로/조건식/여러 줄 코드/경로 목록 일괄 붙여넣기 → 분류·분할 미리보기 → 사용자 확인 후 단계화.
- 목표·조건·이유 검색과 상태 필터.
- 기존 Python 분석 엔진 연동, 범위 제한 검색, 호출/RTE/값 출처/실행조건 후보 조회.
- 후보 선택→이유→새 Step/RelationEdge. 이름 후보와 실제 실행 사실 구별.
- 코드 변경 후 앵커 후보 복구·모호한 일치 선택.
- 기존 SQLite 세션 읽기 전용 import. 기존 DB 양방향 동기화 제외.

### P2 — 후속

대규모 범위·캐시·성능 개선, 보조 그래프. CT 파일 파싱·CT 자동 조작·커버리지 자동 수집·입력 자동 적용·실행 가능성 증명은 별도 요청 전까지 제외한다.

## 12. 검증할 실제 사용 시나리오

가상 AUTOSAR 코드에서 다음을 수동 조사 기록으로 재현한다. P0에서 RTE 후보는 사용자가 직접 코드를 열어 선택하고, P1에서만 엔진 조회를 연결한다.

1. 목표 else 선택→‘정상 경로 통과’ 목표. else 조건식을 임의로 만들지 않고 앞선 조건들이 거짓이어야 한다는 필요 조건을 기록.
2. Rte_Read 위치 추가→이유 ‘분기에 쓰이는 입력 출처 확인’.
3. Writer 후보 코드 추가→가설 ‘이 값이 읽힐 가능성’, 연결·초기값·Runnable 순서·갱신 미확인 표시.
4. 해당 경로 보류→다음 할 일 ‘초기화와 갱신 순서 확인’.
5. 상위 조사단계로 이동→다른 입력·반환값 조사단계를 형제로 추가.
6. CT에서 사람이 확인한 입력·분기 결과를 실행 라벨·시각·메모와 함께 실측 근거로 기록. 자동 CT 실행 없음.
7. 확장/VS Code 재시작→목표·이유·보류 경로·대체 경로·스니펫·현재 조사 복원.

## 13. 필수 검증과 최종 보고

단위 테스트는 모델 참조/순환/목표 경계, CodeNode 공유와 Step 독립, evidence 구별, 방문 이력, 저장 실패·충돌·손상·버전 거부를 검증한다. 단순 화면 문구를 반복 검사하는 테스트보다 실제 데이터 손실·잘못된 이동을 막는 검증을 우선한다.

Extension Host 통합 또는 수동 검증은 두 핵심 E2E, 한글·이모지·CRLF·끝 exclusive, 이유 입력 중 활성 편집기 변경, 파일 삭제/변경, 수동 스니펫, 보류 후 형제 경로, restart, back이 새 Step/Edge를 만들지 않는 것을 확인한다. P1 Python 좌표 변환 테스트는 P0 테스트와 구별한다.

기존 엔진을 변경하지 않았다면 무관한 전체 회귀를 불필요하게 반복하지 않는다. 변경했다면 해당 모듈과 기존 영향 경로 테스트를 실행한다. 모든 테스트는 가상 C와 임시 저장소를 사용한다.

최종 보고에 다음을 포함하라.

1. 구현된 것이 **VS Code 확장**임을 명시하고 구현한 사용자 흐름을 설명.
2. 변경 파일, 기존 엔진 재사용 경계와 기존 프로그램 영향.
3. 실제 실행한 빌드·테스트·Extension Host·패키징 결과, 미실행 검증과 이유.
4. F5 실행 방법, VSIX 위치/오프라인 설치 방법, 가상 C로 5분 내 확인하는 절차.
5. P0 완료/남은 항목, P1 후속 작업, 현장 배포 전 정책 확인 항목.

**수용 기준: 사용자가 VS Code에서 코드를 선택해 이유와 함께 저장하고, 조사 트리에서 그 단계를 다시 클릭하면 왜 선택했는지 확인하면서 정확한 소스 위치로 돌아갈 수 있어야 한다.**
