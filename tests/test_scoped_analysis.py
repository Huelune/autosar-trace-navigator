"""Bounded analysis and explicit search, without loading unrelated source content."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from autosar_trace_navigator.scanner import scan_sources
from autosar_trace_navigator.workbench import AnalysisLimitError, Workbench, analyze_project


ROOT = Path(__file__).resolve().parents[1]


class ScopedAnalysisTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "build").mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=ROOT / "build")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()

    def write(self, name: str, content: str = "int f(void) { return 0; }\n") -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_unselected_directories_are_pruned_before_access(self):
        self.write("module/deep/selected.c")
        self.write("unrelated/forbidden.c", "deliberately invalid C")
        scandir = os.scandir
        visited = []
        def guarded(path):
            visited.append(Path(path))
            self.assertNotEqual(Path(path), self.root / "unrelated")
            return scandir(path)
        with patch("autosar_trace_navigator.scanner.os.scandir", side_effect=guarded):
            project = analyze_project(self.root, include_paths=("module/deep/selected.c",))
        self.assertEqual(len(project.sources), 1)
        self.assertEqual(project.scope, (self.root / "module/deep/selected.c",))
        self.assertNotIn(self.root / "unrelated", visited)

    def test_overlapping_scopes_exclusions_and_invalid_paths(self):
        self.write("module/a.c")
        self.write("module/b.h")
        self.write("module2/c.c")
        sources = scan_sources(self.root, include_paths=("module", "module/a.c", "module"), exclude_paths=("module/b.h",))
        self.assertEqual([s.relative_path.as_posix() for s in sources], ["module/a.c"])
        with self.assertRaises(FileNotFoundError):
            scan_sources(self.root, include_paths=("missing",))
        with self.assertRaises(ValueError):
            scan_sources(self.root, include_paths=(self.root.parent,))

    def test_file_count_budget_fails_before_source_read_or_parse(self):
        self.write("a.c")
        self.write("b.c")
        with patch("autosar_trace_navigator.workbench.parse_source") as parse, patch.object(Path, "open") as read:
            with self.assertRaises(AnalysisLimitError):
                analyze_project(self.root, max_files=1)
            parse.assert_not_called()
            read.assert_not_called()

    def test_byte_budgets_and_invalid_limits(self):
        self.write("a.c", "x" * 12)
        self.write("b.c", "y" * 12)
        for limits in ({"max_file_bytes": 11}, {"max_source_bytes": 23}):
            with self.subTest(limits=limits), patch("autosar_trace_navigator.workbench.parse_source") as parse:
                with self.assertRaises(AnalysisLimitError):
                    analyze_project(self.root, **limits)
                parse.assert_not_called()
        project = analyze_project(self.root, max_file_bytes=12, max_source_bytes=24)
        self.assertEqual(len(project.sources), 2)
        with self.assertRaises(ValueError):
            analyze_project(self.root, max_files=0)

    def test_search_pages_bound_rows_and_match_name_and_path(self):
        self.write("module/가상.c", "\n".join(f"int Fn{i:03}(void) {{ return {i}; }}" for i in range(550)))
        project = analyze_project(self.root)
        self.assertEqual(project.search_functions("").total, 0)
        pages = [project.search_functions("FN 가상", offset=offset) for offset in (0, 100, 500)]
        self.assertEqual([len(p.functions) for p in pages], [100, 100, 50])
        self.assertTrue(all(p.total == 550 for p in pages))
        self.assertFalse({f.id for f in pages[0].functions} & {f.id for f in pages[1].functions})
        self.assertEqual(project.search_functions("fn549 module").functions[0].name, "Fn549")
        self.assertIs(project.functions, project.functions)
        self.assertIs(project.functions_by_name, project.functions_by_name)
        for options in ({"offset": -1}, {"limit": 501}):
            with self.assertRaises(ValueError):
                project.search_functions("fn", **options)

    def test_scope_expansion_resolves_missing_candidate_without_replacing_goal(self):
        workbench = Workbench()
        root = ROOT / "test"
        workbench.project = analyze_project(root, include_paths=("src/BrakeControl.c",))
        function = next(f for f in workbench.project.functions if f.name == "BrakeControl_10ms")
        target = next(b for r in workbench.project.results for b in r.branches if b.condition == "(mode == BRAKE_ASSIST)")
        workbench.start(function.id, target.id, "목표 유지")
        workbench.follow(next(c for c in workbench.candidates() if c.function), "mode 조건 확인")
        missing = next(c for c in workbench.candidates() if c.label == "IsAssistRequested")
        self.assertIsNone(missing.function)
        self.assertIn("not_resolved_in_analysis_scope", missing.uncertainty)
        before = workbench.session
        workbench.project = analyze_project(root, include_paths=("src/BrakeControl.c", "src/AssistDecision.c"))
        candidate = next(c for c in workbench.candidates() if c.label == "IsAssistRequested")
        self.assertIsNotNone(candidate.function)
        self.assertEqual(workbench.session, before)
        workbench.follow(candidate, "요청 조건 확인")
        self.assertEqual(workbench.session.target_branch, target)

    def test_rte_missing_producer_only_means_missing_in_selected_scope(self):
        root = ROOT / "test"
        small = analyze_project(root, include_paths=("src/SpeedSignal.c",))
        self.assertEqual(small.rte.dependencies, ())
        self.assertIn("NO_PRODUCER_CANDIDATE", {d.code for d in small.rte.diagnostics})
        expanded = analyze_project(root, include_paths=("src/SpeedSignal.c", "src/SensorAcquisition.c", "include"))
        self.assertEqual(len(expanded.rte.dependencies), 1)
        self.assertEqual(expanded.rte.dependencies[0].channel, "Speed_Raw")


if __name__ == "__main__":
    unittest.main()
