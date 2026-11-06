"""Versioned SQLite storage for trace snapshots; no parser/source side effects."""

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import sqlite3
from types import TracebackType

from .models import Branch, FunctionDefinition, SourceRange, ValueProbe
from .trace import TraceSession, TraceStep, VariableGoal, validate_session


APPLICATION_ID = 0x41544E56
SCHEMA_VERSION = 1


class TraceConflictError(RuntimeError):
    """The stored revision changed, or an insert would overwrite a session."""


@dataclass(frozen=True)
class StoredTrace:
    session: TraceSession
    revision: int


def _encode_path(value: object) -> str:
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Unsupported snapshot value: {type(value).__name__}")


def _decode(payload: str) -> TraceSession:
    def span(value: dict) -> SourceRange:
        return SourceRange(**{**value, "path": Path(value["path"])})

    def function(value: dict) -> FunctionDefinition:
        return FunctionDefinition(**{
            **value, "location": span(value["location"]),
            "body_location": span(value["body_location"]),
            "uncertainty": tuple(value["uncertainty"]),
        })

    try:
        data = json.loads(payload)
        version = data.pop("format_version", 1)
        if type(version) is not int or version not in {1, 2}:
            raise ValueError("Unsupported trace snapshot format")
        target = data["target_branch"]
        branch = Branch(**{
            **target, "location": span(target["location"]),
            "body_location": span(target["body_location"]),
            "uncertainty": tuple(target["uncertainty"]),
        })
        steps = tuple(TraceStep(**{
            **step, "function": function(step["function"]),
            "evidence": span(step["evidence"]) if step["evidence"] is not None else None,
            "uncertainty": tuple(step["uncertainty"]),
            "selected_location": span(step["selected_location"]) if step.get("selected_location") else None,
            "probe": ValueProbe(**{**step["probe"], "location": span(step["probe"]["location"])})
                     if step.get("probe") else None,
        }) for step in data["steps"])
        goal = data.get("variable_goal")
        session = TraceSession(**{**data, "target_function": function(data["target_function"]),
                                  "target_branch": branch, "steps": steps,
                                  "variable_goal": VariableGoal(**{**goal, "location": span(goal["location"])}) if goal else None})
        validate_session(session)
        return session
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise ValueError("Invalid stored trace snapshot") from error


class TraceStore:
    """Open a dedicated trace DB explicitly; callers should use a with statement."""

    def __init__(self, path: str | os.PathLike[str]):
        name = os.fspath(path)
        if name != ":memory:" and Path(name).suffix.lower() not in {".sqlite3", ".db"}:
            raise ValueError("Trace DB must use .sqlite3 or .db; C/H sources are not storage targets")
        self._connection = sqlite3.connect(name)
        try:
            self._initialize()
        except Exception:
            self._connection.close()
            raise

    def _initialize(self) -> None:
        connection = self._connection
        application_id = connection.execute("PRAGMA application_id").fetchone()[0]
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        objects = set(connection.execute(
            "SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))
        if (application_id == APPLICATION_ID and version == SCHEMA_VERSION
                and ("table", "trace_sessions") in objects):
            return
        if application_id != 0 or version != 0 or objects:
            raise ValueError("Unsupported schema or unrelated database; no migration performed")
        # Explicit transaction also makes DDL and version markers atomic.
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute("CREATE TABLE trace_sessions (id TEXT PRIMARY KEY NOT NULL, "
                               "revision INTEGER NOT NULL CHECK (revision >= 1), payload TEXT NOT NULL)")
            connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "TraceStore":
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None,
                 traceback: TracebackType | None) -> None:
        self.close()

    def save(self, session: TraceSession, *, expected_revision: int | None = None) -> int:
        """Insert when revision is None; otherwise atomically update that exact revision."""
        validate_session(session)
        if expected_revision is not None and (type(expected_revision) is not int or expected_revision < 1):
            raise ValueError("Expected revision must be a positive integer")
        payload = json.dumps({"format_version": 2, **asdict(session)}, default=_encode_path, ensure_ascii=False)
        revision = 1 if expected_revision is None else expected_revision + 1
        with self._connection:
            if expected_revision is None:
                try:
                    self._connection.execute(
                        "INSERT INTO trace_sessions (id, revision, payload) VALUES (?, ?, ?)",
                        (session.id, revision, payload))
                except sqlite3.IntegrityError as error:
                    raise TraceConflictError("Session already exists; load its revision before updating") from error
            else:
                cursor = self._connection.execute(
                    "UPDATE trace_sessions SET revision=?, payload=? WHERE id=? AND revision=?",
                    (revision, payload, session.id, expected_revision))
                if cursor.rowcount != 1:
                    raise TraceConflictError("Stored session revision changed or session does not exist")
        return revision

    def load(self, session_id: str) -> StoredTrace:
        """Restore metadata, history and cursor without opening any referenced source file."""
        row = self._connection.execute(
            "SELECT revision, payload FROM trace_sessions WHERE id=?", (session_id,)).fetchone()
        if row is None:
            raise KeyError(session_id)
        session = _decode(row[1])
        if session.id != session_id or type(row[0]) is not int or row[0] < 1:
            raise ValueError("Invalid stored trace identity or revision")
        return StoredTrace(session, row[0])

    def list_sessions(self) -> tuple[str, ...]:
        """Return saved session IDs in deterministic order."""
        return tuple(row[0] for row in self._connection.execute("SELECT id FROM trace_sessions ORDER BY id"))
