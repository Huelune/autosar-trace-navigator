"""The installer's screen output must not carry paths or raw error text."""

from pathlib import Path
import importlib.util
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("install", ROOT / "scripts" / "install.py")
install = importlib.util.module_from_spec(spec)
spec.loader.exec_module(install)


class InstallTests(unittest.TestCase):
    def test_failure_shows_advice_only_and_skips_the_rest(self):
        ran, logged = [], []

        def fail():
            raise OSError("C:/Users/secret_account/secret_file.txt not found")

        lines, ok = install.run_steps([
            ("첫 단계", "할 일 1", lambda: ran.append(1)),
            ("둘째 단계", "할 일 2", fail),
            ("셋째 단계", "할 일 3", lambda: ran.append(3)),
        ], logged.append)
        self.assertEqual((ok, ran), (False, [1]))
        self.assertEqual(lines, ["  완료    첫 단계", "  실패    둘째 단계 -> 할 일 2", "  건너뜀  셋째 단계"])
        self.assertNotIn("secret", "\n".join(lines))
        self.assertIn("secret_account", logged[0])  # the detail is kept, but only in the log

    def test_all_steps_done(self):
        lines, ok = install.run_steps([("가", "", lambda: None), ("나", "", lambda: None)], lambda text: None)
        self.assertEqual((ok, lines), (True, ["  완료    가", "  완료    나"]))

    def test_settings_lines_are_valid_json_with_backslashes_and_korean(self):
        python = Path(r"C:\Users\가상 계정\repo\.venv\Scripts\python.exe")
        settings = json.loads("{" + install.settings_text(python) + "}")
        self.assertEqual(settings, {"branchInvestigation.pythonPath": str(python),
                                    "branchInvestigation.analysisPaths": ["."]})


if __name__ == "__main__":
    unittest.main()
