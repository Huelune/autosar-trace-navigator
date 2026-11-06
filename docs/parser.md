# C 구문 파서

## 사용법

설치된 Python 환경에서 네트워크 없이 사용할 수 있습니다.

```python
from autosar_trace_navigator.scanner import scan_sources
from autosar_trace_navigator.parser import parse_file

for source in scan_sources("test", exclude_paths=("parser_cases",)):
    result = parse_file(source.path)
    for function in result.functions:
        print(function.name, function.location.path, function.location.start_line)
    for branch in result.branches:
        print(branch.kind, branch.condition, branch.location.start_line,
              branch.parent_id, branch.chain_id, branch.uncertainty)
    for diagnostic in result.diagnostics:
        print(diagnostic.code, diagnostic.location.start_line, diagnostic.message)
```

`parse_file`은 바이트를 읽기만 합니다. 입출력 오류는 예외로 전달합니다.
`parse_source(bytes, path=...)`는 메모리 입력에 명시적인 경로를 부여하며 파일을 쓰지 않습니다.
`known_macros=("HEADER_MACRO",)`로 다른 곳에서 정의된 매크로 이름을 전달할 수 있습니다.
헤더를 자동으로 열거나 전처리기를 실행하지 않습니다.

## 결과 모델

- `FunctionDefinition`: 정의만 추출합니다. 함수 원형 선언은 제외합니다.
  이름, 정의 범위, 본문 범위, ID, 불확실성 사유를 기록합니다.
- `FunctionCall`: 전체 호출 표현식과 대상 표현식, 식별자 이름(있을 경우),
  소속 함수 ID와 분기 ID, 위치를 기록합니다. 반복 호출도 개별 기록합니다.
- `Branch`: if/else_if/else, 조건(else는 None), 본문 범위, 부모 분기 ID,
  체인 ID를 기록합니다. 중괄호로 감싼 else 내부의 if는 별도 중첩 분기입니다.
- `ParseDiagnostic`: 코드, 설명, 소스 범위를 기록합니다.

`SourceRange`의 경로는 절대 경로입니다. 라인과 바이트 열은 1부터 시작하며,
끝 위치와 바이트 오프셋은 끝 문자를 포함하지 않습니다. 다국어 문자 뒤의 열은
화면 문자 수와 다를 수 있습니다. 바이트 오프셋으로 원문을 정확히 잘라낼 수 있습니다.
분기 위치는 해당 팔의 키워드부터 본문 끝까지이고, 다음 else 팔은 포함하지 않습니다.
ID는 경로·구문 종류·시작 바이트에 기반하며 파일 수정 후에도 유지되는 세션 ID는 아닙니다.

## 확정하지 않는 내용

- `direct_candidate`는 식별자 형태 호출 후보입니다. 같은 이름의 함수 정의가
  있어도 실제 연결 대상으로 확정하지 않습니다. C 스코프, 링크, 함수 포인터,
  헤더 매크로 가림을 해석하지 않으므로 `unresolved_call_target`을 기록합니다.
- `macro`는 파일 내 정의 또는 전달된 이름과 일치하는 호출입니다.
  `unexpanded_macro`와 `MACRO_INVOCATION`을 기록하며 확장하지 않습니다.
  미제공 헤더 매크로는 unresolved 후보로 남을 수 있습니다.
- `indirect`는 `(*handler)()`나 `ops->run()` 같은 식 형태의 호출입니다.
- 전처리 구문이 있으면 보수적으로 해당 파일의 결과에
  `preprocessing_not_performed`를 기록합니다. #if의 비활성 대안도 추출될 수 있고,
  같은 이름의 함수 정의도 별도 위치와 ID로 보존합니다. include guard도 평가하지 않습니다.
- 객체 형태 매크로는 알려진 이름 참조를 불확실성으로 표시합니다. 임의의 미제공
  매크로를 식별하거나 매크로 안에서 생성되는 호출·분기를 완전히 추출할 수는 없습니다.
- 구문 오류나 누락 토큰은 `SYNTAX_ERROR`로 남기고 복구된 결과에도
  `file_has_syntax_errors`를 기록합니다. 매크로 기반 AUTOSAR 선언이 복구된 경우
  추출된 이름도 검토해야 합니다.
- UTF-8이 아닌 입력은 `NON_UTF8_SOURCE` 진단과 대체 문자로 표시합니다.
  원본 바이트 오프셋은 유지합니다.

Rte_Read/Write는 이 단계에서 호출 구문입니다. 공급자·소비자의 데이터 연결,
목표 분기의 실행 가능성, 분기를 통과할 입력값은 자동으로 해석하지 않습니다.
별도 [RTE Resolver](rte.md)가 호출 모델과 분리하여 이름 기반 데이터 연결 후보를 제공합니다.
실제 연결과 실행 순서를 확정하지 않습니다.

## 검증

`tests/test_parser.py`는 제품 API를 직접 사용하여 정의/선언 구분, 포인터 반환 선언,
직접·간접·반복 호출, 소속 분기, 중첩/체인 관계, 단일 문장과 주석,
매크로·전처리 조건, 구문 오류, 경로·라인·바이트 위치, 원본 무변경을 확인합니다.
기존 AUTOSAR 샘플의 6단계 호출 후보 경로와 목표 분기 10행도 검증합니다.

`test/parser_cases/`에는 컴파일을 목적으로 하지 않는 파서 전용 사례가 있습니다.
의도적인 오류 파일은 기존 C 실행 하네스와 정상 구문 검사에서 제외합니다.
