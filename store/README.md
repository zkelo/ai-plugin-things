# ChatGPT Plugin Directory Preparation

Status: **draft prepared; not submitted and not published**.

This directory contains the review materials prepared for a future Things plugin submission to the universal Plugins Directory used by ChatGPT and Codex:

- [`listing.json`](listing.json) contains listing copy, starter prompts, release notes, and unresolved owner-supplied fields.
- [`test-cases.json`](test-cases.json) contains exactly five positive and three negative reviewer cases.
- [`tool-annotations.json`](tool-annotations.json) records every required MCP annotation and its justification.
- [`reviewer-notes.md`](reviewer-notes.md) describes the current behavior, data flow, limits, and delivery semantics.
- [`submission-readiness.md`](submission-readiness.md) is the source-of-truth blocker checklist.
- [`public-pages/`](public-pages/) contains unpublished drafts for privacy, terms, and support.

The repository now uses the portable Agent Plugins layout with root `plugin.json` and `mcp.json`, while retaining compatibility manifests for local installations. The current MCP transport remains local stdio because the product hands a Things URI to the Things application on the same Mac. Do not replace this with a nominal HTTP wrapper: a remote process cannot perform that local handoff.

Before anyone opens a portal draft or requests review, resolve every unchecked item in [`submission-readiness.md`](submission-readiness.md). In particular, the final solution needs an OpenAI-supported local MCP route or a validated remote/client architecture, a reviewed credential channel, a verified publisher, public policy and support URLs, reviewer access, and documented Cultured Code authorization for the integration and its Things branding.

Current requirements were checked against:

- [Package your plugin](https://developers.openai.com/plugins/build/plugins)
- [Submit plugins](https://developers.openai.com/plugins/deploy/submission)
- [Plugin submission errors](https://developers.openai.com/plugins/deploy/submission-errors)
- [Plugin guidelines](https://developers.openai.com/plugins/app-guidelines)
- [Security and privacy](https://developers.openai.com/plugins/guides/security-privacy)

No OpenAI Platform submission, review request, domain verification, deployment, or directory publication has been performed.
