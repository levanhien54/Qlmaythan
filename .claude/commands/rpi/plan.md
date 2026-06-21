---
description: Create comprehensive planning documentation for a feature
argument-hint: "<feature-slug>"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** parse the user input to extract the feature slug (the folder name in `rpi/`).

## Purpose

This command creates comprehensive planning documentation for a feature request. It generates detailed specifications, technical design, and implementation plans in the feature's RPI folder.

**Prerequisites**:

- Feature folder exists at `rpi/{feature-slug}/`
- Research completed with GO recommendation (`rpi/{feature-slug}/research/RESEARCH.md` exists)

**Output Location**: All files saved to `rpi/{feature-slug}/plan/`

**This is Step 3 of the RPI Workflow** (after Research approves with GO).

## Outline

1. **Load Context**: Read research report and project constitution (if exists)
2. **Understand Requirements**: Parse feature scope and requirements
3. **Analyze Technical Requirements**: Review architecture and dependencies
4. **Design Architecture**: Create high-level architecture and API contracts
5. **Break Down Implementation**: Create phased task breakdown
6. **Generate Documentation**: Create structured documentation files
7. **Validate Output**: Ensure all quality gates pass
8. **Report Completion**: Provide summary and next steps

## Phases

### Phase 0: Load Context

**Prerequisites**: Feature slug provided

**Process**:

1. **Verify research completed**:
   - Check `rpi/{feature-slug}/research/RESEARCH.md` exists
   - Verify GO recommendation (warn if NO-GO or CONDITIONAL)

2. **Read research findings**:
   - Extract product analysis
   - Extract technical discovery
   - Extract technical feasibility assessment
   - Note risks and constraints

3. **Load project constitution** (if exists):
   - Look for a constitution or principles document in the repository
   - Extract relevant constraints and preferences

**Validation**:

- [ ] Research report exists
- [ ] GO recommendation confirmed
- [ ] Constitution loaded (if exists)

---

### Phase 1: Understand Feature Requirements

**Prerequisites**: Phase 0 complete

**Process**:

1. **Parse Feature Description** from research report:
   - Extract feature name and primary goal
   - Identify target component(s)
   - Understand user-facing vs. technical feature
   - Determine feature complexity level

2. **Identify Affected Components**:
   - Primary component (where feature lives)
   - Secondary components (integration points)
   - Shared utilities needed
   - External dependencies

3. **Research Existing Patterns**:
   - Search for similar features in codebase
   - Review component architecture and patterns
   - Identify reusable code and patterns

---

### Phase 2: Analyze Technical Requirements

**Prerequisites**: Phase 1 complete

**Process**:

1. **Review Component Architecture**:
   - Read component README and documentation
   - Review existing code structure
   - Identify architectural patterns used

2. **Identify Technical Dependencies**:
   - Internal dependencies (other components, shared utilities)
   - External dependencies (APIs, services, libraries)
   - Database/storage requirements
   - Authentication/authorization needs

3. **Assess Integration Points**:
   - APIs that need to be created or modified
   - Database schema changes required
   - Event/message flows
   - Frontend-backend integration

4. **Evaluate Technical Risks**:
   - Breaking changes to existing features
   - Performance implications
   - Security concerns
   - Data migration needs

---

### Phase 3: Design Feature Architecture

**Prerequisites**: Phases 1-2 complete

**Agent**: senior-software-engineer

**Process**:

1. **Design High-Level Architecture**:
   - Component/module structure
   - Data flow diagrams
   - API interfaces
   - Database schema changes

2. **Define Implementation Approach**:
   - File structure and organization
   - Code organization patterns
   - Testing strategy
   - Error handling approach

3. **Plan Database/Storage Changes** (if applicable):
   - New collections/tables
   - Schema modifications
   - Migration strategy
   - Data validation rules

4. **Design API Contracts** (if applicable):
   - Request/response formats
   - Authentication requirements
   - Error responses

5. **Plan Testing Strategy**:
   - Unit test requirements
   - Integration test scenarios
   - End-to-end test cases

---

### Phase 4: Break Down Implementation Tasks

**Prerequisites**: Phases 1-3 complete

**Process**:

1. **Identify Implementation Phases**:
   - Break feature into 3-5 logical phases
   - Each phase should deliver working, testable functionality
   - Phases should build on each other progressively

2. **Create Task Breakdown for Each Phase**:
   - List specific implementation tasks
   - Estimate complexity (Low/Medium/High)
   - Identify task dependencies
   - Assign to appropriate code areas

3. **Define Success Criteria**:
   - Acceptance criteria for each phase
   - Testing requirements
   - Documentation requirements

4. **Identify Parallelization Opportunities**:
   - Tasks that can be done concurrently
   - Frontend/backend parallel work
   - Independent module development

---

### Phase 5: Generate Documentation

**Prerequisites**: Phases 1-4 complete

**Agent**: documentation-analyst-writer (via Task tool)

**Process**:

1. **Generate pm.md** (Product Requirements):
   - Feature description and user stories
   - Business value and success metrics
   - User personas and use cases
   - Acceptance criteria
   - Out of scope items

2. **Generate ux.md** (User Experience Design):
   - User interface mockups (text description)
   - User flows and interactions
   - Accessibility considerations
   - Error states and edge cases

3. **Generate eng.md** (Technical Specification):
   - Architecture design
   - API specifications
   - Database schema changes
   - Technology stack
   - Technical risks and mitigation

4. **Generate PLAN.md** (Implementation Roadmap):
   - Phased implementation breakdown
   - Task list with estimates per phase
   - Dependencies and ordering
   - Success criteria per phase
   - Testing requirements
   - Validation checkpoints

**Output Files** (all saved to `rpi/{feature-slug}/plan/`):

- `pm.md` - Product requirements
- `ux.md` - UX design
- `eng.md` - Technical specification
- `PLAN.md` - Detailed implementation roadmap

---

## Sub-Agent Delegation

This command orchestrates specialist agents:

| Phase | Agent | Type | Purpose |
|-------|-------|------|---------|
| Phase 3 | senior-software-engineer | Custom | Architecture design |
| Phase 5 | product-manager | Custom | Product requirements (pm.md) |
| Phase 5 | ux-designer | Custom | User experience (ux.md) |
| Phase 5 | senior-software-engineer | Custom | Technical spec (eng.md) |
| Phase 5 | documentation-analyst-writer | Custom | Documentation synthesis |

---

## Completion Report

Report the following on successful completion:

### Outputs Created

**Documentation Folder**: `rpi/{feature-slug}/plan/`

Files created:

- **pm.md**: Product requirements and user stories
- **ux.md**: User experience design
- **eng.md**: Technical specification
- **PLAN.md**: Detailed implementation roadmap

### Next Steps

1. **Review Documentation**:
   - Read planning docs in `rpi/{feature-slug}/plan/`
   - Review technical spec in `eng.md`
   - Understand implementation phases in `PLAN.md`

2. **Validate with Stakeholders**:
   - Product review of pm.md
   - UX review of ux.md
   - Technical review of eng.md

3. **Begin Implementation**:
   - Run `/rpi:implement "{feature-slug}"` to execute phased implementation
   - Follow PLAN.md phases
   - Complete validation gates at each phase

---

## Error Handling

**If research report doesn't exist**:

- Action: Stop and inform user
- Message: "Research report not found. Run `/rpi:research` first."

**If research recommendation is NO-GO**:

- Action: Warn user but allow proceeding
- Message: "Research recommended NO-GO. Proceed anyway? (y/n)"

**If documentation agent fails**:

- Action: Generate documentation directly
- Warning: "Documentation may not fully adhere to standards"

---

## Notes

- **Prerequisites**: Research completed with GO recommendation
- **Part of RPI Workflow**: Step 3 of 4 (Describe → Research → Plan → Implement)

---

## Post-Completion Action

**IMPORTANT**: After completing the planning workflow, ALWAYS prompt the user to compact the conversation:

> **Context Management**: This planning workflow consumed significant context. To free up space for implementation, please run:
>
> ```
> /compact
> ```
