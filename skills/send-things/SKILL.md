---
name: send-things
description: "Create and send tasks to Things 3 via its URI scheme on macOS. Use when the user asks to add a task, capture a list of tasks, or prepare a Things URI, including requests in languages other than English."
---

# Send tasks to Things

English is the default language for plugin-authored instructions and responses. Preserve user-provided task titles, notes, tags, checklists, and destination names in their original language unless the user requests translation.

Use the plugin's `add_task` / `add_tasks` tools to dispatch the user's requested tasks. An explicit request to add or send tasks authorizes dispatch; proceed without an extra confirmation. A request to draft or preview a URI uses `preview_task` or `preview: true`. A request to configure or inspect this plugin does not itself request task creation.

The Things key is mandatory for creation and previews in this plugin. Use `get_status` to check `auth_token_configured` when setup is uncertain. If absent, ask the user to obtain the key from **Things → Settings → General → Enable Things URLs → Manage**. When the user supplies a key and asks to configure it, call `configure_auth_token`; never repeat the key in responses, put it in task data, or save it in the plugin source. It is stored separately in a private local configuration. A nonempty `THINGS_AUTH_TOKEN` environment variable takes precedence and prevents local changes; explain the returned configuration error. Configuring a key does not itself create tasks.

Keep each task's title, notes, checklist and destination faithful to the request. Place context and source links in `notes`. Do not infer extra deadlines, tags, reminders or destinations. Unscheduled tasks without a project go to the inbox. Ask only for information whose ambiguity would materially change the requested task; the tool requires a nonempty title.

- `when` is the start date, `deadline` is a separate hard due date. Resolve relative dates in the user's language using the current local date and use `YYYY-MM-DD`, `today` or `tomorrow`; `when` also accepts `evening`, `anytime`, `someday`. Resolve weekdays to calendar dates. Reminders use `YYYY-MM-DD@HH:MM` or `tomorrow@HH:MM` in the Mac's local time zone; reminders on `anytime` or `someday` are unsupported.
- Pass `tags` and `checklist_items` as arrays of strings. Tags must already exist; a checklist has at most 100 entries. Use `list` / `list_id` for an existing project or area, and `heading` / `heading_id` inside that project. IDs take precedence over names. A supplied `things:///show?id=...` destination link contains the destination ID. Do not invent IDs or claim that this plugin can enumerate existing destinations.
- One task uses `add_task`; a list of tasks uses `add_tasks` with each task's own parameters. Each batch supports at most 250 tasks. When a larger user-authorized list requires several dispatches, leave at least 10 seconds between batches to respect Things' documented limit. Validate all batches using preview before the first dispatch; stop on a dispatch error and report which batches were already handed off.
- `reveal: true` asks Things to display the added task. Use preview to review a task before sending; authenticated JSON commands do not support Quick Entry.

Report the observed result accurately. `dispatched` means “Sent to Things”; `creation_verified: false` means persistence and IDs are unverified. `preview` means nothing was sent; its URI deliberately omits the key. Only dispatch through the plugin, so that the key is attached to the transport URI. Do not automatically retry failed or uncertain dispatches: check with the user or inspect Things using an available authorized UI tool first, because a retry can create duplicates.

If dispatch fails, use `get_status` to check macOS and app availability. `uri_scheme_enabled: unknown` does not mean disabled. Things may require **Settings → General → Enable Things URLs**, especially on first use. Explain the specific blocker and provide the prepared URI when useful. On non-macOS systems use preview and let the user open the URI on a device with Things.

If MCP tools are unavailable, the same helper is at `../../scripts/things_uri.py`, relative to this skill directory. Run `python3 <absolute-helper-path> add-task` with a task JSON object on stdin, or `add-tasks` with an array; add `--preview` for draft-only requests. Use a literal quoted heredoc or a JSON file, and pass the helper path as a quoted argument. Never interpolate task text into executable shell syntax or build percent encoding by hand. The helper's `status` command performs an app availability check. See [the plugin README](../../README.md) for field limits and installation troubleshooting.

The helper's `configure-auth-token` command reads the key from a terminal prompt or stdin. Do not pass credentials on its command line. Its status and error output never include the key.
