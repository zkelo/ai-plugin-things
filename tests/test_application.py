"""Use case behavior against replaceable boundaries, without macOS dependencies."""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from things_plugin.application import (
    ApplicationLocator,
    ApplicationStatus,
    AuthenticationError,
    AuthToken,
    AuthTokenStore,
    DeliveryStatus,
    DispatchError,
    PreparedUri,
    TaskOptions,
    TaskService,
    UriBuilder,
    UriDispatcher,
)
from things_plugin.domain import Task, ValidationError


class ApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.token = AuthToken("test-only-key")
        self.builder = Mock(spec=UriBuilder)
        self.builder.build_task.return_value = PreparedUri(
            "single-uri-with-secret", "single-public-uri"
        )
        self.builder.build_tasks.return_value = PreparedUri(
            "batch-uri-with-secret", "batch-public-uri"
        )
        self.dispatcher = Mock(spec=UriDispatcher)
        self.locator = Mock(spec=ApplicationLocator)
        self.store = Mock(spec=AuthTokenStore)
        self.store.get.return_value = self.token
        self.service = TaskService(
            self.builder, self.dispatcher, self.locator, self.store
        )

    def test_preview_authenticates_without_dispatch_or_app_lookup(self) -> None:
        task = Task("Read")
        options = TaskOptions()
        result = self.service.add_task(task, options, preview=True)
        self.assertEqual(result.status, DeliveryStatus.PREVIEW)
        self.assertEqual(result.uri, "single-public-uri")
        self.builder.build_task.assert_called_once_with(task, options, self.token)
        self.dispatcher.dispatch.assert_not_called()
        self.locator.locate.assert_not_called()
        self.assertFalse(result.creation_verified)

    def test_delivery_dispatches_authenticated_uri_and_returns_public_uri(self) -> None:
        result = self.service.add_task(Task("Send"), TaskOptions())
        self.dispatcher.dispatch.assert_called_once_with("single-uri-with-secret")
        self.assertEqual(result.status, DeliveryStatus.DISPATCHED)
        self.assertEqual(result.uri, "single-public-uri")
        self.assertNotIn("secret", repr(result))

    def test_batch_preview_authenticates_complete_snapshot(self) -> None:
        tasks = (Task("First"), Task("Second"))
        result = self.service.add_tasks(tasks, preview=True, reveal=True)
        self.builder.build_tasks.assert_called_once_with(tasks, True, self.token)
        self.assertEqual(result.titles, ("First", "Second"))
        self.assertEqual(result.uri, "batch-public-uri")
        self.dispatcher.dispatch.assert_not_called()
        self.locator.locate.assert_not_called()

    def test_missing_key_prevents_single_and_batch_preview_or_delivery(self) -> None:
        self.store.get.return_value = None
        for preview in (False, True):
            with self.subTest(preview=preview, batch=False):
                with self.assertRaisesRegex(AuthenticationError, "key is required"):
                    self.service.add_task(Task("Single"), TaskOptions(), preview)
            with self.subTest(preview=preview, batch=True):
                with self.assertRaisesRegex(AuthenticationError, "key is required"):
                    self.service.add_tasks((Task("Batch"),), preview)
        self.builder.build_task.assert_not_called()
        self.builder.build_tasks.assert_not_called()
        self.dispatcher.dispatch.assert_not_called()

    def test_uri_failure_prevents_partial_handoff(self) -> None:
        self.builder.build_tasks.side_effect = ValidationError(
            "Request cannot be encoded"
        )
        with self.assertRaises(ValidationError):
            self.service.add_tasks((Task("First"), Task("Second")))
        self.dispatcher.dispatch.assert_not_called()

    def test_delivery_failure_is_preserved_and_never_retried(self) -> None:
        error = DispatchError("Delivery unknown", delivery_unknown=True)
        self.dispatcher.dispatch.side_effect = error
        with self.assertRaises(DispatchError) as raised:
            self.service.add_task(Task("Send"), TaskOptions())
        self.assertIs(raised.exception, error)
        self.assertTrue(raised.exception.delivery_unknown)
        self.dispatcher.dispatch.assert_called_once_with("single-uri-with-secret")

    def test_quick_entry_is_rejected_before_any_boundary(self) -> None:
        with self.assertRaisesRegex(ValidationError, "does not support Quick Entry"):
            self.service.add_task(Task("Review"), TaskOptions(show_quick_entry=True))
        self.store.get.assert_not_called()
        self.builder.build_task.assert_not_called()
        self.dispatcher.dispatch.assert_not_called()

    def test_status_reports_configured_key_without_exposing_it(self) -> None:
        self.locator.locate.return_value = ApplicationStatus(
            "Darwin", "app", "/Applications/Things.app"
        )
        status = self.service.get_status()
        self.assertTrue(status.app_found)
        self.assertTrue(status.auth_token_configured)
        self.assertNotIn(self.token.value, repr(status))
        self.builder.build_task.assert_not_called()
        self.dispatcher.dispatch.assert_not_called()

    def test_status_remains_available_without_key(self) -> None:
        self.store.get.return_value = None
        self.locator.locate.return_value = ApplicationStatus("Darwin", "app")
        self.assertFalse(self.service.get_status().auth_token_configured)
        self.builder.build_task.assert_not_called()
        self.dispatcher.dispatch.assert_not_called()

    def test_configuration_validates_before_persistence(self) -> None:
        with self.assertRaises(AuthenticationError):
            self.service.configure_auth_token(" ")
        self.store.save.assert_not_called()
        self.service.configure_auth_token(" new-test-key ")
        self.store.save.assert_called_once_with(AuthToken("new-test-key"))

    def test_configuration_takes_effect_on_next_send_without_restart(self) -> None:
        self.store.save.side_effect = lambda token: setattr(
            self.store.get, "return_value", token
        )
        self.service.configure_auth_token("replacement-test-key")
        task = Task("Send after configuration")
        options = TaskOptions()
        self.service.add_task(task, options)
        self.builder.build_task.assert_called_once_with(
            task, options, AuthToken("replacement-test-key")
        )

    def test_invalid_control_fails_before_any_boundary(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.add_task(Task("Preview"), TaskOptions(), preview="false")
        with self.assertRaises(ValidationError):
            self.service.add_tasks((Task("Reveal"),), reveal=1)
        self.store.get.assert_not_called()
        self.builder.build_task.assert_not_called()
        self.builder.build_tasks.assert_not_called()
        self.dispatcher.dispatch.assert_not_called()


class AuthTokenTests(unittest.TestCase):
    def test_key_is_immutable_normalized_and_absent_from_repr(self) -> None:
        token = AuthToken(" test-only-secret ")
        self.assertEqual(token.value, "test-only-secret")
        self.assertNotIn(token.value, repr(token))
        with self.assertRaises(AttributeError):
            token.value = "replacement"

    def test_invalid_keys_never_appear_in_errors(self) -> None:
        invalid_values = (
            "",
            " ",
            "test-secret\n",
            "\ttest-secret",
            "test\x00secret",
            "test\x7fsecret",
            "test\x85secret",
            "test\u200esecret",
            "x" * 4001,
        )
        for value in invalid_values:
            with self.subTest(length=len(value)):
                with self.assertRaises(AuthenticationError) as raised:
                    AuthToken(value)
                if value.strip():
                    self.assertNotIn(value, str(raised.exception))

    def test_non_string_key_has_generic_error(self) -> None:
        with self.assertRaisesRegex(AuthenticationError, "must be a string"):
            AuthToken(123)

    def test_prepared_uri_representation_hides_authenticated_transport(self) -> None:
        prepared = PreparedUri(
            "things:///json?auth-token=test-secret", "things:///json"
        )
        self.assertNotIn("test-secret", repr(prepared))
