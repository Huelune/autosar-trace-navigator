"""Shared C99 execution validation for synthetic fixtures only."""

from collections.abc import Iterable
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from unittest import SkipTest


ROOT = Path(__file__).resolve().parents[1]


def run_c99(sources: Iterable[Path], *, include_dirs: Iterable[Path] = ()) -> str:
    """Compile with warnings as errors, run a disposable binary and return stdout."""
    local_zig = ROOT / ".venv/c-tools/ziglang/zig.exe"
    if local_zig.is_file():
        compiler = [str(local_zig), "cc"]
    elif zig := shutil.which("zig"):
        compiler = [zig, "cc"]
    elif cc := (shutil.which("gcc") or shutil.which("clang") or shutil.which("cc")):
        compiler = [cc]
    else:
        raise SkipTest("C compiler unavailable; see test/README.md")
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="c-execution-", dir=build) as directory:
        executable = Path(directory) / ("sample.exe" if os.name == "nt" else "sample")
        command = compiler + ["-std=c99", "-Wall", "-Wextra", "-Werror", "-pedantic"]
        for path in include_dirs:
            command.extend(("-I", str(path)))
        command.extend((*map(str, sources), "-o", str(executable)))
        env = os.environ.copy()
        for name in ("TMP", "TEMP", "TMPDIR"):
            env[name] = directory
        env["ZIG_GLOBAL_CACHE_DIR"] = str(build / "zig-cache")
        env["ZIG_LOCAL_CACHE_DIR"] = str(build / "zig-local-cache")
        result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=180)
        if result.returncode != 0:
            raise AssertionError("C compilation failed:\n" + result.stdout + result.stderr)
        result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            raise AssertionError("C scenarios failed:\n" + result.stdout + result.stderr)
        return result.stdout
