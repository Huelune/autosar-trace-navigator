"""Analysis configuration and diagnostics on an isolated 602-file synthetic project."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from autosar_trace_navigator import bridge

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("scale_fixture", ROOT / "test/scale_scope/generate.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class BridgeLimitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = fixture.generate_project(Path(self.temp.name) / "project")
        self.request = {"root": str(self.root.resolve()), "file": "app/Consumer.c", "line": 4,
                        "includePaths": ["."]}

    def test_over_500_fails_before_parse_then_explicit_budget_resolves_supplier(self) -> None:
        before = {p: p.read_bytes() for p in self.root.rglob("*.c")}
        with patch("autosar_trace_navigator.workbench.parse_source") as parse:
            with self.assertRaises(bridge.BridgeError) as raised:
                bridge.related(self.request)
            self.assertEqual(raised.exception.limit_details, {"metric": "files", "observedAtLeast": 602, "limit": 500})
            parse.assert_not_called()
        result = bridge.related({**self.request, "limits": {"maxFiles": 650}})
        supplier = next(c for c in result["candidates"] if c["label"] == "Supply")
        self.assertEqual(supplier["target"]["path"], "supplier/Producer.c")
        self.assertIn("name_only_call_candidate", supplier["uncertainty"])
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_exclusions_reduce_work_and_excluded_supplier_is_still_unresolved(self) -> None:
        scoped = {**self.request, "excludePaths": ["noise"], "limits": {"maxFiles": 2}}
        result = bridge.related(scoped)
        self.assertTrue(any(c["functionName"] == "Supply" for c in result["candidates"]))
        missing = bridge.related({**scoped, "excludePaths": ["noise", "supplier"]})["candidates"][0]
        self.assertIsNone(missing["target"])
        self.assertIn("not_resolved_in_analysis_scope", missing["uncertainty"])
        with self.assertRaises(bridge.BridgeError) as outside:
            bridge.related({**scoped, "excludePaths": ["../outside"]})
        self.assertEqual(outside.exception.args, ("scope_not_readable",))

    def test_invalid_configuration_is_rejected_before_analysis(self) -> None:
        for options in ({"limits": {"maxFiles": value}} for value in (True, 0, -1, 10001, 1.5, "700")):
            with self.subTest(options=options), patch.object(bridge, "analyze_project") as analyze:
                with self.assertRaises(bridge.BridgeError) as raised:
                    bridge.related({**self.request, **options})
                self.assertEqual(raised.exception.args, ("invalid_request",))
                analyze.assert_not_called()
        for options in ({"limits": {"unknown": 1}}, {"limits": None}, {"excludePaths": "noise"}, {"excludePaths": [""]}):
            with self.subTest(options=options), self.assertRaises(bridge.BridgeError):
                bridge.related({**self.request, **options})

    def test_file_and_total_byte_limits_have_distinct_path_free_diagnostics(self) -> None:
        for limits, metric in (({"maxFileBytes": 16}, "file_bytes"),
                               ({"maxSourceBytes": 160, "maxFileBytes": 1024}, "source_bytes")):
            with self.subTest(metric=metric), patch("autosar_trace_navigator.workbench.parse_source") as parse:
                with self.assertRaises(bridge.BridgeError) as raised:
                    bridge.related({**self.request, "excludePaths": ["noise"], "limits": limits})
                detail = raised.exception.limit_details
                self.assertEqual(detail["metric"], metric)
                self.assertGreater(detail["observedAtLeast"], detail["limit"])
                self.assertNotIn(str(self.root), json.dumps(detail))
                parse.assert_not_called()

    def test_real_process_returns_diagnostics_without_partial_candidates(self) -> None:
        result = subprocess.run([sys.executable, "-I", "-m", "autosar_trace_navigator.bridge"],
                                input=json.dumps(self.request).encode(), capture_output=True, timeout=60)
        self.assertEqual((result.returncode, result.stderr), (0, b""))
        response = json.loads(result.stdout)
        self.assertEqual(set(response), {"ok", "error", "limitDetails"})
        self.assertEqual(response["limitDetails"]["observedAtLeast"], 602)
        self.assertNotIn(str(self.root), result.stdout.decode())

    def test_generator_refuses_existing_output(self) -> None:
        original = (self.root / "app/Consumer.c").read_bytes()
        with self.assertRaises(FileExistsError):
            fixture.generate_project(self.root)
        self.assertEqual((self.root / "app/Consumer.c").read_bytes(), original)

    def test_function_search_obeys_the_same_budget_and_exclusions(self) -> None:
        request = {"op": "functions", "root": str(self.root.resolve()), "includePaths": ["."]}
        with self.assertRaises(bridge.BridgeError) as raised:
            bridge.functions(request)
        self.assertEqual(raised.exception.limit_details["metric"], "files")
        result = bridge.functions({**request, "excludePaths": ["noise"], "limits": {"maxFiles": 2}})
        self.assertEqual({f["name"] for f in result["functions"]}, {"Consumer", "Supply"})
        invalid = {**request, "limits": {"maxFiles": True}}
        with patch.object(bridge, "analyze_project") as analyze, self.assertRaises(bridge.BridgeError) as bad:
            bridge.functions(invalid)
        self.assertEqual(bad.exception.args, ("invalid_request",))
        analyze.assert_not_called()

    def test_scope_check_counts_before_any_analysis_and_leaves_sources_untouched(self) -> None:
        request = {"op": "scope", "root": str(self.root.resolve()), "includePaths": ["."]}
        before = {path: (path.stat().st_mtime_ns, path.read_bytes()) for path in self.root.rglob("*.c")}
        sizes = [len(data) for _, data in before.values()]
        with patch.object(bridge, "analyze_project") as analyze:
            found = bridge.scope(request)
        analyze.assert_not_called()
        self.assertEqual((found["files"], found["sourceBytes"], found["largestFileBytes"]), (602, sum(sizes), max(sizes)))
        self.assertEqual(found["limits"], {"maxFiles": 500, "maxSourceBytes": 32 * 1024 * 1024, "maxFileBytes": 4 * 1024 * 1024})
        self.assertEqual((found["over"], found["filesOverFileLimit"], found["foldersTruncated"]), (["files"], 0, False))
        self.assertEqual(found["folders"][0]["path"], "noise")
        self.assertEqual(found["folders"][0]["files"], 600)
        self.assertEqual({item["path"] for item in found["folders"]}, {"noise", "app", "supplier"})
        self.assertNotIn(str(self.root.resolve()), json.dumps(found))
        self.assertEqual({path: (path.stat().st_mtime_ns, path.read_bytes()) for path in self.root.rglob("*.c")}, before)
        # The check obeys the same exclusions and budgets as the analysis it predicts.
        scoped = bridge.scope({**request, "excludePaths": ["noise"], "limits": {"maxFiles": 2, "maxFileBytes": 16}})
        self.assertEqual((scoped["files"], scoped["over"], scoped["filesOverFileLimit"]), (2, ["file_bytes"], 2))
        self.assertEqual(bridge.scope({**request, "limits": {"maxFiles": 650}})["over"], [])
        for bad, code in (({**request, "limits": {"maxFiles": 0}}, "invalid_request"), ({**request, "root": "relative"}, "invalid_request"),
                          ({**request, "includePaths": ["../secret"]}, "scope_not_readable"), ([], "invalid_request")):
            with self.subTest(code=code), self.assertRaises(bridge.BridgeError) as raised:
                bridge.scope(bad)
            self.assertEqual(raised.exception.args, (code,))
        done = subprocess.run([sys.executable, "-I", "-m", "autosar_trace_navigator.bridge"], input=json.dumps(request).encode(),
                              capture_output=True, timeout=120)
        self.assertEqual((done.returncode, done.stderr), (0, b""))
        self.assertEqual(json.loads(done.stdout)["files"], 602)

