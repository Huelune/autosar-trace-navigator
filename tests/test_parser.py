"""Product parser tests, distinct from the original fixture syntax checks."""

import hashlib
from pathlib import Path
import unittest

from autosar_trace_navigator.parser import parse_file, parse_source
from autosar_trace_navigator.scanner import scan_sources


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "test" / "parser_cases"


class ParserTests(unittest.TestCase):
    def parse(self, source: str):
        return parse_source(source.encode("utf-8"), path=CASES / "virtual.c")

    def test_definitions_not_prototypes_and_pointer_return_declarator(self):
        result = self.parse("int Prototype(int);\nstatic int *Pick(void) { return 0; }\n"
                            "int (*Factory(void))(int) { return 0; }\n")
        self.assertEqual([item.name for item in result.functions], ["Pick", "Factory"])
        self.assertEqual(result.diagnostics, ())
        self.assertEqual(result.functions[0].location.start_line, 2)

    def test_repeated_and_indirect_calls_and_branch_ownership(self):
        result = self.parse("void f(void) { if (Check()) { Send(); Send(); } "
                            "else (*handler)(); ops->run(); }")
        self.assertEqual([call.callee_expression for call in result.calls],
                         ["Check", "Send", "Send", "(*handler)", "ops->run"])
        self.assertEqual([call.kind for call in result.calls],
                         ["direct_candidate"] * 3 + ["indirect"] * 2)
        self.assertNotEqual(result.calls[1].location, result.calls[2].location)
        self.assertEqual(result.calls[0].branch_id, result.branches[0].id)
        self.assertEqual(result.calls[3].branch_id, result.branches[1].id)
        self.assertIsNone(result.calls[4].branch_id)
        self.assertTrue(all("unresolved_call_target" in call.uncertainty for call in result.calls))

    def test_nested_branch_chain_parentage_comments_and_single_statements(self):
        result = parse_file(CASES / "branches.c")
        self.assertFalse(any(item.code == "SYNTAX_ERROR" for item in result.diagnostics))
        outer, nested_if, nested_else, outer_elif, outer_else, last_if = result.branches
        self.assertEqual([b.kind for b in result.branches],
                         ["if", "if", "else", "else_if", "else", "if"])
        self.assertEqual(outer.chain_id, outer_elif.chain_id)
        self.assertEqual(outer.chain_id, outer_else.chain_id)
        self.assertEqual(nested_if.chain_id, nested_else.chain_id)
        self.assertNotEqual(outer.chain_id, nested_if.chain_id)
        self.assertEqual(nested_if.parent_id, outer.id)
        self.assertEqual(nested_else.parent_id, outer.id)
        self.assertEqual(last_if.parent_id, outer_else.id)
        self.assertIsNone(outer_elif.parent_id)
        self.assertIsNone(outer_else.condition)
        self.assertEqual(outer_elif.location.start_line, 8)
        self.assertEqual(outer_else.location.start_line, 10)

    def test_local_header_macros_and_inactive_alternatives_remain_uncertain(self):
        result = parse_file(CASES / "macros.c", known_macros=("HEADER_MACRO",))
        self.assertEqual([item.name for item in result.functions], ["Select", "Select", "Decide"])
        self.assertNotEqual(result.functions[0].id, result.functions[1].id)
        self.assertEqual([call.kind for call in result.calls], ["macro", "macro"])
        self.assertIn("unexpanded_macro", result.branches[0].uncertainty)
        self.assertTrue(all("preprocessing_not_performed" in f.uncertainty for f in result.functions))
        self.assertEqual(sum(d.code == "MACRO_INVOCATION" for d in result.diagnostics), 2)

    def test_unknown_header_macro_is_not_confirmed_as_a_function(self):
        result = parse_file(CASES / "macros.c")
        call = next(call for call in result.calls if call.callee_name == "HEADER_MACRO")
        self.assertEqual(call.kind, "direct_candidate")
        self.assertIn("unresolved_call_target", call.uncertainty)

    def test_malformed_syntax_has_diagnostics_and_tainted_results(self):
        result = parse_file(CASES / "malformed.c")
        self.assertIn("SYNTAX_ERROR", {d.code for d in result.diagnostics})
        for record in (*result.functions, *result.calls, *result.branches):
            self.assertIn("file_has_syntax_errors", record.uncertainty)

    def test_exact_utf8_byte_ranges_and_crlf_lines(self):
        source = "// 한글\r\nvoid f(void) {\r\n  if (Ready()) Go();\r\n}\r\n".encode("utf-8")
        result = parse_source(source, path=CASES / "virtual.c")
        call = result.calls[0]
        self.assertEqual((call.location.start_line, call.location.start_column), (3, 7))
        self.assertEqual(call.location.path, (CASES / "virtual.c").resolve())
        for record in (*result.functions, *result.calls, *result.branches):
            span = record.location
            self.assertGreater(span.end_byte, span.start_byte)
        span = call.location
        self.assertEqual(source[span.start_byte:span.end_byte], b"Ready()")
        self.assertEqual(span.end_column, 14)

    def test_non_utf8_is_disclosed_and_empty_file_is_valid(self):
        result = parse_source(b"// \xff\nvoid f(void) {}", path=CASES / "virtual.c")
        self.assertIn("NON_UTF8_SOURCE", {d.code for d in result.diagnostics})
        empty = self.parse("")
        self.assertEqual((empty.functions, empty.calls, empty.branches, empty.diagnostics), ((), (), (), ()))

    def test_missing_input_raises_io_error(self):
        with self.assertRaises(FileNotFoundError):
            parse_file(CASES / "not_present.c")

    def test_autosar_declaration_macro_is_not_misreported_as_void_function(self):
        result = parse_source(
            b"FUNC(void, CODE) Runnable(void) { if (Gate()) Act(); }",
            path=CASES / "virtual.c", known_macros=("FUNC",),
        )
        self.assertEqual(result.functions, ())
        self.assertTrue({"SYNTAX_ERROR", "UNRESOLVED_FUNCTION", "MACRO_INVOCATION"}
                        .issubset({d.code for d in result.diagnostics}))

    def test_six_step_autosar_trace_with_product_parser_and_unchanged_sources(self):
        paths = [item.path for item in scan_sources(ROOT / "test", include_paths=("include", "src", "support"))]
        before = {path: (hashlib.sha256(path.read_bytes()).digest(), path.stat().st_mtime_ns)
                  for path in paths}
        results = [parse_file(path) for path in paths]
        definitions = {f.id: f for result in results for f in result.functions}
        calls = [call for result in results for call in result.calls]
        # Names verify syntactic edges here; they do not implement C symbol linking.
        edges = {(definitions[call.caller_id].name, call.callee_name)
                 for call in calls if call.caller_id in definitions}
        trace = ("BrakeControl_10ms", "EvaluateBrakeMode", "IsAssistRequested",
                 "IsSpeedEligible", "GetValidatedSpeed", "DecodeSpeed", "ReadRawSpeed")
        self.assertTrue(set(zip(trace, trace[1:])).issubset(edges))
        self.assertIn(("ReadRawSpeed", "Rte_Read_Speed_Raw"), edges)
        self.assertNotIn(("ReadRawSpeed", "SensorAcquisition_10ms"), edges)
        target = next(branch for result in results for branch in result.branches
                      if branch.condition == "(mode == BRAKE_ASSIST)")
        self.assertEqual(target.kind, "else_if")
        self.assertEqual(target.location.start_line, 10)
        self.assertEqual(target.location.path, (ROOT / "test/src/BrakeControl.c").resolve())
        macro = next(call for call in calls if call.callee_name == "RAW_TO_KPH")
        self.assertEqual(macro.kind, "macro")
        self.assertTrue(all(d.code != "SYNTAX_ERROR" for r in results for d in r.diagnostics))
        self.assertEqual(before, {path: (hashlib.sha256(path.read_bytes()).digest(), path.stat().st_mtime_ns)
                                  for path in paths})


if __name__ == "__main__":
    unittest.main()
