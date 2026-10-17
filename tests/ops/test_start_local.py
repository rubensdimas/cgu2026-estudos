"""Test the public local-start command with a recording Docker CLI boundary."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/start-local.sh"


class StartLocalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cgu-start-local-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.backups = self.directory / "backups"
        self.backups.mkdir()
        self.log = self.directory / "docker.jsonl"
        fake_docker = self.directory / "docker"
        fake_docker.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            "args = sys.argv[1:]\n"
            "with open(os.environ['CGU_DOCKER_LOG'], 'a') as log:\n"
            " json.dump({'args': args, 'cwd': os.getcwd()}, log); log.write('\\n')\n"
            "if args[:4] == ['compose', 'config', '--format', 'json']:\n"
            " print(json.dumps({'services': {'backup': {'volumes': "
            "[{'type': 'bind', 'source': os.environ['CGU_BACKUP_DIR'], "
            "'target': '/backups'}]}}}))\n"
            "elif 'psql' in args:\n"
            " print(os.environ.get('CGU_DATABASE_NONEMPTY', 'f'))\n"
            "elif 'pg_restore' in args:\n"
            " with open(os.environ['CGU_RESTORED_INPUT'], 'w') as dst: "
            "dst.write(sys.stdin.read())\n"
        )
        fake_docker.chmod(0o755)
        self.environment = os.environ.copy()
        self.environment["PATH"] = f"{self.directory}{os.pathsep}{self.environment['PATH']}"
        self.environment["CGU_DOCKER_LOG"] = str(self.log)
        self.environment["CGU_BACKUP_DIR"] = str(self.backups)
        self.environment["CGU_RESTORED_INPUT"] = str(self.directory / "restored.dump")
        self.environment["CGU_DATABASE_NONEMPTY"] = "f"

    def run_script(self, *args):
        try:
            return subprocess.run(
                [str(SCRIPT), *args], cwd=self.directory, env=self.environment,
                capture_output=True, text=True, timeout=10,
            )
        except FileNotFoundError:
            self.fail(f"public command does not exist: {SCRIPT}")

    def docker_calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_starts_the_project_without_restoring_by_default(self):
        result = self.run_script()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            ["compose", "up", "-d", "--build"],
            [call["args"] for call in self.docker_calls()],
        )
        self.assertTrue(all(call["cwd"] == str(ROOT) for call in self.docker_calls()))
        self.assertFalse((self.directory / "restored.dump").exists())

    def test_restore_reports_missing_backup_before_starting_services(self):
        result = self.run_script("--restore")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nenhum backup", result.stderr.lower())
        self.assertNotIn(
            "up", [arg for call in self.docker_calls() for arg in call["args"]],
        )

    def test_restore_uses_latest_dump_before_starting_the_app(self):
        older = self.backups / "cgu-20261016-120000.dump"
        latest = self.backups / "cgu-20261017-120000.dump"
        unrelated = self.backups / "other-20261018.dump"
        older.write_text("older archive")
        latest.write_text("latest archive")
        unrelated.write_text("not a CGU backup")

        result = self.run_script("--restore")

        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [call["args"] for call in self.docker_calls()]
        db_command = ["compose", "up", "-d", "--wait", "db"]
        app_command = ["compose", "up", "-d", "--build"]
        self.assertIn(db_command, calls)
        self.assertTrue(any("pg_restore" in call for call in calls))
        self.assertIn(app_command, calls)
        db_start = calls.index(db_command)
        restore = next(i for i, call in enumerate(calls) if "pg_restore" in call)
        app_start = calls.index(app_command)
        self.assertLess(db_start, restore)
        self.assertLess(restore, app_start)
        self.assertEqual((self.directory / "restored.dump").read_text(), "latest archive")

    def test_restore_refuses_a_nonempty_database(self):
        (self.backups / "cgu-20261017-120000.dump").write_text("archive")
        self.environment["CGU_DATABASE_NONEMPTY"] = "t"

        result = self.run_script("--restore")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("preservar os dados", result.stderr)
        calls = [call["args"] for call in self.docker_calls()]
        self.assertFalse(any("pg_restore" in call for call in calls))
        self.assertNotIn(["compose", "up", "-d", "--build"], calls)
