# 사용 예제

[따라 하기 사용법](../docs/user-guide.md)을 먼저 읽으세요.

- `tutorial.sqlite3`: 가상 AUTOSAR 코드로 만든 4단계·10단계 조사 세션 두 개.
- `create_demo.py`: 현재 저장소 경로로 같은 사용 사례를 새 DB에 기록하는 스크립트.
- `struct_tutorial.sqlite3`: 구조체 값 공급·포인터 인수·전역 객체의 14/13/3단계 조사 세션 세 개.
- `create_struct_demo.py`: 현재 경로용 구조체 예제 DB 생성기. [사용 순서](../docs/structs.md#예제-db로-열어보기).

프로젝트 루트에서 실행합니다.

```powershell
.venv\Scripts\python examples\create_demo.py
```

출력은 `build/tutorial.sqlite3`입니다. 이미 있으면 거부합니다.
`--output build/tutorial-02.sqlite3`처럼 새 이름을 지정할 수 있습니다.
생성기는 가상 C/H를 읽기만 하고 사용자의 기존 DB를 덮어쓰지 않습니다.

DB는 실제 제품의 TraceStore 형식이며 GUI의 **세션 불러오기**로 열 수 있습니다.
세션 ID는 `example-01-ct-global`, `example-02-nested-conditions`입니다.
입력 계획은 조사 이유에 사람이 검토한 값으로 기록되어 있습니다.

동봉 DB는 작성 당시 Windows 경로 `E:\01.Projects\autosar-trace-navigator`를 참조합니다.
다른 설치 경로에서는 스크립트로 다시 생성하세요. 원본 코드·분석 인덱스는 DB에 없으므로,
코드 미리보기와 후보 탐색에는 GUI에서 `test/value_paths`를 루트로
`value_paths.c;value_paths.h`를 분석해야 합니다.

구조체 DB는 `test/struct_paths`를 루트로 `struct_paths.h;Rte_StructPaths.h;producer.c;consumer.c;rte_stub.c`를
분석합니다. `.venv\Scripts\python examples\create_struct_demo.py`로 새 `build/struct_tutorial.sqlite3`를 만들 수 있습니다.
이 생성기도 기존 DB를 덮어쓰지 않습니다.
