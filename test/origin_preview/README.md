# 변수 전체 출처 미리보기 구문 샘플

직접 작성한 독립 합성 코드다. `Consumer.c`의 `pedal >= 60u`에서 pedal을 선택한다.
반환값 3단계 → Rte_Read 출력 인수 → 별도 Publisher → 두 계산 경로 → Raw/Enable/Quality 전역 입력 후보를 검사한다.
else if는 앞선 조건 거짓·현재 조건 참을 각각 유지한다.

재귀 함수·미정의 외부 함수·배열·static/const를 포함해 순환/미해결/미지원 경계를 확인한다.
전처리 미확장·이름 기반 연결 등의 불확실성을 제거하지 않는다. 실행용 하네스나 고객 코드는 없다.
Python 자동 검증은 tests/test_value_graph.py, 40단계 확장 검증은 tests/test_mega_autosar.py를 사용한다.
