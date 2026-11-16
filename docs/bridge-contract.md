# Python 분석 브리지 계약 v1

`bridge.py`와 VS Code 확장의 `traceAnalysisPort.ts` 사이의 로컬 프로세스 계약이다. Python 패키지와 확장은 각각 배포할 수 있지만, 이 계약과 [공통 fixture](../test/bridge_contract/expected.json)가 호환성 기준이다. Tkinter·SQLite·네트워크는 이 경계에 포함되지 않는다.

## 실행과 버전

- 설정된 Python으로 `python -I -m autosar_trace_navigator.bridge`를 실행한다. stdin에 UTF-8 JSON 문서 1개를 주고 stdout에서 ASCII로 이스케이프된 JSON 문서 1개를 읽는다. stderr와 예외 문구는 사용자에게 노출하지 않는다.
- 요청의 `protocolVersion`은 정수 `1`이다. 생략한 구버전 호출은 v1로 간주한다. 응답은 성공·실패 모두 `protocolVersion: 1`을 포함한다. 버전 필드가 없는 구버전 응답도 v1 형태로 파싱하되, 다른 버전은 응답 전체를 거부한다.
- 지원하지 않는 요청 버전은 `invalid_request`다. 형식 변경이 필요하면 v2 계약과 양쪽 fixture 검증을 먼저 추가한다. 구버전 필드를 임의로 다른 의미로 재사용하지 않는다.
- 처리한 오류도 종료 코드 0이며 `ok: false`로 구분한다. 예상하지 못한 내부 오류만 종료 코드 1과 `internal`을 반환한다.

## 요청

공통 필드: `root`는 절대 경로인 분석 루트, `includePaths`는 루트 안의 명시적 경로 배열이다. 빈 배열은 루트 전체다. `excludePaths`는 선택적 경로 배열이며 glob이 아닌 파일·디렉터리 경로다. include/exclude는 루트 밖으로 나갈 수 없다. 선택 범위의 C/H 파일만 읽고 원본은 바꾸지 않는다. 심볼릭 링크는 건너뛴다.

| 작업 | 추가 필드 | 의미 |
|---|---|---|
| 관련 후보 | `file`, `line`, 선택적 `character` | `file`은 루트 상대 경로. `line`과 `character`는 0부터 시작하며 `character`는 UTF-16 코드 단위. `character`가 없으면 함수 단위 후보만 조회한다. `op` 생략이 현재 호환 형식이다. |
| 함수 목록 | `op: "functions"` | 선택 범위의 함수 정의를 이름순으로 반환한다. 검색·필터는 확장이 수행한다. |

선택적 `limits`의 기본값은 `maxFiles: 500`, `maxSourceBytes: 33554432`, `maxFileBytes: 4194304`다. 각 값은 양의 정수이며 상한은 각각 10,000개, 268,435,456바이트, 16,777,216바이트다. 요청 전체는 최대 1,048,576바이트다. 한도 초과 시 부분 결과 없이 `analysis_limit`이다. 확장은 프로세스당 기본 60초 제한과 stdout 8,388,608바이트 제한을 적용하고 취소할 수 있다. 이 세 제한의 실패는 각각 `timeout`, `output_limit`, `cancelled`이며 Python 응답 코드가 아니라 확장 로컬 오류다.

## 응답

`related` 성공은 `ok`, `protocolVersion`, `function`(`{name}` 또는 `null`), `variable`(추적 가능한 커서 접근식 또는 `null`), `notes`, `candidates`, `truncated`를 반환한다. `functions` 성공은 `ok`, `protocolVersion`, `functions`(`{name, signature}` 배열), `truncated`를 반환한다. 관련 후보는 최대 200개, 함수 정의는 최대 5,000개이며 초과 시 잘린 결과에 `truncated: true`를 붙인다. 미발견은 선택 범위 안에서만 미발견이라는 뜻이다.

위치 객체는 `{path, startLine, endLine, startCharacter, endCharacter, text}`다. `path`는 루트 상대 POSIX 경로, 줄과 UTF-16 열은 0부터 시작한다. `text`는 해당 소스 범위의 원문이다. UTF-8로 안전하게 변환할 수 없거나 텍스트가 20,000자를 넘으면 열·텍스트를 모두 `null`로 두므로 확장이 추정 열로 이동하면 안 된다. 함수 `signature`는 본문 전 선언 부분을 가리킨다.

후보는 `{relation, label, functionName, uncertainty, requiredTruth, evidence, target}`다. `relation`은 `value`, `execution_condition`, `call`, `rte_data` 중 하나다. `evidence`는 근거 위치, `target`은 다음 조사 위치 또는 `null`이다. `requiredTruth`는 실행 조건에서만 도달에 필요한 참·거짓이며 조건이 실제 성립함을 증명하지 않는다. 그 외 관계에서는 `null`이다. `uncertainty`와 `notes`는 추정·미해석 이유 코드다. 이름 기반 호출/RTE 후보, 미해석 매크로, 범위 밖 대상은 확정된 연결로 바꾸지 않는다. 후보는 사용자가 선택하기 전 조사 단계가 아니다.

오류 응답은 `{ok: false, protocolVersion: 1, error}`다. `analysis_limit`에는 `limitDetails: {metric, observedAtLeast, limit}`를 붙인다. `metric`은 `files`, `source_bytes`, `file_bytes` 중 하나다. 안정 오류 코드는 `invalid_request`, `analysis_limit`, `scope_not_readable`, `file_not_in_scope`, `internal`이다. 확장 쪽의 `python_not_runnable`, `timeout`, `cancelled`, `output_limit`, `invalid_response`는 프로세스/응답 처리 오류다. 절대 경로·원본 소스·예외 메시지를 오류에 싣지 않는다.

## 변경 검증

공통 가상 C 코드 `test/bridge_contract/sample.c`와 기대 응답 `expected.json`을 Python의 실제 격리 프로세스 테스트와 확장의 파서 테스트가 함께 사용한다. 브리지나 어댑터 변경 시 Python `tests/test_bridge.py`와 확장 `npm test`를 모두 실행한다. UI·저장 흐름을 바꾸는 경우에만 별도로 VS Code Host를 실행한다. 공통 fixture는 고객 소스가 아니며 실제 AUTOSAR 연결을 증명하지 않는다.
