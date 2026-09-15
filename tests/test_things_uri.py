"""Authenticated request behavior and secret-free public results."""

import json
import os
import plistlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, quote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import things_uri
from things_plugin.application import AuthenticationError, AuthToken, TaskOptions
from things_plugin.domain import Task
from things_plugin.infrastructure import macos
from things_plugin.infrastructure.uri import ThingsUriBuilder
from things_plugin.payloads import serialize_error

TEST_TOKEN = "synthetic-secret+&%=value"


def parameters(uri):
    return parse_qs(urlsplit(uri).query, keep_blank_values=True)


def task_attributes(uri):
    return json.loads(parameters(uri)["data"][0])[0]["attributes"]


class UriTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {"THINGS_AUTH_TOKEN": TEST_TOKEN})
        environment.start()
        self.addCleanup(environment.stop)

    def test_authenticated_uri_encodes_secret_once_but_public_uri_omits_it(self):
        title = "Купить 🥛 & кофе + 50% # ? `whoami` $(id)"
        notes = "Строка 1\nhttps://example.com/?a=1&b=2"
        request = ThingsUriBuilder().build_task(
            Task(title, notes=notes), TaskOptions(), AuthToken(TEST_TOKEN)
        )
        self.assertEqual(parameters(request.uri)["auth-token"], [TEST_TOKEN])
        self.assertEqual(task_attributes(request.uri), {"title": title, "notes": notes})
        self.assertEqual(
            task_attributes(request.display_uri), {"title": title, "notes": notes}
        )
        self.assertNotIn("auth-token", parameters(request.display_uri))
        self.assertNotIn(TEST_TOKEN, repr(request))
        self.assertNotIn(quote(TEST_TOKEN, safe=""), repr(request))

    def test_task_fields_and_destination_id_precedence_survive_json_translation(self):
        uri = things_uri.build_task_uri(
            {
                "title": "Release",
                "when": "2026-09-16@10:30",
                "deadline": "2026-09-18",
                "tags": ["Работа, дом", "Urgent"],
                "checklist_items": ["Build", "Docs"],
                "list": "Ignored",
                "list_id": "project-id",
                "heading": "Ignored",
                "heading_id": "heading-id",
                "reveal": True,
            }
        )
        attributes = task_attributes(uri)
        self.assertEqual(attributes["list-id"], "project-id")
        self.assertEqual(attributes["heading-id"], "heading-id")
        self.assertNotIn("list", attributes)
        self.assertNotIn("heading", attributes)
        self.assertEqual(
            attributes["checklist-items"],
            [
                {"type": "checklist-item", "attributes": {"title": "Build"}},
                {"type": "checklist-item", "attributes": {"title": "Docs"}},
            ],
        )
        self.assertEqual(attributes["tags"], ["Работа, дом", "Urgent"])
        self.assertEqual(parameters(uri)["reveal"], ["true"])
        self.assertNotIn("auth-token", parameters(uri))

    def test_batch_keeps_each_tasks_parameters(self):
        tasks = [
            {"title": "Чай", "tags": ["Дом"]},
            {"title": "Отчёт", "deadline": "2026-09-18", "list_id": "work"},
        ]
        objects = json.loads(parameters(things_uri.build_tasks_uri(tasks))["data"][0])
        self.assertEqual([task["operation"] for task in objects], ["create", "create"])
        self.assertNotIn("deadline", objects[0]["attributes"])
        self.assertEqual(objects[1]["attributes"]["deadline"], "2026-09-18")

    def test_missing_key_blocks_single_batch_and_preview_before_dispatch(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(
                os.environ,
                {
                    "THINGS_AUTH_TOKEN": "",
                    "THINGS_URI_CONFIG_FILE": str(Path(directory) / "absent.json"),
                },
            ),
            patch.object(macos.subprocess, "run") as opening,
        ):
            calls = [
                lambda: things_uri.add_task({"title": "x"}),
                lambda: things_uri.add_tasks([{"title": "x"}]),
                lambda: things_uri.build_task_uri({"title": "x"}),
            ]
            for call in calls:
                with self.assertRaises(AuthenticationError):
                    call()
            self.assertFalse(things_uri.get_status()["auth_token_configured"])
            opening.assert_not_called()

    def test_invalid_task_and_request_limits_prevent_dispatch(self):
        invalid = [
            None,
            [],
            {},
            {"title": " "},
            {"title": 4},
            {"title": "x", "unknown": 1},
            {"title": "x", "when": "2026-02-30"},
            {"title": "x", "when": "завтра"},
            {"title": "x", "when": "tomorrow@25:00"},
            {"title": "x", "deadline": "today@10:00"},
            {"title": "x", "heading": "Orphan"},
            {"title": "x", "tags": "Work"},
            {"title": "x", "notes": "NUL\x00"},
            {"title": "x", "show_quick_entry": True},
        ]
        with patch.object(macos.subprocess, "run") as opening:
            for task in invalid:
                with self.subTest(task=str(task)[:80]), self.assertRaises(ValueError):
                    things_uri.add_task(task)
            for tasks in (
                [],
                [{"title": "x"}] * 251,
                [{"title": "Good"}, {"notes": "Bad"}],
            ):
                with self.assertRaises(ValueError):
                    things_uri.add_tasks(tasks)
            with self.assertRaises(ValueError):
                things_uri.add_task({"title": "x"}, preview="false")
            opening.assert_not_called()

    def test_json_preserves_checklists_longer_than_adds_text_limit(self):
        task = {
            "title": "x" * 4000,
            "notes": "x" * 10000,
            "checklist_items": ["x" * 2000] * 2,
        }
        self.assertEqual(
            len(task_attributes(things_uri.build_task_uri(task))["checklist-items"]), 2
        )
        things_uri.build_tasks_uri([{"title": "x"}] * 250)

    def test_preview_never_opens_app_and_never_returns_secret(self):
        with patch.object(macos.subprocess, "run") as opening:
            result = things_uri.add_task({"title": "x"}, preview=True)
            self.assertEqual(result["status"], "preview")
            self.assertFalse(result["creation_verified"])
            self.assertNotIn("auth-token", parameters(result["uri"]))
            self.assertNotIn(TEST_TOKEN, json.dumps(result))
            opening.assert_not_called()

    def test_dispatch_sends_token_only_to_things_in_one_argument(self):
        with (
            patch.object(macos.platform, "system", return_value="Darwin"),
            patch.object(
                macos.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ) as opening,
        ):
            result = things_uri.add_task({"title": "$(id); `whoami` & title=x"})
            arguments = opening.call_args.args[0]
            self.assertEqual(arguments[:3], ["/usr/bin/open", "-b", macos.BUNDLE_ID])
            self.assertEqual(len(arguments), 4)
            self.assertEqual(parameters(arguments[3])["auth-token"], [TEST_TOKEN])
            self.assertNotIn("shell", opening.call_args.kwargs)
            self.assertEqual(result["status"], "dispatched")
            self.assertFalse(result["creation_verified"])
            self.assertNotIn("auth-token", parameters(result["uri"]))

    def test_dispatch_failures_do_not_echo_secret_or_retry(self):
        failures = [
            subprocess.CompletedProcess(
                [], 1, "", TEST_TOKEN + quote(TEST_TOKEN, safe="")
            ),
            subprocess.TimeoutExpired(TEST_TOKEN, 15),
            OSError(TEST_TOKEN),
        ]
        for failure in failures:
            options = (
                {"return_value": failure}
                if isinstance(failure, subprocess.CompletedProcess)
                else {"side_effect": failure}
            )
            with (
                self.subTest(failure=type(failure)),
                patch.object(macos.platform, "system", return_value="Darwin"),
                patch.object(macos.subprocess, "run", **options) as opening,
            ):
                with self.assertRaises(RuntimeError) as raised:
                    things_uri.add_task({"title": "x"})
                encoded_error = json.dumps(serialize_error(raised.exception))
                self.assertNotIn(TEST_TOKEN, encoded_error)
                self.assertNotIn(quote(TEST_TOKEN, safe=""), encoded_error)
                opening.assert_called_once()

    def test_status_identifies_renamed_app_without_launching(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contents = root / "Renamed Things.app" / "Contents"
            contents.mkdir(parents=True)
            with (contents / "Info.plist").open("wb") as handle:
                plistlib.dump({"CFBundleIdentifier": macos.BUNDLE_ID}, handle)
            with (
                patch.object(macos.platform, "system", return_value="Darwin"),
                patch.object(macos, "APPLICATION_ROOTS", (root,)),
                patch.object(macos.subprocess, "run") as opening,
            ):
                status = things_uri.get_status()
                self.assertTrue(status["app_found"])
                self.assertTrue(status["auth_token_configured"])
                self.assertNotIn(TEST_TOKEN, json.dumps(status))
                opening.assert_not_called()

    def test_non_mac_preview_is_portable_but_dispatch_fails(self):
        with (
            patch.object(macos.platform, "system", return_value="Linux"),
            patch.object(macos.subprocess, "run") as opening,
        ):
            self.assertEqual(
                things_uri.add_task({"title": "x"}, preview=True)["status"], "preview"
            )
            with self.assertRaises(RuntimeError):
                things_uri.add_task({"title": "x"})
            opening.assert_not_called()
