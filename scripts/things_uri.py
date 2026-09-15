#!/usr/bin/env python3
"""Compatibility API and JSON CLI for the Things URI application."""

import argparse
import getpass
import json
import sys
from typing import Any, Dict, List

from things_plugin.composition import create_service
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

__all__ = [
    "MAX_TASKS",
    "TASK_PROPERTIES",
    "SINGLE_TASK_PROPERTIES",
    "build_task_uri",
    "build_tasks_uri",
    "add_task",
    "add_tasks",
    "get_status",
    "configure_auth_token",
    "main",
]


TaskPayload = Dict[str, Any]
JsonResult = Dict[str, Any]


def build_task_uri(task: TaskPayload) -> str:
    parsed_task, options = parse_task(task)
    result = create_service().add_task(parsed_task, options, preview=True)
    return result.uri


def build_tasks_uri(tasks: List[TaskPayload], reveal: bool = False) -> str:
    parsed_tasks = parse_tasks(tasks)
    result = create_service().add_tasks(parsed_tasks, preview=True, reveal=reveal)
    return result.uri


def add_task(task: TaskPayload, preview: bool = False) -> JsonResult:
    parsed_task, options = parse_task(task)
    result = create_service().add_task(parsed_task, options, preview=preview)
    return serialize_delivery(result)


def add_tasks(
    tasks: List[TaskPayload], preview: bool = False, reveal: bool = False
) -> JsonResult:
    parsed_tasks = parse_tasks(tasks)
    result = create_service().add_tasks(parsed_tasks, preview=preview, reveal=reveal)
    return serialize_delivery(result)


def get_status() -> JsonResult:
    return serialize_status(create_service().get_status())


def configure_auth_token(value: str) -> JsonResult:
    create_service().configure_auth_token(value)
    return {"status": "configured", "auth_token_configured": True}


def _create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=["add-task", "add-tasks", "status", "configure-auth-token"]
    )
    parser.add_argument(
        "--preview", action="store_true", help="Build a URI without opening Things."
    )
    parser.add_argument(
        "--reveal",
        action="store_true",
        help="Show the first task after a batch dispatch.",
    )
    return parser


def main() -> int:
    parser = _create_argument_parser()
    arguments = parser.parse_args()
    try:
        if arguments.command == "configure-auth-token":
            value = (
                getpass.getpass("Things auth token: ")
                if sys.stdin.isatty()
                else sys.stdin.read().rstrip("\r\n")
            )
            result = configure_auth_token(value)
        elif arguments.command == "status":
            result = get_status()
        elif arguments.command == "add-task":
            if arguments.reveal:
                parser.error("For add-task, supply reveal inside the task JSON.")
            result = add_task(json.load(sys.stdin), preview=arguments.preview)
        else:
            result = add_tasks(
                json.load(sys.stdin), preview=arguments.preview, reveal=arguments.reveal
            )
    except (ValueError, RuntimeError) as error:
        print(json.dumps(serialize_error(error), ensure_ascii=False))
        return 1

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
