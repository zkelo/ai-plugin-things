"""Portable Agent Plugins package metadata checks."""

import json
import re
import unittest
from pathlib import Path
from typing import Any, Dict, Iterable


ROOT = Path(__file__).resolve().parents[1]
PORTABLE_PLUGIN_PATH = ROOT / "plugin.json"
LEGACY_PLUGIN_PATH = ROOT / ".codex-plugin" / "plugin.json"
PORTABLE_MCP_PATH = ROOT / "mcp.json"
LEGACY_MCP_PATH = ROOT / ".mcp.json"


def load_json(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise TypeError("Package metadata must be a JSON object")
    return value


def nested_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from nested_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from nested_strings(item)


class PortablePackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.portable_plugin = load_json(PORTABLE_PLUGIN_PATH)
        self.legacy_plugin = load_json(LEGACY_PLUGIN_PATH)
        self.portable_mcp = load_json(PORTABLE_MCP_PATH)
        self.legacy_mcp = load_json(LEGACY_MCP_PATH)

    def test_portable_manifest_declares_schema_and_required_identity(self) -> None:
        self.assertEqual(
            self.portable_plugin["$schema"],
            "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        )
        self.assertRegex(self.portable_plugin["name"], r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        for field in ("name", "version", "description"):
            self.assertIsInstance(self.portable_plugin[field], str)
            self.assertTrue(self.portable_plugin[field].strip())

    def test_portable_and_legacy_plugin_metadata_stay_in_sync(self) -> None:
        for field in ("name", "version", "description", "author"):
            self.assertEqual(
                self.portable_plugin[field],
                self.legacy_plugin[field],
                msg=f"Portable and legacy {field} differ",
            )
        self.assertEqual(
            self.portable_plugin["extensions"]["com.openai"]["interface"],
            self.legacy_plugin["interface"],
        )

    def test_install_surface_metadata_is_english(self) -> None:
        metadata = {
            "description": self.portable_plugin["description"],
            "interface": self.portable_plugin["extensions"]["com.openai"][
                "interface"
            ],
        }
        for value in nested_strings(metadata):
            with self.subTest(value=value):
                self.assertIsNone(re.search(r"[\u0400-\u04ff]", value))

    def test_install_surface_metadata_respects_submission_limits(self) -> None:
        interface = self.portable_plugin["extensions"]["com.openai"]["interface"]
        self.assertLessEqual(len(interface["displayName"]), 30)
        self.assertLessEqual(len(interface["shortDescription"]), 30)
        self.assertLessEqual(len(interface["longDescription"]), 4_000)
        self.assertLessEqual(len(interface["developerName"]), 80)
        prompts = interface["defaultPrompt"]
        self.assertLessEqual(len(prompts), 3)
        self.assertTrue(prompts)
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                self.assertLessEqual(len(prompt), 128)

    def test_interface_asset_paths_are_safe_and_present(self) -> None:
        interface = self.portable_plugin["extensions"]["com.openai"]["interface"]
        paths = [interface[field] for field in ("composerIcon", "logo", "logoDark")]
        paths.extend(interface.get("screenshots", []))
        for configured_path in paths:
            with self.subTest(path=configured_path):
                self.assertTrue(configured_path.startswith("./assets/"))
                relative_path = Path(configured_path.removeprefix("./"))
                self.assertNotIn("..", relative_path.parts)
                resolved_path = (ROOT / relative_path).resolve()
                self.assertTrue(resolved_path.is_relative_to(ROOT.resolve()))
                self.assertTrue(resolved_path.is_file())

    def test_portable_mcp_declares_schema_and_matches_legacy_servers(self) -> None:
        self.assertEqual(
            self.portable_mcp["$schema"],
            "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
        )
        portable_servers = self.portable_mcp["mcpServers"]
        legacy_servers = self.legacy_mcp["mcpServers"]
        self.assertEqual(portable_servers.keys(), legacy_servers.keys())
        portable_server = portable_servers["things"]
        legacy_server = legacy_servers["things"]
        self.assertEqual(portable_server["type"], "stdio")
        self.assertEqual(portable_server["type"], legacy_server["type"])
        self.assertEqual(portable_server["command"], legacy_server["command"])
        self.assertEqual(
            [
                argument.replace("${PLUGIN_ROOT}", "${CLAUDE_PLUGIN_ROOT}")
                for argument in portable_server["args"]
            ],
            legacy_server["args"],
        )


if __name__ == "__main__":
    unittest.main()
