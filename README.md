# autosar-trace-navigator

AUTOSAR Classic C 통합 테스트에서 목표 분기와 탐색 맥락을 보존하는 로컬 도구.

**다른 PC의 Codex·Claude Code에서 개발을 이어가려면 [개발 환경 구성](CONTRIBUTING.md)과
[현재 작업·인수인계](docs/work/STATUS.md)를 먼저 읽으세요.** 해야 할 일은 작업 카드에,
실제로 한 일과 검증·다음 행동은 세션별 기록에 남겨 Git으로 공유합니다.

**VS Code 조사 확장 P0**는 [extensions/branch-investigation](extensions/branch-investigation/README.md)에 있습니다.
코드 선택·이유 저장 → 조사 트리 → 상세·정확한 소스 재방문을 VS Code 안에서 제공하며 P0는 Python 없이 동작합니다.
아래 Python/Tkinter 도구와 저장소는 그대로 유지합니다.
현재 **STEP 1: 프로젝트 구조 및 Python 환경**과 사용자 요청에 따른
[6단계 추적용 가상 AUTOSAR 샘플](test/README.md)을 구현했습니다.
읽기 전용 C/H 파일 스캐너와 함수 정의·호출·분기 구문 파서를 구현했습니다.
목표 분기·조사 경로를 보존하는 Trace Manager와 SQLite 세션 저장을 구현했습니다.
이름 기반 RTE Read/Write 공급·소비 후보 분석과 Tkinter GUI도 구현했습니다.
변수 목표값의 공급 위치 역추적, 선택 라인 이력, 이동 전 후보 코드 미리보기를 지원합니다.
분기 안의 여러 변수 중 조사할 값을 선택하고, 현재 소스와 후보·이력 코드를 동시에 비교할 수 있습니다.
가운데 소스는 기준으로 고정하고, 출처를 따라갈 때 오른쪽 단계별 코드만 현재 함수로 전환합니다.
상단 목표 카드와 단계별 다음 행동 안내, 후보 수·근거 요약과 선택에 따른 버튼 활성화를 제공합니다.
`b.a`, `p->a`의 멤버 경로와 `Rte_Read_State(&b)` 출력 인수도 추적합니다.
[구조체 사용 예제와 저장 DB](docs/structs.md)를 제공합니다.

처음 사용한다면 **[예제 DB로 따라 하는 사용법](docs/user-guide.md)**을 읽어보세요.
전역 입력 후보까지 찾는 4단계 예시와 중첩 실행 조건을 조사하는 10단계 예시를 제공합니다.

## 구조

```text
src/autosar_trace_navigator/  분석·Trace·SQLite·RTE·화면 상태·Tkinter GUI
tests/                       환경·분석·탐색 상태·저장·C 실행 검증 테스트
test/                        가상 AUTOSAR C/H 및 C 실행 하네스
examples/                    저장된 사용 예제 DB와 현재 경로용 DB 생성기
docs/architecture.md         계층 설계와 후속 단계
AGENTS.md                    개발 및 테스트 규칙
pyproject.toml               패키지 및 파서 의존성
uv.lock                      실행·테스트 패키지 버전과 배포 파일 해시
```

## 환경 구성 (PowerShell)

Python 3.11–3.14를 사용합니다. SQLite와 Tkinter는 Python 배포판에 포함된
기능을 사용하므로 별도 pip 패키지를 설치하지 않습니다. Python 설치 시 Tcl/Tk를 포함하세요.

프로젝트 루트에서 uv를 설치하고 필요한 패키지를 동기화합니다.

```powershell
python -m pip install --user uv
python -m uv sync --locked
```

`uv`가 PATH에 있다면 `python -m uv` 대신 `uv`를 사용할 수 있습니다. 가상환경 활성화는 필요 없습니다.
기본 설치는 tree-sitter와 C 문법 패키지를 포함합니다. 전체 테스트용 Zig 컴파일러까지 설치하려면:

```powershell
python -m uv sync --locked --group test
python -m uv run --locked --group test python -m unittest discover -s tests -v
```

기존 `.venv`의 다른 패키지를 유지할 때는 sync에 `--inexact`를 추가하세요.
Python 자동 다운로드는 비활성화했습니다. Tcl/Tk가 포함된 Python을 먼저 준비하세요.
[설치·실행·오프라인 사용법](docs/uv.md)을 참고하세요. 기존 pip 설치도 계속 지원합니다.

## GUI 실행

```powershell
python -m uv run --locked autosar-trace-navigator
```

같은 실행을 `python -m uv run --locked python -m autosar_trace_navigator`로 할 수도 있습니다.
루트 선택 → 파일/폴더 범위 지정·분석 → 함수 검색·목표 분기 선택 → 조사 이유 입력 → 호출/RTE 후보 조사 →
SQLite 저장·복원을 지원합니다. [GUI 사용법](docs/gui.md)을 참고하세요.
`pedal → 60`처럼 변수 목표를 고정하고 **값 출처**에서 공급자·반환값·테스트 입력 위치를
조사할 수 있습니다. 소스 변경이나 자동 조건 해결은 수행하지 않습니다. [역추적 안내](docs/values.md)를 참고하세요.

전체 함수를 자동으로 나열하지 않고 검색 결과를 100개씩 표시합니다. 분석은 선택 범위에
제한하며 기본 500파일·파일당 4 MiB·소스 합계 32 MiB의 예산을 적용합니다.
[범위 분석과 검색](docs/scoped-analysis.md)을 참고하세요. 증분 캐시는 아직 제공하지 않습니다.

## 스캐너 사용

설치한 Python 환경에서 다음과 같이 호출합니다.

```python
from autosar_trace_navigator.scanner import scan_sources

for source in scan_sources("test", exclude_paths=("support",)):
    print(source.path, source.relative_path, source.is_rte_header)
```

- 하위 폴더의 `.c`/`.h`를 대소문자 구분 없이 찾고 상대 경로순으로 반환합니다.
- 각 결과는 절대 경로 `path`, 루트 기준 `relative_path`를 가집니다.
- `is_rte_header`는 `Rte_*.h` 이름 패턴이며 실제 생성 여부나 데이터 의미를 판정하지 않습니다.
- 제외 항목은 루트 기준 상대 경로 또는 루트 내부 절대 경로입니다. 파일/폴더를
  지정하며 와일드카드는 지원하지 않습니다. 기본 제외 항목은 없습니다.
- 하위 심볼릭 링크와 Windows junction/reparse point는 건너뜁니다.
  명시적으로 전달한 루트는 실제 경로로 정규화합니다.
- 없는 루트, 파일인 루트, 루트 외부 제외 경로, 파일 접근 오류는 예외로 알립니다.
  탐색 중 파일이 삭제되면 재시도할 수 있습니다.
- 스캐너는 파일 내용을 읽거나 수정하지 않습니다. 라인 번호와 코드 구조는 파서에서 추출합니다.

## 파서 사용

```python
from autosar_trace_navigator.parser import parse_file

result = parse_file("test/src/BrakeControl.c")
for branch in result.branches:
    print(branch.kind, branch.condition, branch.location.start_line)
```

매크로, 전처리 조건, 호출 대상은 확정하지 않고 불확실성과 진단을 기록합니다.
상세 모델·사용법·제약은 [파서 문서](docs/parser.md)를 참고하세요.

현재 범위의 [통합 검증 결과](docs/verification.md): Python 테스트 171개와
C 시나리오 216개(기존 12개 + 확장 192개 + 실행 조건 6개 + 구조체 6개) 통과. [Trace Manager 및 SQLite 사용법](docs/trace.md)을 참고하세요.

**실행 조건** 탭에서는 값을 만드는 코드의 조건 변수를 별도 하위 조사로 따라갑니다.
extern 등 외부 연결 이름의 전역을 CT 제어 후보로 표시하며 static·const는 제외합니다.
실제 CT 접근성은 확인이 필요합니다. [목표 상수 없는 계산·조건 예제](test/value_paths/README.md)를 참고하세요.

## 확장 C 프로젝트

[test/large_autosar](test/large_autosar/README.md)에 24 SWC의 C/H 171개,
함수 정의 424개·분기 665개를 추가했습니다. GUI 루트를 해당 폴더로 선택하고
`swc/Brake_000;shared`부터 조사할 수 있습니다. [시나리오·변형 생성 방법](docs/large-sample.md)을 참고하세요.

## RTE 후보 분석

[RTE Resolver 사용법](docs/rte.md)에 따라 파서 결과와 Rte_*.h의 선언·매크로를
입력하면 Read/Write 접근과 이름 기반 데이터 연결 후보를 별도로 얻을 수 있습니다.
여러 공급자와 헤더 모호성을 유지하며 실제 ARXML 연결이나 실행 순서는 확정하지 않습니다.
공급자 후보를 조사 단계에 추가한 뒤 SQLite에 저장·복원하는 통합 검증도 포함합니다.
GUI에서도 호출 후보와 RTE 공급자 후보를 별도 탭으로 표시합니다.

## 오프라인 환경 구성

[uv 오프라인 준비](docs/uv.md#오프라인-실행)에서 캐시를 준비하고 `--offline`으로 실행할 수 있습니다.
아래는 별도 PC에 wheelhouse를 전달하는 기존 pip 방식입니다.

인터넷 연결이 가능한 동일 OS/아키텍처/Python 버전의 준비 환경에서:

```powershell
python -m pip download --only-binary=:all: --dest wheelhouse "setuptools>=77,<81" "tree-sitter==0.25.2" "tree-sitter-c==0.24.1"
```

프로젝트와 wheelhouse를 오프라인 PC로 복사한 후:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --no-index --find-links wheelhouse -e .
.venv\Scripts\python -m unittest discover -s tests -v
```

Python 설치 프로그램 자체도 별도로 준비해야 합니다. wheelhouse와 .venv는
Git에 포함하지 않습니다. 패키지는 import 시 네트워크·스캔·DB 접근을 수행하지 않습니다.
설계는 [architecture](docs/architecture.md), 작업 규칙은 [AGENTS.md](AGENTS.md)를 참고하세요.
