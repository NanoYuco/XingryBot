# Project Agent Instructions

This file is the entry point for Codex in this repository.

Before implementing, fixing, refactoring, or reviewing code:

1. Read `.agent/prompts/shared-engineering-rules.md` completely.
2. Read `.agent/project-context.md` completely.
3. For implementation work, read `.agent/prompts/development-agent.md` completely.
4. For an independent review, read `.agent/prompts/technical-reviewer.md` completely.
5. Read the task contract and other task artifacts named in the current request.

Treat `AGENTS.md` and everything under `.agent/` as developer-owned Agent configuration. Do not modify them unless the developer explicitly asks to update the Agent workflow or its rules.

Store temporary plans, debugging notes, delivery reports, review reports, and acceptance reports only under `.agent-work/tasks/<task-id>/`. Never place production code or runtime resources there.

If a required instruction or task file is missing, report the exact missing path instead of guessing its contents.

