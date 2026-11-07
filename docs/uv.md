# uv로 설치하고 실행하기

Python 3.11–3.14와 Tcl/Tk를 먼저 설치합니다. Windows에서는 Python 설치 프로그램의
Tcl/Tk 항목을 포함하세요. SQLite와 Tkinter는 Python 제공 기능이며 pip 설치 대상이 아닙니다.
프로젝트 설정은 Python 자동 다운로드를 막습니다. 패키지의 최초 준비에는 인터넷 또는 미리 준비한 캐시가 필요합니다.

## 최초 설치

가상환경을 활성화하지 않은 PowerShell에서 프로젝트 루트로 이동해 실행합니다.

```powershell
python -m pip install --user uv
python -m uv sync --locked
python -m uv run --locked autosar-trace-navigator
```

`uv`가 PATH에 있으면 `uv sync --locked`, `uv run --locked autosar-trace-navigator`처럼 사용할 수 있습니다.
PATH에 없어도 위의 `python -m uv` 형식으로 실행할 수 있습니다. uv 자체는 프로젝트 `.venv` 밖에 설치합니다.
uv는 `.venv`를 생성하고 프로젝트를 editable로 설치하며 tree-sitter 0.25.2와 tree-sitter-c 0.24.1을 설치합니다.
별도의 `requirements.txt` 없이 `pyproject.toml`과 `uv.lock`을 사용합니다.

`--locked`는 pyproject와 잠금 파일이 맞지 않으면 중단합니다. 의존성을 변경하는 개발 작업에서만
`python -m uv lock`으로 갱신하고 잠금 파일도 함께 커밋합니다.
기존 가상환경의 다른 패키지를 유지하려면 `sync --locked --inexact`를 사용하세요.

GUI 명령과 같은 실행은 다음 명령으로도 할 수 있습니다.

```powershell
python -m uv run --locked python -m autosar_trace_navigator
```

## 테스트 패키지 설치

```powershell
python -m uv sync --locked --group test
python -m uv run --locked --group test python -m unittest discover -s tests -v
```

test 그룹은 Zig 0.15.2를 추가합니다. unittest는 표준 라이브러리여서 별도 테스트 프레임워크는 설치하지 않습니다.
Zig는 가상 C 하네스를 컴파일할 때만 사용하며 GUI 실행에는 필요하지 않습니다.
컴파일러가 없으면 C 실행 검증은 skip될 수 있으므로 전체 검증에는 test 그룹을 포함하세요.

## 예제 DB 생성

```powershell
python -m uv run --locked python examples/create_demo.py
python -m uv run --locked python examples/create_struct_demo.py
```

각각 build/tutorial.sqlite3와 build/struct_tutorial.sqlite3를 만듭니다. 기존 DB는 덮어쓰지 않습니다.

## 오프라인 실행

인터넷을 사용할 수 있는 준비 단계에서 설치와 캐시를 준비합니다. 아래 캐시는 이 프로젝트의 공개 의존성 준비에만 사용합니다.

```powershell
python -m uv sync --locked --group test --cache-dir build/uv-cache
python -m uv run --locked --group test --cache-dir build/uv-cache python -c "import tkinter, sqlite3, tree_sitter, tree_sitter_c, ziglang"
```

이미 설치된 패키지는 캐시에 새로 저장되지 않을 수 있습니다. 다른 환경에 설치할 캐시도 준비하려면
새 폴더의 가상환경에서 한 번 동기화합니다. 예시의 폴더 이름은 아직 없는 이름을 사용하세요.

```powershell
$env:UV_PROJECT_ENVIRONMENT = 'build/uv-cache-prepare'
python -m uv sync --locked --group test --cache-dir build/uv-cache
Remove-Item Env:UV_PROJECT_ENVIRONMENT
```

이후 다음 명령은 네트워크 접근을 비활성화합니다.

```powershell
python -m uv run --offline --locked --cache-dir build/uv-cache autosar-trace-navigator
python -m uv run --offline --locked --group test --cache-dir build/uv-cache python -m unittest discover -s tests -v
```

다른 오프라인 PC에는 프로젝트와 `build/uv-cache`, uv 및 Tcl/Tk 포함 Python을 준비해야 합니다.
대상 OS·아키텍처·Python 버전과 같은 환경에서 캐시를 준비하세요. `.venv`를 PC 간 복사하는 방식은 사용하지 않습니다.
프로젝트 소스의 editable 빌드에도 setuptools 캐시가 필요하며 위의 새 환경 동기화가 이를 준비합니다.
캐시가 불완전하면 오프라인 설치는 오류로 중단합니다. 자동으로 인터넷을 켜거나 Python을 다운로드하지 않습니다.

## 기존 pip 방식

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python -m pip install ziglang==0.15.2
.venv\Scripts\python -m autosar_trace_navigator
```

설치 방식만 다르며 같은 프로그램을 사용합니다. [기존 wheelhouse 안내](../README.md#오프라인-환경-구성)를 참고하세요.

명령의 동작은 [uv 설치 문서](https://docs.astral.sh/uv/getting-started/installation/),
[잠금·동기화 문서](https://docs.astral.sh/uv/concepts/projects/sync/),
[Zig Python 배포 안내](https://pypi.org/project/ziglang/0.15.2/)를 참고했습니다.
