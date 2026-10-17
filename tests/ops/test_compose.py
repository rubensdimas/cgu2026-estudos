"""Exercise the Compose CLI without starting services or using personal secrets."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def render_compose(
    env_file_values: dict[str, str],
    shell_overrides: dict[str, str] | None = None,
) -> dict:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in {"APP_PORT", "POSTGRES_PASSWORD"}
        and not key.startswith("COMPOSE_")
    }
    environment.update(shell_overrides or {})
    with tempfile.TemporaryDirectory() as directory:
        env_file = Path(directory) / ".env"
        env_file.write_text(
            "".join(f"{key}={value}\n" for key, value in env_file_values.items())
        )
        result = subprocess.run(
            [
                "docker", "compose",
                "--project-directory", str(ROOT),
                "--env-file", str(env_file),
                "-f", str(ROOT / "docker-compose.yml"),
                "--profile", "test", "config", "--format", "json",
            ],
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
    return json.loads(result.stdout)


class ComposeConfigurationTests(unittest.TestCase):
    def test_empty_shell_port_overrides_root_env(self):
        config = render_compose(
            {"POSTGRES_PASSWORD": "fixture-password", "APP_PORT": "18082"},
            {"APP_PORT": ""},
        )
        self.assertEqual(config["services"]["app"]["ports"][0]["published"], "8082")

    def test_shell_port_overrides_root_env(self):
        config = render_compose(
            {"POSTGRES_PASSWORD": "fixture-password", "APP_PORT": "18082"},
            {"APP_PORT": "18083"},
        )
        self.assertEqual(config["services"]["app"]["ports"][0]["published"], "18083")

    def test_empty_file_port_uses_default(self):
        config = render_compose(
            {"POSTGRES_PASSWORD": "fixture-password", "APP_PORT": ""},
        )
        self.assertEqual(config["services"]["app"]["ports"][0]["published"], "8082")

    def test_app_port_from_root_env(self):
        config = render_compose({
            "POSTGRES_PASSWORD": "fixture-password", "APP_PORT": "18082",
        })
        port = config["services"]["app"]["ports"][0]
        self.assertEqual(port["published"], "18082")
        self.assertEqual(port["host_ip"], "127.0.0.1")
        self.assertEqual(port["target"], 8000)

    def test_default_app_port_and_database_isolation(self):
        config = render_compose({"POSTGRES_PASSWORD": "fixture-password"})
        services = config["services"]
        port = services["app"]["ports"][0]
        self.assertEqual(port["host_ip"], "127.0.0.1")
        self.assertEqual(port["published"], "8082")
        self.assertEqual(port["target"], 8000)
        self.assertFalse(services["db"].get("ports"))
        self.assertEqual(config["name"], "cgu2026")
        self.assertEqual(config["volumes"]["pgdata"]["name"], "cgu2026_pgdata")
        self.assertEqual(config["networks"]["default"]["name"], "cgu2026_default")
        self.assertTrue(
            services["app"]["environment"]["DATABASE_URL"].endswith("@db:5432/cgu")
        )
        self.assertTrue(
            services["test"]["environment"]["DATABASE_URL"].endswith("@db:5432/cgu_test")
        )
        self.assertEqual(services["backup"]["environment"]["PGHOST"], "db")
        self.assertTrue(any(
            mount["type"] == "volume"
            and mount["source"] == "pgdata"
            and mount["target"] == "/var/lib/postgresql/data"
            for mount in services["db"]["volumes"]
        ))
