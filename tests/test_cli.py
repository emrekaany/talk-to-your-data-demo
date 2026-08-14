import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        root = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        env["PYTHONPATH"] = str(root / "src")
        return subprocess.run(
            [sys.executable, "-m", "talk_to_your_data_demo", *args],
            cwd=root,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_demo_json(self) -> None:
        completed = self._run("demo", "--json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["plan"]["plan_id"], "monthly_revenue_by_region")
        self.assertEqual(payload["synthetic_source_rows"], 720)

    def test_questions_command(self) -> None:
        completed = self._run("questions")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.count("\n"), 5)

    def test_version(self) -> None:
        completed = self._run("--version")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("0.1.0", completed.stdout)


if __name__ == "__main__":
    unittest.main()
