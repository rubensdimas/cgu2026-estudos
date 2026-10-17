"""Exercise the runtime image against a disposable database at an applied revision.

Build the image first with docker compose build app. No existing database,
volume, network or personal .env is used by this test.
"""

import json
import os
from http.client import RemoteDisconnected
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4


class StartupTests(unittest.TestCase):
    def test_starts_with_already_applied_occurrence_theme_revision(self):
        with tempfile.TemporaryDirectory(prefix="cgu-startup-") as directory:
            config = Path(directory) / "compose.json"
            config.write_text(json.dumps({
                "services": {
                    "db": {
                        "image": "postgres:17.6",
                        "environment": {
                            "POSTGRES_DB": "cgu_startup_test",
                            "POSTGRES_USER": "cgu",
                            "POSTGRES_PASSWORD": "fixture-password",
                        },
                        "tmpfs": ["/var/lib/postgresql/data"],
                        "healthcheck": {
                            "test": ["CMD-SHELL", "pg_isready -U cgu -d cgu_startup_test"],
                            "interval": "1s", "timeout": "3s", "retries": 30,
                        },
                    },
                    "app": {
                        "image": os.environ.get("CGU_STARTUP_IMAGE", "cgu2026-app"),
                        "environment": {
                            "DATABASE_URL": "postgresql+psycopg://cgu:fixture-password@db:5432/cgu_startup_test",
                            "ALLOWED_HOSTS": "127.0.0.1,localhost",
                        },
                        "ports": ["127.0.0.1::8000"],
                        "restart": "no",
                    },
                },
            }))
            environment = {
                key: value for key, value in os.environ.items()
                if not key.startswith("COMPOSE_")
            }
            command = [
                "docker", "compose", "--env-file", os.devnull,
                "--project-directory", directory,
                "--project-name", f"cgu-startup-{uuid4().hex}",
                "-f", str(config),
            ]

            def compose(*args, timeout=60):
                result = subprocess.run(
                    [*command, *args], env=environment, capture_output=True,
                    text=True, timeout=timeout,
                )
                if result.returncode:
                    raise RuntimeError(
                        f"Fixture command {args!r} failed:\n{result.stdout}{result.stderr}"
                    )
                return result.stdout.strip()

            # unittest cleanups run even when fixture preparation or an assertion fails.
            # The directory must still exist when Compose reads its configuration.
            try:
                self.addCleanup(compose, "down", "--remove-orphans", "--timeout", "5")
                compose("up", "-d", "--wait", "--wait-timeout", "30", "db")
                compose(
                    "run", "--rm", "--no-deps", "--entrypoint", "sh", "app", "-c",
                    "alembic upgrade 2a16732b4a43 && python -m app.seed",
                )
                compose(
                    "exec", "-T", "db", "psql", "-U", "cgu", "-d", "cgu_startup_test",
                    "-v", "ON_ERROR_STOP=1", "-c",
                    "ALTER TABLE occurrences ADD COLUMN theme_id varchar(16); "
                    "UPDATE alembic_version SET version_num = '5c9e1f3a7b21';",
                )
                compose("up", "-d", "--no-deps", "app")
                address = compose("port", "app", "8000")
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    state = compose("ps", "-a", "--format", "{{.State}}", "app")
                    if state != "running":
                        self.fail(f"Runtime exited before HTTP was ready:\n{compose('logs', '--no-color', 'app')}")
                    try:
                        with urlopen(f"http://{address}/api/v1/health", timeout=1) as response:
                            self.assertEqual(response.status, 200)
                            self.assertEqual(json.load(response), {"status": "ok"})
                        break
                    except (URLError, TimeoutError, ConnectionError, RemoteDisconnected):
                        time.sleep(0.2)
                else:
                    self.fail(f"Runtime did not become ready:\n{compose('logs', '--no-color', 'app')}")

                with urlopen(f"http://{address}/api/v1/subjects", timeout=5) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(json.load(response)["total"], 13)
            finally:
                self.doCleanups()
