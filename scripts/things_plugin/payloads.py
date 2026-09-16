"""Map external JSON shapes to task values and back to response payloads."""

from typing import Any, Dict, Tuple, Union

from .application import (
    ApplicationStatus,
    DeliveryResult,
    DeliveryStatus,
    DispatchError,
    TaskOptions,
)
from .domain import (
    CHECKLIST_MAX_ITEMS,
    NOTES_MAX_LENGTH,
    TITLE_MAX_LENGTH,
    Destination,
    Task,
    ValidationError,
)
from .uri_contract import MAX_TASKS as MAX_TASKS

JsonObject = Dict[str, Any]
TASK_PROPERTIES: JsonObject = {
    "title": {"type": "string", "minLength": 1, "maxLength": TITLE_MAX_LENGTH},
    "notes": {"type": "string", "maxLength": NOTES_MAX_LENGTH},
    "when": {
        "type": "string",
        "description": "Start: YYYY-MM-DD, today, tomorrow, evening, anytime, someday; optional @HH:MM local reminder except anytime/someday.",
    },
    "deadline": {
        "type": "string",
        "description": "Hard deadline: YYYY-MM-DD, today or tomorrow.",
    },
    "tags": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Existing tag names. Tags are not created.",
    },
    "checklist_items": {
        "type": "array",
        "maxItems": CHECKLIST_MAX_ITEMS,
        "items": {"type": "string"},
    },
    "list": {"type": "string", "description": "Existing project or area name."},
    "list_id": {
        "type": "string",
        "description": "Existing project/area ID; takes precedence over list.",
    },
    "heading": {
        "type": "string",
        "description": "Existing heading inside the specified project.",
    },
    "heading_id": {
        "type": "string",
        "description": "Heading ID; takes precedence over heading.",
    },
}
SINGLE_TASK_PROPERTIES: JsonObject = dict(
    TASK_PROPERTIES,
    **{
        "reveal": {"type": "boolean", "default": False},
    },
)
DELIVERY_MESSAGES = {
    DeliveryStatus.PREVIEW: "URI prepared; nothing sent.",
    DeliveryStatus.DISPATCHED: "URI handed to Things. Persistence and task IDs are not verified by macOS open.",
}


def parse_task(payload: object, single: bool = True) -> Tuple[Task, TaskOptions]:
    if not isinstance(payload, dict):
        raise ValidationError("Each task must be an object.")
    allowed_fields = SINGLE_TASK_PROPERTIES if single else TASK_PROPERTIES
    unknown_fields = set(payload) - set(allowed_fields)
    if unknown_fields:
        names = ", ".join(sorted(str(name) for name in unknown_fields))
        raise ValidationError(f"Unknown task fields: {names}")
    if "title" not in payload:
        raise ValidationError("title is required.")
    for name, value in payload.items():
        if allowed_fields[name]["type"] == "string" and not isinstance(value, str):
            raise ValidationError(f"{name} must be a string.")
    destination = Destination(
        name=payload.get("list"),
        identifier=payload.get("list_id"),
        heading=payload.get("heading"),
        heading_identifier=payload.get("heading_id"),
    )
    task = Task(
        title=payload["title"],
        notes=payload.get("notes"),
        when=payload.get("when"),
        deadline=payload.get("deadline"),
        tags=_parse_string_array(payload, "tags"),
        checklist_items=_parse_string_array(payload, "checklist_items"),
        destination=destination,
    )
    options = TaskOptions(
        reveal=payload.get("reveal", False),
    )
    return task, options


def parse_tasks(payload: object) -> Tuple[Task, ...]:
    if not isinstance(payload, list):
        raise ValidationError("tasks must be an array of task objects.")
    return tuple(parse_task(task, single=False)[0] for task in payload)


def _parse_string_array(payload: JsonObject, name: str) -> Tuple[str, ...]:
    if name not in payload:
        return ()
    value = payload[name]
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValidationError(f"{name} must be an array of strings.")
    return tuple(value)


def serialize_delivery(result: DeliveryResult) -> JsonObject:
    return {
        "status": result.status.value,
        "uri": result.uri,
        "task_count": len(result.titles),
        "titles": list(result.titles),
        "creation_verified": result.creation_verified,
        "message": DELIVERY_MESSAGES[result.status],
    }


def serialize_status(status: ApplicationStatus) -> JsonObject:
    payload: JsonObject = {
        "platform": status.platform,
        "bundle_id": status.bundle_id,
        "app_found": status.app_found,
        "auth_token_configured": status.auth_token_configured,
        "uri_scheme_enabled": "unknown",
        "can_preview": status.auth_token_configured,
    }
    if status.app_path is not None:
        payload["app_path"] = status.app_path
    return payload


def serialize_error(error: Union[ValueError, RuntimeError]) -> JsonObject:
    payload: JsonObject = {"status": "error", "message": str(error)}
    if isinstance(error, DispatchError):
        payload["delivery_unknown"] = error.delivery_unknown
    return payload
