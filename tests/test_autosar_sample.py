"""Fixture validation only; this is not the application's future C parser."""

from pathlib import Path
import unittest
from c_build import run_c99

from tree_sitter import Language, Parser
import tree_sitter_c


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "test"
TRACE = (
    "BrakeControl_10ms", "EvaluateBrakeMode", "IsAssistRequested",
    "IsSpeedEligible", "GetValidatedSpeed", "DecodeSpeed", "ReadRawSpeed",
)


def walk(node):
    """Walk concrete syntax nodes without preprocessing or symbol resolution."""
    yield node
    for child in node.named_children:
        yield from walk(child)


class AutosarSampleStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parser = Parser(Language(tree_sitter_c.language()))
        cls.trees = {
            path: parser.parse(path.read_bytes())
            for path in sorted(SAMPLE.rglob("*"))
            if path.suffix in {".c", ".h"} and not {"parser_cases", "large_autosar", "value_paths"}.intersection(path.parts)
        }
        cls.functions = {}
        for path, tree in cls.trees.items():
            for node in walk(tree.root_node):
                if node.type == "function_definition":
                    declarator = node.child_by_field_name("declarator")
                    name = declarator.child_by_field_name("declarator").text.decode()
                    cls.functions[name] = (path, node)

    def calls(self, name):
        return {
            node.child_by_field_name("function").text.decode()
            for node in walk(self.functions[name][1])
            if node.type == "call_expression"
        }

    def test_all_sample_files_parse_without_syntax_errors(self):
        self.assertGreaterEqual(len(self.trees), 10)
        for path, tree in self.trees.items():
            with self.subTest(path=path):
                self.assertFalse(tree.root_node.has_error)

    def test_target_to_rte_input_crosses_six_call_edges(self):
        self.assertEqual(len(TRACE) - 1, 6)
        for caller, callee in zip(TRACE, TRACE[1:]):
            with self.subTest(caller=caller, callee=callee):
                self.assertIn(callee, self.calls(caller))
                path, definition = self.functions[callee]
                self.assertTrue(path.is_file())
                self.assertGreaterEqual(definition.start_point.row + 1, 1)
        self.assertIn("Rte_Read_Speed_Raw", self.calls(TRACE[-1]))
        self.assertEqual(len({self.functions[name][0] for name in TRACE}), 3)

    def test_target_is_else_if_and_nested_branches_exist(self):
        function = self.functions["BrakeControl_10ms"][1]
        first_if = next(node for node in walk(function) if node.type == "if_statement")
        else_clause = first_if.child_by_field_name("alternative")
        target = next(node for node in else_clause.named_children if node.type == "if_statement")
        self.assertEqual(target.child_by_field_name("condition").text,
                         b"(mode == BRAKE_ASSIST)")
        self.assertIsNotNone(target.child_by_field_name("alternative"))
        decision = self.functions["IsAssistRequested"][1]
        nested = next(
            node for node in walk(decision)
            if node.type == "if_statement" and
            node.child_by_field_name("condition").text ==
            b"((eligible == 1) && (pedal >= 60u))"
        )
        self.assertEqual(nested.parent.type, "compound_statement")
        self.assertEqual(nested.parent.parent.type, "else_clause")

    def test_rte_producer_is_separate_from_consumer_call_chain(self):
        producer_calls = self.calls("SensorAcquisition_10ms")
        self.assertIn("Rte_Write_Speed_Raw", producer_calls)
        self.assertIn("Rte_Write_Pedal_Percent", producer_calls)
        for name in TRACE:
            self.assertNotIn("SensorAcquisition_10ms", self.calls(name))
        self.assertIn("Rte_Read_Pedal_Percent", self.calls("IsAssistRequested"))

    def test_macro_expression_is_not_a_function_definition(self):
        # Syntax alone sees a call-like expression; no claim of resolved semantics.
        self.assertIn("RAW_TO_KPH", self.calls("DecodeSpeed"))
        self.assertNotIn("RAW_TO_KPH", self.functions)


class AutosarSampleExecutionTests(unittest.TestCase):
    def test_compile_and_run_all_c_scenarios(self):
        sources = sorted((SAMPLE / "src").glob("*.c")) + sorted((SAMPLE / "support").glob("*.c"))
        output = run_c99(sources, include_dirs=(SAMPLE / "include",))
        self.assertIn("PASS all 12 scenarios", output)
        print("\n" + output, end="")


if __name__ == "__main__":
    unittest.main()
