# 확장 가상 AUTOSAR 프로젝트

test/generate_large_autosar.py로 생성한 독립 C99 fixture다. 실제 차량 동작 모델이나
벤더 AUTOSAR 생성물이 아니며, 여러 SWC의 제어/판단/신호/공급/진단 탐색을 모사한다.
이 변형은 24 SWC, C 122개 + H 49개,
실행 시나리오 192개다.

GUI 루트는 이 폴더를 선택하고, 범위는 swc/Brake_000;shared부터 시작한다.
함수명 Brake_000_10ms를 검색하고 MODE_ACTIVE else-if를 목표로 선택한다.
manifest.json에 각 SWC의 6단계 호출 경로와 입력 threshold가 있다.
RTE 후보는 제어/신호 범위만 선택했을 때와 Producer.c를 포함했을 때를 비교한다.
swc 범위를 넓히면 Normalize 동명 static 후보와 일부 백업 공급자의 모호성이 나타난다.
공급·소비·실행 순서가 확정된다는 뜻은 아니다.

소스는 편집하지 않고, 변형은 생성기를 새 폴더에 실행하여 만든다.
루트 범위 . 은 171파일이다. 80 SWC 변형은 563파일로
전체 범위 기본 500파일 제한을 넘으므로 일부 SWC를 선택해 분석해야 한다.
