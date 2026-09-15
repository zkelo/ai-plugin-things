#!/usr/bin/env python3
"""Dependency-free MCP stdio input adapter for the Things application."""

import json
import sys
from typing import Any, BinaryIO, Dict, List, Optional, Sequence, Union

from things_plugin.application import AUTH_TOKEN_MAX_LENGTH, TaskService
from things_plugin.payloads import (
    MAX_TASKS,
    SINGLE_TASK_PROPERTIES,
    TASK_PROPERTIES,
    parse_task,
    parse_tasks,
    serialize_delivery,
    serialize_error,
    serialize_status,
)

JsonObject = Dict[str, Any]
RequestId = Union[str, int]
SUPPORTED_VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18")
PREVIEW_PROPERTY: JsonObject = {
    "type": "boolean",
    "description": "Build and validate the URI without opening Things (default false).",
}
CREATE_ANNOTATIONS: Dict[str, bool] = {
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": False,
    "openWorldHint": True,
}
READ_ANNOTATIONS: Dict[str, bool] = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}


def object_schema(properties: JsonObject, required: Sequence[str] = ()) -> JsonObject:
    return {
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }


def tool_definitions() -> List[JsonObject]:
    return [
        {
            "name": "add_task",
            "description": (
                "Send one new task to Things through its URI scheme on this Mac. "
                "Requires a configured Things auth token. "
                "Requires the user's intent to add a task. A successful dispatch "
                "does not confirm persistence or return a Things task ID. "
                "Use preview=true to avoid opening Things."
            ),
            "inputSchema": object_schema(
                dict(SINGLE_TASK_PROPERTIES, preview=PREVIEW_PROPERTY),
                ("title",),
            ),
            "annotations": CREATE_ANNOTATIONS,
        },
        {
            "name": "add_tasks",
            "description": (
                "Send several new tasks in one Things JSON URI on this Mac. "
                "Requires a configured Things auth token. "
                "Requires the user's intent to add these tasks. Do not retry an "
                "uncertain dispatch automatically: it could create duplicates. "
                "Use preview=true to avoid opening Things."
            ),
            "inputSchema": object_schema(
                {
                    "tasks": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": MAX_TASKS,
                        "items": object_schema(TASK_PROPERTIES, ("title",)),
                    },
                    "preview": PREVIEW_PROPERTY,
                    "reveal": {
                        "type": "boolean",
                        "description": "Reveal imported tasks in Things (default false).",
                    },
                },
                ("tasks",),
            ),
            "annotations": CREATE_ANNOTATIONS,
        },
        {
            "name": "preview_task",
            "description": "Validate one task and return its Things URI without opening Things.",
            "inputSchema": object_schema(SINGLE_TASK_PROPERTIES, ("title",)),
            "annotations": READ_ANNOTATIONS,
        },
        {
            "name": "get_status",
            "description": "Check local platform, Things availability and whether the required key is configured. Never returns the key.",
            "inputSchema": object_schema({}),
            "annotations": READ_ANNOTATIONS,
        },
        {
            "name": "configure_auth_token",
            "description": "Save the Things auth token in this plugin's private local configuration. Use only when the user asks to configure their key. Never repeat the key in replies.",
            "inputSchema": object_schema(
                {
                    "auth_token": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": AUTH_TOKEN_MAX_LENGTH,
                    }
                },
                ("auth_token",),
            ),
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        },
    ]


class ProtocolError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def error_response(
    request_id: Optional[RequestId], code: int, message: str
) -> JsonObject:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def tool_result(value: JsonObject, is_error: bool = False) -> JsonObject:
    content_text = json.dumps(value, ensure_ascii=False, allow_nan=False)
    return {"content": [{"type": "text", "text": content_text}], "isError": is_error}


def validate_arguments(
    arguments: Any, schema: JsonObject, label: str = "arguments"
) -> None:
    """Check transport types and bounds; business rules belong to the application."""
    schema_type = schema.get("type")
    if schema_type == "object":
        _validate_object_arguments(arguments, schema, label)
    elif schema_type == "boolean":
        if not isinstance(arguments, bool):
            raise ValueError(label + " must be a boolean")
    elif schema_type == "string":
        _validate_string_arguments(arguments, schema, label)
    elif schema_type == "array":
        _validate_array_arguments(arguments, schema, label)
    else:
        raise ValueError("Unsupported transport schema type: " + str(schema_type))


def _validate_object_arguments(arguments: Any, schema: JsonObject, label: str) -> None:
    if not isinstance(arguments, dict):
        raise ValueError(label + " must be an object")
    if any(not isinstance(name, str) for name in arguments):
        raise ValueError(label + " field names must be strings")
    properties = schema["properties"]
    unknown_fields = set(arguments) - set(properties)
    if unknown_fields:
        raise ValueError(
            label + " contains unknown fields: " + ", ".join(sorted(unknown_fields))
        )
    missing_fields = set(schema.get("required", ())) - set(arguments)
    if missing_fields:
        raise ValueError(
            label + " is missing required fields: " + ", ".join(sorted(missing_fields))
        )
    for field_name, value in arguments.items():
        validate_arguments(value, properties[field_name], label + "." + field_name)


def _validate_string_arguments(arguments: Any, schema: JsonObject, label: str) -> None:
    if not isinstance(arguments, str):
        raise ValueError(label + " must be a string")
    if len(arguments) < schema.get("minLength", 0):
        raise ValueError(label + " is too short")
    if "maxLength" in schema and len(arguments) > schema["maxLength"]:
        raise ValueError(label + " is too long")


def _validate_array_arguments(arguments: Any, schema: JsonObject, label: str) -> None:
    if not isinstance(arguments, list):
        raise ValueError(label + " must be an array")
    if len(arguments) < schema.get("minItems", 0):
        raise ValueError(label + " must contain at least one item")
    if "maxItems" in schema and len(arguments) > schema["maxItems"]:
        raise ValueError(label + " contains too many items")
    for index, value in enumerate(arguments):
        validate_arguments(value, schema["items"], label + "[" + str(index) + "]")


def _request_id(message: Any) -> Optional[RequestId]:
    if not isinstance(message, dict):
        return None
    candidate = message.get("id")
    if isinstance(candidate, str) or (
        isinstance(candidate, int) and not isinstance(candidate, bool)
    ):
        return candidate
    return None


def _valid_envelope(message: Any, request_id: Optional[RequestId]) -> bool:
    return (
        isinstance(message, dict)
        and message.get("jsonrpc") == "2.0"
        and isinstance(message.get("method"), str)
        and ("id" not in message or request_id is not None)
        and "result" not in message
        and "error" not in message
    )


class Server:
    def __init__(self, task_service: TaskService) -> None:
        self._task_service = task_service
        self.initialized = False
        self.ready = False
        self.tools: Dict[str, JsonObject] = {
            definition["name"]: definition for definition in tool_definitions()
        }

    def handle(self, message: Any) -> Optional[JsonObject]:
        request_id = _request_id(message)
        if not _valid_envelope(message, request_id):
            return error_response(request_id, -32600, "Invalid Request")
        if "id" not in message:
            self._handle_notification(message)
            return None

        try:
            parameters = message.get("params", {})
            if not isinstance(parameters, dict):
                raise ProtocolError(-32602, "params must be an object")
            result = self.dispatch(message["method"], parameters)
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except ProtocolError as error:
            return error_response(request_id, error.code, error.message)
        except Exception:
            # This transport boundary must preserve the connection after an unforeseen
            # application failure, without sending task contents or tracebacks to stdout.
            return error_response(request_id, -32603, "Internal error")

    def _handle_notification(self, message: JsonObject) -> None:
        if message["method"] == "notifications/initialized" and self.initialized:
            self.ready = True
        # A notification never triggers task creation, even if named tools/call.

    def dispatch(self, method: str, parameters: JsonObject) -> JsonObject:
        if method == "ping":
            return {}
        if method == "initialize":
            return self._initialize(parameters)
        if method not in ("tools/list", "tools/call"):
            raise ProtocolError(-32601, "Method not found: " + method)
        if not self.ready:
            raise ProtocolError(
                -32000,
                "Initialize and send notifications/initialized before using tools",
            )
        if method == "tools/list":
            return self._list_tools(parameters)
        return self._call_tool(parameters)

    def _initialize(self, parameters: JsonObject) -> JsonObject:
        if self.initialized:
            raise ProtocolError(-32600, "Server already initialized")
        client_information = parameters.get("clientInfo")
        requested_version = parameters.get("protocolVersion")
        if (
            not isinstance(requested_version, str)
            or not isinstance(parameters.get("capabilities"), dict)
            or not isinstance(client_information, dict)
            or not isinstance(client_information.get("name"), str)
            or not isinstance(client_information.get("version"), str)
        ):
            raise ProtocolError(
                -32602,
                "initialize requires protocolVersion, capabilities and clientInfo",
            )
        negotiated_version = (
            requested_version
            if requested_version in SUPPORTED_VERSIONS
            else SUPPORTED_VERSIONS[-1]
        )
        self.initialized = True
        return {
            "protocolVersion": negotiated_version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "things", "version": "1.0.0"},
            "instructions": (
                "Create tasks only when the user asks to add them to Things. "
                "Configure the required auth token before creating or previewing tasks. Never echo credentials. "
                "Dispatch acknowledgements do not confirm persistence. Never "
                "automatically repeat a dispatch with an uncertain outcome."
            ),
        }

    def _list_tools(self, parameters: JsonObject) -> JsonObject:
        if set(parameters) - {"_meta", "cursor"}:
            raise ProtocolError(-32602, "Unknown tools/list parameter")
        if "cursor" in parameters:
            raise ProtocolError(-32602, "This server has no pagination cursor")
        return {"tools": list(self.tools.values())}

    def _call_tool(self, parameters: JsonObject) -> JsonObject:
        if set(parameters) - {"name", "arguments", "_meta"}:
            raise ProtocolError(-32602, "Unknown tools/call parameter")
        tool_name = parameters.get("name")
        if not isinstance(tool_name, str) or tool_name not in self.tools:
            raise ProtocolError(-32602, "Unknown tool: " + str(tool_name))
        arguments = parameters.get("arguments", {})
        try:
            validate_arguments(arguments, self.tools[tool_name]["inputSchema"])
            return tool_result(self._execute_tool(tool_name, arguments))
        except (ValueError, RuntimeError) as error:
            return tool_result(serialize_error(error), is_error=True)

    def _execute_tool(self, tool_name: str, arguments: JsonObject) -> JsonObject:
        if tool_name == "configure_auth_token":
            self._task_service.configure_auth_token(arguments["auth_token"])
            return {"status": "configured", "auth_token_configured": True}
        if tool_name == "get_status":
            return serialize_status(self._task_service.get_status())
        if tool_name == "add_tasks":
            tasks = parse_tasks(arguments["tasks"])
            result = self._task_service.add_tasks(
                tasks,
                preview=arguments.get("preview", False),
                reveal=arguments.get("reveal", False),
            )
            return serialize_delivery(result)
        task_payload = dict(arguments)
        preview = (
            task_payload.pop("preview", False) if tool_name == "add_task" else True
        )
        task, options = parse_task(task_payload)
        result = self._task_service.add_task(task, options, preview=preview)
        return serialize_delivery(result)


def reject_constant(value: str) -> None:
    raise ValueError("Invalid JSON constant: " + value)


def _parse_message(line: bytes) -> Any:
    return json.loads(line.decode("utf-8"), parse_constant=reject_constant)


def _write_response(response: JsonObject, output_stream: BinaryIO) -> None:
    encoded_response = json.dumps(
        response, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    )
    output_stream.write((encoded_response + "\n").encode("utf-8"))
    output_stream.flush()


def serve(
    input_stream: BinaryIO, output_stream: BinaryIO, task_service: TaskService
) -> None:
    server = Server(task_service)
    for line in input_stream:
        try:
            message = _parse_message(line)
        except (UnicodeDecodeError, ValueError, RecursionError):
            response = error_response(None, -32700, "Parse error")
        else:
            response = server.handle(message)
        if response is not None:
            _write_response(response, output_stream)


if __name__ == "__main__":
    from things_plugin.composition import create_service

    serve(sys.stdin.buffer, sys.stdout.buffer, create_service())
