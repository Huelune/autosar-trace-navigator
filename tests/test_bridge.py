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


def ask(file: str, line: int, *, root: Path = ROOT / "test", includes: list[str] | None = None,
        character: int | None = None) -> dict:
    return bridge.related({"root": str(root), "file": file, "line": line, "character": character,
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
                         {"ok": True, "function": None, "variable": None, "notes": [], "candidates": [],
                          "truncated": False})

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

    def test_cursor_variable_gets_value_sources_and_conditions_before_function_candidates(self):
        lines = (ROOT / "test/src/AssistDecision.c").read_text(encoding="utf-8").splitlines()
        line = next(i for i, text in enumerate(lines) if "pedal >= 60u" in text)
        result = ask("src/AssistDecision.c", line, character=lines[line].index("pedal"))
        self.assertEqual((result["variable"], result["notes"]), ("pedal", []))
        relations = [c["relation"] for c in result["candidates"]]
        self.assertEqual(relations, sorted(relations, key=["value", "execution_condition", "call", "rte_data"].index))
        supplier = next(c for c in result["candidates"] if c["label"] == "rte_data: pedal")
        self.assertEqual((supplier["relation"], supplier["functionName"], supplier["target"]["text"]),
                         ("value", "SensorAcquisition_10ms", "pedal"))
        self.assertIn("name_only_connection", supplier["uncertainty"])
        constant = next(c for c in result["candidates"] if c["label"] == "constant: 0u")
        self.assertIn("constant_source_not_constraint_solution", constant["uncertainty"])
        conditions = [(c["label"], c["requiredTruth"]) for c in result["candidates"]
                      if c["relation"] == "execution_condition"]
        self.assertEqual(conditions, [("(eligible < 0)", False), ("(Rte_Read_Pedal_Percent(&pedal) != E_OK)", False),
                                      ("(pedal > 100u)", False)])
        condition = next(c for c in result["candidates"] if c["relation"] == "execution_condition")
        self.assertIn("condition_satisfiability_not_proven", condition["uncertainty"])
        self.assertEqual(condition["target"]["text"], "(eligible < 0)")
        self.assertTrue(all(c["requiredTruth"] is None for c in result["candidates"]
                            if c["relation"] != "execution_condition"))
        # Without a column only the function-wide candidates are returned.
        self.assertEqual({c["relation"] for c in ask("src/AssistDecision.c", line)["candidates"]}, {"call", "rte_data"})

    def test_return_value_source_targets_the_callee_signature(self):
        lines = (ROOT / "test/src/AssistDecision.c").read_text(encoding="utf-8").splitlines()
        line = next(i for i, text in enumerate(lines) if "eligible < 0" in text)
        result = ask("src/AssistDecision.c", line, character=lines[line].index("eligible"))
        source = next(c for c in result["candidates"] if c["label"].startswith("return_value"))
        self.assertEqual((source["functionName"], source["target"]["text"]),
                         ("IsSpeedEligible", "int IsSpeedEligible(void)"))

    def test_cursor_limits_are_notes_and_global_declaration_path_is_relative(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            write(root, "a.c", "int g_input;\nint table[4];\nint F(void)\n{\n    if (g_input > 3) { return table[1]; }\n"
                               "    /* 한글 */ return g_input;\n}\n")
            result = ask("a.c", 4, root=root, includes=[], character=8)
            self.assertEqual(result["variable"], "g_input")
            source = next(c for c in result["candidates"] if c["label"] == "ct_global_input: g_input")
            self.assertIn("declaration: a.c:1", source["uncertainty"])
            self.assertNotIn(root.as_posix(), json.dumps(result).replace("\\\\", "/"))
            array = ask("a.c", 4, root=root, includes=[], character=30)
            self.assertEqual((array["variable"], array["notes"]), (None, ["access_path_not_supported"]))
            self.assertEqual([c["label"] for c in array["candidates"]], ["(g_input > 3)"])
            self.assertTrue(array["candidates"][0]["requiredTruth"])
            # Column counted in UTF-16 units after non-ASCII text on the same line.
            self.assertEqual(ask("a.c", 5, root=root, includes=[], character=20)["variable"], "g_input")
            beyond = ask("a.c", 5, root=root, includes=[], character=999)
            self.assertEqual((beyond["notes"], beyond["candidates"]), (["cursor_position_not_resolved"], []))
            (root / "a.c").write_bytes(b"int g_input;\nint F(void)\n{\n    /* \xc7\xd1 */ return g_input;\n}\n")
            unknown = ask("a.c", 3, root=root, includes=[], character=20)
            self.assertEqual((unknown["variable"], unknown["notes"]), (None, ["cursor_position_not_resolved"]))

    def test_no_reason_in_any_form_carries_the_absolute_root(self):
        root = ROOT / "test" / "struct_paths"
        lines = (root / "consumer.c").read_text(encoding="utf-8").splitlines()
        line = next(i for i, text in enumerate(lines) if "a = b.a" in text)
        result = ask("consumer.c", line, root=root, includes=["."], character=lines[line].index("b.a"))
        self.assertEqual(result["variable"], "b.a")
        reasons = [reason for c in result["candidates"] for reason in c["uncertainty"]]
        self.assertIn("member_type_layout_not_verified", reasons)
        self.assertNotIn(root.resolve().as_posix().casefold(), json.dumps(result).replace("\\\\", "/").casefold())
        project = bridge.analyze_project(root)
        hidden = bridge._notes(project, (f"declaration: {root.parent / 'secret.c'}:3", f"seen in {project.root}",
                                         f"initializer_declaration: {project.root / 'producer.c'}:7", "plain_reason"))
        self.assertEqual(hidden, ["declaration: outside_analysis_root:3", "path_detail_withheld",
                                  "initializer_declaration: producer.c:7", "plain_reason"])

    def test_failures_are_codes_without_paths_or_messages(self):
        for request, code in (
                ([], "invalid_request"),
                ({"root": "relative", "file": "a.c", "line": 0, "includePaths": []}, "invalid_request"),
                ({"root": str(ROOT / "test"), "file": "a.c", "line": -1, "includePaths": []}, "invalid_request"),
                ({"root": str(ROOT / "test"), "file": "a.c", "line": 0, "character": "1", "includePaths": []},
                 "invalid_request"),
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
