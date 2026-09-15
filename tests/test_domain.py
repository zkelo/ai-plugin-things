"""Domain invariants do not require Things, JSON or a URI encoder."""

import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from things_plugin.domain import Destination, Task, ValidationError


class TaskTests(unittest.TestCase):
    def test_tasks_and_nested_destination_are_immutable(self):
        task = Task("Release", destination=Destination(name="Work"))
        with self.assertRaises(FrozenInstanceError):
            task.title = "Changed"
        with self.assertRaises(FrozenInstanceError):
            task.destination.name = "Changed"
        self.assertIsInstance(task.tags, tuple)
        self.assertIsInstance(task.checklist_items, tuple)
        self.assertEqual(Task("Release"), Task("Release"))

    def test_domain_retains_text_and_accepts_multiline_or_empty_notes(self):
        title = " Купить 🥛 & кофе + 50% # ? `whoami` $(id) "
        notes = "Строка 1\nСтрока 2\r\nhttps://example.com/?a=1&b=2"
        task = Task(title, notes=notes)
        self.assertEqual(task.title, title)
        self.assertEqual(task.notes, notes)
        self.assertEqual(Task("x", notes="").notes, "")

    def test_text_requires_real_strings_and_nonempty_content(self):
        for title in (
            None,
            True,
            4,
            {},
            [],
            "",
            " \t",
            "two\nrows",
            "two\rrows",
            "NUL\x00",
        ):
            with self.subTest(title=title), self.assertRaises(ValidationError):
                Task(title)
        for notes in (False, {}, "NUL\x00"):
            with self.subTest(notes=notes), self.assertRaises(ValidationError):
                Task("x", notes=notes)

    def test_collections_require_immutable_tuples_of_valid_strings(self):
        for field_name in ("tags", "checklist_items"):
            for values in (
                [],
                ["valid"],
                "valid",
                None,
                (False,),
                ({},),
                (" ",),
                ("two\nrows",),
                ("NUL\x00",),
            ):
                with (
                    self.subTest(field=field_name, values=values),
                    self.assertRaises(ValidationError),
                ):
                    Task("x", **{field_name: values})

    def test_exact_text_and_checklist_limits(self):
        Task(
            "x" * 4000,
            notes="x" * 10000,
            tags=("x" * 4000,),
            checklist_items=("x",) * 100,
        )
        invalid = (
            {"title": "x" * 4001},
            {"title": "x", "notes": "x" * 10001},
            {"title": "x", "tags": ("x" * 4001,)},
            {"title": "x", "checklist_items": ("x" * 4001,)},
            {"title": "x", "checklist_items": ("x",) * 101},
        )
        for arguments in invalid:
            with (
                self.subTest(fields=tuple(arguments)),
                self.assertRaises(ValidationError),
            ):
                Task(**arguments)

    def test_transport_limits_do_not_restrict_domain_data(self):
        task = Task(
            "x",
            tags=("One,Two", "x" * 3000, "y" * 3000),
            checklist_items=("x" * 2000,) * 2,
        )
        self.assertEqual(task.tags[0], "One,Two")
        self.assertEqual(len(task.checklist_items), 2)

    def test_supported_schedule_keywords_dates_and_local_reminders(self):
        for when in (
            "today",
            "tomorrow",
            "evening",
            "anytime",
            "someday",
            "2028-02-29",
            "0001-01-01",
            "9999-12-31",
            "today@00:00",
            "tomorrow@23:59",
            "evening@18:00",
            "2028-02-29@10:30",
        ):
            with self.subTest(when=when):
                self.assertEqual(Task("x", when=when).when, when)
        for deadline in ("today", "tomorrow", "2028-02-29"):
            with self.subTest(deadline=deadline):
                self.assertEqual(Task("x", deadline=deadline).deadline, deadline)

    def test_invalid_schedule_values_and_calendar_dates(self):
        invalid_dates = (
            True,
            {},
            "",
            "2026-02-29",
            "2026-02-30",
            "2026-13-01",
            "0000-01-01",
            "2026-9-15",
            "20260915",
            "завтра",
            " today",
            "today\n",
        )
        for field_name in ("when", "deadline"):
            for value in invalid_dates:
                with (
                    self.subTest(field=field_name, value=value),
                    self.assertRaises(ValidationError),
                ):
                    Task("x", **{field_name: value})

    def test_invalid_reminders_and_deadline_keywords(self):
        for when in (
            "anytime@10:00",
            "someday@10:00",
            "today@",
            "today@9:00",
            "today@25:00",
            "today@12:60",
            "today@12:00:01",
            "today@12:00Z",
            "today@12:00@13:00",
        ):
            with self.subTest(when=when), self.assertRaises(ValidationError):
                Task("x", when=when)
        for deadline in (
            "evening",
            "anytime",
            "someday",
            "today@10:00",
            "2028-02-29@10:00",
        ):
            with self.subTest(deadline=deadline), self.assertRaises(ValidationError):
                Task("x", deadline=deadline)

    def test_destination_must_be_domain_data(self):
        for destination in (None, False, {}, "Work"):
            with (
                self.subTest(destination=destination),
                self.assertRaises(ValidationError),
            ):
                Task("x", destination=destination)


class DestinationTests(unittest.TestCase):
    def test_ids_take_precedence_over_names(self):
        destination = Destination(
            "Ignored name", "project-id", "Ignored heading", "heading-id"
        )
        self.assertEqual(
            destination,
            Destination(identifier="project-id", heading_identifier="heading-id"),
        )
        self.assertIsNone(destination.name)
        self.assertIsNone(destination.heading)

    def test_heading_requires_project_destination(self):
        self.assertEqual(Destination(name="Work", heading="Next").heading, "Next")
        self.assertEqual(
            Destination(
                identifier="work", heading_identifier="next"
            ).heading_identifier,
            "next",
        )
        for arguments in ({"heading": "Next"}, {"heading_identifier": "next"}):
            with self.subTest(arguments=arguments), self.assertRaises(ValidationError):
                Destination(**arguments)

    def test_each_supplied_destination_field_is_validated_before_id_precedence(self):
        for field_name in ("name", "identifier", "heading", "heading_identifier"):
            for value in (
                True,
                {},
                "",
                " ",
                "two\nrows",
                "two\rrows",
                "NUL\x00",
                "x" * 4001,
            ):
                arguments = {
                    "identifier": "project-id",
                    "heading_identifier": "heading-id",
                    field_name: value,
                }
                with (
                    self.subTest(field=field_name, value=str(value)[:20]),
                    self.assertRaises(ValidationError),
                ):
                    Destination(**arguments)


if __name__ == "__main__":
    unittest.main()
