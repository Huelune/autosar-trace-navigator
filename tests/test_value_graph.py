"""Recursive preview preserves candidates, uncertainty, finite limits and source bytes."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from autosar_trace_navigator import bridge
from autosar_trace_navigator.models import ValueProbe
from autosar_trace_navigator.value_graph import trace_origins
from autosar_trace_navigator.workbench import analyze_project

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "test/origin_preview"


def request_at(root: Path, file: str, needle: str) -> dict:
    source = (root / file).read_text(encoding="utf-8")
    offset = source.index(needle)
    before = source[:offset]
    return {"op": "value_graph", "root": str(root.resolve()), "file": file,
            "line": before.count("\n"), "character": len(before.rsplit("\n", 1)[-1].encode("utf-16-le")) // 2,
            "includePaths": ["."]}


class ValueGraphTests(unittest.TestCase):
    def setUp(self):
        self.before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in SAMPLE.glob("*") if p.suffix in {".c", ".h"}}
        self.request = request_at(SAMPLE, "Consumer.c", "pedal >=")

    def tearDown(self):
        self.assertEqual(self.before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.before})

    def test_recursive_returns_rte_calculations_and_guard_inputs_use_one_analysis(self):
        with patch.object(bridge, "analyze_project", wraps=analyze_project) as analyze:
            result = bridge.value_graph(self.request)
        self.assertEqual(analyze.call_count, 1)
        self.assertFalse(result["truncated"])
        inputs = {n["expression"] for n in result["nodes"] if n["terminal"] == "ct_input"}
        self.assertTrue({"Preview_Raw", "Preview_Enable", "Preview_Quality"}.issubset(inputs), inputs)
        self.assertTrue(any(e["relation"] == "rte_data" for e in result["edges"]))
        self.assertTrue(any(e["relation"] == "call" for e in result["edges"]))
        conditions = [n for n in result["nodes"] if n["kind"] == "condition"]
        self.assertTrue(any(n["requiredTruth"] is False and "== 1u" in n["expression"] for n in conditions))
        self.assertTrue(any(n["requiredTruth"] is True and "== 2u" in n["expression"] for n in conditions))
        self.assertNotIn(str(SAMPLE), json.dumps(result))
        ids = {n["id"] for n in result["nodes"]}
        self.assertTrue(all(e["from"] in ids and e["to"] in ids for e in result["edges"]))

    def test_node_and_depth_limits_are_partial_not_successful_endpoints(self):
        for limits, reason in (({"maxNodes": 1}, "nodes"), ({"maxDepth": 1}, "depth")):
            with self.subTest(limits=limits):
                result = bridge.value_graph({**self.request, "traceLimits": limits})
                self.assertTrue(result["truncated"])
                self.assertIn(reason, result["limitReasons"])
                self.assertTrue(any(n["terminal"] == "limit" for n in result["nodes"]))
                self.assertLessEqual(len(result["nodes"]), limits.get("maxNodes", 1000))

    def test_invalid_limits_rejected_before_source_analysis(self):
        for value in (True, 0, 2001, "100", -1):
            with self.subTest(value=value), patch.object(bridge, "analyze_project") as analyze:
                with self.assertRaises(bridge.BridgeError) as error:
                    bridge.value_graph({**self.request, "traceLimits": {"maxNodes": value}})
                self.assertEqual(error.exception.args, ("invalid_request",))
                analyze.assert_not_called()

    def test_cycle_is_finite_and_not_marked_ct_input(self):
        project = analyze_project(SAMPLE)
        function = project.functions_by_name["Origin_Cycle"][0]
        result = trace_origins(project, ValueProbe(function.id, "$return", function.location, "return"))
        self.assertTrue(result.cycle_edges)
        self.assertLess(len(result.nodes), 10)
        self.assertTrue(any(n.terminal == "cycle" for n in result.nodes))

    def test_time_limit_marks_waiting_probes(self):
        project = analyze_project(SAMPLE)
        function = project.functions_by_name["Origin_First"][0]
        with patch("autosar_trace_navigator.value_graph.time.monotonic", side_effect=[0, 2]):
            result = trace_origins(project, ValueProbe(function.id, "$return", function.location, "return"), max_seconds=1)
        self.assertEqual(result.limit_reasons, ["time"])
        self.assertEqual(result.nodes[0].terminal, "limit")

    def test_unknown_call_and_unsupported_array_are_not_guessed(self):
        result = bridge.value_graph(request_at(SAMPLE, "Consumer.c", "x; }"))
        self.assertTrue(any(n["terminal"] == "unresolved" for n in result["nodes"]))
        with self.assertRaises(bridge.BridgeError) as raised:
            bridge.value_graph(request_at(SAMPLE, "Consumer.c", "table[0]"))
        self.assertEqual(raised.exception.args, ("variable_not_supported",))

    def test_member_and_pointer_output_argument_reach_raw_input(self):
        root = ROOT / "test/struct_paths"
        result = bridge.value_graph(request_at(root, "consumer.c", "a >="))
        self.assertTrue(any(n["terminal"] == "ct_input" and n["expression"] == "Struct_RawInput"
                            for n in result["nodes"]))

    def test_real_isolated_bridge_op_returns_a_graph(self):
        result = subprocess.run([sys.executable, "-I", "-m", "autosar_trace_navigator.bridge"],
                                input=json.dumps(self.request).encode(), capture_output=True, timeout=20)
        self.assertEqual((result.returncode, result.stderr), (0, b""))
        graph = json.loads(result.stdout)
        self.assertEqual(graph["rootId"], "n1")
        self.assertEqual(graph["variable"], "pedal")

    def test_static_and_const_do_not_become_ct_input_candidates(self):
        project = analyze_project(SAMPLE)
        function = project.functions_by_name["Origin_Hidden"][0]
        graph = trace_origins(project, ValueProbe(function.id, "$return", function.location, "return"))
        self.assertFalse(any(n.terminal == "ct_input" for n in graph.nodes))

    def test_parameter_position_maps_all_callers_and_keeps_condition_inputs(self):
        root = ROOT / "test/caller_paths"
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.glob("*") if p.suffix in {".c", ".h"}}
        graph = bridge.value_graph(request_at(root, "Callers.c", "pedal >="))
        self.assertFalse(graph["truncated"])
        inputs = {n["expression"] for n in graph["nodes"] if n["terminal"] == "ct_input"}
        self.assertEqual(inputs, {"Caller_Raw", "Caller_AlternateRaw", "Caller_Enable"})
        args = [n for n in graph["nodes"] if n["kind"] == "parameter_input"]
        self.assertTrue(any(n["functionName"] == "Caller_Relay" and n["expression"] == "command" for n in args))
        self.assertTrue(any(n["functionName"] == "Caller_Run" and n["expression"] == "amount" for n in args))
        constants = {n["expression"] for n in graph["nodes"] if n["terminal"] == "constant"}
        self.assertIn("65u", constants)
        self.assertNotIn("999u", constants)
        self.assertNotIn("7u", constants)
        self.assertNotIn("123u", constants)
        returned = next(n for n in graph["nodes"] if n["kind"] == "return_value" and n["expression"] == "Caller_GetRaw()")
        self.assertEqual(returned["functionName"], "Caller_GetRaw")
        self.assertEqual(returned["siteFunctionName"], "Caller_FromFunction")
        self.assertTrue(all("call_context_not_bound" in n["uncertainty"] for n in args))
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before})

    def test_context_contains_condition_but_does_not_widen_navigation_anchor(self):
        graph = bridge.value_graph(self.request)
        root = graph["nodes"][0]
        self.assertEqual(root["location"]["text"], "pedal")
        self.assertIn("pedal >= 60u", root["context"]["text"])
        self.assertLessEqual(len(root["context"]["text"]), 2000)

    def test_oversize_context_falls_back_to_the_exact_selected_text(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "Long.c").write_text("unsigned Input;\n/*" + "x" * 9000 + "*/\n"
                                         "int Check(unsigned value) { if (value >= 60u) return 1; return 0; }\n")
            graph = bridge.value_graph(request_at(root, "Long.c", "value >="))
            self.assertIsNone(graph["nodes"][0]["context"])
            self.assertEqual(graph["nodes"][0]["location"]["text"], "value")

    def test_high_fanout_is_explicitly_truncated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = "unsigned Many(unsigned a) {\n" + "".join(
                f"if(a == {i}u) return {i}u;\n" for i in range(80)) + "return 99u; }\n"
            (root / "Many.c").write_text(source, encoding="ascii")
            project = analyze_project(root)
            function = project.functions[0]
            graph = trace_origins(project, ValueProbe(function.id, "$return", function.location, "return"))
            self.assertIn("sources", graph.limit_reasons)
            self.assertLessEqual(len(graph.nodes), 1000)
