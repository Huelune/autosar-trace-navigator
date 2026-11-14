"""Small supervision tests; the generated overload matrix is an explicit separate command."""

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("stress_analysis", ROOT / "scripts/verification/stress_analysis.py")
stress = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stress)


class StressSupervisionTests(unittest.TestCase):
    def test_existing_output_is_rejected_before_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "keep.c").write_bytes(b"int keep;\n")
            with patch.object(stress, "prepare") as prepare, self.assertRaises(FileExistsError):
                stress.run_suite(root, python=sys.executable, node="not-used")
            prepare.assert_not_called()
            self.assertEqual((root / "keep.c").read_bytes(), b"int keep;\n")

    def test_normal_stdout_and_stderr_are_drained_and_worker_reaped(self):
        record, raw = stress.run_process([sys.executable, "-I", "-c",
                                         "import sys;sys.stdout.write('ok');sys.stderr.write('note')"])
        self.assertEqual((record["status"], record["exit_code"], raw), ("completed", 0, b"ok"))
        self.assertEqual(record["stderr_bytes"], 4)
        self.assertTrue(record["worker_reaped"])

    def test_slow_worker_is_killed_on_deadline(self):
        record, _ = stress.run_process([sys.executable, "-I", "-c", "import time;time.sleep(30)"], timeout=0.1)
        self.assertEqual(record["status"], "timeout")
        self.assertTrue(record["worker_reaped"])
        self.assertLess(record["seconds"], 5)

    def test_output_flood_is_bounded(self):
        record, raw = stress.run_process([sys.executable, "-I", "-c", "import sys;sys.stdout.buffer.write(b'x'*131072)"],
                                        output_bytes=1024)
        self.assertEqual(record["status"], "output_limit")
        self.assertLessEqual(len(raw), 1024)
        self.assertTrue(record["worker_reaped"])

    def test_memory_guard_reaps_worker_when_sampler_reports_excess(self):
        with patch.object(stress, "peak_bytes", return_value=2 * stress.MIB):
            record, _ = stress.run_process([sys.executable, "-I", "-c", "import time;time.sleep(30)"], memory_mib=1)
        self.assertEqual(record["status"], "memory_limit")
        self.assertTrue(record["worker_reaped"])

    def test_timeout_also_terminates_the_real_python_behind_a_venv_launcher(self):
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp) / "pid.txt"
            code = f"import os,pathlib,time;pathlib.Path({str(marker)!r}).write_text(str(os.getpid()));time.sleep(30)"
            record, _ = stress.run_process([sys.executable, "-I", "-c", code], timeout=0.5)
            pid = int(marker.read_text())
            self.assertNotIn(pid, stress.process_table())
            self.assertTrue(record["worker_reaped"])
            self.assertEqual(record["status"], "timeout")
