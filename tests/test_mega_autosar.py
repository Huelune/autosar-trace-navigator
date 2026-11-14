"""5,125-file synthetic scope and a real 40-stage consumer/publisher example."""

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from c_build import run_c99
from autosar_trace_navigator.workbench import AnalysisLimitError, analyze_project, function_candidates


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("mega_generator", ROOT / "test/mega_autosar/generate.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def source_snapshot(root: Path) -> dict:
    """Record source bytes and timestamps to detect accidental source modification."""
    return {p.relative_to(root): (hashlib.sha256(p.read_bytes()).digest(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.suffix in (".c", ".h")}


class MegaAutosarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="mega-autosar-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = generator.generate_project(Path(cls.temp.name) / "project")
        cls.before = source_snapshot(cls.root)
        started = time.perf_counter()
        cls.project = analyze_project(cls.root, include_paths=["."], max_files=6000)
        cls.elapsed = time.perf_counter() - started

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.before != source_snapshot(cls.root):
            raise AssertionError("Generated C/H files were modified during analysis or execution")
        print(f"Mega fixture: 5125 C/H, full analysis {cls.elapsed:.3f}s (single local run, not a performance guarantee)")

    def test_full_project_has_5125_files_and_each_component_is_parseable(self) -> None:
        project = self.project
        manifest = json.loads((self.root / "manifest.json").read_text())
        self.assertEqual((manifest["c_files"], manifest["h_files"]), (2563, 2562))
        self.assertEqual(len(project.sources), 5125)
        self.assertEqual(sum(len(data) for _, data in project.sources), manifest["source_bytes"])
        syntax_errors = [(r.path.name, d.location.start_line) for r in project.results
                         for d in r.diagnostics if d.code == "SYNTAX_ERROR"]
        self.assertEqual(syntax_errors, [])
        self.assertTrue(any(d.code == "PREPROCESSOR_NOT_EVALUATED"
                            for r in project.results for d in r.diagnostics))
        for component in (0, 1, 31, 63):
            for stage in (0, 19, 39):
                self.assertEqual(len(project.functions_by_name[f"Mega_{component:03}_Stage_{stage:02}"]), 1)

    def test_default_budget_fails_before_parsing_without_partial_results(self) -> None:
        with patch("autosar_trace_navigator.workbench.parse_source") as parse:
            with self.assertRaises(AnalysisLimitError) as raised:
                analyze_project(self.root, include_paths=["."])
            self.assertEqual((raised.exception.metric, raised.exception.observed_at_least, raised.exception.limit),
                             ("files", 5125, 500))
            parse.assert_not_called()

    def test_goal_traverses_40_stages_then_output_argument_read_and_separate_writer(self) -> None:
        project = self.project
        current = project.functions_by_name["Mega_Goal"][0]
        for stage in range(40):
            expected = f"Mega_000_Stage_{stage:02}"
            candidate, = (c for c in function_candidates(project, current)
                          if c.relation == "call" and c.function and c.function.name == expected)
            current = candidate.function
            self.assertEqual(current.location.path.name, f"Stage_{stage:02}.c")
            self.assertGreaterEqual(current.location.start_line, 1)
        candidates = function_candidates(project, current)
        self.assertTrue(any(c.relation == "call" and c.label == "Rte_Read_Mega000_Pedal" for c in candidates))
        writer, = (c for c in candidates if c.relation == "rte_data" and c.function and c.function.name == "Mega_000_Publish")
        self.assertIn("name_only_connection", writer.uncertainty)
        self.assertFalse(any(c.relation == "call" and c.function and c.function.name == "Mega_000_Publish" for c in candidates))
        publisher = next(r for r in project.results if r.path == current.location.path)
        conditions = [b.condition for b in publisher.branches if b.function_id == writer.function.id]
        self.assertIn("(g_Stimulus_000.quality == 1u)", conditions)
        self.assertIn("(g_Stimulus_000.quality == 2u)", conditions)
        self.assertIn("(g_Stimulus_000.enabled != 0u)", conditions)

    def test_selected_component_fits_default_budget_and_preserves_target_chain(self) -> None:
        project = analyze_project(self.root, include_paths=["app", "include", "components/Mega_000", "support"])
        self.assertEqual(len(project.sources), 84)
        self.assertNotIn("Mega_063_Stage_00", project.functions_by_name)
        self.assertIn("Mega_000_Stage_39", project.functions_by_name)
        read = project.functions_by_name["Mega_000_Stage_39"][0]
        self.assertTrue(any(c.relation == "rte_data" and c.function and c.function.name == "Mega_000_Publish"
                            for c in function_candidates(project, read)))

    def test_active_chain_executes_9_boundary_condition_and_order_scenarios(self) -> None:
        component = self.root / "components/Mega_000"
        sources = [self.root / "app/Mega_Goal.c", self.root / "support/Rte_Memory.c",
                   self.root / "runtime/Scenarios.c", *sorted(component.glob("*.c"))]
        self.assertEqual(len(sources), 43)
        output = run_c99(sources, include_dirs=[self.root / "include", component])
        self.assertIn("PASS mega AUTOSAR: 9 scenarios", output)

    def test_generator_is_deterministic_and_refuses_existing_or_invalid_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a = generator.generate_project(root / "a", components=1, stages=2)
            b = generator.generate_project(root / "b", components=1, stages=2)
            self.assertEqual({p.relative_to(a): p.read_bytes() for p in a.rglob("*") if p.is_file()},
                             {p.relative_to(b): p.read_bytes() for p in b.rglob("*") if p.is_file()})
            before = source_snapshot(a)
            with self.assertRaises(FileExistsError):
                generator.generate_project(a, components=1, stages=2)
            self.assertEqual(source_snapshot(a), before)
            for options in ({"components": True}, {"components": 97}, {"stages": 1}, {"stages": 49}):
                with self.subTest(options=options), self.assertRaises(ValueError):
                    generator.generate_project(root / "invalid", **options)
                self.assertFalse((root / "invalid").exists())


if __name__ == "__main__":
    unittest.main()
