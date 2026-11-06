"""Producer investigation through parser, RTE candidates, trace state and SQLite."""

import hashlib
from pathlib import Path
import tempfile
import unittest

from autosar_trace_navigator.parser import parse_file
from autosar_trace_navigator.rte import parse_rte_header, resolve_rte
from autosar_trace_navigator.scanner import scan_sources
from autosar_trace_navigator.storage import TraceStore
from autosar_trace_navigator.trace import TraceManager


ROOT = Path(__file__).resolve().parents[1]


class RtePipelineTests(unittest.TestCase):
    def setUp(self):
        self.sources = scan_sources(ROOT / "test", include_paths=("include", "src", "support"))
        self.before = {s.path: (hashlib.sha256(s.path.read_bytes()).digest(), s.path.stat().st_mtime_ns)
                       for s in self.sources}
        self.results = tuple(parse_file(s.path) for s in self.sources)
        headers = tuple(parse_rte_header(s.path) for s in self.sources if s.is_rte_header)
        self.rte = resolve_rte(self.results, headers=headers)
        self.functions = {f.id: f for result in self.results for f in result.functions}

    def test_sample_has_two_separate_data_candidates_and_no_invented_call_edge(self):
        self.assertEqual(len(self.rte.accesses), 7)
        self.assertEqual(len(self.rte.dependencies), 2)
        self.assertEqual({d.channel for d in self.rte.dependencies}, {"Speed_Raw", "Pedal_Percent"})
        self.assertEqual(self.rte.diagnostics, ())
        by_id = {access.id: access for access in self.rte.accesses}
        for dependency in self.rte.dependencies:
            read = by_id[dependency.consumer_access_id]
            write = by_id[dependency.producer_access_id]
            self.assertEqual(self.functions[write.function_id].name, "SensorAcquisition_10ms")
            self.assertEqual(read.direction, "read")
            self.assertEqual(write.direction, "write")
            self.assertTrue(read.header_locations and write.header_locations)
            self.assertIn("arxml_not_resolved", dependency.uncertainty)
        self.assertFalse(any(call.callee_name == "SensorAcquisition_10ms"
                             for result in self.results for call in result.calls
                             if call.caller_id is not None and
                             self.functions[call.caller_id].name == "ReadRawSpeed"))
        self.assertEqual(self.before,
                         {s.path: (hashlib.sha256(s.path.read_bytes()).digest(), s.path.stat().st_mtime_ns)
                          for s in self.sources})

    def test_six_call_steps_then_rte_producer_survive_database_reopen(self):
        by_name = {function.name: function for function in self.functions.values()}
        target = next(branch for result in self.results for branch in result.branches
                      if branch.condition == "(mode == BRAKE_ASSIST)")
        manager = TraceManager.start(by_name["BrakeControl_10ms"], target, reason="ASSIST 목표 분기 조사")
        for name in ("EvaluateBrakeMode", "IsAssistRequested", "IsSpeedEligible",
                     "GetValidatedSpeed", "DecodeSpeed", "ReadRawSpeed"):
            call = next(call for result in self.results for call in result.calls
                        if call.caller_id == manager.current_step.function.id and call.callee_name == name)
            manager.follow(by_name[name], reason=f"{name}의 입력 조건 조사", relation="call",
                           evidence=call.location, uncertainty=call.uncertainty)
        access_by_id = {access.id: access for access in self.rte.accesses}
        read = next(access for access in self.rte.accesses
                    if access.function_id == manager.current_step.function.id and access.direction == "read")
        candidate = next(d for d in self.rte.dependencies if d.consumer_access_id == read.id)
        write = access_by_id[candidate.producer_access_id]
        manager.follow(self.functions[write.function_id], reason=f"{candidate.channel} 공급자 후보 조사",
                       relation="rte_data", evidence=write.location, uncertainty=candidate.uncertainty)
        self.assertEqual(len(manager.current_path), 8)
        self.assertEqual(manager.current_step.function.name, "SensorAcquisition_10ms")
        self.assertEqual(manager.session.target_branch, target)
        self.assertEqual(manager.current_step.evidence.path.name, "SensorAcquisition.c")
        build = ROOT / "build"
        build.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="rte-integration-", dir=build) as directory:
            database = Path(directory) / "trace.sqlite3"
            with TraceStore(database) as store:
                store.save(manager.session)
            with TraceStore(database) as store:
                restored = TraceManager(store.load(manager.session.id).session)
                self.assertEqual(restored.session, manager.session)
                self.assertEqual(restored.current_step.relation, "rte_data")
                self.assertIn("name_only_connection", restored.current_step.uncertainty)
                self.assertEqual(restored.current_step.reason, "Speed_Raw 공급자 후보 조사")
                restored.back()
                self.assertEqual(restored.current_step.function.name, "ReadRawSpeed")
                self.assertEqual(restored.session.target_branch.location.start_line, 10)
        self.assertEqual(self.before,
                         {s.path: (hashlib.sha256(s.path.read_bytes()).digest(), s.path.stat().st_mtime_ns)
                          for s in self.sources})


if __name__ == "__main__":
    unittest.main()
