---
title: Terms of Use
status: "DRAFT — DO NOT PUBLISH"
architecture_scope: "Current local macOS/stdio architecture only"
effective_date: "{{EFFECTIVE_DATE}}"
publisher: "{{PUBLISHER_LEGAL_NAME}}"
support_contact: "{{SUPPORT_EMAIL}}"
governing_law: "{{GOVERNING_LAW}}"
publication_blockers:
  - "Confirm the final distribution and service architecture."
  - "Verify the publisher's legal identity, contact, and governing law."
  - "Set the effective date."
  - "Resolve Cultured Code authorization for the integration, public distribution, URI-scheme use, and Things brand assets."
---

# Terms of Use

> **Draft — do not publish.** These terms cover only the current local macOS version of the Plugin. They require review after the final distribution architecture, publisher identity, contact details, effective date, governing law, and Cultured Code authorization for the integration and its Things branding are resolved.

Effective date: **{{EFFECTIVE_DATE}}**  
Publisher: **{{PUBLISHER_LEGAL_NAME}}**  
Support contact: **{{SUPPORT_EMAIL}}**

## 1. About the Plugin

The Things plugin (the “Plugin”) is a local integration that prepares Things URI scheme requests and can hand them to the Things application installed on the same Mac. The current Plugin runs as a local stdio process. It does not operate a hosted task service or a Plugin-managed user account.

The Plugin is an independent integration. It is not affiliated with, endorsed by, or supported by Cultured Code unless a later written authorization expressly states otherwise. Things and related names, icons, and marks belong to their respective owners. The publisher must resolve **{{THINGS_BRAND_AUTHORIZATION_REFERENCE}}** for the integration, its public distribution, its use of the Things URI scheme, and its protected Things assets before submission.

## 2. Requirements

To use automatic delivery, you need a compatible Mac, an installed copy of Things, the Things URL feature enabled, Python 3.9 or later in the Plugin environment, and a Things authentication token. A displayed preview URI is for inspection only: it omits the mandatory authentication token and cannot create a task by itself.

You are responsible for obtaining and using Things and the authentication token lawfully, protecting the token, and following the terms that apply to Things, the conversational host, and your device.

## 3. How the Plugin works

You can ask the Plugin to prepare or send individual tasks and batches. Task content can include titles, notes, dates, reminders, tags, checklists, and existing Things destinations. The Plugin does not create projects or tags, enumerate existing destinations, create recurring tasks, or update existing tasks.

The authentication token is mandatory for creation and preview operations in the current Plugin. When saved through the Plugin, it is stored in a private local configuration file. The Plugin uses the token to build the private delivery URI and excludes it from the URI shown in results.

## 4. Confirmation and duplicate risk

A successful handoff means that macOS accepted the request to open a Things URI. It does not confirm that Things saved the task, and the Plugin does not receive a task identifier or acknowledgement from Things. The Plugin reports this limitation through `creation_verified: false`.

If delivery times out or has an uncertain result, inspect Things before retrying. A retry may create a duplicate. Things can also ignore unsupported or unknown values, including some tags, headings, or destinations.

## 5. Your responsibilities

You agree to:

- review task content and destination details before sending sensitive or consequential information;
- keep the Things token confidential and avoid placing it in task content, source control, logs, or support messages;
- use the Plugin only with accounts, devices, data, and software you are authorized to use;
- verify important tasks in Things, especially after an uncertain handoff; and
- comply with applicable laws and third-party terms.

You remain responsible for tasks and other content you provide through the Plugin and for decisions made from its output.

## 6. Privacy

The current Plugin processes task content and the Things token locally as described in the Privacy Policy at **{{PRIVACY_POLICY_URL}}**. The final public URL and policy must be available before publication.

## 7. Third-party services and software

Things, macOS, the conversational host, and any distribution platform are third-party products. Their availability, behavior, security, and policies are outside the Plugin publisher’s control. Changes to those products may affect the Plugin.

## 8. Availability and changes

The Plugin is provided as available. The publisher does not promise uninterrupted operation, permanent compatibility with third-party software, or successful creation of every task. Features may change to address security, compatibility, legal, or platform requirements. Material changes should be documented for users.

## 9. Warranty and responsibility limits

To the extent permitted by applicable law, the Plugin is provided without a promise that it will be error-free or suitable for every purpose. Nothing in these terms excludes rights or responsibilities that cannot lawfully be excluded. The final publisher should obtain appropriate legal review before setting any specific warranty disclaimer or liability limitation.

## 10. Suspension or termination

You may stop using and uninstall the Plugin at any time. The publisher may stop distributing a version that is insecure, incompatible, unlawful, or no longer supportable. Uninstalling the Plugin may not remove its separate local configuration; remove the saved token separately if desired.

## 11. Governing terms

These terms are intended to be governed by **{{GOVERNING_LAW}}**, subject to mandatory consumer protections and other applicable law. This section must be completed and reviewed before publication.

## 12. Contact

Questions about these terms or the Plugin may be sent to:

**{{PUBLISHER_LEGAL_NAME}}**  
**{{PUBLISHER_POSTAL_ADDRESS}}**  
**{{SUPPORT_EMAIL}}**  
**{{SUPPORT_URL}}**
