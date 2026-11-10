# 다른 PC와 AI 도구에서 개발하기

## 처음 읽을 것

1. [AGENTS.md](AGENTS.md): 공통 설계·테스트·커밋 규칙. Claude Code는 [CLAUDE.md](CLAUDE.md)에서 가져온다.
2. [현재 상태](docs/work/STATUS.md): 구현된 기능, 검증 근거와 남은 일.
3. [작업 공유 절차](docs/work/README.md): 작업 카드, 세션 기록, 인수인계와 복사할 시작 프롬프트.
4. [아키텍처](docs/architecture.md), 담당 영역의 README와 코드.

## 새 PC 구성

Git과 승인된 개발 도구를 먼저 설치한다. Codex/Claude Code 설치·계정·회사 정책은 이 저장소에 포함되지 않는다.
저장소를 복제한 후 루트에서 시작한다. 기존 대화나 원래 PC의 절대 경로는 필요하지 않다.

```powershell
git clone https://github.com/Huelune/autosar-trace-navigator.git
cd autosar-trace-navigator
git status --short
git log -5 --oneline
```

원격에 공유된 커밋까지만 받을 수 있다. 현재 PC에서만 커밋한 변경은 별도 push 이후 보인다.
작업 시작 전에 두 PC가 같은 기준 커밋을 받았는지 확인한다.

| 담당 영역 | 필요한 도구 | 잠금 파일 |
|---|---|---|
| Python 분석·Tkinter | Tcl/Tk 포함 Python 3.11–3.14, uv | `uv.lock` |
| VS Code 확장 P0 | Node.js 22 이상/npm, VS Code 1.95 이상 | `extensions/branch-investigation/package-lock.json` |
| 작업 기록 생성 | Python 3.11 이상 표준 라이브러리 | 추가 패키지 없음 |

### Python 분석 엔진

가상환경을 활성화하지 않은 터미널에서 실행한다. 회사 PC에서는 승인된 uv 설치 경로를 사용한다.

```powershell
python -m pip install --user uv
python -m uv sync --locked --group test
python -m uv run --locked --group test python -m unittest discover -s tests -v
python -m uv run --locked autosar-trace-navigator
```

Tkinter·SQLite는 pip 설치 대상이 아니다. C 실행 테스트에는 test 그룹의 Zig가 필요하다.
GUI가 없는 환경의 skip은 GUI 검증 통과로 기록하지 않는다. [uv·오프라인 구성](docs/uv.md)을 참고한다.

Windows의 제한된 실행 환경에서 임시 폴더 `WinError 5`가 발생하면 그 실패를 기록하고,
쓰기 가능한 저장소 `build/temp`를 만든 뒤 **현재 셸에만** TEMP/TMP를 그 경로로 지정해 재실행할 수 있다.
일반 사용자/시스템 환경 변수를 영구 변경하지 않는다.

### VS Code 확장

Node/npm을 PATH에 준비한다. 다른 PC에 원래 개발자의 `build/tools` 경로가 있다고 가정하지 않는다.

```powershell
cd extensions/branch-investigation
npm ci
npm test
npm run package:vsix
# 설치된 VS Code를 실제로 여는 검증: 화면 사용 가능한 PC에서 실행
npm run test:host
```

VSIX는 루트 `build/branch-investigation-0.1.0.vsix`에 생성한다. 새 체크아웃에도 build를 자동 준비한다.
Host 위치가 기본 Windows 설치 경로와 다르면 PowerShell에서
`$env:VSCODE_EXECUTABLE_PATH = '승인된 VS Code 실행 파일의 전체 경로'`를 지정한다.
macOS/Linux에서는 같은 환경 변수를 해당 셸 방식으로 설정한다. 다른 OS의 Host는 아직 검증하지 않았다.
F5는 **확장 폴더 자체**를 VS Code로 열어 실행한다. [확장 사용법](extensions/branch-investigation/README.md).
P0 실행에는 Python이 필요하지 않다. Python 엔진 연동은 후속 작업 카드의 범위다.

### 인터넷 없는 PC

잠금 파일은 패키지 자체를 포함하지 않는다. 최초 설치에는 승인된 연결 또는 대상 OS/아키텍처/버전에 맞는 준비된 캐시가 필요하다.
`.venv`나 `node_modules`를 PC 사이에서 복사하는 방식 대신 잠금 파일로 새 환경을 구성한다.

Python 캐시 준비/검증은 [uv 안내](docs/uv.md)를 따른다. npm은 연결 가능한 승인 환경에서 빈 개발 환경에
`npm ci --cache <캐시경로> --no-audit --no-fund`로 준비한 뒤, 캐시를 승인된 방식으로 옮겨
`npm ci --offline --cache <캐시경로> --no-audit --no-fund`로 확인한다. 캐시가 없으면 중단하며 임의로 외부 연결하지 않는다.
공개 의존성 캐시와 사내 자료를 섞지 않는다. 완성 VSIX를 사용만 할 때는 Node/npm 캐시가 필요 없다.

## 회사 Claude Code에서 시작

회사에서 허용한 방식으로 이 저장소를 열고 루트에서 Claude Code를 시작한다.
`CLAUDE.md`는 `@AGENTS.md`를 가져와 공통 규칙을 유지한다. 설치 버전에 맞는 `/memory` 또는
`/context` 화면에서 실제로 읽힌 지침을 확인한다. 회사의 관리 정책·권한을 저장소 설정으로 우회하지 않는다.
지침 불러오기는 문서로 구성했으며 이 PC에서 Claude Code를 실제 구동해 검증한 것은 아니다.
[공식 지침 가져오기 문서](https://code.claude.com/docs/en/memory#import-additional-files).

이 저장소에는 직접 만든 가상 코드·제품 코드·비민감 작업 기록만 공유한다.
고객/회사 소스, CT 결과, 캡처, 내부 주소, 비밀키와 계정 정보는 작업 카드·로그·커밋에 넣지 않는다.
`.gitignore`는 반출 허가를 의미하지 않는다. 도구가 사내 자료를 읽어도 된다는 승인도 이 문서에 포함되지 않는다.
개인 설정은 `CLAUDE.local.md` 또는 `.claude/settings.local.json`에 두고 공유하지 않는다.
