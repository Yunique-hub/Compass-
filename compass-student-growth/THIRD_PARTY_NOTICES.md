# Third-Party Notices

Compass 2.0 incorporates or adapts material from the upstream projects listed below. The exact source revisions are pinned in `reference/open_source/upstream-lock.json`. Upstream source snapshots are kept under `vendor/`; Compass-specific code is kept outside those directories.

No upstream copyright header is intentionally removed. Copies of discovered license files are stored under `licenses/`. A project-specific authorization note is provided when an upstream repository did not contain a `LICENSE`, `NOTICE`, or `COPYING` file at the pinned revision.

## final-review

- Repository: https://github.com/lucianwhy/final-review
- Branch: `master`
- Commit: `622df4d7334508ed844b5312b8f0ad648b725ccd`
- Upstream license files discovered: none
- Authorization record: `licenses/final-review/AUTHORIZATION.md`
- Compass integration: Review Brain source-priority, Markdown-cleaning, question-generation, answer-separation, scoring-keyword, and mistake-review rules are adapted into executable and tested Compass modules. The original Skill and Agent documents remain in `vendor/final-review/`.

Usage authorized separately by project owner/user authorization. No OSI license is inferred by Compass.

## Neo4j Agent Memory

- Repository: https://github.com/neo4j-labs/agent-memory
- Branch: `main`
- Commit: `ac86a8ff01354e6b9c4d1b17089fba89d42dcf2b`
- Upstream package version: `neo4j-agent-memory` 0.5.0
- License: Apache License 2.0
- License copies: `licenses/agent-memory/LICENSE`, `licenses/agent-memory/typescript-LICENSE`, `licenses/agent-memory/vercel-ai-provider-LICENSE`
- Compass integration: the Full Mode adapter uses the upstream async `MemoryClient` surface when configured and reachable. Competition Mode supplies isolated SQLite and JSON stores with the same Compass-facing contract. Compass stores decision summaries, evidence, outcomes, and reusable experience only; it does not store hidden chain-of-thought.

## Self Improving Agent

- Repository: https://github.com/pskoett/self-improving-agent
- Branch: `master`
- Commit: `b889ef0724c27b7181111b8dd1ac3a108d0b5160`
- Upstream Skill version: 4.0.2
- Upstream license files discovered: none
- Authorization record: `licenses/self-improving-agent/AUTHORIZATION.md`
- Compass integration: `LEARNINGS`, `ERRORS`, and `FEATURE_REQUESTS` concepts, stable `Pattern-Key`, recurrence counting, deduplication, and promotion are adapted into student-growth JSONL events. Compass never copies raw transcripts or secrets into learning logs.

Usage authorized separately by project owner/user authorization. No OSI license is inferred by Compass.

## agent-browser

- Repository: https://github.com/vercel-labs/agent-browser
- Branch: `main`
- Commit: `acbc22bdc5d4f6c5a88d97d4a4745d3c5eb0591f`
- Upstream package version: `agent-browser` 0.33.2
- License: Apache License 2.0
- License copy: `licenses/agent-browser/LICENSE`
- Compass integration: Full Mode invokes the installed CLI for read-only public-page open, read, snapshot, and text extraction. Domain, page-count, timeout, output-size, login, upload, checkout, and form-submission restrictions are enforced by Compass policy. Competition Mode falls back to versioned local snapshots.

## Capability Evolver

- Repository: https://github.com/NMTZ-z/capability-evolver
- Branch: `main`
- Commit: `56bad38c48ed31f97c49aef99fa34edb7b92b03c`
- Upstream package version: `evolver` 1.20.0
- License: MIT License, Copyright (c) 2026 OpenClaw
- License copy: `licenses/capability-evolver/LICENSE`
- Compass integration: Gene, Capsule, Signal, selector, validation, audit, trial, activation, and rollback concepts are adapted for learning-strategy state only. Compass does not invoke the upstream autonomous source-modification loop and never modifies Python source, `SKILL.md`, `manifest.yaml`, safety rules, or licenses during user runtime.

## ProactiveAgent

- Repository: https://github.com/thunlp/ProactiveAgent
- Branch: `main`
- Commit: `3fcf9beebe256b86871659fbb12541c41c9381b9`
- Upstream package version: 0.1.0
- License: Apache License 2.0
- License copy: `licenses/proactive-agent/LICENSE`
- Compass integration: environment/state signals, proactive recommendation, accept/reject/ignore feedback, and evaluation concepts are adapted into deterministic education and career risk checks. Compass does not enable ActivityWatcher collection, desktop monitoring, background notification, or training-model downloads.

## Distribution notes

The Full Development Distribution contains the pinned upstream source snapshots and these notices. The Competition Skill Distribution excludes full upstream repositories and development-only runtimes; it contains Compass-owned runtime adapters and the notices needed to preserve attribution. Third-party components retain their own license terms, and this notice does not replace those terms.
