"""Integration contracts between scanner output and parser records."""

from pathlib import Path
import tempfile
import unittest

from autosar_trace_navigator.parser import parse_file
from autosar_trace_navigator.scanner import scan_sources


ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def test_mixed_project_preserves_locations_references_and_error_isolation(self):
        sources = scan_sources(ROOT / "test", include_paths=("include", "src", "support", "parser_cases"))
        results = tuple(parse_file(source.path) for source in sources)
        self.assertEqual(len(sources), 14)
        self.assertEqual(tuple(result.path for result in results), tuple(s.path for s in sources))
        self.assertEqual(results, tuple(parse_file(s.path) for s in sources))
        all_ids = []
        for result in results:
            with self.subTest(path=result.path):
                functions = {f.id: f for f in result.functions}
                branches = {b.id: b for b in result.branches}
                all_ids.extend(functions)
                all_ids.extend(branches)
                data = result.path.read_bytes()
                for record in (*result.functions, *result.branches, *result.calls, *result.diagnostics):
                    span = record.location
                    self.assertEqual(span.path, result.path)
                    self.assertLessEqual(0, span.start_byte)
                    self.assertLessEqual(span.start_byte, span.end_byte)
                    self.assertLessEqual(span.end_byte, len(data))
                for branch in result.branches:
                    self.assertIn(branch.function_id, functions)
                    self.assertIn(branch.chain_id, branches)
                    self.assertEqual(branch.parent_id, branches[branch.chain_id].parent_id)
                    if branch.parent_id is not None:
                        self.assertIn(branch.parent_id, branches)
                        self.assertEqual(branch.function_id, branches[branch.parent_id].function_id)
                for call in result.calls:
                    if call.caller_id is not None:
                        self.assertIn(call.caller_id, functions)
                    if call.branch_id is not None:
                        self.assertIn(call.branch_id, branches)
                        self.assertEqual(call.caller_id, branches[call.branch_id].function_id)
                    span = call.location
                    self.assertEqual(data[span.start_byte:span.end_byte].decode("utf-8"), call.expression)
                    self.assertTrue(call.uncertainty)
        self.assertEqual(len(all_ids), len(set(all_ids)))
        error_paths = {r.path for r in results if any(d.code == "SYNTAX_ERROR" for d in r.diagnostics)}
        self.assertEqual(error_paths, {(ROOT / "test/parser_cases/malformed.c").resolve()})
        self.assertIn("BrakeControl_10ms", {f.name for r in results for f in r.functions})

    def test_same_named_static_functions_in_separate_units_have_distinct_owners(self):
        build = ROOT / "build"
        build.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="pipeline-", dir=build) as directory:
            root = Path(directory)
            for name in ("first.c", "second.c"):
                (root / name).write_bytes(
                    b"static int Helper(void) { return 1; }\n"
                    b"int Entry(void) { if (Helper()) return 1; else return 0; }\n"
                )
            results = [parse_file(source.path) for source in scan_sources(root)]
            self.assertEqual(len(results), 2)
            owners = []
            for result in results:
                self.assertEqual([f.name for f in result.functions], ["Helper", "Entry"])
                call = result.calls[0]
                self.assertEqual(call.caller_id, result.functions[1].id)
                self.assertEqual(call.branch_id, result.branches[0].id)
                self.assertEqual(call.callee_name, "Helper")
                self.assertIn("unresolved_call_target", call.uncertainty)
                owners.append(call.caller_id)
            self.assertNotEqual(*owners)


if __name__ == "__main__":
    unittest.main()
