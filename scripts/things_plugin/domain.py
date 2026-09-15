"""Immutable task data and business rules, independent of URI delivery."""

import re
from dataclasses import dataclass, field
from datetime import date, time
from typing import Optional, Tuple

TITLE_MAX_LENGTH = 4000
NOTES_MAX_LENGTH = 10000
CHECKLIST_MAX_ITEMS = 100
START_KEYWORDS = frozenset({"today", "tomorrow", "evening", "anytime", "someday"})
DEADLINE_KEYWORDS = frozenset({"today", "tomorrow"})
UNSCHEDULED_KEYWORDS = frozenset({"anytime", "someday"})


class ValidationError(ValueError):
    """Task data does not satisfy a domain rule."""


def _validate_text(
    value: str,
    field_name: str,
    *,
    character_limit: int = TITLE_MAX_LENGTH,
    allow_empty: bool = False,
    allow_multiline: bool = False,
) -> None:
    if not isinstance(value, str):
        raise ValidationError(field_name + " must be a string.")
    if not allow_empty and not value.strip():
        raise ValidationError(field_name + " must not be empty.")
    if len(value) > character_limit:
        raise ValidationError(
            "{} exceeds {} characters.".format(field_name, character_limit)
        )
    if "\x00" in value or (not allow_multiline and ("\n" in value or "\r" in value)):
        raise ValidationError(field_name + " contains unsupported control characters.")


def _validate_optional_text(value: Optional[str], field_name: str) -> None:
    if value is not None:
        _validate_text(value, field_name)


def _validate_calendar_date(value: str, field_name: str) -> None:
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        raise ValidationError(
            field_name + " must use YYYY-MM-DD or a supported Things keyword."
        )
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValidationError(
            field_name + " contains an invalid calendar date."
        ) from None


def _validate_reminder(value: str) -> None:
    if re.fullmatch(r"[0-9]{2}:[0-9]{2}", value) is None:
        raise ValidationError("Reminder time must use HH:MM in the local time zone.")
    try:
        time.fromisoformat(value)
    except ValueError:
        raise ValidationError("Reminder time is invalid.") from None


def _validate_schedule(value: Optional[str], field_name: str) -> None:
    if value is None:
        return
    _validate_text(value, field_name)
    day, reminder_separator, reminder = value.partition("@")
    keywords = START_KEYWORDS if field_name == "when" else DEADLINE_KEYWORDS
    if day not in keywords:
        _validate_calendar_date(day, field_name)
    if reminder_separator:
        if field_name != "when" or day in UNSCHEDULED_KEYWORDS:
            raise ValidationError("Reminders require a scheduled when value.")
        _validate_reminder(reminder)


def _validate_text_tuple(values: Tuple[str, ...], field_name: str) -> None:
    if not isinstance(values, tuple):
        raise ValidationError(field_name + " must be a tuple of strings.")
    for value in values:
        _validate_text(value, field_name)


@dataclass(frozen=True)
class Destination:
    """An existing project or area, optionally with an existing project heading."""

    name: Optional[str] = None
    identifier: Optional[str] = None
    heading: Optional[str] = None
    heading_identifier: Optional[str] = None

    def __post_init__(self) -> None:
        _validate_optional_text(self.name, "list")
        _validate_optional_text(self.identifier, "list_id")
        _validate_optional_text(self.heading, "heading")
        _validate_optional_text(self.heading_identifier, "heading_id")
        if self.identifier is not None:
            object.__setattr__(self, "name", None)
        if self.heading_identifier is not None:
            object.__setattr__(self, "heading", None)
        if (self.heading is not None or self.heading_identifier is not None) and (
            self.name is None and self.identifier is None
        ):
            raise ValidationError(
                "A heading requires an existing project in list or list_id."
            )


@dataclass(frozen=True)
class Task:
    """A task to create; transport and presentation options are separate concerns."""

    title: str
    notes: Optional[str] = None
    when: Optional[str] = None
    deadline: Optional[str] = None
    tags: Tuple[str, ...] = ()
    checklist_items: Tuple[str, ...] = ()
    destination: Destination = field(default_factory=Destination)

    def __post_init__(self) -> None:
        _validate_text(self.title, "title")
        if self.notes is not None:
            _validate_text(
                self.notes,
                "notes",
                character_limit=NOTES_MAX_LENGTH,
                allow_empty=True,
                allow_multiline=True,
            )
        _validate_schedule(self.when, "when")
        _validate_schedule(self.deadline, "deadline")
        _validate_text_tuple(self.tags, "tags")
        _validate_text_tuple(self.checklist_items, "checklist_items")
        if len(self.checklist_items) > CHECKLIST_MAX_ITEMS:
            raise ValidationError("A checklist supports at most 100 items.")
        if not isinstance(self.destination, Destination):
            raise ValidationError("destination must be a Destination.")
