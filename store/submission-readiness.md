# ChatGPT Plugin Directory Submission Readiness

Status: **draft prepared; not submitted and not published**.

## Complete

- [x] The product name, English listing copy, category, capabilities, starter prompts, and release notes are drafted in `listing.json`.
- [x] Five positive and three negative evaluation cases are drafted in `test-cases.json`.
- [x] All five tools have review justifications for their read-only, open-world, and destructive annotations in `tool-annotations.json`.
- [x] Plugin-authored source, metadata, tool descriptions, and documentation use English; the Russian guide is isolated in `README_ru.md` and linked from `README.md`.
- [x] The plugin has explicit tools for one task, task batches, previews, status checks, and required key configuration.
- [x] The current implementation keeps the Things key out of returned URIs, tool responses, error messages, and repository content.
- [x] Task-creation tools are marked as writes and non-idempotent; preview and status tools are marked read-only.
- [x] Automated unit tests and the main-branch GitHub Actions workflow are present.
- [x] Reviewer-facing behavior and limitations are documented in `reviewer-notes.md`.
- [x] Draft source pages for privacy, terms, and support are prepared under `public-pages/` and explicitly marked as unpublished drafts for the current local architecture.

## Blocked before submission

- [ ] **Choose and implement a reviewable distribution architecture.** The current MCP server is local stdio software. It calls macOS `open` so that the Things URI is handled by Things on the same Mac. A cloud-hosted MCP server cannot perform that local handoff. A public directory submission therefore needs either a supported local-MCP review route or a separately reviewed design that safely transfers the user-approved URI action to the user's device.
- [ ] **Provide a stable public HTTPS MCP URL if the remote-MCP route is selected.** `publicMcpUrl` remains `null`; no public endpoint has been deployed.
- [ ] **Record the required demo.** `demoRecordingUrl` remains `null`; record the final reviewer flow only after the submission architecture and authentication are complete.
- [ ] **Verify the publisher identity and a controlled domain.** `Local developer` is local placeholder metadata in both plugin manifests; replace it with the exact verified publisher identity before submission. The listing identity remains unresolved, and no domain has been selected or verified.
- [ ] **Publish owner-approved legal and support pages.** Public website, support, privacy-policy, and terms-of-service URLs remain unresolved. The final privacy policy must match the architecture actually submitted, especially key storage and task-data handling.
- [ ] **Define reviewer access and authentication.** Document a review environment with a licensed Things 3 installation, Things URLs enabled, and a non-production test key. Never add a real key to the repository, listing, test cases, or reviewer notes. The current local `configure_auth_token` tool accepts the key as a model-visible argument and is not an acceptable public remote authentication flow; use an OpenAI-approved local secret channel, OAuth or another reviewed credential mechanism in the submitted architecture.
- [ ] **Obtain and record third-party authorization.** Written Cultured Code authorization is unresolved for the integration itself, its public distribution, and the Things name. The plugin uses an original icon representing different quantities of tasks, without borrowing the Things application icon. Confirm that the intended use of the Things URI scheme complies with Cultured Code's terms. The listing must not imply that this is an official Cultured Code product unless that claim is authorized.
- [ ] **Finalize country availability.** `countryAvailability` remains `null` pending the publisher's distribution decision and any legal or product restrictions.
- [ ] **Produce final store assets.** Confirm the icon and logo dimensions and formats against the submission portal, and use only assets covered by documented permission. The current plugin has no custom UI, so do not submit screenshots unless the final reviewed server adds UI; OpenAI allows screenshots only for plugins whose scan reports a UI output template.
- [ ] **Run end-to-end review tests in the final architecture.** Re-run all positive and negative cases through the same endpoint and authentication flow that reviewers will use, and record the results without secrets.
- [ ] **Complete security and privacy review.** Validate credential lifecycle, deletion, encryption, logging, retention, incident contact, rate limits, and data-flow disclosures for the final hosted or local distribution model.

## Publication guardrail

Do not create a portal submission, request review, or publish this plugin until every blocked item above has an owner-approved resolution. Preparing or committing these files does not constitute submission or publication.
