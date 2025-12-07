---
argument-hint: [phase-doc-path] [swim-lane-id]
description: "Execute a specific swim lane from a phase implementation plan by orchestrating parallel sub-agents for each task"
allowed-tools: Read, Bash(git status:*), Bash(git branch:*), Agent
---

# Execute Swim Lane with Parallel Sub-Agents

## Inputs
- `$1` = Phase document path (e.g., `plans/phase-2-ingestion.md`)
- `$2` = Swim lane identifier (e.g., `SL-1`, `lane-api-routes`, etc.)

## Execution Strategy

### 1. Load Phase Plan & Extract Swim Lane

Read the phase implementation document:
- `@$1`

Locate swim lane `$2` within the document. Extract:
- **Swim lane scope**: Component boundaries, files, interfaces owned
- **Task list**: Individual work items with their dependencies
- **Interface contracts**: Frozen interfaces this lane depends on or provides
- **Acceptance criteria**: Definition of done for this lane

### 2. Verify Preconditions

Before spawning agents, check:

**Interface Dependencies:**
- All interfaces this lane **consumes** must be frozen (have `IF-*` gate marked complete)
- If any dependency is not ready, list them and STOP with message:
```
  ⚠️ Cannot proceed - waiting on interface freeze gates:
  - IF-0-xyz: [description]
  
  Recommend: Execute dependent lanes first or request interface definition
```

**Git State:**
- Current branch: !`git branch --show-current`
- Verify branch matches expected feature branch for this phase
- Check for uncommitted changes: !`git status --short`
- If dirty, warn but allow continuation (agents will commit their changes)

**File Conflicts:**
- Check if any files in this lane's scope are already modified in working tree
- List conflicts and ask user to confirm continuation

### 3. Task Dependency Analysis

From the task list for lane `$2`:
- Build dependency graph (which tasks can run in parallel vs sequential)
- Identify tasks with no dependencies ("ready" tasks)
- Group related tasks that should execute sequentially in one agent

**Grouping heuristics:**
- Tasks touching the same file → same agent (sequential)
- Tasks with direct data dependencies → same agent (sequential)
- Tasks on different files with no dependencies → parallel agents
- Avoid creating more than 5 parallel agents (diminishing returns)

### 4. Spawn Sub-Agents for Tasks

For each task or task group:

**Use the `lane-executor` subagent** (defined separately)

**Spawn with context:**
```
Use the lane-executor subagent to implement [task description]

Context:
- Phase: [phase name from $1]
- Swim Lane: $2
- Task ID: [task-id]
- Files in scope: [list]
- Interfaces to implement: [list with signatures]
- Interfaces to consume: [list with usage notes]
- Acceptance criteria: [specific criteria for this task]

Constraints:
- Do NOT modify files outside this task's scope
- Do NOT change interface signatures (they are frozen)
- Follow existing code patterns in adjacent files
- Write tests for new functionality
- Commit work with message: "feat(${2}): [task description]"

If you encounter blockers, report them and pause for guidance.
```

**For parallel agents:**
- Track spawned agent IDs
- Monitor for completion or blockers
- Handle conflicts if agents touch overlapping concerns (should be rare with good task division)

### 5. Progress Monitoring

As agents execute:

**Track:**
- ✅ Completed tasks (agent finished successfully)
- 🔄 In-progress tasks (agent still working)
- ⚠️ Blocked tasks (agent reported blocker)
- ❌ Failed tasks (agent encountered error)

**Display progress:**
```
Swim Lane: $2
Progress: [N/M tasks complete]

✅ Task A: Implement User model
🔄 Task B: Add authentication endpoints (agent-abc123)
⚠️ Task C: Database migration (blocked: needs schema review)
```

### 6. Integration & Verification

After all agents complete:

**Integration checks:**
- Run full test suite for this swim lane's components
- Verify interface contracts match specifications
- Check for any introduced file conflicts
- Validate all acceptance criteria met

**If issues found:**
- Spawn additional lane-executor agent to fix specific issues
- Re-run verification

**If all pass:**
- Create summary commit (optional): "feat(${2}): complete swim lane implementation"
- Update phase document to mark swim lane complete
- Output completion report

### 7. Completion Report

Provide summary:
```
🎯 Swim Lane Completed: $2

Tasks Executed: [count]
- [list of completed tasks with commit hashes]

Interface Contracts Fulfilled:
- [list of interfaces this lane provides, now implemented]

Files Modified:
- [list with line count changes]

Tests Added/Updated:
- [count and list]

Next Steps:
- ✅ Mark lane complete in phase doc
- 🔄 Notify dependent lanes (if any)
- 📋 Consider: [any follow-up recommendations]

Agent IDs (for resume if needed):
- Task A: agent-abc123
- Task B: agent-def456
```

## Error Handling

**If any agent fails:**
- Capture the agent ID and error
- Pause remaining parallel agents
- Report failure details
- Offer to:
  - Resume failed agent with additional context
  - Spawn new agent with revised approach
  - Manual intervention

**If interface mismatch detected:**
- This is critical - interfaces are supposed to be frozen
- Report discrepancy clearly
- Suggest:
  - Fix consumer to match frozen interface, OR
  - Escalate for interface contract revision (requires cross-lane coordination)

## Notes

- This command orchestrates; the `lane-executor` subagent does the actual coding
- Ideal swim lanes have 2-8 tasks each (too few = underutilized parallelism; too many = overhead)
- If lane has >10 tasks, consider running command multiple times on task subgroups
- Resume capability: If interrupted, you can resume individual agents by their IDs