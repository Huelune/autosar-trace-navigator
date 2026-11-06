"""Value-source candidates and the synthetic pedal input chain, not constraint solving."""

from pathlib import Path
import tempfile
import unittest

from autosar_trace_navigator.dataflow import ValueResolver
from autosar_trace_navigator.models import SourceRange, ValueProbe
from autosar_trace_navigator.workbench import analyze_project


ROOT = Path(__file__).resolve().parents[1]


class DataflowTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "build").mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=ROOT / "build")
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "values.c"

    def project(self, source: str):
        self.path.write_text(source, encoding="utf-8")
        return analyze_project(self.path.parent)

    def at(self, project, function: str, variable: str, marker: str):
        fn = project.functions_by_name[function][0]
        data = dict(project.sources)[fn.location.path]
        offset = data.index(marker.encode(), fn.location.start_byte)
        prefix = data[:offset]
        line, column = prefix.count(b"\n") + 1, len(prefix.rsplit(b"\n", 1)[-1]) + 1
        span = SourceRange(fn.location.path, line, column, line, column + len(marker), offset, offset + len(marker))
        return ValueProbe(fn.id, variable, span)

    def test_initializers_assignments_and_no_later_write(self):
        project = self.project("int F(void) { int value=0; if (flag) value=10; else value=20; "
                               "if (value >= 10) Use(); value=99; return value; }")
        probe = self.at(project, "F", "value", "if (value")
        rows = ValueResolver(project).sources(probe)
        self.assertEqual({r.expression for r in rows}, {"0", "10", "20"})
        self.assertTrue(all("control_flow_not_proven" in r.uncertainty for r in rows))
        self.assertTrue(all(r.next_probe is None for r in rows))

    def test_return_call_and_arithmetic_operands_keep_transform_uncertainty(self):
        project = self.project("int Get(void) { int raw=5; return (int)(raw + 1); } "
                               "int F(void) { int value=Get(); return value; }")
        resolver = ValueResolver(project)
        source = resolver.sources(self.at(project, "F", "value", "return value"))[0]
        self.assertEqual(source.kind, "return_value")
        returns = resolver.sources(source.next_probe)
        operand = next(r for r in returns if r.next_probe)
        self.assertEqual(operand.next_probe.expression, "raw")
        self.assertIn("expression_not_inverted", operand.uncertainty)
        self.assertEqual(resolver.sources(operand.next_probe)[0].expression, "5")

    def test_parameter_maps_to_call_arguments_without_binding_one_execution(self):
        project = self.project("int F(int value) { return value; } "
                               "void A(void) { F(60); F(item->value); }")
        rows = ValueResolver(project).sources(self.at(project, "F", "value", "return value"))
        self.assertEqual({r.expression for r in rows}, {"60", "item->value"})
        self.assertTrue(all(r.next_probe is None for r in rows))
        self.assertTrue(all("call_context_not_bound" in r.uncertainty for r in rows))

    def test_unknown_output_alias_and_macro_are_boundaries(self):
        project = self.project("#define SCALE(x) ((x)*2)\n"
                               "int F(void) { int raw=3; int value=SCALE(raw); ReadUnknown(&value); return value; }")
        rows = ValueResolver(project).sources(self.at(project, "F", "value", "return value"))
        self.assertIn("unresolved_call", {r.kind for r in rows})
        self.assertIn("possible_output_argument", {r.kind for r in rows})
        argument = next(r for r in rows if r.kind == "call_argument")
        self.assertEqual(argument.next_probe.expression, "raw")
        self.assertIn("call_transformation_not_resolved", argument.uncertainty)

    def test_member_target_rejected_and_unrelated_member_write_not_matched(self):
        project = self.project("int F(void) { object.value=60; return value; }")
        resolver = ValueResolver(project)
        probe = self.at(project, "F", "value", "return value")
        self.assertEqual(resolver.sources(probe)[0].kind, "input_boundary")
        with self.assertRaises(ValueError):
            resolver.sources(ValueProbe(probe.function_id, "object.value", probe.location))

    def test_missing_rte_producer_is_explicit(self):
        project = self.project("int F(void) { int pedal=0; Rte_Read_Pedal_Percent(&pedal); if (pedal>=60) return 1; return 0; }")
        rows = ValueResolver(project).sources(self.at(project, "F", "pedal", "if (pedal"))
        missing = next(r for r in rows if r.kind == "missing_rte_producer")
        self.assertIn("no_producer_in_analysis_scope", missing.uncertainty)

    def test_pedal_chain_reaches_reset_parameter_and_literal_test_input(self):
        project = analyze_project(ROOT / "test", include_paths=("include", "src", "support"))
        resolver = ValueResolver(project)
        probe = self.at(project, "IsAssistRequested", "pedal", "if ((eligible")
        row = next(r for r in resolver.sources(probe) if r.kind == "rte_data")
        self.assertEqual(project.functions_by_id[row.function_id].name, "SensorAcquisition_10ms")
        self.assertEqual(row.next_probe.expression, "pedal")
        self.assertIn("name_only_connection", row.uncertainty)
        getter = next(r for r in resolver.sources(row.next_probe) if r.kind == "return_value")
        self.assertEqual(project.functions_by_id[getter.function_id].name, "IoHwAb_ReadPedalPercent")
        global_value = next(r for r in resolver.sources(getter.next_probe) if r.next_probe)
        self.assertEqual(global_value.next_probe.expression, "hardware_pedal")
        writer = next(r for r in resolver.sources(global_value.next_probe) if r.kind == "global_write")
        self.assertEqual(project.functions_by_id[writer.function_id].name, "TestPlatform_Reset")
        inputs = resolver.sources(writer.next_probe)
        self.assertTrue(any(r.expression == "60u" and r.next_probe is None for r in inputs))
        self.assertTrue(any("call_context_not_bound" in r.uncertainty for r in inputs))


if __name__ == "__main__":
    unittest.main()
