# autosar-trace-navigator

AUTOSAR Classic C 통합 테스트에서 목표 분기와 탐색 맥락을 보존하는 로컬 도구.
현재 **STEP 1: 프로젝트 구조 및 Python 환경**과 사용자 요청에 따른
[6단계 추적용 가상 AUTOSAR 샘플](test/README.md)을 구현했습니다.
읽기 전용 C/H 파일 스캐너와 함수 정의·호출·분기 구문 파서를 구현했습니다.
목표 분기·조사 경로를 보존하는 Trace Manager와 SQLite 세션 저장을 구현했습니다.
GUI와 RTE Resolver는 아직 구현하지 않았습니다.

## 구조

```text
src/autosar_trace_navigator/  스캐너·파서·모델·Trace Manager·SQLite 저장
tests/                       환경·분석·탐색 상태·저장·C 실행 검증 테스트
test/                        가상 AUTOSAR C/H 및 C 실행 하네스
docs/architecture.md         계층 설계와 후속 단계
AGENTS.md                    개발 및 테스트 규칙
pyproject.toml               패키지 및 파서 의존성
```

## 환경 구성 (PowerShell)

Python 3.11–3.14를 사용합니다. SQLite와 Tkinter는 Python 배포판에 포함된
기능을 사용하므로 별도 pip 패키지를 설치하지 않습니다. Python 설치 시 Tcl/Tk를 포함하세요.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python -m unittest discover -s tests -v
```

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

현재 범위의 [통합 검증 결과](docs/verification.md): Python 테스트 47개와
C 시나리오 12개 통과. [Trace Manager 및 SQLite 사용법](docs/trace.md)을 참고하세요.
RTE Resolver와 GUI는 후속 범위입니다.

## 오프라인 환경 구성

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
