---
description: Execute phased implementation with validation gates
argument-hint: "<feature-slug> [--phase N] [--validate-only]"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** parse the user input to extract the feature slug (the folder name in `rpi/`).

## Purpose

This command executes phased implementation of features based on planning documentation. It orchestrates specialized agents, enforces validation gates, and ensures constitutional compliance throughout implementation.

**Prerequisites**:

- Feature folder exists at `rpi/{feature-slug}/`
- Planning completed (`rpi/{feature-slug}/plan/PLAN.md` exists)

**Output Location**: `rpi/{feature-slug}/implement/`

**This is Step 4 of the RPI Workflow** (final step - actual implementation).

## Flags

- `--phase N`: Execute specific phase number (1-8), if omitted starts from phase 1
- `--validate-only`: Only validate current phase, don't implement
- `--skip-validation`: Skip validation gate and proceed (use with caution)

## Available Agents

All agents use **Opus model** for maximum quality.

### Implementation Agent

| Agent | Role |
|-------|------|
| senior-software-engineer | Primary implementer |

### Support Agents

| Agent | Role |
|-------|------|
| code-reviewer | Code review at each phase |
| Explore (built-in) | Code discovery before implementation |
| constitutional-validator | Constitutional compliance check |

### Agent Routing

- **Implementation tasks** → senior-software-engineer
- **Code review** → code-reviewer
- **Code discovery** → Explore (via Task tool)
- **Constitutional check** → constitutional-validator (on demand)

---

## Phase 0: Load Context and Rules

### 0.1 Load Project Constitution

- Check for constitution/principles document
- Extract constraints and rules
- These MUST be enforced throughout implementation

### 0.2 Load Domain-Specific Guidelines

- Read project-specific rules from CLAUDE.md
- Identify coding standards and conventions
- Note testing requirements

### 0.3 Analyze Implementation Scope

- Read `rpi/{feature-slug}/plan/PLAN.md`
- Identify total phases and tasks
- Determine starting phase (from --phase flag or Phase 1)

---

## Phased Implementation Workflow

### Phase Implementation Loop

For each phase in PLAN.md:

```
┌─────────────────────────────────────────────────────────────┐
│ Phase N: [Phase Name]                                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Code Discovery (Explore Agent)                          │
│     └─→ Understand existing code before changing it         │
│                                                              │
│  2. Implementation (senior-software-engineer)               │
│     └─→ Implement phase deliverables                        │
│                                                              │
│  3. Self-Validation                                         │
│     └─→ Engineer validates against phase checklist          │
│                                                              │
│  4. Code Review (code-reviewer Agent)                       │
│     └─→ Security, correctness, maintainability              │
│                                                              │
│  5. User Validation Gate                                    │
│     └─→ STOP and request user approval                      │
│         ├─→ PASS: Proceed to next phase                     │
│         ├─→ CONDITIONAL PASS: Note issues, proceed          │
│         └─→ FAIL: Fix issues, re-validate                   │
│                                                              │
│  6. Documentation Update                                    │
│     └─→ Update phase status in PLAN.md                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 1: Code Discovery (Per Phase)

**Agent**: Explore (Built-in, via Task tool)

**Purpose**: Ground implementation in code reality before making changes.

**Process**:

1. Launch Explore agent via Task tool with `subagent_type="Explore"`
2. Request analysis of files affected by current phase
3. Understand existing patterns, integration points, constraints

**Output**: Discovery summary for implementation agent

---

## Step 2: Implementation (Per Phase)

**Agent**: senior-software-engineer

**Process**:

1. Use senior-software-engineer agent
2. Provide discovery context from Step 1
3. Implement all deliverables for the phase
4. Follow constitutional constraints and project rules

**Quality Checklist**:

- [ ] Code follows existing patterns
- [ ] Type annotations present where applicable
- [ ] Tests written and passing
- [ ] No breaking changes to existing functionality
- [ ] Logging added for observability
- [ ] Error handling comprehensive

---

## Step 3: Self-Validation

**Agent**: senior-software-engineer (same as Step 2)

**Process**:

1. Agent validates implementation against phase checklist
2. Run linting (use project's configured linter)
3. Run tests relevant to changes
4. Verify build succeeds

**Self-Validation Checklist**:

- [ ] All deliverables implemented
- [ ] Linting passes
- [ ] Tests pass
- [ ] Build succeeds
- [ ] No regressions in existing tests
- [ ] Constitutional constraints honored

---

## Step 4: Code Review

**Agent**: code-reviewer (Custom, auto-invoked)

**Review Verdicts**:

- **APPROVED**: Proceed to user validation
- **APPROVED WITH SUGGESTIONS**: Note suggestions, proceed
- **NEEDS REVISION**: Fix issues, re-review

---

## Step 5: User Validation Gate

**CRITICAL**: This step REQUIRES user interaction. DO NOT proceed automatically.

**Process**:

1. Present phase deliverables checklist
2. Show what was implemented (files changed, features added)
3. Present validation criteria from PLAN.md
4. Show code review results
5. **STOP and wait for user decision**

**User Decisions**:

- **PASS**: Proceed to next phase
- **CONDITIONAL PASS**: Document issues, proceed to next phase
- **FAIL**: Fix issues, re-run Steps 2-5

---

## Step 6: Documentation Update

**Process**:

1. Update `rpi/{feature-slug}/plan/PLAN.md` with phase status
2. Update `rpi/{feature-slug}/implement/IMPLEMENT.md` with validation results

---

## Error Handling

### Implementation Failures

1. Document the specific failure
2. Analyze root cause
3. Try alternative approach (max 2 attempts)
4. If still failing, STOP and ask user for guidance

### Test Failures

1. Analyze failure cause (code bug vs test bug)
2. Fix the issue
3. Re-run tests
4. If persistent, document and ask user

### Build Failures

1. Check for type errors, missing imports, syntax errors
2. Fix and rebuild
3. If persistent, escalate to user

### Agent Failures

1. Retry once with same inputs
2. If still failing, proceed without that agent's contribution
3. Document gap in validation request

---

## Quality Gates

### Per-Phase Quality Gate

- [ ] All deliverables implemented
- [ ] Linting passes
- [ ] Tests pass
- [ ] Build succeeds
- [ ] Code review passed
- [ ] User validation received
- [ ] Documentation updated

### Final Quality Gate

- [ ] All phases validated
- [ ] No failing tests
- [ ] Build succeeds in full
- [ ] Constitutional compliance verified
- [ ] PR notes generated

---

## Notes

### When to Use This Command

- After `/rpi:plan` generates PLAN.md
- When phased implementation with validation gates is needed
- For features requiring structured implementation

### When NOT to Use This Command

- Bug fixes (too heavy, just fix directly)
- Very simple changes (<30 minutes work)
- Exploratory prototyping
- Documentation-only changes

### Best Practices

1. **Review PLAN.md first**: Understand what you're implementing
2. **Trust code discovery**: Let Explore agent inform implementation
3. **Follow existing patterns**: Let code discovery inform implementation
4. **Don't skip validation**: Gates exist to catch issues early
5. **Document as you go**: Update status after each phase
6. **Ask when stuck**: Better to ask than to proceed incorrectly

### Part of RPI Workflow

Step 4 of 4 (Describe → Research → Plan → **Implement**)

---

## Post-Completion Action

**IMPORTANT**: After completing implementation, ALWAYS prompt the user to compact the conversation:

> **Context Management**: This implementation workflow consumed significant context. To preserve progress and free up space, please run:
>
> ```
> /compact
> ```
