# RTE Resolver (이름 기반 후보 분석)

명시적 `Rte_Read_<suffix>` 및 `Rte_Write_<suffix>` 접근 구문을 수집하고,
동일한 전체 suffix의 쓰기 지점을 읽기 지점의 공급자 후보로 반환한다.
실제 AUTOSAR 배포 연결을 확정하는 Resolver는 아니다.

```python
from autosar_trace_navigator.scanner import scan_sources
from autosar_trace_navigator.parser import parse_file
from autosar_trace_navigator.rte import parse_rte_header, resolve_rte

sources = scan_sources("test", exclude_paths=("parser_cases",))
parsed = [parse_file(source.path) for source in sources]
headers = [parse_rte_header(source.path) for source in sources if source.is_rte_header]
rte = resolve_rte(parsed, headers=headers)
accesses = {access.id: access for access in rte.accesses}
for candidate in rte.dependencies:
    producer = accesses[candidate.producer_access_id]
    consumer = accesses[candidate.consumer_access_id]
    print(candidate.channel, producer.location, consumer.location, candidate.uncertainty)
```

## 데이터 모델

- `RteHeaderApi`: API 이름·read/write·전체 접미사·선언 또는 매크로 형식·원문·위치·불확실성.
- `RteAccess`: API 호출 위치·소속 함수 ID·방향·채널 후보 키·제공된 헤더의 동명 API 위치.
- `RteDataDependency`: 쓰기 접근 ID와 읽기 접근 ID, 채널 후보 키, 불확실성.
- `RteDiagnostic`: 미지원 API, 헤더 오류, 미확인 소속 함수, 공급자/헤더 누락·중복 등을 기록.
- `RteResolution`: 위 접근·연결 후보·진단의 불변 결과다. 기존 FunctionCall은 변경하지 않는다.

`Speed_Raw`는 분리하지 않은 이름 키다. 실제 포트명·데이터 요소명을 추정하여
나누지 않는다. 모든 이름 비교는 대소문자를 구분한다. 후보 연결은 쓰기→읽기 방향이다.
같은 함수 안의 여러 쓰기 지점도 각각 보존하므로 다중 공급자 진단은 함수 개수가 아닌
쓰기 접근 지점 수를 뜻한다. 각 위치는 파서와 동일한 절대 경로·1기반 라인/바이트 열이다.

`parse_rte_header`는 파일을 읽기만 한다. `inspect_rte_header(bytes, path=...)`는
가상 헤더를 지원한다. `resolve_rte` 자체는 파일이나 네트워크에 접근하지 않는다.
원본 파싱과 헤더 검사는 같은 소스 스냅샷에서 수행해야 한다. 중간 수정은 감지하지 않는다.
중복 입력 경로는 ValueError이며 빈 입력은 빈 결과다.

## 반드시 확인할 한계

- 모든 연결에 `name_only_connection`, `arxml_not_resolved`,
  `execution_order_not_resolved`가 있다. 함수 호출 그래프의 간선으로 사용하지 않는다.
- 헤더는 함수 형태 선언과 #define의 원문을 수집하지만 포함 관계와 컴포넌트별
  API 스코프를 해석하지 않는다. 모든 접근에 `header_scope_not_resolved`가 있다.
  동명 API가 여러 헤더에 있으면 각 위치를 유지하고 모호성을 표시한다.
- 매크로 alias, 함수 형태 매크로, 조건부 선언을 확장·선택하지 않는다.
  `header_macro_not_expanded`, `header_preprocessing_not_performed` 및 파서의
  기존 불확실성을 보존한다. 매크로 본문에서 숨겨진 호출을 만들어내지 않는다.
- 알려지지 않은 매크로의 이름이 Rte_Read/Write 형태여도 접근 후보일 뿐이다.
  선언·헤더 근거가 없어도 후보는 남기되 `MISSING_HEADER_API`로 표시한다.
- 같은 이름의 쓰기가 여럿이면 모두 반환한다. 공급자 미발견은 분석 입력 안에
  후보가 없다는 뜻이며 실제 시스템에 공급자가 없다는 뜻은 아니다.
- implicit `Rte_IRead/IWrite`, client/server `Rte_Call`, `Rte_Receive/Send`, 간접 호출은
  현재 미지원이며 진단으로 남긴다. 인수·타입·상태 코드·함수 실행 가능성은 검증하지 않는다.
- ARXML 매핑, runnable 스케줄, 버퍼 alias/배열/인스턴스 및 return-code 흐름은 해석하지 않는다.

현재 샘플의 `ReadRawSpeed`와 `SensorAcquisition_10ms`는 `Speed_Raw`를 통해
연결 후보가 된다. 실제 호출 관계에는 소비자→공급자 간선이 없고, RTE 데이터 후보
모델에 쓰기→읽기 연결만 있다. 조사자는 해당 후보의 근거와 한계를 검토한 후
TraceManager.follow(..., relation="rte_data", evidence=producer.location,
uncertainty=candidate.uncertainty)로 공급자 조사 단계를 추가할 수 있다.
