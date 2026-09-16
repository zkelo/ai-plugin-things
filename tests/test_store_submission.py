"""Checks for the review materials prepared for the public plugin directory."""

import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "store"
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

SERVER_SPEC = importlib.util.spec_from_file_location(
    "things_store_server", SCRIPTS / "server.py"
)
server = importlib.util.module_from_spec(SERVER_SPEC)
SERVER_SPEC.loader.exec_module(server)


def load_json(name: str) -> Dict[str, Any]:
    with (STORE / name).open(encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise TypeError(name + " must contain a JSON object")
    return value


class StoreSubmissionTests(unittest.TestCase):
    def test_listing_copy_respects_final_directory_limits(self) -> None:
        listing = load_json("listing.json")
        package = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(listing["status"], "draft_not_submitted")
        self.assertEqual(listing["version"], package["version"])
        self.assertEqual(listing["version"], server.SERVER_VERSION)
        self.assertLessEqual(len(listing["name"]), 30)
        self.assertNotIn("\n", listing["name"])
        self.assertLessEqual(len(listing["shortDescription"]), 30)
        self.assertNotIn("\n", listing["shortDescription"])
        self.assertLessEqual(len(listing["longDescription"]), 4_000)
        prompts = listing["starterPrompts"]
        self.assertGreater(len(prompts), 0)
        self.assertLessEqual(len(prompts), 3)
        self.assertEqual(len(prompts), len(set(prompts)))
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                self.assertLessEqual(len(prompt), 128)
                self.assertNotIn("\n", prompt)
                self.assertNotIn("@", prompt)

    def test_owner_supplied_submission_values_remain_explicitly_unresolved(self) -> None:
        listing = load_json("listing.json")
        self.assertEqual(
            listing["publisher"],
            {"verifiedIdentity": None, "developerName": None},
        )
        for field in (
            "websiteUrl",
            "supportUrl",
            "privacyPolicyUrl",
            "termsOfServiceUrl",
            "publicMcpUrl",
            "demoRecordingUrl",
            "countryAvailability",
        ):
            with self.subTest(field=field):
                self.assertIsNone(listing[field])

    def test_review_suite_has_exact_required_case_counts_and_shapes(self) -> None:
        cases = load_json("test-cases.json")["cases"]
        positives = [case for case in cases if case["kind"] == "positive"]
        negatives = [case for case in cases if case["kind"] == "negative"]
        self.assertEqual(len(positives), 5)
        self.assertEqual(len(negatives), 3)
        self.assertEqual(len(cases), 8)
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertTrue(case["input"].strip())
                self.assertIn("toolSelection", case["expected"])
                self.assertTrue(case["expected"]["behavior"])
                self.assertTrue(case["expected"]["nonDisclosure"])
                if case["kind"] == "positive":
                    self.assertIn("resultShape", case["expected"])
                    self.assertTrue(case["expected"]["resultShape"])
                else:
                    self.assertTrue(case["expected"]["why"].strip())

    def test_annotation_justifications_match_live_tool_metadata(self) -> None:
        live_tools = {item["name"]: item for item in server.tool_definitions()}
        review_tools = {
            item["name"]: item for item in load_json("tool-annotations.json")["tools"]
        }
        self.assertEqual(review_tools.keys(), live_tools.keys())
        for name, review_tool in review_tools.items():
            with self.subTest(tool=name):
                self.assertEqual(
                    review_tool["annotations"],
                    {
                        hint: live_tools[name]["annotations"][hint]
                        for hint in (
                            "readOnlyHint",
                            "openWorldHint",
                            "destructiveHint",
                        )
                    },
                )
                self.assertTrue(review_tool["justification"].strip())

    def test_public_pages_are_unpublished_drafts_with_owner_placeholders(self) -> None:
        page_names = ("privacy-policy.md", "terms-of-use.md", "support.md")
        combined = ""
        for name in page_names:
            with self.subTest(page=name):
                content = (STORE / "public-pages" / name).read_text(encoding="utf-8")
                self.assertIn('status: "DRAFT — DO NOT PUBLISH"', content)
                self.assertIn("Current local macOS/stdio architecture only", content)
                combined += content
        for placeholder in (
            "{{EFFECTIVE_DATE}}",
            "{{PUBLISHER_LEGAL_NAME}}",
            "{{PRIVACY_CONTACT_EMAIL}}",
            "{{SECURITY_CONTACT_EMAIL}}",
            "{{SUPPORT_EMAIL}}",
            "{{SUPPORT_URL}}",
            "{{PRIVACY_POLICY_URL}}",
            "{{GOVERNING_LAW}}",
            "{{THINGS_BRAND_AUTHORIZATION_REFERENCE}}",
        ):
            with self.subTest(placeholder=placeholder):
                self.assertIn(placeholder, combined)

    def test_plugin_authored_text_is_english_except_russian_readme(self) -> None:
        text_suffixes = {".md", ".json", ".py", ".yml", ".yaml"}
        for path in ROOT.rglob("*"):
            if (
                not path.is_file()
                or path.name == "README_ru.md"
                or ".git" in path.parts
                or "__pycache__" in path.parts
                or path.suffix not in text_suffixes
            ):
                continue
            with self.subTest(path=str(path.relative_to(ROOT))):
                content = path.read_text(encoding="utf-8")
                self.assertIsNone(re.search(r"[\u0400-\u04ff]", content))


if __name__ == "__main__":
    unittest.main()
