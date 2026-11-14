# 분석 한도용 독립 가상 프로젝트

기존 AUTOSAR 실행 샘플과 분리한 구문 분석용 가상 데이터다. `Consumer()`가 다른 폴더의 `Supply()`를 호출하고,
분석과 무관한 함수 파일을 600개 추가한다. C/H 원본을 수정하지 않는지와 범위 제한 동작을 검증한다.

루트에서 **아직 존재하지 않는 출력 폴더**로 생성한다.

```powershell
python test/scale_scope/generate.py build/scale-fixture
```

결과는 `app/Consumer.c`, `supplier/Producer.c`, `noise/Noise_*.c` 합계 602개다.
출력 폴더가 이미 있으면 덮어쓰지 않고 실패한다. Python 검증은 `tests/test_bridge_limits.py`에서 임시 폴더로 수행한다.

새 엔진과 VSIX를 설치한 VS Code에서 `build/scale-fixture` 자체를 열고 `Consumer.c`의 `Supply()`에 커서를 둔다.
사용자 설정의 pythonPath는 새 엔진을 설치한 인터프리터를 지정한다.

1. `analysisPaths: ["."]`, 기본 한도 500개: 파일 수 602/500 초과로 중단. 부분 후보와 조사 단계는 만들지 않는다.
2. `analysisMaxFiles: 650`: 같은 범위에서 `supplier/Producer.c`의 `Supply()` 호출 후보가 보인다.
3. `analysisMaxFiles: 2`, `analysisExcludePaths: ["noise"]`: 관련 두 파일만 분석하고 같은 후보가 보인다.
4. 공급자 폴더까지 제외: 정의를 찾지 못한 **범위 내 미해결 후보**로 표시한다. 함수가 프로젝트 전체에 없다는 뜻이 아니다.

자동 검증은 단일 파일/합계 크기 구분, 잘못된 한도·범위 거부, 실제 stdin/stdout JSON 오류와 원본 무변경도 확인한다.
실제 고객 프로젝트의 수만 파일 처리 속도·메모리를 측정한 자료는 아니다.
