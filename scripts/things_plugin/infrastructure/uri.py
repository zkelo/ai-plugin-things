"""Translate task values into the documented Things URI contract."""

import json
from typing import Dict, Sequence
from urllib.parse import quote, urlencode

from ..application import AuthToken, PreparedUri, TaskOptions
from ..domain import Task, ValidationError
from ..uri_contract import MAX_TASKS


class ThingsUriBuilder:
    def build_task(
        self, task: Task, options: TaskOptions, token: AuthToken
    ) -> PreparedUri:
        if options.show_quick_entry:
            raise ValidationError(
                "Quick Entry is not supported by authenticated Things JSON commands; use preview instead."
            )
        return self.build_tasks((task,), options.reveal, token)

    def build_tasks(
        self, tasks: Sequence[Task], reveal: bool, token: AuthToken
    ) -> PreparedUri:
        if not 1 <= len(tasks) <= MAX_TASKS:
            raise ValidationError(
                f"tasks must be a nonempty array of at most {MAX_TASKS} tasks."
            )
        objects = [self._task_object(task) for task in tasks]
        parameters = {
            "data": json.dumps(objects, ensure_ascii=False, separators=(",", ":"))
        }
        if reveal:
            parameters["reveal"] = "true"
        display_uri = self._encode("json", parameters)
        authenticated_parameters = dict(parameters, **{"auth-token": token.value})
        return PreparedUri(
            uri=self._encode("json", authenticated_parameters), display_uri=display_uri
        )

    def _task_object(self, task: Task) -> Dict[str, object]:
        attributes: Dict[str, object] = {"title": task.title}
        text_fields: Dict[str, str] = {}
        self._add_text_fields(task, text_fields)
        attributes.update(text_fields)
        if task.tags:
            attributes["tags"] = list(task.tags)
        if task.checklist_items:
            attributes["checklist-items"] = [
                {"type": "checklist-item", "attributes": {"title": item}}
                for item in task.checklist_items
            ]
        return {"type": "to-do", "operation": "create", "attributes": attributes}

    @staticmethod
    def _add_text_fields(task: Task, parameters: Dict[str, str]) -> None:
        destination = task.destination
        fields = (
            ("notes", task.notes),
            ("when", task.when),
            ("deadline", task.deadline),
            ("list", destination.name),
            ("list-id", destination.identifier),
            ("heading", destination.heading),
            ("heading-id", destination.heading_identifier),
        )
        for name, value in fields:
            if value is not None:
                parameters[name] = value

    @staticmethod
    def _encode(command: str, parameters: Dict[str, str]) -> str:
        query = urlencode(parameters, quote_via=quote, safe="")
        return f"things:///{command}?{query}"
