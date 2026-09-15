# Things

[Russian documentation](README_ru.md)

A local Codex plugin for sending tasks to **Things 3 on macOS** through the [official Things URI scheme](https://culturedcode.com/things/support/articles/2803573/). **A Things authentication token is required to use this plugin.** The code uses Python 3.9+ and the standard library. The icon comes from the installed Things application. Task titles and notes support Unicode, emoji, and links.

## Getting started

If the plugin is registered in your personal plugin marketplace, open its card in Codex and select **Install**. Alternatively, use `codex plugin add things@personal`.

After installation, start a new task in Codex to make the plugin tools available. In Things, enable **Things → Settings → General → Enable Things URLs**. Things may also prompt you to enable this setting when you first use a Things URL.

## Required Things authentication token

Copy the token from **Things → Settings → General → Enable Things URLs → Manage**. In a new Codex task, ask to configure your Things token and provide it: the plugin uses the `configure_auth_token` tool. It saves the token locally and returns only a configuration confirmation. You can then send tasks using ordinary requests.

Adding individual tasks, adding batches, and previewing tasks are blocked until a token is configured. `get_status` reports `auth_token_configured: true/false` without exposing the token. This checks whether a token is present and has a valid format; a successful macOS `open` response does not verify the token's authenticity or confirm that tasks were saved.

The token is stored separately from the plugin in `~/.config/things-uri/config.json`; the file is created with `0600` permissions. Writes are atomic, and a token change takes effect on the next request without restarting the server. The token is excluded from responses, displayed URIs, error messages, and the plugin archive.

For terminal launches, you can use `THINGS_AUTH_TOKEN`, which takes priority over the saved configuration. While this environment variable is set, attempts to change the token through the plugin are rejected with an explanation. `THINGS_URI_CONFIG_FILE` lets you choose another location for the local configuration.

Configure the token through the CLI using hidden input:

```sh
python3 scripts/things_uri.py configure-auth-token
```

Example requests:

- "Add to Things: buy milk tomorrow."
- "Add a task to send the report in the Work project, start tomorrow, with a deadline on Friday."
- "Send the tasks from this list to Things."
- "Add a task to prepare the release with a checklist: check the build, update the documentation."
- "Show the URI for a task to call the doctor tomorrow at 10:00, without sending it."

## Tools

| Tool | Purpose |
| --- | --- |
| `add_task` | Send one task; `preview: true` only prepares its URI |
| `add_tasks` | Send a batch of tasks with individual settings; supports `preview` and `reveal` |
| `preview_task` | Prepare one task's URI without launching Things |
| `get_status` | Check macOS, Things availability, and token configuration without creating tasks |
| `configure_auth_token` | Save the required Things token in the local configuration |

A task accepts `title` and the optional fields `notes`, `when`, `deadline`, `tags` (an array), `checklist_items` (an array), `list` / `list_id`, and `heading` / `heading_id`. `reveal` shows the added task. Previewing lets you check its contents before sending it.

`when` sets the start date: `today`, `tomorrow`, `evening`, `anytime`, `someday`, or `YYYY-MM-DD`. Set a reminder using `YYYY-MM-DD@HH:MM` or `tomorrow@HH:MM` in the local time zone. Reminders are unavailable for `anytime` and `someday`. `deadline` is a separate due date: `YYYY-MM-DD`, `today`, or `tomorrow`. Codex converts natural-language dates into these formats before calling the tool.

Without a date or destination project, the task goes to the Inbox. Projects, areas, headings, and tags must already exist in Things. An identifier takes priority over a name. Things may ignore unknown tags and headings. The plugin does not create recurring tasks, new projects, or tags, and it does not update existing tasks.

## Sending tasks and checking the result

Individual tasks and batches use `things:///json` with `create` operations and an `auth-token` parameter. Values are percent-encoded, then the complete URI is passed to Things as one argument to macOS `open`, without executing task contents in a shell. The displayed URI includes task contents and excludes the token; the URI used for delivery is kept separately and is never returned in responses. Quick Entry is unavailable for this command, so use a preview to inspect a task before sending it.

A successful handoff returns `status: dispatched`; **this does not confirm that the tasks were saved**. macOS `open` does not return a task ID or an acknowledgement from Things, and `creation_verified` is always `false`. After a timeout, check Things before retrying to avoid duplicates. A preview returns `status: preview` and sends nothing. Checking whether the application exists does not determine whether its URI scheme is enabled.

Titles are limited to 4,000 characters, notes to 10,000 characters, and checklists to 100 items. A batch is limited to 250 tasks. Things documents a limit of 250 items every 10 seconds; split larger lists into batches and wait between them. Commas in tag names are supported.

## Running without MCP

From the plugin root, pass JSON through standard input:

```sh
python3 scripts/things_uri.py add-task --preview <<'JSON'
{"title":"Buy milk 🥛","when":"tomorrow","checklist_items":["Milk","Bread"]}
JSON
```

Remove `--preview` to send the task. For a batch, use `add-tasks` with a JSON array of tasks. Check application availability with `python3 scripts/things_uri.py status`.

If Python is unavailable in the Codex environment, set `THINGS_PYTHON` to the absolute path of a Python 3.9+ executable in the application's launch environment. On an iPhone or iPad, you can open a prepared `things:///` URI manually; automatic delivery through this plugin works on a Mac.

## Architecture and verification

The code follows Clean Architecture principles:

| Layer | Files | Responsibility |
| --- | --- | --- |
| Domain | `scripts/things_plugin/domain.py` | Immutable tasks and destinations, data invariants |
| Application | `scripts/things_plugin/application.py` | Delivery and preview use cases, typed results, dependency ports |
| Infrastructure | `scripts/things_plugin/infrastructure/` | Things URI encoding, macOS delivery, application lookup, token storage |
| Adapters | `scripts/things_plugin/payloads.py`, `scripts/things_uri.py`, `scripts/server.py` | JSON conversion, CLI, and the MCP protocol |
| Composition | `scripts/things_plugin/composition.py` | Wiring concrete adapters into the application |

The domain does not import protocols, the URI encoder, or macOS integrations. The application depends on four `Protocol` ports: URI encoding, delivery, application lookup, and token storage; concrete implementations are supplied externally. The token is not part of the task domain model. `PreparedUri` separates the private delivery URI from the preview URI that omits the token. The encoder checks transport limits imposed by the Things command. Delivery starts only after the entire request has been prepared; errors with an uncertain delivery outcome carry a separate `delivery_unknown` flag. A task's state cannot change after construction.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Tests cover URI encoding and structure, validation, delivery errors, and the MCP protocol. Task-creation calls are replaced with test doubles, so the tests do not add tasks to Things.
