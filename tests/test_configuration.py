"""Credential behavior uses only temporary fixtures and synthetic keys."""

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Dict
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from things_plugin.application import AuthenticationError, AuthToken
from things_plugin.infrastructure.configuration import FileAuthTokenStore


class ConfigurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.directory = Path(self.temporary_directory.name)
        self.path = self.directory / "private" / "config.json"
        self.environment: Dict[str, str] = {}
        self.store = FileAuthTokenStore(self.path, self.environment)

    def write_private_configuration(self, content: str) -> None:
        self.path.parent.mkdir(exist_ok=True)
        self.path.write_text(content, encoding="utf-8")
        self.path.chmod(0o600)

    def test_missing_configuration_returns_no_key_and_does_not_create_files(
        self,
    ) -> None:
        self.assertIsNone(self.store.get())
        self.assertFalse(self.path.exists())
        self.assertFalse(self.path.parent.exists())

    def test_atomic_save_reloads_key_and_sets_private_permissions(self) -> None:
        token = AuthToken("fixture-test-secret")
        self.store.save(token)
        self.assertEqual(FileAuthTokenStore(self.path, {}).get(), token)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.path.parent.stat().st_mode), 0o700)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_all_new_parent_directories_are_private(self) -> None:
        nested = self.directory / "first" / "second" / "config.json"
        FileAuthTokenStore(nested, {}).save(AuthToken("fixture-test-key"))
        self.assertEqual(stat.S_IMODE(nested.parent.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(nested.parent.parent.stat().st_mode), 0o700)

    def test_save_preserves_unrelated_configuration_fields(self) -> None:
        self.write_private_configuration(
            json.dumps(
                {"auth_token": "old-fixture-key", "preferences": {"reveal": True}}
            )
        )
        self.store.save(AuthToken("replacement-fixture-key"))
        document = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(document["preferences"], {"reveal": True})
        self.assertEqual(document["auth_token"], "replacement-fixture-key")
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)

    def test_nonempty_environment_key_takes_read_priority(self) -> None:
        self.store.save(AuthToken("file-fixture-key"))
        self.environment["THINGS_AUTH_TOKEN"] = " environment-fixture-key "
        self.assertEqual(self.store.get(), AuthToken("environment-fixture-key"))

    def test_empty_environment_key_falls_back_to_file(self) -> None:
        self.store.save(AuthToken("file-fixture-key"))
        self.environment["THINGS_AUTH_TOKEN"] = ""
        self.assertEqual(self.store.get(), AuthToken("file-fixture-key"))
        self.store.save(AuthToken("updated-fixture-key"))
        self.assertEqual(self.store.get(), AuthToken("updated-fixture-key"))

    def test_whitespace_environment_key_is_invalid_without_file_fallback(self) -> None:
        self.store.save(AuthToken("file-fixture-key"))
        self.environment["THINGS_AUTH_TOKEN"] = " "
        with self.assertRaises(AuthenticationError):
            self.store.get()

    def test_environment_override_prevents_ineffective_local_save(self) -> None:
        self.store.save(AuthToken("file-fixture-key"))
        self.environment["THINGS_AUTH_TOKEN"] = "environment-fixture-key"
        with self.assertRaisesRegex(AuthenticationError, "takes precedence") as raised:
            self.store.save(AuthToken("replacement-fixture-key"))
        self.assertNotIn("environment-fixture-key", str(raised.exception))
        self.environment.clear()
        self.assertEqual(self.store.get(), AuthToken("file-fixture-key"))

    def test_custom_configuration_path_from_environment(self) -> None:
        custom_path = self.directory / "custom.json"
        store = FileAuthTokenStore(
            environment={"THINGS_URI_CONFIG_FILE": str(custom_path)}
        )
        store.save(AuthToken("custom-fixture-key"))
        self.assertEqual(
            FileAuthTokenStore(custom_path, {}).get(), AuthToken("custom-fixture-key")
        )
        self.assertFalse(self.path.exists())

    def test_explicit_path_takes_priority_over_environment_configuration_path(
        self,
    ) -> None:
        other_path = self.directory / "other.json"
        store = FileAuthTokenStore(
            self.path, {"THINGS_URI_CONFIG_FILE": str(other_path)}
        )
        store.save(AuthToken("explicit-fixture-key"))
        self.assertTrue(self.path.exists())
        self.assertFalse(other_path.exists())

    def test_default_configuration_path_is_resolved_without_reading_real_keys(
        self,
    ) -> None:
        with patch(
            "things_plugin.infrastructure.configuration.Path.home",
            return_value=self.directory,
        ):
            store = FileAuthTokenStore(environment={})
        store.save(AuthToken("default-fixture-key"))
        self.assertTrue(
            (self.directory / ".config" / "things-uri" / "config.json").is_file()
        )

    def test_invalid_stored_key_is_redacted_and_not_overwritten_by_read(self) -> None:
        original = json.dumps({"auth_token": "fixture-secret\n"})
        self.write_private_configuration(original)
        with self.assertRaises(AuthenticationError) as raised:
            self.store.get()
        self.assertNotIn("fixture-secret", str(raised.exception))
        self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    def test_invalid_json_and_nonobject_configuration_have_redacted_errors(
        self,
    ) -> None:
        for document in ('{"auth_token": "fixture-secret"', '["fixture-secret"]'):
            with self.subTest(document_type=document[:1]):
                self.write_private_configuration(document)
                with self.assertRaises(AuthenticationError) as raised:
                    self.store.get()
                self.assertNotIn("fixture-secret", str(raised.exception))
                with self.assertRaises(AuthenticationError):
                    self.store.save(AuthToken("new-fixture-key"))
                self.assertEqual(self.path.read_text(encoding="utf-8"), document)

    def test_configuration_without_auth_token_returns_none(self) -> None:
        self.write_private_configuration('{"preferences": {}}')
        self.assertIsNone(self.store.get())

    def test_insecure_permissions_are_refused_without_exposing_the_key(self) -> None:
        key = "fixture-permission-secret"
        self.path.parent.mkdir()
        self.path.write_text(json.dumps({"auth_token": key}), encoding="utf-8")
        self.path.chmod(0o644)
        with self.assertRaisesRegex(AuthenticationError, "owner-only") as raised:
            self.store.get()
        self.assertNotIn(key, str(raised.exception))
        with self.assertRaises(AuthenticationError):
            self.store.save(AuthToken("replacement-fixture-key"))
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o644)

    def test_symbolic_link_is_refused_without_modifying_destination(self) -> None:
        self.path.parent.mkdir()
        destination = self.directory / "destination.json"
        original = '{"auth_token": "target-fixture-key"}'
        destination.write_text(original, encoding="utf-8")
        self.path.symlink_to(destination)
        with self.assertRaisesRegex(AuthenticationError, "symbolic link"):
            self.store.get()
        with self.assertRaises(AuthenticationError):
            self.store.save(AuthToken("new-fixture-key"))
        self.assertEqual(destination.read_text(encoding="utf-8"), original)

    def test_directory_configuration_path_is_refused(self) -> None:
        self.path.mkdir(parents=True)
        with self.assertRaises(AuthenticationError):
            self.store.get()
        with self.assertRaises(AuthenticationError):
            self.store.save(AuthToken("new-fixture-key"))

    def test_file_owned_by_another_user_is_refused(self) -> None:
        metadata = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_uid=os.getuid() + 1)
        with patch(
            "things_plugin.infrastructure.configuration.Path.lstat",
            return_value=metadata,
        ):
            with self.assertRaisesRegex(AuthenticationError, "belong to this user"):
                self.store.get()
            with self.assertRaises(AuthenticationError):
                self.store.save(AuthToken("new-fixture-key"))
        self.assertFalse(self.path.exists())

    def test_private_permissions_remain_exact_under_restrictive_umask(self) -> None:
        previous = os.umask(0o777)
        try:
            self.store.save(AuthToken("fixture-test-key"))
        finally:
            os.umask(previous)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.path.parent.stat().st_mode), 0o700)

    def test_read_errors_do_not_expose_operating_system_error_details(self) -> None:
        self.store.save(AuthToken("fixture-test-key"))
        with patch(
            "things_plugin.infrastructure.configuration.Path.open",
            side_effect=OSError("fixture-secret must not appear in errors"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Cannot read") as raised:
                self.store.get()
        self.assertNotIn("fixture-secret", str(raised.exception))

    def test_failed_atomic_replace_preserves_old_key_and_removes_temporary_file(
        self,
    ) -> None:
        self.store.save(AuthToken("original-fixture-key"))
        with patch(
            "things_plugin.infrastructure.configuration.os.replace",
            side_effect=OSError("fixture-secret must not appear in errors"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Cannot save") as raised:
                self.store.save(AuthToken("replacement-fixture-key"))
        self.assertNotIn("fixture-secret", str(raised.exception))
        self.assertEqual(self.store.get(), AuthToken("original-fixture-key"))
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])
