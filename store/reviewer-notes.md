# Reviewer Notes

## Product scope

Things creates new to-dos in Things 3 through the Things URI scheme. It supports one task or a batch of up to 250 tasks, notes, start dates, local-time reminders, deadlines, existing tags, checklists, and existing project, area, or heading destinations. It can also prepare a preview URI without opening Things.

The plugin does not read, update, complete, or delete existing tasks. It does not create projects, areas, headings, or tags. It cannot enumerate the user's Things data. It has no recurring-task operation.

## Current runtime architecture

The repository currently contains a local stdio MCP server implemented in Python 3.9 or later with the standard library. The process runs on the user's Mac and hands a single `things:///json` URI to `/usr/bin/open`. Things must be installed on that Mac and Things URLs must be enabled.

This is not yet a public remote MCP service. Running the existing server in the cloud would break its core behavior because the cloud process cannot open Things on the user's Mac. The directory submission remains blocked until the publisher establishes a supported review and distribution architecture.

## Authentication and data handling

A Things authentication token is mandatory for creation and preview operations in the current product contract. The user obtains it from Things and configures it explicitly. By default it is stored outside the plugin at `~/.config/things-uri/config.json` with owner-only permissions and atomic writes. A `THINGS_AUTH_TOKEN` environment variable can override the file.

The token is used only in the private delivery URI. Tool responses, display URIs, status results, and expected errors omit it. `get_status` reports only whether a syntactically valid token is configured. The plugin has no operation that retrieves a stored token.

Under the current local architecture, task content is encoded in a URI and passed from the local MCP process to the installed Things application. The repository contains no analytics, advertising, telemetry, or hosted data service. These statements must be reassessed if a remote endpoint is introduced.

## Dispatch semantics

`status: dispatched` means that macOS accepted the request to open the URI. It does not prove that Things persisted the task, and no task identifier is returned. Creation results therefore always set `creation_verified` to `false`.

The assistant must not retry automatically after an error with an uncertain delivery outcome because a retry may create a duplicate. A preview returns `status: preview`, opens no application, and exposes only the token-free display URI.

## Tool-use boundaries

- `add_task` is for one user-authorized task creation request.
- `add_tasks` is for a user-authorized batch and validates the full batch before handoff.
- `preview_task` prepares one task without opening Things.
- `get_status` checks platform, application availability, and whether a token is configured.
- `configure_auth_token` stores a token only after the user asks to configure it.

Task titles, notes, checklists, tags, and destination names remain in the user's language. The assistant does not invent schedules, destinations, tags, or identifiers. Existing object identifiers take precedence over names.

## Limits and reviewer setup

Titles are limited to 4,000 characters, notes to 10,000 characters, checklists to 100 items, and a batch to 250 tasks. Reminders require a scheduled start value and cannot be attached to `anytime` or `someday`.

Local end-to-end review currently requires:

1. A Mac with a licensed Things 3 installation.
2. Things URLs enabled in Things settings.
3. A dedicated non-production Things authentication token configured outside the repository.
4. Python 3.9 or later.
5. The test commands and evaluation cases in this repository.

Do not place reviewer credentials in source control or submission text. The current local configuration tool accepts a token as a model-visible argument; it must be replaced by an OpenAI-approved secret channel or authentication flow in any public submission. Cultured Code authorization for the integration, public distribution, URI-scheme use, Things name, and copied application icon has not been documented. This package has not been submitted for review and has not been published.
