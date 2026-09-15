"""MCP transport and argument checks; these tests never dispatch a Things URI."""

import importlib.util
import io
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, Union
from unittest.mock import Mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from things_plugin.application import (  # noqa: E402
    ApplicationStatus,
    DeliveryResult,
    DeliveryStatus,
    DispatchError,
    TaskOptions,
    TaskService,
)
from things_plugin.domain import Task  # noqa: E402

SPEC = importlib.util.spec_from_file_location(
    "things_uri_server", SCRIPTS / "server.py"
)
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


def request(
    request_id: Union[str, int], method: str, params: Any = None
) -> Dict[str, Any]:
    value = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        value["params"] = params
    return value


def initialize(version: str = "2025-06-18") -> Dict[str, Any]:
    return request(
        1,
        "initialize",
        {
            "protocolVersion": version,
            "capabilities": {},
            "clientInfo": {"name": "tests", "version": "1"},
        },
    )


INITIALIZED = {"jsonrpc": "2.0", "method": "notifications/initialized"}


def ready_server(task_service: TaskService) -> server.Server:
    instance = server.Server(task_service)
    instance.handle(initialize())
    instance.handle(INITIALIZED)
    return instance


class ServerTests(unittest.TestCase):
    def test_supported_version_negotiation_and_latest_fallback(self) -> None:
        for version in server.SUPPORTED_VERSIONS + ("2099-01-01",):
            with self.subTest(version=version):
                response = server.Server(Mock(spec=TaskService)).handle(
                    initialize(version)
                )
                expected = (
                    version
                    if version in server.SUPPORTED_VERSIONS
                    else server.SUPPORTED_VERSIONS[-1]
                )
                self.assertEqual(response["result"]["protocolVersion"], expected)
                self.assertEqual(
                    response["result"]["capabilities"],
                    {"tools": {"listChanged": False}},
                )

    def test_stdio_handshake_listing_unicode_preview_and_clean_eof(self) -> None:
        messages = [
            initialize(),
            INITIALIZED,
            request(2, "tools/list"),
            request(
                3,
                "tools/call",
                {
                    "name": "preview_task",
                    "arguments": {
                        "title": "Buy tea 🍵 & coffee",
                        "notes": "First line\nSecond line",
                    },
                },
            ),
            request(4, "ping"),
        ]
        payload = "".join(
            json.dumps(item, ensure_ascii=False) + "\n" for item in messages
        ).encode("utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "server.py")],
            env=dict(
                os.environ,
                THINGS_AUTH_TOKEN="synthetic-mcp-token",
                PYTHONDONTWRITEBYTECODE="1",
            ),
            input=payload,
            capture_output=True,
            timeout=10,
            check=True,
        )
        responses = [
            json.loads(line) for line in result.stdout.decode("utf-8").splitlines()
        ]
        self.assertEqual([item["id"] for item in responses], [1, 2, 3, 4])
        tools = responses[1]["result"]["tools"]
        self.assertEqual(
            {tool["name"] for tool in tools},
            {
                "add_task",
                "add_tasks",
                "preview_task",
                "get_status",
                "configure_auth_token",
            },
        )
        self.assertFalse(responses[2]["result"]["isError"])
        preview = json.loads(responses[2]["result"]["content"][0]["text"])
        self.assertIn("things:///json?", json.dumps(preview))
        self.assertNotIn("synthetic-mcp-token", result.stdout.decode("utf-8"))
        self.assertEqual(responses[3]["result"], {})
        self.assertEqual(result.stderr, b"")

    def test_invalid_lines_do_not_break_next_request(self) -> None:
        source = io.BytesIO(
            b"{broken\n\xff\n[1,2]\n" + json.dumps(request(4, "ping")).encode() + b"\n"
        )
        output = io.BytesIO()
        server.serve(source, output, Mock(spec=TaskService))
        responses = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(
            [item["error"]["code"] for item in responses[:3]], [-32700, -32700, -32600]
        )
        self.assertEqual(responses[3], {"jsonrpc": "2.0", "id": 4, "result": {}})

    def test_invalid_envelopes_and_unknown_method(self) -> None:
        for invalid in (
            None,
            [],
            {"jsonrpc": "1.0", "id": 2, "method": "ping"},
            {"jsonrpc": "2.0", "id": None, "method": "ping"},
            {"jsonrpc": "2.0", "id": True, "method": "ping"},
            {"jsonrpc": "2.0", "id": 1.5, "method": "ping"},
        ):
            with self.subTest(invalid=invalid):
                self.assertEqual(
                    server.Server(Mock(spec=TaskService)).handle(invalid)["error"][
                        "code"
                    ],
                    -32600,
                )
        self.assertEqual(
            server.Server(Mock(spec=TaskService)).handle(request(1, "unknown"))[
                "error"
            ]["code"],
            -32601,
        )
        self.assertEqual(
            server.Server(Mock(spec=TaskService)).handle(request(1, "ping", []))[
                "error"
            ]["code"],
            -32602,
        )

    def test_tools_require_initialization(self) -> None:
        instance = server.Server(Mock(spec=TaskService))
        self.assertEqual(
            instance.handle(request(2, "tools/list"))["error"]["code"], -32000
        )
        instance.handle(initialize())
        self.assertEqual(
            instance.handle(request(3, "tools/list"))["error"]["code"], -32000
        )
        instance.handle(INITIALIZED)
        self.assertIn("tools", instance.handle(request(4, "tools/list"))["result"])

    def test_invalid_tool_arguments_never_reach_core(self) -> None:
        invalid_calls = [
            ("add_task", {}),
            ("add_task", {"title": "Task", "preview": "false"}),
            ("add_task", {"title": "Task", "reveal": 1}),
            ("add_task", {"title": "Task", "show_quick_entry": None}),
            ("add_task", {"title": "Task", "unsupported": "value"}),
            ("add_task", {"title": "Task", "tags": "tag"}),
            ("add_task", {"title": ""}),
            ("preview_task", {"title": "Task", "preview": False}),
            ("get_status", {"title": "Task"}),
            ("add_tasks", {}),
            ("add_tasks", {"tasks": []}),
            ("add_tasks", {"tasks": [{"title": "Task"}] * (server.MAX_TASKS + 1)}),
            ("add_tasks", {"tasks": [{"title": "Task", "reveal": True}]}),
            ("add_tasks", {"tasks": [{"notes": "No title"}]}),
            ("add_tasks", {"tasks": [{"title": "Task"}], "preview": 0}),
            ("add_tasks", {"tasks": [{"title": "Task"}], "reveal": "true"}),
        ]
        task_service = Mock(spec=TaskService)
        instance = ready_server(task_service)
        for index, (name, arguments) in enumerate(invalid_calls, start=2):
            with self.subTest(name=name, arguments=arguments):
                response = instance.handle(
                    request(index, "tools/call", {"name": name, "arguments": arguments})
                )
                self.assertTrue(response["result"]["isError"])
        task_service.add_task.assert_not_called()
        task_service.add_tasks.assert_not_called()
        task_service.get_status.assert_not_called()

    def test_validator_enforces_advertised_string_and_array_bounds(self) -> None:
        string_schema = {"type": "string", "minLength": 1, "maxLength": 3}
        for value in ("", "four"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                server.validate_arguments(value, string_schema)
        server.validate_arguments("abc", string_schema)
        array_schema = {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 2,
        }
        for value in ([], ["a", "b", "c"]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                server.validate_arguments(value, array_schema)
        server.validate_arguments(["a", "b"], array_schema)

    def test_unknown_tool_is_protocol_error_and_notification_never_dispatches(
        self,
    ) -> None:
        task_service = Mock(spec=TaskService)
        instance = ready_server(task_service)
        response = instance.handle(
            request(2, "tools/call", {"name": "delete_task", "arguments": {}})
        )
        self.assertEqual(response["error"]["code"], -32602)
        self.assertIsNone(
            instance.handle(
                {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "add_task",
                        "arguments": {"title": "Never create"},
                    },
                }
            )
        )
        task_service.add_task.assert_not_called()

    def test_core_errors_are_readable_tool_errors_and_controls_are_forwarded(
        self,
    ) -> None:
        task_service = Mock(spec=TaskService)
        task_service.add_task.side_effect = RuntimeError("Things unavailable")
        instance = ready_server(task_service)
        response = instance.handle(
            request(
                2,
                "tools/call",
                {
                    "name": "add_task",
                    "arguments": {"title": "Task", "preview": True},
                },
            )
        )
        task_service.add_task.assert_called_once_with(
            Task(title="Task"), TaskOptions(), preview=True
        )
        error_payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(
            error_payload, {"status": "error", "message": "Things unavailable"}
        )
        self.assertTrue(response["result"]["isError"])

        task_service.add_tasks.return_value = DeliveryResult(
            DeliveryStatus.PREVIEW, "things:///json?data=preview", ("Task",)
        )
        response = instance.handle(
            request(
                3,
                "tools/call",
                {
                    "name": "add_tasks",
                    "arguments": {
                        "tasks": [{"title": "Task"}],
                        "preview": True,
                        "reveal": True,
                    },
                },
            )
        )
        task_service.add_tasks.assert_called_once_with(
            (Task(title="Task"),), preview=True, reveal=True
        )
        self.assertFalse(response["result"]["isError"])

    def test_preview_options_and_status_use_injected_service(self) -> None:
        task_service = Mock(spec=TaskService)
        task_service.add_task.return_value = DeliveryResult(
            DeliveryStatus.PREVIEW, "things:///add?title=Task", ("Task",)
        )
        task_service.get_status.return_value = ApplicationStatus(
            "Darwin", "test.bundle"
        )
        instance = ready_server(task_service)
        preview_response = instance.handle(
            request(
                2,
                "tools/call",
                {
                    "name": "preview_task",
                    "arguments": {"title": "Task", "reveal": True},
                },
            )
        )
        task_service.add_task.assert_called_once_with(
            Task(title="Task"), TaskOptions(reveal=True), preview=True
        )
        self.assertFalse(preview_response["result"]["isError"])
        status_response = instance.handle(
            request(
                3,
                "tools/call",
                {
                    "name": "get_status",
                    "arguments": {},
                },
            )
        )
        status_payload = json.loads(status_response["result"]["content"][0]["text"])
        self.assertEqual(status_payload["bundle_id"], "test.bundle")
        self.assertFalse(status_payload["app_found"])
        task_service.get_status.assert_called_once_with()

    def test_dispatch_error_preserves_delivery_uncertainty(self) -> None:
        task_service = Mock(spec=TaskService)
        task_service.add_task.side_effect = DispatchError(
            "Inspect Things before retrying.", delivery_unknown=True
        )
        response = ready_server(task_service).handle(
            request(
                2,
                "tools/call",
                {
                    "name": "add_task",
                    "arguments": {"title": "Task"},
                },
            )
        )
        self.assertTrue(response["result"]["isError"])
        error_payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(
            error_payload,
            {
                "status": "error",
                "message": "Inspect Things before retrying.",
                "delivery_unknown": True,
            },
        )

    def test_configure_auth_token_never_returns_the_key_or_creates_tasks(self) -> None:
        task_service = Mock(spec=TaskService)
        token = "synthetic-configuration-secret"
        response = ready_server(task_service).handle(
            request(
                2,
                "tools/call",
                {
                    "name": "configure_auth_token",
                    "arguments": {"auth_token": token},
                },
            )
        )
        task_service.configure_auth_token.assert_called_once_with(token)
        task_service.add_task.assert_not_called()
        self.assertNotIn(token, json.dumps(response))
        self.assertEqual(
            json.loads(response["result"]["content"][0]["text"]),
            {"status": "configured", "auth_token_configured": True},
        )

    def test_unexpected_failure_preserves_connection_and_hides_internal_details(
        self,
    ) -> None:
        task_service = Mock(spec=TaskService)
        task_service.add_task.side_effect = LookupError("Private details")
        instance = ready_server(task_service)
        response = instance.handle(
            request(
                2,
                "tools/call",
                {
                    "name": "preview_task",
                    "arguments": {"title": "Task"},
                },
            )
        )
        self.assertEqual(
            response["error"], {"code": -32603, "message": "Internal error"}
        )
        self.assertEqual(
            instance.handle(request(3, "ping")),
            {"jsonrpc": "2.0", "id": 3, "result": {}},
        )


if __name__ == "__main__":
    unittest.main()
