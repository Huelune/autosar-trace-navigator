"""JSON bridge for the VS Code extension, checked on virtual C code only."""

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

from autosar_trace_navigator import bridge


ROOT = Path(__file__).resolve().parents[1]
SCOPE = ["include", "src", "support"]


def ask(file: str, line: int, *, root: Path = ROOT / "test", includes: list[str] | None = None) -> dict:
    return bridge.related({"root": str(root), "file": file, "line": line,
                           "includePaths": SCOPE if includes is None else includes})


def write(root: Path, name: str, text: str) -> None:
    (root / name).write_bytes(text.encode("utf-8"))


class BridgeTests(unittest.TestCase):
    def test_call_and_rte_candidates_stay_separate_with_editor_positions(self):
        before = {path: path.read_bytes() for path in (ROOT / "test").rglob("*.[ch]")}
        result = ask("src/SpeedSignal.c", 36)
        self.assertEqual(result["function"], {"name": "ReadRawSpeed"})
        rte = next(c for c in result["candidates"] if c["relation"] == "rte_data")
        self.assertEqual((rte["label"], rte["functionName"]), ("Speed_Raw", "SensorAcquisition_10ms"))
        self.assertIn("name_only_connection", rte["uncertainty"])
        self.assertEqual(rte["target"]["text"], "Rte_Write_Speed_Raw(speed)")
        self.assertEqual(rte["target"]["path"], "src/SensorAcquisition.c")
        call = next(c for c in ask("src/BrakeControl.c", 8)["candidates"] if c["label"] == "EvaluateBrakeMode")
        self.assertEqual(call["relation"], "call")
        self.assertIn("name_only_call_candidate", call["uncertainty"])
        self.assertEqual(call["target"]["text"], "BrakeMode EvaluateBrakeMode(void)")
        self.assertEqual(call["target"]["startLine"], call["target"]["endLine"])
        self.assertEqual(before, {path: path.read_bytes() for path in before})

    def test_out_of_scope_callee_is_reported_not_resolved(self):
        result = ask("src/SpeedSignal.c", 36, includes=["src"])
        call = next(c for c in result["candidates"] if c["relation"] == "call")
        self.assertIsNone(call["target"])
        self.assertIsNone(call["functionName"])
        self.assertIn("not_resolved_in_analysis_scope", call["uncertainty"])

    def test_line_outside_any_function_has_no_candidates(self):
        self.assertEqual(ask("src/SpeedSignal.c", 0),
                         {"ok": True, "function": None, "candidates": [], "truncated": False})

    def test_columns_are_utf16_and_invalid_utf8_gives_no_column(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            write(root, "a.c", "void Callee(void)\n{\n}\nvoid F(void)\n{\n    /* 한글😀 */ Callee();\n}\n")
            call = ask("a.c", 5, root=root, includes=[])["candidates"][0]
            # 4 spaces + "/* 한글😀 */ ": the emoji is two UTF-16 units but four UTF-8 bytes.
            self.assertEqual((call["evidence"]["startCharacter"], call["evidence"]["text"]), (15, "Callee()"))
            (root / "a.c").write_bytes(b"void Callee(void)\n{\n}\nvoid F(void)\n{\n    /* \xc7\xd1 */ Callee();\n}\n")
            call = ask("a.c", 5, root=root, includes=[])["candidates"][0]
            self.assertEqual((call["evidence"]["startLine"], call["evidence"]["startCharacter"],
                              call["evidence"]["text"]), (5, None, None))
            self.assertEqual(call["target"]["text"], "void Callee(void)")

    def test_failures_are_codes_without_paths_or_messages(self):
        for request, code in (
                ([], "invalid_request"),
                ({"root": "relative", "file": "a.c", "line": 0, "includePaths": []}, "invalid_request"),
                ({"root": str(ROOT / "test"), "file": "a.c", "line": -1, "includePaths": []}, "invalid_request"),
                ({"root": str(ROOT / "secret_missing"), "file": "a.c", "line": 0, "includePaths": []},
                 "scope_not_readable"),
                ({"root": str(ROOT / "test"), "file": "a.c", "line": 0, "includePaths": ["../secret"]},
                 "scope_not_readable"),
                ({"root": str(ROOT / "test"), "file": "secret.c", "line": 0, "includePaths": SCOPE},
                 "file_not_in_scope")):
            with self.subTest(code=code, request=request):
                with self.assertRaises(bridge.BridgeError) as raised:
                    bridge.related(request)
                self.assertEqual(raised.exception.args, (code,))

    def test_scope_over_file_budget_returns_no_partial_result(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            for index in range(501):
                (root / f"f{index}.c").write_bytes(b"")
            with self.assertRaises(bridge.BridgeError) as raised:
                ask("f0.c", 0, root=root, includes=[])
            self.assertEqual(raised.exception.args, ("analysis_limit",))

    def test_isolated_process_prints_one_ascii_json_and_no_secret(self):
        def run(payload: bytes) -> subprocess.CompletedProcess:
            return subprocess.run([sys.executable, "-I", "-m", "autosar_trace_navigator.bridge"],
                                  input=payload, capture_output=True, timeout=120)
        good = run(json.dumps({"root": str(ROOT / "test"), "file": "src/SpeedSignal.c", "line": 36,
                               "includePaths": SCOPE}).encode())
        self.assertEqual((good.returncode, good.stderr), (0, b""))
        self.assertTrue(good.stdout.isascii())
        self.assertEqual(json.loads(good.stdout)["function"]["name"], "ReadRawSpeed")
        bad = run(json.dumps({"root": str(ROOT / "secret_missing"), "file": "secret.c", "line": 0,
                              "includePaths": []}).encode())
        self.assertEqual((bad.returncode, bad.stderr), (0, b""))
        self.assertEqual(json.loads(bad.stdout), {"ok": False, "error": "scope_not_readable"})
        self.assertNotIn(b"secret", bad.stdout)
        self.assertEqual(json.loads(run(b"not json").stdout), {"ok": False, "error": "invalid_request"})


if __name__ == "__main__":
    unittest.main()
