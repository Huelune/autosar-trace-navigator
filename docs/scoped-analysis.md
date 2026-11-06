# 범위 분석과 함수 검색

```python
from autosar_trace_navigator.workbench import analyze_project

project = analyze_project(
    "test", include_paths=("src/BrakeControl.c", "include"),
    exclude_paths=("parser_cases",),
)
page = project.search_functions("brakecontrol src", offset=0, limit=100)
print(page.total, [function.name for function in page.functions])
```

- include_paths는 루트 기준의 실제 파일·폴더 또는 루트 내부 절대 경로다.
  와일드카드는 지원하지 않는다. 여러 범위는 합집합이며 제외가 우선한다.
- 미선택 하위 폴더는 탐색 중 진입 전에 가지치기한다. 경로 존재·루트 내부 여부를 검증한다.
- API의 빈 include_paths는 기존 호환을 위해 전체 루트를 뜻한다. GUI는 범위를 명시해야 한다.
- 한 작업의 기본 제한은 500파일, 파일당 4 MiB, 합계 소스 32 MiB다.
  제한을 넘으면 AnalysisLimitError이며 일부 결과를 정상 결과처럼 반환하지 않는다.
  이는 입력 바이트 예산이며 파서 트리·객체를 포함한 RAM 상한을 보장하지 않는다.
- 함수 검색은 함수명과 상대 파일 경로에서 대소문자를 구분하지 않고 모든 검색 토큰을 찾는다.
  빈 검색어는 결과가 없다. 기본 100개, API 최대 500개/페이지이며 전체 일치 수를 제공한다.
- 함수 이름·ID·호출 소속·RTE 소속과 검색 문자열은 분석 스냅샷별로 한 번 인덱싱한다.
  검색은 명시적 요청 시 인덱스를 순회한다. 디스크 영속 캐시나 변경 파일 증분 분석은 아니다.
- 선택 범위 전체는 여전히 파싱한다. 필요한 파일부터 범위를 지정하고, 외부 대상이 필요하면
  include_paths를 넓혀 다시 분석한다. 헤더는 자동으로 범위에 추가하거나 include를 따라가지 않는다.
- Workbench.project를 새 결과로 교체해도 목표와 조사 이력은 바뀌지 않는다. 범위를 좁혀
  현재 조사 함수가 빠지거나 메타데이터가 달라지면 후보를 제공하지 않는다.
- 미확인 호출이나 공급자 누락은 현재 분석 입력에 없거나 해석되지 않았다는 뜻이다.
  실제 시스템에 대상이 없다는 판정이 아니다. 이름 기반 후보의 기존 불확실성도 유지한다.

현재 검증은 가상 파일·550개 함수와 범위 확장 시나리오다. 실제 대형 고객 프로젝트의
성능을 보장하는 벤치마크는 아니며, 증분 캐시·취소·전체 심볼 인덱스는 후속 작업이다.
