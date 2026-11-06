"""SQLite recovery, concurrency and failure tests using only temporary databases."""

from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from autosar_trace_navigator.storage import APPLICATION_ID, TraceConflictError, TraceStore
from autosar_trace_navigator.trace import TraceManager
from test_trace import sample_manager


ROOT = Path(__file__).resolve().parents[1]


class StorageTests(unittest.TestCase):
    def setUp(self):
        build = ROOT / "build"
        build.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(prefix="trace-db-", dir=build)
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "sessions.sqlite3"
        self.manager, self.functions = sample_manager()

    def test_reopen_restores_goal_cursor_alternatives_and_unicode(self):
        manager = self.manager
        first = manager.follow(self.functions["EvaluateBrakeMode"], reason="mode='ASSIST'; 조사")
        manager.back()
        manager.follow(self.functions["SensorAcquisition_10ms"], reason="RTE 공급자 조사",
                       relation="rte_data", evidence=self.functions["ReadRawSpeed"].body_location,
                       uncertainty=("unresolved_rte_mapping",))
        manager.select(first.id)
        with TraceStore(self.path) as store:
            self.assertEqual(store.save(manager.session), 1)
            self.assertEqual(store.list_sessions(), (manager.session.id,))
        with TraceStore(self.path) as store:
            saved = store.load(manager.session.id)
            self.assertEqual(saved.session, manager.session)
            restored = TraceManager(saved.session)
            self.assertEqual(restored.current_path, manager.current_path)
            self.assertEqual(len(restored.session.steps), 3)
            restored.back()
            revision = store.save(restored.session, expected_revision=saved.revision)
            self.assertEqual(revision, 2)
            self.assertEqual(store.load(manager.session.id).session, restored.session)

    def test_two_connections_reject_stale_updates_and_duplicate_inserts(self):
        with TraceStore(self.path) as first, TraceStore(self.path) as second:
            session = self.manager.session
            first.save(session)
            stale = second.load(session.id)
            self.manager.follow(self.functions["DecodeSpeed"], reason="새 조사")
            self.assertEqual(first.save(self.manager.session, expected_revision=1), 2)
            with self.assertRaises(TraceConflictError):
                second.save(stale.session, expected_revision=stale.revision)
            with self.assertRaises(TraceConflictError):
                second.save(stale.session)
            self.assertEqual(first.load(session.id).session, self.manager.session)

    def test_missing_sessions_and_invalid_revisions(self):
        with TraceStore(":memory:") as store:
            self.assertEqual(store.list_sessions(), ())
            with self.assertRaises(KeyError):
                store.load("missing")
            with self.assertRaises(TraceConflictError):
                store.save(self.manager.session, expected_revision=1)
            for revision in (0, -1, True):
                with self.assertRaises(ValueError):
                    store.save(self.manager.session, expected_revision=revision)
            with self.assertRaises(ValueError):
                store.save(replace(self.manager.session, current_step_id="missing"))
            self.assertEqual(store.list_sessions(), ())

    def test_source_file_cannot_be_a_database(self):
        path = ROOT / "test/src/BrakeControl.c"
        before = path.read_bytes()
        with self.assertRaises(ValueError):
            TraceStore(path)
        self.assertEqual(path.read_bytes(), before)

    def test_view_only_database_is_not_treated_as_empty(self):
        connection = sqlite3.connect(self.path)
        try:
            connection.execute("CREATE VIEW unrelated AS SELECT 1")
            connection.commit()
        finally:
            connection.close()
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            TraceStore(self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_unrelated_and_future_schema_refused_without_initialization(self):
        connection = sqlite3.connect(self.path)
        try:
            connection.execute("CREATE TABLE unrelated (value TEXT)")
            connection.commit()
        finally:
            connection.close()
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            TraceStore(self.path)
        self.assertEqual(self.path.read_bytes(), before)
        future = self.path.with_name("future.db")
        connection = sqlite3.connect(future)
        try:
            connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
            connection.execute("PRAGMA user_version = 99")
        finally:
            connection.close()
        with self.assertRaises(ValueError):
            TraceStore(future)

    def test_corrupt_snapshot_is_not_loaded_as_a_valid_session(self):
        with TraceStore(self.path) as store:
            store.save(self.manager.session)
            connection = sqlite3.connect(self.path)
            try:
                payload = connection.execute("SELECT payload FROM trace_sessions").fetchone()[0]
                for field in ("current_step_id", "id", "target_branch"):
                    data = json.loads(payload)
                    if field == "target_branch":
                        data[field]["location"]["start_byte"] = 999999
                    else:
                        data[field] = "missing"
                    connection.execute("UPDATE trace_sessions SET payload=?", (json.dumps(data),))
                    connection.commit()
                    with self.subTest(field=field), self.assertRaises(ValueError):
                        store.load(self.manager.session.id)
            finally:
                connection.close()

    def test_failed_update_rolls_back_and_other_sessions_are_preserved(self):
        with TraceStore(self.path) as store:
            original = self.manager.session
            other, _ = sample_manager()
            store.save(original)
            store.save(other.session)
            connection = sqlite3.connect(self.path)
            try:
                connection.execute("CREATE TRIGGER fail_update BEFORE UPDATE ON trace_sessions "
                                   "BEGIN SELECT RAISE(ABORT, 'simulated write failure'); END")
                connection.commit()
            finally:
                connection.close()
            self.manager.follow(self.functions["DecodeSpeed"], reason="저장 실패 시나리오")
            with self.assertRaises(sqlite3.IntegrityError):
                store.save(self.manager.session, expected_revision=1)
            self.assertEqual(store.load(original.id).session, original)
            self.assertEqual(store.load(other.session.id).session, other.session)


if __name__ == "__main__":
    unittest.main()
