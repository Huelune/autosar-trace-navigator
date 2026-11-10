"""Repository collaboration records use temporary files, not real task history."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts.worklog import create_session, create_task, list_tasks

REPO = Path(__file__).resolve().parents[1]


class WorklogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        shutil.copytree(REPO / "docs/work/templates", self.root / "docs/work/templates")

    def test_task_preserves_title_and_refuses_overwrite(self) -> None:
        task = create_task(self.root, "TASK-010", "RTE $값 출처 조사")
        original = task.read_bytes()
        self.assertIn("RTE $값 출처 조사", original.decode())
        self.assertIn("상태: planned", original.decode())
        with self.assertRaises(FileExistsError):
            create_task(self.root, "TASK-010", "덮어쓰기 시도")
        self.assertEqual(original, task.read_bytes())

    def test_two_tools_create_distinct_sessions_without_changing_card(self) -> None:
        task = create_task(self.root, "TASK-010", "인수인계")
        original = task.read_bytes()
        first = create_session(self.root, "TASK-010", "codex", "dev-a")
        second = create_session(self.root, "TASK-010", "claude", "dev-b")
        self.assertNotEqual(first, second)
        self.assertEqual(task.read_bytes(), original)
        for session in (first, second):
            text = session.read_text(encoding="utf-8")
            self.assertIn("../tasks/TASK-010.md", text)
            self.assertIn("+00:00", text)
            self.assertNotIn("$base_commit", text)

    def test_invalid_paths_or_multiline_titles_do_not_create_records(self) -> None:
        for task_id in ("../TASK-010", "TASK-010/other", "task-010", "TASK-1"):
            with self.assertRaises(ValueError):
                create_task(self.root, task_id, "제목")
        for title in ("", "\n", "두\n줄", "tab\tline"):
            with self.assertRaises(ValueError):
                create_task(self.root, "TASK-010", title)
        self.assertFalse((self.root / "docs/work/tasks").exists())

    def test_missing_task_and_invalid_actor_do_not_create_sessions(self) -> None:
        with self.assertRaises(ValueError):
            create_session(self.root, "TASK-010", "codex", "dev-a")
        create_task(self.root, "TASK-010", "제목")
        for tool, actor in (("unknown", "dev-a"), ("claude", "../person"), ("codex", "a\nb")):
            with self.assertRaises(ValueError):
                create_session(self.root, "TASK-010", tool, actor)
        self.assertFalse((self.root / "docs/work/sessions").exists())

    def test_list_is_sorted_and_read_only(self) -> None:
        create_task(self.root, "TASK-020", "둘")
        create_task(self.root, "TASK-010", "하나")
        before = {p: p.read_bytes() for p in self.root.rglob("*.md")}
        self.assertEqual([p.stem for p in list_tasks(self.root)], ["TASK-010", "TASK-020"])
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*.md")})

    def test_cli_uses_its_checkout_from_another_directory(self) -> None:
        scripts = self.root / "scripts"
        scripts.mkdir()
        shutil.copy2(REPO / "scripts/worklog.py", scripts / "worklog.py")
        for args in (["new", "TASK-010", "--title", "CLI task"],
                     ["start", "TASK-010", "--tool", "claude", "--actor", "dev-b"], ["list"]):
            result = subprocess.run([sys.executable, str(scripts / "worklog.py"), *args],
                                    cwd=REPO, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("docs/work/", result.stdout)
        self.assertTrue((self.root / "docs/work/tasks/TASK-010.md").is_file())
        self.assertEqual(len(list((self.root / "docs/work/sessions").glob("*.md"))), 1)


if __name__ == "__main__":
    unittest.main()
