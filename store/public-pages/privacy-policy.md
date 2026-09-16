---
title: Privacy Policy
status: "DRAFT — DO NOT PUBLISH"
architecture_scope: "Current local macOS/stdio architecture only"
effective_date: "{{EFFECTIVE_DATE}}"
publisher: "{{PUBLISHER_LEGAL_NAME}}"
privacy_contact: "{{PRIVACY_CONTACT_EMAIL}}"
publication_blockers:
  - "Confirm the final distribution and data-flow architecture."
  - "Verify the publisher's legal identity and privacy contact."
  - "Set the effective date."
  - "Resolve Cultured Code authorization for the integration, public distribution, URI-scheme use, and Things brand assets."
---

# Privacy Policy

> **Draft — do not publish.** This policy describes only the current local macOS version of the plugin. It must be reviewed and updated if the plugin gains a hosted service, remote MCP server, analytics, account system, or any other change to its data flow. The publisher identity, contact details, effective date, final distribution architecture, and Cultured Code authorization for the integration and its Things branding must be resolved before publication.

Effective date: **{{EFFECTIVE_DATE}}**  
Publisher: **{{PUBLISHER_LEGAL_NAME}}**  
Privacy contact: **{{PRIVACY_CONTACT_EMAIL}}**

## Scope

This policy applies to the current local Things plugin for macOS (the “Plugin”). The Plugin runs as a local stdio process and prepares Things URI scheme requests for the Things application installed on the same Mac. It does not currently operate a hosted service or maintain a remote user account.

The Plugin is an independent integration. It is not affiliated with, endorsed by, or supported by Cultured Code unless a later written authorization expressly states otherwise. Things and related marks belong to their respective owners.

## Information the Plugin handles

The Plugin handles the following information when you use it:

- **Things authentication token.** You must provide a Things token before creating or previewing tasks. You can configure it through the Plugin or supply it through the `THINGS_AUTH_TOKEN` environment variable.
- **Task content.** This can include task titles, notes, dates, reminders, tags, checklist items, project or area names and identifiers, headings, and options such as whether to reveal a created task.
- **Local operational information.** The Plugin can check the operating system, whether the Things application is available, and whether a token with a valid local format is configured. It does not verify that the token is authentic.

Do not include information in a task that you do not want processed by the conversational host and the Things application.

## How information is used

The Plugin uses the authentication token and task content only to prepare a Things URI and, when you request delivery, hand that URI to the locally installed Things application through macOS `/usr/bin/open`.

If you provide the token or task content through a conversational interface, that host processes the information before passing the tool request to the local Plugin. The host’s privacy policy and account settings apply to that processing. Supplying the token through the local `THINGS_AUTH_TOKEN` environment variable avoids entering it in a conversation.

The authenticated delivery URI contains the token and task content. The Plugin passes that URI to Things as a single local process argument. The separate URI shown in Plugin results omits the token, but it can contain the task content. A preview prepares this redacted URI and does not open Things.

The Plugin returns operational results such as whether a request was prepared or handed off, whether the app appears to be available, and whether a token is configured. It does not return the token in normal responses, displayed URIs, or error messages.

## Local storage and retention

When configured through the Plugin, the token is stored on the local Mac in `~/.config/things-uri/config.json`. The Plugin creates the file with `0600` permissions and uses an atomic replacement when saving changes. The token remains there until it is replaced or the local configuration is removed.

When `THINGS_AUTH_TOKEN` is set, the Plugin reads the token from the local process environment and does not replace it through the configuration tool.

The Plugin does not maintain its own task database and does not intentionally retain task content after processing a request. The conversational host, operating system, Things application, backups, or diagnostic systems outside the Plugin may process or retain information under their own settings and policies.

To remove a token saved by the current Plugin, remove the `auth_token` value or the local configuration file. Back up any unrelated settings in that file before deleting it. Removing the Plugin does not necessarily remove its separate local configuration.

## Network access, telemetry, and sharing

The current Plugin code does not send information to a Plugin-operated server, and it does not include analytics, advertising, or telemetry. It does not sell personal information.

Task content and the authenticated URI are handed locally to Things when you request delivery. The Plugin does not control how Things, the conversational host, macOS, device backups, or other software process information. Their own terms and privacy policies apply.

If the distribution architecture later includes a remote server or any additional recipient, this policy must be revised before that version is released.

## Security

The Plugin separates the private delivery URI from the displayed URI, redacts the token from Plugin responses and error messages, avoids placing the token in the Plugin archive, and restricts the saved configuration file to the local user account. The private delivery URI is still passed to macOS as a process argument, so operating-system diagnostics or another local process with sufficient access may be able to observe it briefly. Files and processes running under the same local account may also be able to read the saved configuration. These measures reduce accidental exposure but cannot guarantee absolute security.

Keep the token confidential. Do not paste it into task titles or notes, commit it to source control, or share it in support requests. Protect access to the Mac and to any host conversation that contains sensitive task content.

## Delivery status and data accuracy

A `dispatched` result means only that macOS accepted the request to open the URI. macOS does not return a Things task identifier or confirmation that Things saved the task. The Plugin therefore reports `creation_verified: false`. After a timeout or uncertain result, check Things before retrying to avoid duplicate tasks.

## Your choices and requests

You can preview a task without opening Things, choose what task content to provide, replace or remove the locally stored token, and stop using the Plugin. Depending on applicable law, you may also have rights concerning information handled by the publisher. Contact **{{PRIVACY_CONTACT_EMAIL}}** to make a privacy request after this address has been verified.

## Changes to this policy

Material changes to the Plugin’s data flow require an updated policy and effective date. The current version of the policy should be made available at **{{PRIVACY_POLICY_URL}}** before publication.

## Contact

Questions about this policy may be sent to:

**{{PUBLISHER_LEGAL_NAME}}**  
**{{PUBLISHER_POSTAL_ADDRESS}}**  
**{{PRIVACY_CONTACT_EMAIL}}**
