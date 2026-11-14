"""Bounded, offline overload checks using generated sources only; no GUI or product edits."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
MIB = 1024 * 1024


def available_memory_mib() -> int | None:
    """Check headroom before launching the bounded two-worker test."""
    if os.name == "nt":
        class Memory(ctypes.Structure):
            _fields_ = [("length", ctypes.c_uint32), ("load", ctypes.c_uint32)] + [
                (name, ctypes.c_uint64) for name in ("total", "available", "page_total", "page_available",
                                                    "virtual_total", "virtual_available", "extended")]
        memory = Memory()
        memory.length = ctypes.sizeof(memory)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
            return memory.available // MIB
    try:
        return next(int(line.split()[1]) // 1024 for line in Path("/proc/meminfo").read_text().splitlines()
                    if line.startswith("MemAvailable:"))
    except (OSError, StopIteration):
        return None


def peak_bytes(pid: int) -> int | None:
    """Read a worker's OS peak working set; unavailable measurements remain null."""
    if os.name == "nt":
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    "peak", "working", "quota_peak_paged", "quota_paged", "quota_peak_nonpaged",
                    "quota_nonpaged", "pagefile", "peak_pagefile")]

        kernel, psapi = ctypes.WinDLL("kernel32", use_last_error=True), ctypes.WinDLL("psapi")
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        psapi.GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
        handle = kernel.OpenProcess(0x0410, False, pid)
        if not handle:
            return None
        try:
            counters = Counters()
            counters.cb = ctypes.sizeof(counters)
            return counters.peak if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb) else None
        finally:
            kernel.CloseHandle(handle)
    status = Path(f"/proc/{pid}/status")
    try:
        return next(int(line.split()[1]) * 1024 for line in status.read_text().splitlines()
                    if line.startswith("VmHWM:"))
    except (OSError, StopIteration):
        return None


def process_table() -> dict[int, int]:
    """PID/parent pairs only, including Windows venv launcher descendants."""
    if os.name == "nt":
        from ctypes import wintypes

        class Entry(ctypes.Structure):
            _fields_ = [("size", wintypes.DWORD), ("usage", wintypes.DWORD), ("pid", wintypes.DWORD),
                        ("heap", ctypes.c_size_t), ("module", wintypes.DWORD), ("threads", wintypes.DWORD),
                        ("parent", wintypes.DWORD), ("priority", wintypes.LONG), ("flags", wintypes.DWORD),
                        ("exe", wintypes.WCHAR * 260)]

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
        kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        kernel.Process32FirstW.argtypes = kernel.Process32NextW.argtypes = (wintypes.HANDLE, ctypes.POINTER(Entry))
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = kernel.CreateToolhelp32Snapshot(2, 0)
        if handle == ctypes.c_void_p(-1).value:
            raise OSError("Process snapshot unavailable")
        try:
            entry = Entry()
            entry.size = ctypes.sizeof(entry)
            table = {}
            found = kernel.Process32FirstW(handle, ctypes.byref(entry))
            while found:
                table[entry.pid] = entry.parent
                found = kernel.Process32NextW(handle, ctypes.byref(entry))
            return table
        finally:
            kernel.CloseHandle(handle)
    table = {}
    for status in Path("/proc").glob("[0-9]*/status"):
        try:
            table[int(status.parent.name)] = next(int(line.split()[1]) for line in status.read_text().splitlines()
                                                  if line.startswith("PPid:"))
        except (OSError, StopIteration):
            pass
    return table


def descendants(pid: int, table: dict[int, int]) -> set[int]:
    family = {pid}
    while additional := {child for child, parent in table.items() if parent in family} - family:
        family.update(additional)
    return family


def stop_tree(worker: subprocess.Popen) -> None:
    """Terminate only the process tree launched for this case."""
    if worker.poll() is not None:
        return
    if os.name == "nt":
        executable = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/taskkill.exe"
        subprocess.run([str(executable), "/PID", str(worker.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5, check=False)
    else:
        import signal
        os.killpg(worker.pid, signal.SIGKILL)
    if worker.poll() is None:
        worker.kill()


def run_process(command: list[str], payload: bytes = b"", *, timeout: float = 60,
                memory_mib: int = 512, output_bytes: int = 8 * MIB) -> tuple[dict, bytes]:
    """Drain both pipes, bound result bytes/time/memory and reap this worker on every exit."""
    started = time.perf_counter()
    worker = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              start_new_session=os.name != "nt")
    chunks: list[bytes] = []
    overflow = threading.Event()
    stderr_count = [0]

    def drain(stream, *, result: bool) -> None:
        size = 0
        while chunk := stream.read(65536):
            size += len(chunk)
            if result:
                if size <= output_bytes:
                    chunks.append(chunk)
                else:
                    overflow.set()
            else:
                stderr_count[0] += len(chunk)
        stream.close()

    readers = [threading.Thread(target=drain, args=(worker.stdout,), kwargs={"result": True}),
               threading.Thread(target=drain, args=(worker.stderr,), kwargs={"result": False})]
    for reader in readers:
        reader.start()
    reason, peak = "completed", None
    known = {worker.pid}
    try:
        try:
            worker.stdin.write(payload)
            worker.stdin.close()
        except BrokenPipeError:
            pass
        while worker.poll() is None:
            family = descendants(worker.pid, process_table())
            known.update(family)
            measured = [amount for pid in family if (amount := peak_bytes(pid)) is not None]
            if measured:
                peak = max(peak or 0, sum(measured))
            if overflow.is_set():
                reason = "output_limit"
            elif peak is not None and peak > memory_mib * MIB:
                reason = "memory_limit"
            elif time.perf_counter() - started > timeout:
                reason = "timeout"
            if reason != "completed":
                stop_tree(worker)
                break
            time.sleep(0.05)
    finally:
        if worker.poll() is None:
            stop_tree(worker)
        worker.wait(timeout=5)
        for reader in readers:
            reader.join(timeout=5)
    if overflow.is_set():
        reason = "output_limit"
    remaining = known.intersection(process_table())
    return {"status": reason, "exit_code": worker.returncode,
            "seconds": round(time.perf_counter() - started, 3),
            "peak_tree_mib_upper_bound": round(peak / MIB, 2) if peak is not None else None,
            "processes_seen": len(known),
            "stderr_bytes": stderr_count[0], "output_bytes": sum(map(len, chunks)),
            "worker_reaped": worker.poll() is not None and not remaining}, b"".join(chunks)


def load_generator(relative: str):
    """Load only the repository's synthetic fixture generator."""
    spec = importlib.util.spec_from_file_location(relative.replace("/", "_"), ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.generate_project


def snapshot(root: Path) -> dict:
    """Include both source bytes and modification times in the no-write check."""
    return {p.relative_to(root).as_posix(): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.suffix in (".c", ".h")}


def prepare(output: Path) -> dict[str, Path]:
    """Create new datasets; never pad or change an existing project."""
    mega = load_generator("test/mega_autosar/generate.py")
    scale = load_generator("test/scale_scope/generate.py")
    datasets = {"5125": mega(output / "files-5125"),
                "9221": mega(output / "files-9221", components=96, stages=48),
                "10002": scale(output / "files-10002", noise_files=10000)}
    for label, count in (("bytes-exact", 8), ("bytes-over", 8), ("file-over", 1)):
        root = output / label
        root.mkdir()
        for index in range(count):
            size = 4 * MIB + (label == "file-over")
            prefix = f"int Volume_{index}(void) {{ return {index}; }}\n".encode()
            data = prefix + b"/*" + b"x" * (size - len(prefix) - 5) + b"*/\n"
            with (root / f"Volume_{index}.c").open("xb") as stream:
                stream.write(data)
        if label == "bytes-over":
            (root / "Extra.c").write_bytes(b"\n")
        datasets[label] = root
    root = output / "functions-6001"
    root.mkdir()
    (root / "Many.c").write_text("".join(f"int Function_{i:05}(void) {{ return {i}; }}\n" for i in range(6001)), encoding="ascii")
    datasets["functions"] = root
    return datasets


def run_suite(output: Path, *, python: str, node: str, timeout: int = 60) -> dict:
    """Sequential ramp, then at most two concurrent workers; no unbounded stress loops."""
    output.mkdir(parents=True, exist_ok=False)
    available = available_memory_mib()
    if available is not None and available < 1536:
        raise RuntimeError("Less than 1536MiB available; two-worker test was not started")
    datasets = prepare(output)
    before = snapshot(output)
    result = {"python_version": sys.version.split()[0], "platform": sys.platform,
              "timeout_seconds": timeout, "per_process_tree_memory_mib": 512, "max_concurrent_workers": 2,
              "available_memory_mib_before": available,
              "cases": []}

    def query(name: str, dataset: str, *, count: int | None = None, metric: str | None = None,
              scoped: bool = False, truncated: bool = False, limit: int = 10000) -> dict:
        request = {"op": "functions", "root": str(datasets[dataset].resolve()),
                   "includePaths": ["app", "include", "components/Mega_000", "support"] if scoped else ["."],
                   "limits": {"maxFiles": limit}}
        record, raw = run_process([python, "-I", "-m", "autosar_trace_navigator.bridge"],
                                  json.dumps(request).encode(), timeout=timeout)
        record["name"] = name
        record["passed"] = False
        if record["status"] == "completed" and record["exit_code"] == 0 and not record["stderr_bytes"]:
            try:
                reply = json.loads(raw)
                if metric:
                    record["limit_details"] = reply.get("limitDetails")
                    record["passed"] = (set(reply) == {"ok", "error", "limitDetails"}
                                        and reply["ok"] is False and reply["error"] == "analysis_limit"
                                        and reply["limitDetails"]["metric"] == metric)
                else:
                    record["functions"] = len(reply.get("functions", []))
                    record["truncated"] = reply.get("truncated")
                    record["passed"] = reply.get("ok") is True and record["functions"] == count and record["truncated"] is truncated
            except (ValueError, KeyError, TypeError):
                record["status"] = "invalid_reply"
        print(json.dumps(record), flush=True)
        return record

    cases = result["cases"]
    for repeat in range(3):
        cases.append(query(f"scoped-84-{repeat+1}", "5125", count=170, scoped=True))
    for repeat in range(2):
        cases.append(query(f"full-5125-{repeat+1}", "5125", count=2755))
    cases.append(query("full-9221", "9221", count=4899))
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = [pool.submit(query, f"concurrent-5125-{n}", "5125", count=2755) for n in (1, 2)]
        cases.extend(future.result() for future in pending)
    cases.append(query("files-over-10000", "10002", metric="files"))
    cases.append(query("file-over-4MiB", "file-over", metric="file_bytes"))
    cases.append(query("source-over-32MiB", "bytes-over", metric="source_bytes"))
    cases.append(query("source-exact-32MiB", "bytes-exact", count=8))
    cases.append(query("functions-truncated-5000", "functions", count=5000, truncated=True))
    with zipfile.ZipFile(ROOT / "release/branch-investigation-0.1.0.vsix") as archive:
        adapter = output / "released-adapter.cjs"
        adapter.write_bytes(archive.read("extension/dist/src/adapters/traceAnalysisPort.js"))
    record, raw = run_process([node, str(ROOT / "scripts/verification/stress_transport.cjs"),
                              python, str(adapter), str(datasets["5125"]), str(output)], timeout=20)
    record["name"] = "released-transport"
    try:
        record["checks"] = json.loads(raw)
    except ValueError:
        record["checks"] = []
    record["passed"] = (record["status"] == "completed" and record["exit_code"] == 0
                        and len(record["checks"]) == 4 and all(check["passed"] for check in record["checks"]))
    cases.append(record)
    result["source_files"] = len(before)
    result["sources_unchanged"] = before == snapshot(output)
    result["passed"] = all(case["passed"] and case["worker_reaped"] for case in cases) and result["sources_unchanged"]
    (output / "results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new output directory (must not exist)")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--node", required=True)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 120:
        parser.error("timeout must be 1..120 seconds")
    result = run_suite(args.output.resolve(), python=args.python, node=args.node, timeout=args.timeout)
    print(json.dumps({"passed": result["passed"], "cases": len(result["cases"]),
                      "sources_unchanged": result["sources_unchanged"]}), flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
