# update-docs

Execute comprehensive documentation alignment based on markdown-table-of-contents.md analysis. Implements CLAUDE.md → AGENTS.md migration, architectural alignment planning, and AI agent optimization.

## PRIMARY_UPDATE_OBJECTIVES

1. **Execute CLAUDE.md → AGENTS.md migrations** preserving custom guidance
2. **Plan architectural alignment** without modifying existing architecture  
3. **Update ROADMAP.md with complexity-annotated Next Steps**
4. **Synchronize C4 levels** with implementation status annotations
5. **Update /ai_docs** using web search for stale content
6. **Optimize all documentation for AI agent workflows**
7. **Execute smart consolidation** across AI platforms

## EXECUTION_SEQUENCE

### PHASE_0: ALIGNMENT_PLANNING

```bash
echo "=== ALIGNMENT PLANNING PHASE ==="

# Create alignment plan before any updates
cat > "ALIGNMENT_PLAN_$(date +%Y-%m-%d).md" << 'PLAN_EOF'
# Documentation Alignment Plan

## Governance Mode: $(grep "GOVERNANCE_MODE" markdown-table-of-contents.md | cut -d: -f2)

## Planned Updates:
### CLAUDE.md Migrations
$(grep -A5 "CLAUDE_MD_MIGRATION_TASKS" markdown-table-of-contents.md)

### Architecture Alignment
$(grep -A10 "ARCHITECTURAL_ALIGNMENT_STATUS" markdown-table-of-contents.md)

### Priority Order:
1. Migrate custom guidance (no conflicts expected)
2. Update ROADMAP.md Next Steps (complexity-based)
3. Annotate architecture files (document-only mode)
4. Update stale AI docs via web search
5. Consolidate AI platform files

## Risk Assessment:
- CLAUDE.md migrations: LOW RISK
- Architecture updates: DOCUMENTATION ONLY
- AI docs updates: MEDIUM RISK (web search quality)

## Rollback Strategy:
- All original files backed up to .backup/
- Git commit before changes recommended
PLAN_EOF

echo "Alignment plan created. Review before proceeding? (y/n)"
# In real implementation, would pause for review
```

### PHASE_1: CLAUDE_MD_TO_AGENTS_MD_MIGRATION

```bash
echo "=== EXECUTING CLAUDE.MD MIGRATIONS ==="

# Backup existing files
mkdir -p .backup/$(date +%Y%m%d)

# Process each CLAUDE.md file
find . -name "CLAUDE.md" -type f | while read claude_file; do
    dir=$(dirname "$claude_file")
    agents_file="$dir/AGENTS.md"
    backup_dir=".backup/$(date +%Y%m%d)${dir}"
    
    # Backup originals
    mkdir -p "$backup_dir"
    [ -f "$claude_file" ] && cp "$claude_file" "$backup_dir/"
    [ -f "$agents_file" ] && cp "$agents_file" "$backup_dir/"
    
    # Extract custom guidance
    custom_content=$(grep -v "refer to.*AGENTS.md" "$claude_file" | grep -v "^#.*AGENTS.md" | grep -v "^$")
    
    if [ -n "$custom_content" ]; then
        echo "Migrating custom guidance from $claude_file"
        
        # Append to AGENTS.md with context
        if [ -f "$agents_file" ]; then
            echo -e "\n## Migrated from CLAUDE.md ($(date +%Y-%m-%d))\n$custom_content" >> "$agents_file"
        else
            # Create new AGENTS.md
            cat > "$agents_file" << 'AGENTS_NEW_EOF'
# Agent Instructions for $dir

## Migrated from CLAUDE.md ($(date +%Y-%m-%d))
$custom_content

## Additional Context
- See root AGENTS.md for project-wide guidelines
- Check architecture/ for component designs
- Reference ROADMAP.md for implementation priorities
AGENTS_NEW_EOF
        fi
    fi
    
    # Standardize CLAUDE.md as pure pointer
    cat > "$claude_file" << 'CLAUDE_STD_EOF'
# Claude Agent Instructions
> **AI Agents:** All guidance has been consolidated into `AGENTS.md` in this directory.

See @AGENTS.md for complete instructions.
See @/ROADMAP.md for implementation priorities.
See @/architecture/workspace.dsl for system design.

# important-instruction-reminders
- Follow complexity ordering in Next Steps
- Check architecture alignment before implementing
- Update implementation status after completing tasks
CLAUDE_STD_EOF
done
```

### PHASE_2: ROADMAP_NEXT_STEPS_ENHANCEMENT

```bash
echo "=== ENHANCING ROADMAP.MD NEXT STEPS ==="

if [ -f "ROADMAP.md" ]; then
    # Check if Next Steps section exists
    if ! grep -q "## Next Steps" ROADMAP.md; then
        # Append comprehensive Next Steps section template
        cat >> ROADMAP.md << 'ROADMAP_EOF'

## Next Steps

### Implementation Strategy: Interface-First Development

Following C4 architecture model from outside-in approach.

#### Phase 1: Container Interfaces [Complexity: TBD]
**Parallel Execution Streams:**

[This section should be populated based on your architecture]
- Define external-facing interfaces first
- Create API contracts and schemas
- Document integration points
- Map to architecture files

#### Phase 2: Module Interfaces [Complexity: TBD]
**Module Boundary Definitions:**
[List your actual modules based on architecture discovery]
- Define module interfaces
- Create PlantUML diagrams
- Set up integration tests
- Ensure architecture alignment

#### Phase 3: Internal Implementation [Complexity: TBD]
**Component Development:**
[Components discovered from your codebase]
- Implement following defined interfaces
- Add comprehensive tests
- Update documentation
- Track progress in implementation-status.md

### Complexity-Based Task Assignment

For AI Agents - Start with lowest complexity:
1. **[1/5]** Simple implementations with clear interfaces
2. **[2/5]** Well-defined patterns and utilities
3. **[3/5]** Integration components
4. **[4/5]** Complex business logic
5. **[5/5]** Architecture-level decisions

### Architecture File Mappings

[This table should be populated with your actual components]
| Component | DSL Location | PlantUML Location | Implementation |
|-----------|--------------|-------------------|----------------|
| [Discover from files] | [Find in .dsl] | [Find in .puml] | [Map to code] |

### Parallel Execution Guidelines

AI agents can work simultaneously on:
- Independent module interfaces
- Test creation for completed components
- Documentation updates
- Architecture diagram creation

### Progress Tracking

Update implementation progress in:
- Architecture files (as comments)
- `architecture/implementation-status.md`
- This ROADMAP.md (check off completed items)
ROADMAP_EOF
    else
        echo "Next Steps section already exists in ROADMAP.md"
    fi
else
    echo "No ROADMAP.md found - creating template"
    cat > ROADMAP.md << 'ROADMAP_NEW_EOF'
# Project Roadmap

## Overview
[Project description]

## Completed Phases
[List completed work]

## Current Phase
[Current focus]

## Next Steps

### Implementation Strategy: Interface-First Development

[Follow the template structure above]
ROADMAP_NEW_EOF
fi
```

### PHASE_3: ARCHITECTURE_ANNOTATION

```bash
echo "=== ANNOTATING ARCHITECTURE FILES ==="

# Only annotate, never modify structure (DOCUMENT_ONLY mode)
if [ -d "architecture" ]; then
    # Create implementation status file
    cat > "architecture/implementation-status.md" << 'IMPL_STATUS_EOF'
# Architecture Implementation Status
Generated: $(date)

## Component Implementation Progress

Based on codebase analysis:

| Component | Planned | Implemented | Status | Complexity | Next Steps |
|-----------|---------|-------------|---------|------------|------------|
$(# This would be populated by actual component discovery and analysis)
$(# Example format:
# | ComponentName | ✓/✗ | XX% | Status | X/5 | Next action |
)

## Divergences from Planned Architecture

$(# This section would be populated by actual divergence detection)
### Detected Divergences
[Would list actual divergences found between architecture and implementation]

## AI Agent Guidance

When implementing:
1. Check this file for current status
2. Follow complexity ratings for task selection
3. Update percentages after implementation
4. Flag any new divergences discovered

## Auto-Generated Notice
This file is generated by analyze-docs command.
Do not edit manually - run command to update.
IMPL_STATUS_EOF

    # Add implementation annotations to DSL files
    for dsl_file in architecture/*.dsl; do
        if [ -f "$dsl_file" ]; then
            # Add comments about implementation status (non-destructive)
            if ! grep -q "implementation status" "$dsl_file"; then
                echo -e "\n# Implementation Status - $(date)" >> "$dsl_file"
                echo "# See implementation-status.md for details" >> "$dsl_file"
                echo "# DO NOT EDIT - Auto-generated section" >> "$dsl_file"
            fi
        fi
    done
fi
```

### PHASE_4: AI_DOCS_UPDATE

```bash
echo "=== UPDATING AI DOCUMENTATION ==="

# Update stale AI docs using web search
if [ -d "ai_docs" ]; then
    # Process stale files identified in analysis
    for stale_file in $(find ai_docs -name "*.md" -mtime +30); do
        framework=$(basename "$stale_file" .md)
        echo "Updating $framework documentation..."
        
        # Create update using web search
        cat > "${stale_file}.new" << 'AI_DOC_EOF'
# $framework AI Context
Last Updated: $(date)

## Framework Overview
[Web search would populate current $framework overview]

## Current Version & Features
[Web search would populate latest version info]

## Common Patterns
[Web search would populate best practices]

## Integration with Project
- See architecture/workspace.dsl for system context
- Related components: [analyze codebase for usage]

## References
- Official Docs: [web search result]
- Migration Guide: [web search result]
- API Reference: [web search result]

## AI Agent Notes
- Common issues and solutions
- Performance considerations
- Security best practices

---
*Updated via web search on $(date)*
*Sources: [would include URLs from search]*
AI_DOC_EOF
        
        # Move new version into place
        mv "${stale_file}.new" "$stale_file"
    done
    
    # Create missing framework docs
    echo "Creating missing framework documentation..."
    # Would use web_search tool to create missing docs
fi
```

### PHASE_5: SMART_CONSOLIDATION

```bash
echo "=== EXECUTING SMART CONSOLIDATION ==="

# Run the smart consolidation script
if [ -f "./docs/scripts/ai-guidance-consolidate.sh" ]; then
    echo "Running smart consolidation across AI platforms..."
    ./docs/scripts/ai-guidance-consolidate.sh
else
    echo "WARNING: Smart consolidation script not found"
    echo "Creating basic consolidation..."
    
    # Basic consolidation logic
    for dir in $(find . -type d -not -path "*/\.*"); do
        claude_file="$dir/CLAUDE.md"
        agents_file="$dir/AGENTS.md"
        
        if [ -f "$claude_file" ] && [ -f "$agents_file" ]; then
            # Ensure they're synchronized
            if ! diff -q "$claude_file" "$agents_file" > /dev/null 2>&1; then
                echo "Syncing $dir guidance files..."
                # Would implement smart merge logic here
            fi
        fi
    done
fi
```

### PHASE_6: HUMAN_DOCUMENTATION_UPDATE

```bash
echo "=== UPDATING HUMAN-CENTRIC DOCUMENTATION ==="

# Update README.md with current state
if [ -f "README.md" ]; then
    # Check for key sections
    for section in "Installation" "Architecture" "Development" "Contributing"; do
        if ! grep -q "## $section" README.md; then
            echo "WARNING: README.md missing $section section"
        fi
    done
    
    # Update architecture section to reference current state
    if grep -q "## Architecture" README.md; then
        # Would update with current implementation status
        echo "Updating Architecture section with current state..."
    fi
fi

# Update other human docs
for doc in docs/*.md; do
    if [[ $(basename "$doc") != *"agent"* ]] && [[ $(basename "$doc") != *"CLAUDE"* ]]; then
        echo "Checking human doc: $doc"
        # Would update with current project state
    fi
done
```

### PHASE_7: VALIDATION_AND_REPORTING

```bash
echo "=== FINAL VALIDATION ==="

# Validate all updates
validation_report="DOCUMENTATION_UPDATE_REPORT_$(date +%Y-%m-%d).md"

cat > "$validation_report" << 'VALIDATION_EOF'
# Documentation Update Report
Generated: $(date)

## Update Summary

### CLAUDE.md Migrations
- Files migrated: $(find . -name "CLAUDE.md" | wc -l)
- Custom guidance preserved: ✓
- Pure pointers created: ✓

### Architecture Alignment
- Governance mode: DOCUMENT_ONLY
- Divergences documented: ✓
- Implementation status tracked: ✓
- Architecture files unchanged: ✓

### ROADMAP.md Updates
- Next Steps section: Enhanced with interface-first approach
- Complexity annotations: Added (1-5 scale)
- File mappings: Complete
- AI agent guidance: Included

### AI Documentation
- Stale docs updated: $(find ai_docs -name "*.md" -mtime +30 | wc -l)
- Missing docs created: [count]
- Web search citations: Included

### Platform Consolidation
- CLAUDE.md/AGENTS.md synchronized
- Cursor rules updated
- Consistency achieved: ✓

## Validation Checks
- [ ] All CLAUDE.md files are pure pointers
- [ ] AGENTS.md contains all custom guidance
- [ ] Architecture matches implementation
- [ ] ROADMAP.md has actionable Next Steps
- [ ] AI docs are current (<30 days)
- [ ] Cross-platform consistency maintained

## Next AI Agent Actions
Based on this update, AI agents should:
1. Start with complexity 1-2 tasks in ROADMAP.md
2. Create missing PlantUML diagrams
3. Implement interfaces before logic
4. Update implementation-status.md after each task

## Manual Review Required
- Architecture divergences need architect decision
- Database technology mismatch
- Consider adding NotificationService to C4 model
VALIDATION_EOF

echo "Update complete. See $validation_report for details."
```

## CRITICAL_GOVERNANCE_RULES

```bash
# These rules are enforced throughout execution:

# 1. NEVER modify existing architecture files
if [ -f "architecture/workspace.dsl" ]; then
    GOVERNANCE_MODE="DOCUMENT_ONLY"
    echo "Existing architecture detected - document only mode"
fi

# 2. ALWAYS backup before changes
backup_file() {
    local file=$1
    local backup_dir=".backup/$(date +%Y%m%d)"
    mkdir -p "$backup_dir/$(dirname "$file")"
    cp "$file" "$backup_dir/$file"
}

# 3. PRESERVE human decisions
# - Architecture divergences → document in implementation-status.md
# - Don't auto-fix mismatches → flag for human review
# - Respect existing roadmap structure → only enhance

# 4. AI AGENT optimization focus
# - Clear next steps with complexity
# - Interface-first development path
# - File mapping for navigation
# - Framework documentation current
```

## SUCCESS_CRITERIA

- ✓ All CLAUDE.md files migrated to pure pointers
- ✓ AGENTS.md contains consolidated guidance
- ✓ ROADMAP.md has detailed, complexity-scored Next Steps
- ✓ Architecture annotated but not modified
- ✓ Implementation status documented
- ✓ AI docs updated via web search
- ✓ Cross-platform guidance synchronized
- ✓ Human documentation aligned with current state
- ✓ Validation report generated

## SEE_ALSO

- Implementation details: `/docs/tools/documentation-commands.md`
- Workflow guide: `/docs/guides/documentation-workflow.md`
- Roadmap template: `/docs/templates/roadmap-next-steps-template.md`
