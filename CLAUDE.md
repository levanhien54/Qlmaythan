# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Repository Overview

This project uses the **RPI (Research → Plan → Implement)** workflow for feature development. All new features should go through the structured RPI process.

## Key Components

### RPI Workflow

- `/rpi:research <feature-slug>` — Research and GO/NO-GO gate
- `/rpi:plan <feature-slug>` — Technical planning and task breakdown
- `/rpi:implement <feature-slug>` — Phased implementation with quality gates

### Skill Definition Structure

Skills in `.claude/skills/<name>/SKILL.md` use YAML frontmatter:

- `name`: Display name and `/slash-command`
- `description`: When to invoke (for auto-discovery)
- `allowed-tools`: Tools allowed without permission prompts

### Subagent Orchestration

Subagents **cannot** invoke other subagents via bash commands. Use the Task tool:

```
Task(subagent_type="agent-name", description="...", prompt="...")
```

### Configuration Hierarchy

1. `.claude/settings.local.json`: Personal settings (git-ignored)
2. `.claude/settings.json`: Team-shared settings
3. `hooks-config.local.json` overrides `hooks-config.json`

## Workflow Best Practices

- Keep CLAUDE.md under 150 lines for reliable adherence
- Use commands for workflows instead of standalone agents
- Create feature-specific subagents with skills (progressive disclosure)
- Perform manual `/compact` at ~50% context usage
- Start with plan mode for complex tasks
- Break subtasks small enough to complete in under 50% context
- Commit often, as soon as task is completed

### Debugging Tips

- Use `/doctor` for diagnostics
- Run long-running terminal commands as background tasks for better log visibility
- Use browser automation MCPs for Claude to inspect console logs
- Provide screenshots when reporting visual issues

## Reports

- Plans and reports are stored in `./reports/`
