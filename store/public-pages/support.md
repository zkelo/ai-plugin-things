---
title: Support
status: "DRAFT — DO NOT PUBLISH"
architecture_scope: "Current local macOS/stdio architecture only"
effective_date: "{{EFFECTIVE_DATE}}"
publisher: "{{PUBLISHER_LEGAL_NAME}}"
support_email: "{{SUPPORT_EMAIL}}"
support_url: "{{SUPPORT_URL}}"
security_contact: "{{SECURITY_CONTACT_EMAIL}}"
publication_blockers:
  - "Confirm the final distribution and support architecture."
  - "Verify the publisher and support contacts."
  - "Set the effective date."
  - "Set an owner-approved support policy."
  - "Resolve Cultured Code authorization for the integration, public distribution, URI-scheme use, and Things brand assets."
---

# Support for the Things Plugin

> **Draft — do not publish.** This page documents the current local macOS version. The publisher identity, support contacts, support policy, effective date, final distribution architecture, and Cultured Code authorization for the integration and its Things branding must be resolved before publication.

Effective date: **{{EFFECTIVE_DATE}}**  
Support email: **{{SUPPORT_EMAIL}}**  
Support site: **{{SUPPORT_URL}}**  
Security contact: **{{SECURITY_CONTACT_EMAIL}}**

## About this integration

The Plugin is an independent integration that sends local Things URI scheme requests to the Things application on macOS. It is not affiliated with, endorsed by, or supported by Cultured Code unless a later written authorization expressly states otherwise. For questions about the Things application itself, use Cultured Code’s official support channels.

## Before requesting support

Confirm the following:

1. You are using macOS with Things installed.
2. **Things → Settings → General → Enable Things URLs** is enabled.
3. The Plugin reports `auth_token_configured: true` through `get_status`.
4. The Plugin environment can run Python 3.9 or later.
5. You have restarted the conversation after installing or updating the Plugin so that its tools are available.

Do not send your Things authentication token in a support request. The support team should never ask you to include it in an email, screenshot, task, log excerpt, issue, or chat message.

## Common issues

### A token is required

The current Plugin requires a Things authentication token for both previews and task creation. Obtain it from **Things → Settings → General → Enable Things URLs → Manage**, then ask the Plugin to configure it. The token is saved locally in `~/.config/things-uri/config.json` unless `THINGS_AUTH_TOKEN` is supplied through the process environment.

If the environment variable is set, it takes priority and the Plugin will reject attempts to replace it through the configuration tool. Update the launch environment instead.

### Things does not open

Run `get_status` and check the reported platform and application availability. Automatic delivery requires macOS and a local Things installation. App detection does not confirm that the Things URI scheme is enabled, so check the setting in Things even when the app is found.

A preview URI cannot be used as a manual creation fallback because it deliberately omits the mandatory authentication token. The current Plugin's automatic handoff requires Things on the same Mac.

### The Plugin says `dispatched`, but no task appears

`dispatched` means only that macOS accepted the URI handoff. macOS does not return a Things task identifier or acknowledgement, so the Plugin cannot verify persistence and reports `creation_verified: false`.

Check Things, including the Inbox and intended destination. Confirm that the URL feature is enabled and that referenced projects, areas, headings, and tags already exist. Things may ignore unknown tags or headings.

### Delivery timed out or the result is uncertain

Inspect Things before retrying. The first request may have succeeded even when the Plugin could not determine the outcome, and retrying can create duplicates.

### A task has the wrong date or destination

Check that dates use a supported value or format. Start dates accept `today`, `tomorrow`, `evening`, `anytime`, `someday`, `YYYY-MM-DD`, or a supported reminder form such as `YYYY-MM-DD@HH:MM`. Deadlines accept `today`, `tomorrow`, or `YYYY-MM-DD`.

Projects, areas, headings, and tags must already exist. Identifiers take priority over names. Use a preview to inspect task content before sending it.

## Information to include

Include only non-sensitive details that help reproduce the issue:

- Plugin version;
- macOS version;
- Things version;
- Python version;
- the operation used, such as preview, single-task delivery, batch delivery, status, or token configuration;
- the redacted result or exact error text; and
- minimal sample task data with private content removed.

State only whether a token is configured. Never include the token itself or an authenticated Things URI. A displayed preview URI excludes the token but can still contain task content, so redact private content before sharing it.

## Privacy and security reports

Privacy questions: **{{PRIVACY_CONTACT_EMAIL}}**  
Security reports: **{{SECURITY_CONTACT_EMAIL}}**

For a security report, describe the impact and reproduction steps without including live credentials or private task content. The publisher must define an owner-approved response and disclosure process before this page is published.

## Support scope

Support can cover installation, local configuration, supported task fields, URI preparation, and handoff behavior in the current Plugin. It cannot confirm whether Cultured Code received a request, recover tasks from Things, manage a Things account, or provide official support for Things, macOS, Python, or the conversational host.

The final support channel and any expected response times must be approved by **{{PUBLISHER_LEGAL_NAME}}** before publication.
