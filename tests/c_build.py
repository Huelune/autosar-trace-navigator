"""Shared C99 execution validation for synthetic fixtures only."""

from collections.abc import Iterable
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest import SkipTest


ROOT = Path(__file__).resolve().parents[1]


def compiler_command() -> list[str]:
    """Return a C compiler command suitable for the current host."""
    if sys.platform == "darwin" and (cc := (shutil.which("clang") or shutil.which("cc"))):
        return [cc]
    if importlib.util.find_spec("ziglang") is not None:
        return [sys.executable, "-m", "ziglang", "cc"]
    local_zig = ROOT / ".venv/c-tools/ziglang/zig.exe"
    if local_zig.is_file():
        return [str(local_zig), "cc"]
    if zig := shutil.which("zig"):
        return [zig, "cc"]
    if cc := (shutil.which("gcc") or shutil.which("clang") or shutil.which("cc")):
        return [cc]
    raise SkipTest("C compiler unavailable; see test/README.md")


def run_c99(sources: Iterable[Path], *, include_dirs: Iterable[Path] = ()) -> str:
    """Compile with warnings as errors, run a disposable binary and return stdout."""
    compiler = compiler_command()
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
