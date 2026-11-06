"""Real multi-file fixture analysis, scoped exploration and compiled C behavior."""

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from c_build import run_c99
from autosar_trace_navigator.storage import TraceStore
from autosar_trace_navigator.trace import TraceManager
from autosar_trace_navigator.workbench import AnalysisLimitError, Workbench, analyze_project


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "test/large_autosar"


def fixture_snapshot() -> dict:
    """Detect fixture modifications including metadata and whitespace changes."""
    return {path.relative_to(SAMPLE): (hashlib.sha256(path.read_bytes()).digest(), path.stat().st_mtime_ns)
            for path in SAMPLE.rglob("*") if path.is_file()}


class LargeAutosarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = fixture_snapshot()
        cls.project = analyze_project(SAMPLE)
        cls.manifest = json.loads((SAMPLE / "manifest.json").read_text(encoding="utf-8"))
        spec = importlib.util.spec_from_file_location("large_fixture_generator", ROOT / "test/generate_large_autosar.py")
        cls.generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.generator)

    @classmethod
    def tearDownClass(cls):
        if fixture_snapshot() != cls.before:
            raise AssertionError("Large AUTOSAR fixture was modified during analysis/execution")

    def test_all_files_parse_and_have_expected_diverse_structure(self):
        project = self.project
        self.assertEqual(len(self.manifest["components"]), 24)
        self.assertEqual(sum(path.suffix == ".c" for path, _ in project.sources), 122)
        self.assertEqual(sum(path.suffix == ".h" for path, _ in project.sources), 49)
        self.assertEqual(len(project.functions), 424)
        self.assertEqual(sum(len(result.branches) for result in project.results), 665)
        self.assertFalse(any(d.code == "SYNTAX_ERROR" for r in project.results for d in r.diagnostics))
        self.assertEqual({b.kind for r in project.results for b in r.branches}, {"if", "else_if", "else"})
        self.assertTrue(any(c.kind == "indirect" for r in project.results for c in r.calls))

    def test_every_swc_has_six_call_edges_to_raw_input(self):
        names_by_id = {function.id: function.name for function in self.project.functions}
        edges = {(names_by_id[call.caller_id], call.callee_name)
                 for result in self.project.results for call in result.calls if call.caller_id in names_by_id}
        for component in self.manifest["components"]:
            name = component["name"]
            trace = [f"{name}_{suffix}" for suffix in ("10ms", "Evaluate", "Decide", "Eligible", "Validated", "Decode", "Read")]
            with self.subTest(component=name):
                self.assertEqual(component["trace"], trace)
                self.assertTrue(set(zip(trace, trace[1:])).issubset(edges))
                self.assertIn((trace[-1], f"Rte_Read_{name}_Signal_Raw"), edges)
                owner = next(f for f in self.project.functions if f.name == trace[0])
                targets = [b for r in self.project.results for b in r.branches
                           if b.function_id == owner.id and b.condition == "(mode == MODE_ACTIVE)"]
                self.assertEqual(len(targets), 1)
                self.assertEqual(targets[0].kind, "else_if")

    def test_same_named_static_and_conditional_functions_are_not_merged(self):
        normalizers = self.project.functions_by_name["Normalize"]
        self.assertEqual(len(normalizers), 24)
        self.assertEqual(len({function.id for function in normalizers}), 24)
        diagnostics = self.project.functions_by_name["Brake_000_Diagnostic"]
        self.assertEqual(len(diagnostics), 2)
        self.assertNotEqual(diagnostics[0].id, diagnostics[1].id)
        workbench = Workbench()
        workbench.project = self.project
        function = self.project.functions_by_name["Brake_000_Decode"][0]
        branch = next(b for r in self.project.results for b in r.branches if b.function_id == function.id)
        workbench.start(function.id, branch.id, "정규화 후보 조사")
        candidates = [c for c in workbench.candidates() if c.label == "Normalize"]
        self.assertEqual(len(candidates), 24)
        self.assertTrue(all("multiple_function_candidates" in c.uncertainty for c in candidates))

    def test_rte_multiple_producers_and_macro_evidence_remain_uncertain(self):
        rte = self.project.rte
        self.assertEqual(len(rte.accesses), 172)
        self.assertEqual(len(rte.dependencies), 52)
        self.assertEqual(sum(d.code == "MULTIPLE_PRODUCER_CANDIDATES" for d in rte.diagnostics), 4)
        self.assertEqual(sum("header_macro_not_expanded" in a.uncertainty for a in rte.accesses), 12)
        self.assertTrue(all(a.header_locations for a in rte.accesses))
        self.assertTrue(all("name_only_connection" in d.uncertainty for d in rte.dependencies))
        self.assertFalse(any(d.code == "NO_PRODUCER_CANDIDATE" for d in rte.diagnostics))

    def test_scope_expansion_six_call_investigation_and_database_restore(self):
        workbench = Workbench()
        scope = ("swc/Brake_000", "shared")
        workbench.project = analyze_project(SAMPLE, include_paths=scope, exclude_paths=("swc/Brake_000/Producer.c",))
        self.assertEqual(workbench.project.rte.dependencies, ())
        function = workbench.project.functions_by_name["Brake_000_10ms"][0]
        target = next(b for r in workbench.project.results for b in r.branches
                      if b.function_id == function.id and b.condition == "(mode == MODE_ACTIVE)")
        workbench.start(function.id, target.id, "확장 샘플의 목표 유지")
        for suffix in ("Evaluate", "Decide", "Eligible", "Validated", "Decode", "Read"):
            candidate = next(c for c in workbench.candidates() if c.function and c.function.name == f"Brake_000_{suffix}")
            workbench.follow(candidate, f"{suffix} 입력 조건 조사")
        before = workbench.session
        workbench.project = analyze_project(SAMPLE, include_paths=scope)
        self.assertEqual(workbench.session, before)
        candidates = [c for c in workbench.candidates() if c.relation == "rte_data"]
        self.assertEqual(len(candidates), 2)
        workbench.follow(next(c for c in candidates if c.function.name == "Brake_000_Producer"), "원시 신호 공급자 후보 조사")
        self.assertEqual(len(workbench.manager.current_path), 8)
        build = ROOT / "build"
        build.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=build) as directory:
            database = Path(directory) / "large.sqlite3"
            workbench.save(database)
            with TraceStore(database) as store:
                restored = TraceManager(store.load(workbench.session.id).session)
                self.assertEqual(restored.session, workbench.session)
                self.assertEqual(restored.session.target_branch, target)
                self.assertIn("multiple_producer_candidates", restored.current_step.uncertainty)

    def test_search_paginates_real_multi_file_functions(self):
        pages = [self.project.search_functions(".c", offset=offset) for offset in (0, 100, 400)]
        self.assertEqual([page.total for page in pages], [424, 424, 424])
        self.assertEqual([len(page.functions) for page in pages], [100, 100, 24])
        self.assertFalse({f.id for f in pages[0].functions} & {f.id for f in pages[1].functions})
        self.assertEqual(self.project.search_functions("brake_000 signal.c").total, 4)

    def test_generator_reproduces_content_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            destination = Path(directory) / "generated"
            manifest = self.generator.generate(destination)
            self.assertEqual(manifest, self.manifest)
            expected = {path.relative_to(SAMPLE) for path in SAMPLE.rglob("*") if path.is_file()}
            actual = {path.relative_to(destination) for path in destination.rglob("*") if path.is_file()}
            self.assertEqual(actual, expected)
            for relative in expected:
                self.assertEqual((destination / relative).read_text(encoding="utf-8"),
                                 (SAMPLE / relative).read_text(encoding="utf-8"), str(relative))
            with self.assertRaises(FileExistsError):
                self.generator.generate(SAMPLE)
            invalid = Path(directory) / "invalid"
            with self.assertRaises(ValueError):
                self.generator.generate(invalid, 0)
            self.assertFalse(invalid.exists())

    def test_80_swc_variant_exceeds_full_scope_budget_but_selected_swc_works(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as directory:
            destination = Path(directory) / "80-swc"
            manifest = self.generator.generate(destination, 80)
            self.assertEqual(manifest["c_files"] + manifest["h_files"], 563)
            with patch("autosar_trace_navigator.workbench.parse_source") as parse:
                with self.assertRaises(AnalysisLimitError):
                    analyze_project(destination)
                parse.assert_not_called()
            project = analyze_project(destination, include_paths=("swc/Brake_000", "shared"))
            self.assertEqual(len(project.sources), 8)
            self.assertTrue(project.search_functions("brake_000_10ms").functions)

    def test_compile_and_run_192_behavior_scenarios(self):
        output = run_c99(sorted(SAMPLE.rglob("*.c")))
        self.assertIn("PASS large AUTOSAR: 192 scenarios", output)
        print("\n" + output, end="")


if __name__ == "__main__":
    unittest.main()
