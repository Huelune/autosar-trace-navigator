"""Install the analysis engine and the VS Code extension from this checkout.

Standard library only, so it runs before anything is installed. The screen shows
one line per step and what to do on failure; paths and raw error text go only to
a log file in the temp folder, because a screenshot of this output may be shared.
"""

from collections.abc import Callable
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
VSIX = ROOT / "release" / "branch-investigation-0.1.0.vsix"
LOG_NAME = "atn-install.log"
SETTINGS_NAME = "atn-settings.txt"

Step = tuple[str, str, Callable[[], None]]


def settings_text(python: Path) -> str:
    """The two user-settings lines, ready to paste between the braces of settings.json."""
    return (f'"branchInvestigation.pythonPath": {json.dumps(str(python), ensure_ascii=False)},\n'
            '"branchInvestigation.analysisPaths": ["."]\n')


def run_steps(steps: list[Step], log: Callable[[str], None]) -> tuple[list[str], bool]:
    """Run until the first failure. Returned lines carry step names and advice only."""
    lines, failed = [], False
    for name, advice, action in steps:
        if failed:
            lines.append(f"  건너뜀  {name}")
            continue
        try:
            action()
            lines.append(f"  완료    {name}")
        except Exception as error:  # noqa: BLE001 - the detail may hold paths; it goes to the log only
            failed = True
            log(f"{name}: {error!r}")
            lines.append(f"  실패    {name} -> {advice}")
    return lines, not failed


def main() -> int:
    temp = Path(tempfile.gettempdir())
    log_path = temp / LOG_NAME
    log_path.write_text("", encoding="utf-8")

    def log(text: str) -> None:
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(text + "\n")

    def command(*args: str) -> None:
        done = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log(done.stdout.decode("utf-8", errors="replace"))
        if done.returncode != 0:
            raise RuntimeError(f"exit {done.returncode}")

    def check_tools() -> None:
        if not (3, 11) <= sys.version_info[:2] <= (3, 14):
            raise RuntimeError("python version")
        if shutil.which("code") is None or not VSIX.is_file():
            raise RuntimeError("code command or vsix missing")

    def write_settings() -> None:
        target = temp / SETTINGS_NAME
        target.write_text(settings_text(VENV_PYTHON), encoding="utf-8-sig")
        if os.name == "nt":
            subprocess.Popen(["notepad", str(target)])

    steps: list[Step] = [
        ("도구 확인 (python, code)", "Python 3.11~3.14와 VS Code의 code 명령을 설치하고 새 창에서 다시 실행", check_tools),
        ("Python 가상환경", "Python 설치에 venv가 포함됐는지 확인",
         lambda: command(sys.executable, "-m", "venv", str(ROOT / ".venv"))),
        ("분석 엔진 설치", "PyPI 접속(사내 프록시·미러 설정) 확인",
         lambda: command(str(VENV_PYTHON), "-m", "pip", "install", "--disable-pip-version-check", "--quiet", str(ROOT))),
        ("분석 엔진 동작 확인", "분석 엔진 설치 단계를 다시 실행",
         lambda: command(str(VENV_PYTHON), "-I", "-c", "import autosar_trace_navigator.bridge")),
        ("VS Code 확장 설치", "VSIX 설치가 정책으로 막혀 있는지 확인",
         lambda: command(shutil.which("code") or "code", "--install-extension", str(VSIX), "--force")),
        ("설정 두 줄을 메모장에 준비", "직접 입력: pythonPath에 설치 폴더의 .venv 안 python 경로", write_settings),
    ]
    lines, ok = run_steps(steps, log)
    os.system("cls" if os.name == "nt" else "clear")  # fixed literal, no user input reaches the shell
    print("Branch Investigation 설치 결과")
    print("\n".join(lines))
    print()
    if ok:
        print("다음 순서로 설정하세요.")
        print("  1. 열린 메모장의 두 줄을 전체 복사 (창이 안 떴으면 %TEMP%\\" + SETTINGS_NAME + ")")
        print("  2. VS Code에서 Ctrl+Shift+P -> Preferences: Open User Settings (JSON)")
        print("  3. 중괄호 안에 붙여 넣고 저장. 기존 항목과는 쉼표로 구분")
        print("  4. 설치 폴더의 test\\struct_paths 폴더를 열고 폴더를 신뢰")
    else:
        print("실패한 단계의 할 일을 처리한 뒤 같은 명령을 다시 실행하세요.")
        print("자세한 기록(이 PC에서만 확인): %TEMP%\\" + LOG_NAME)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
