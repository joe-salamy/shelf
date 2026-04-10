## Overview

Shelf is a CLI tool that converts PDF and EPUB textbooks into nested, grep-friendly Markdown directories split by heading depth. It also supports LLM-powered section summarization via OpenAI-compatible or Ollama backends.

## Environment

- Activate venv before any pip/python commands: `venv\Scripts\Activate.ps1`
- Never pip install into the global or user environment — always use the venv.

## Git & Commits

- Read `.gitignore` before running any git commit to know what files to exclude.

## Off-Limits Files

- Never read from, write to, or git diff `docs/scratchpad.md`.
- When running `/code-reviewer` or `/python-pro`, exclude diffs of files in `.claude/` and `docs/` — these are settings/prose, not reviewable code.

## Plan Mode

- When asking clarifying questions in plan mode, be liberal; when in doubt, ask more rather than fewer.

## Documentation

- Keep READMEs concise.
