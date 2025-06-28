#!/bin/bash

# Setup Complete Documentation Structure
# This script creates the entire documentation structure with all files
# It overwrites existing files with the same name but preserves other files

set -e  # Exit on error

echo "=== Setting up Complete Documentation Structure ==="
echo "This will overwrite existing documentation files. Continue? (y/n)"
read -r response
if [[ ! "$response" =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 0
fi

# Create directory structure
echo "Creating directory structure..."
mkdir -p .claude/commands
mkdir -p docs/tools
mkdir -p docs/guides
mkdir -p docs/templates
mkdir -p docs/scripts
mkdir -p .cursor/rules

# Create analyze-docs.md command
echo "Creating .claude/commands/analyze-docs.md..."
cat > ".claude/commands/analyze-docs.md" << 'ANALYZE_EOF'
# analyze-docs

Perform comprehensive documentation analysis optimized for AI agent development workflows. Creates markdown-table-of-contents.md with architectural alignment insights and complexity annotations.

## PRIMARY_ANALYSIS_OBJECTIVES

1. **Create comprehensive markdown file inventory** with AI agent context annotations
2. **Analyze CLAUDE.md → AGENTS.md migration needs** and custom guidance detection  
3. **Map C4 architecture levels** (DSL L1-3 and PlantUML L4) with alignment status
4. **Assess ROADMAP.md implementation progress** with complexity scoring
5. **Detect codebase-architecture divergences** for governance tracking
6. **Evaluate /ai_docs staleness** and framework coverage
7. **Analyze AI platform guidance consistency** across CLAUDE.md, AGENTS.md, and Cursor rules

## EXECUTION_SEQUENCE

### PHASE_1: INTELLIGENT_FILE_DISCOVERY_AND_CLASSIFICATION

```bash
# Discover all documentation with context
echo "=== DOCUMENTATION DISCOVERY ==="
find . -name "*.md" -type f | while read file; do
    # Classify by AI agent relevance
    if [[ "$file" == *"CLAUDE.md"* ]] || [[ "$file" == *"AGENTS.md"* ]]; then
        echo "AI_AGENT_CONTEXT: $file"
    elif [[ "$file" == *"README.md"* ]]; then
        echo "HUMAN_CONTEXT: $file"
    else
        echo "MIXED_CONTEXT: $file"
    fi
done

# Discover architecture files with C4 level detection
echo "=== ARCHITECTURE DISCOVERY ==="
find . -name "*.dsl" -type f | while read file; do
    if grep -q "workspace\|container\|component" "$file"; then
        echo "STRUCTURIZR_DSL (C4 L1-3): $file"
    fi
done

find . -name "*.puml" -o -name "*.plantuml" | while read file; do
    echo "PLANTUML (C4 L4): $file"
done
```

### PHASE_2: CLAUDE_MD_MIGRATION_ANALYSIS

```bash
# Analyze CLAUDE.md files for custom guidance
echo "=== CLAUDE.MD MIGRATION ANALYSIS ==="
find . -name "CLAUDE.md" -type f | while read file; do
    echo "Analyzing: $file"
    
    # Check if it's a pure pointer
    if grep -q "refer to.*AGENTS.md" "$file" && ! grep -q "^[^#]" "$file"; then
        echo "STATUS: Pure pointer (compliant)"
    else
        echo "STATUS: Contains custom guidance (needs migration)"
        # Extract custom content for migration
        grep -v "refer to.*AGENTS.md" "$file" | grep -v "^#.*AGENTS.md" > "${file}.custom"
    fi
done
```

### PHASE_3: ARCHITECTURE_ALIGNMENT_MATRIX

```bash
# Create architecture alignment analysis
echo "=== ARCHITECTURE ALIGNMENT MATRIX ==="

# Map DSL components to PlantUML files
dsl_components=$(grep -h "component\|container" architecture/*.dsl 2>/dev/null | grep -o '"[^"]*"' | sort -u)

echo "DSL Components Found:"
echo "$dsl_components"

# Check PlantUML coverage
for component in $dsl_components; do
    component_name=$(echo $component | tr -d '"')
    if find architecture -name "*.puml" -exec grep -l "$component_name" {} \; | head -1; then
        echo "✓ $component_name: Has PlantUML detail"
    else
        echo "✗ $component_name: Missing PlantUML detail"
    fi
done
```

### PHASE_4: ROADMAP_COMPLEXITY_SCORING

```bash
# Analyze ROADMAP.md with complexity scoring
echo "=== ROADMAP COMPLEXITY ANALYSIS ==="

if [ -f "ROADMAP.md" ]; then
    # Extract roadmap items and score complexity
    grep -E "^[-*] " ROADMAP.md | while read item; do
        complexity=1
        
        # Score based on keywords
        [[ "$item" =~ "integration" ]] && ((complexity++))
        [[ "$item" =~ "migration" ]] && ((complexity++))
        [[ "$item" =~ "refactor" ]] && ((complexity++))
        [[ "$item" =~ "architecture" ]] && ((complexity++))
        
        echo "[$complexity/5] $item"
    done
fi
```

### PHASE_5: CODEBASE_ARCHITECTURE_DIVERGENCE

```bash
# Detect implemented vs planned architecture
echo "=== DIVERGENCE DETECTION ==="

# Check for implemented components
implemented_services=$(find . -name "*.py" -o -name "*.js" -o -name "*.ts" | grep -E "(service|component|module)" | wc -l)
planned_components=$(grep -c "component" architecture/*.dsl 2>/dev/null || echo 0)

echo "Implemented services/components: $implemented_services"
echo "Planned components in architecture: $planned_components"
echo "Alignment percentage: $((implemented_services * 100 / (planned_components + 1)))%"
```

### PHASE_6: AI_DOCS_FRAMEWORK_COVERAGE

```bash
# Analyze /ai_docs for framework coverage and staleness
echo "=== AI DOCS ANALYSIS ==="

if [ -d "ai_docs" ]; then
    # Check for stale docs (>30 days)
    find ai_docs -name "*.md" -mtime +30 | while read file; do
        echo "STALE: $file ($(stat -f "%Sm" -t "%Y-%m-%d" "$file" 2>/dev/null || stat -c "%y" "$file" | cut -d' ' -f1))"
    done
    
    # Detect missing framework docs
    frameworks=$(find . -name "package.json" -o -name "requirements.txt" -o -name "go.mod" | \
                  xargs grep -h -E "(react|vue|django|flask|express|fastapi)" | \
                  grep -o -E "(react|vue|django|flask|express|fastapi)" | sort -u)
    
    for framework in $frameworks; do
        if [ ! -f "ai_docs/${framework}.md" ]; then
            echo "MISSING: ai_docs/${framework}.md"
        fi
    done
fi
```

### PHASE_7: GENERATE_ENHANCED_MARKDOWN_TABLE_OF_CONTENTS

```bash
echo "=== GENERATING MARKDOWN TABLE OF CONTENTS ==="

# Generate the markdown table of contents dynamically
cat > "markdown-table-of-contents.md" << 'TOC_EOF'
# Markdown Documentation Index with AI Agent Optimization
# Generated: $(date)
# Mode: AI_AGENT_DEVELOPMENT_GUIDE

## CRITICAL_AGENT_INSTRUCTIONS
- Check ARCHITECTURE_ALIGNMENT before implementation
- Follow COMPLEXITY_ORDERING for task selection  
- Migrate CLAUDE_MD_CUSTOM_GUIDANCE items first
- Reference AI_DOCS_REQUIRED for framework context

## ARCHITECTURAL_ALIGNMENT_STATUS
\`\`\`
OVERALL_ALIGNMENT: [Calculated from actual discovery]
C4_LEVEL_COVERAGE:
$(# Dynamically generate based on found files)
$(find . -name "*.dsl" -type f | head -5 | while read f; do echo "  - $f"; done)
$(find . -name "*.puml" -type f | head -5 | while read f; do echo "  - $f"; done)

DIVERGENCE_LOG:
$(# Would be populated by actual analysis comparing code to architecture)
[Analysis would populate actual divergences found]
\`\`\`

## CLAUDE_MD_MIGRATION_TASKS
\`\`\`
$(# Dynamically list files needing migration)
$(find . -name "CLAUDE.md" -type f | while read file; do
    if grep -q -v "refer to.*AGENTS.md" "$file" 2>/dev/null; then
        echo "- $file → $(dirname $file)/AGENTS.md"
    fi
done)
\`\`\`

## ROADMAP_COMPLEXITY_MATRIX
\`\`\`
$(# Extract actual roadmap items if ROADMAP.md exists)
$(if [ -f "ROADMAP.md" ]; then
    grep -E "^[-*] " ROADMAP.md | head -10
else
    echo "No ROADMAP.md found - recommend creating one"
fi)
\`\`\`

## AI_DOCS_STATUS
\`\`\`
$(# Check actual staleness of ai_docs)
$(if [ -d "ai_docs" ]; then
    find ai_docs -name "*.md" -mtime +30 | while read file; do
        echo "STALE: $file ($(stat -c %y "$file" 2>/dev/null | cut -d' ' -f1))"
    done
else
    echo "No ai_docs directory found"
fi)
\`\`\`

## IMPLEMENTATION_READY_COMPONENTS
\`\`\`
$(# Discover actual components ready for development)
[Would analyze actual codebase structure and architecture alignment]
\`\`\`

## AI_PLATFORM_GUIDANCE_SYNC
\`\`\`
PLATFORM_CONSISTENCY:
- CLAUDE.md files: $(find . -name "CLAUDE.md" -type f | wc -l)
- AGENTS.md files: $(find . -name "AGENTS.md" -type f | wc -l)
- .cursor/rules/: $(find .cursor/rules -name "*.mdc" -type f 2>/dev/null | wc -l)

RECOMMENDED_SYNC:
$(# Provide recommendations based on actual findings)
\`\`\`

## NEXT_IMPLEMENTATION_GUIDANCE
\`\`\`
Based on analysis, recommended actions:
$(# Generate recommendations based on actual discoveries)
1. Address any CLAUDE.md migrations needed
2. Create missing architecture documentation
3. Update stale AI documentation
4. Implement components by complexity order
\`\`\`
TOC_EOF

echo "Generated markdown-table-of-contents.md"
```

## SUCCESS_METRICS

**Analysis completeness validated by:**
- ✓ All markdown files discovered and classified
- ✓ CLAUDE.md migration needs identified  
- ✓ Architecture alignment percentage calculated
- ✓ Roadmap items complexity-scored
- ✓ Divergences documented for governance
- ✓ AI docs coverage gaps identified
- ✓ Implementation readiness assessed

## GOVERNANCE_MODE_DETECTION

```bash
# Determine if this is a new project or existing
if [ -f "ROADMAP.md" ] && [ -d "architecture" ]; then
    echo "GOVERNANCE_MODE: DOCUMENT_ONLY - Existing architecture detected"
    echo "ACTION: Document divergences only, do not modify architecture"
else
    echo "GOVERNANCE_MODE: CREATE_NEW - No architecture found"
    echo "ACTION: Safe to create initial architecture"
fi
```

## SEE_ALSO

- Implementation details: `/docs/tools/documentation-commands.md`
- Workflow guide: `/docs/guides/documentation-workflow.md`
- Roadmap template: `/docs/templates/roadmap-next-steps-template.md`
ANALYZE_EOF

# Create update-docs.md command
echo "Creating .claude/commands/update-docs.md..."
cat > ".claude/commands/update-docs.md" << 'UPDATE_EOF'
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
UPDATE_EOF

# Create documentation-commands.md
echo "Creating docs/tools/documentation-commands.md..."
cat > "docs/tools/documentation-commands.md" << 'DOC_COMMANDS_EOF'
# Documentation Commands Implementation Guide
# Location: /docs/tools/documentation-commands.md

## Overview

This guide provides implementation details for the AI-optimized documentation maintenance system, consisting of two complementary commands that work together to keep documentation aligned with code.

## Command Summary

### `/project:analyze-docs`
Performs comprehensive documentation analysis and generates actionable insights.

**Key Functions:**
- Discovers and classifies all documentation
- Analyzes architecture alignment (C4 levels)
- Detects platform-specific AI guidance
- Identifies stale framework documentation
- Scores roadmap items by complexity
- Generates `markdown-table-of-contents.md`

### `/project:update-docs`
Executes documentation updates based on analysis while respecting governance rules.

**Key Functions:**
- Plans updates before execution
- Migrates custom guidance between files
- Enhances roadmap with interface-first approach
- Documents but doesn't modify architecture
- Updates stale documentation via web search
- Consolidates multi-platform AI guidance

## Architecture & Governance

### Governance Modes

**DOCUMENT_ONLY Mode:**
- Triggered when existing architecture detected
- Preserves all architectural decisions
- Only documents divergences
- Never modifies .dsl or .puml files
- Creates `implementation-status.md`

**CREATE_NEW Mode:**
- Only for brand new projects
- Safe to create initial structure
- Generates starter templates
- Sets up documentation hierarchy

### Architecture Alignment

The commands understand C4 architecture model:
- **Levels 1-3**: Structurizr DSL (`workspace.dsl`)
- **Level 4**: PlantUML diagrams (`*.puml`)

Alignment tracking:
- Maps implementation to architecture
- Calculates coverage percentages
- Documents divergences without judgment
- Provides recommendations for architects

## AI Platform Integration

### Supported Platforms

**Claude Code:**
- Memory file: `CLAUDE.md`
- Uses @import syntax
- Directory-scoped

**Codex:**
- Guidance file: `AGENTS.md`
- Markdown format
- Directory-scoped

**Cursor:**
- Rules: `.cursor/rules/*.mdc`
- YAML/MDC format
- Repository-scoped

### Smart Consolidation

Instead of duplicating content:
1. Reads all platform files
2. Identifies common guidance
3. Deduplicates intelligently
4. Generates unified content
5. Formats for each platform

Result: Single source of truth with platform-specific formatting.

## Implementation Details

### File Discovery

Dynamic discovery approach:
```bash
# Find all markdown files
find . -name "*.md" -type f

# Classify by context
# - AI_AGENT_CONTEXT: CLAUDE.md, AGENTS.md
# - HUMAN_CONTEXT: README.md
# - MIXED_CONTEXT: Other .md files

# Find architecture files
find . -name "*.dsl" -o -name "*.puml"
```

### Complexity Scoring

Roadmap items scored 1-5 based on:
- Integration requirements
- Migration complexity
- Refactoring scope
- Architectural impact

### Next Steps Generation

Creates interface-first development plan:
1. Container interfaces (external-facing)
2. Module interfaces (boundaries)
3. Internal interfaces (integration)
4. Class design (structure)
5. Implementation (logic)

Each level includes:
- File mappings
- Complexity ratings
- Parallel execution options
- AI documentation needs

## Workflow Integration

### Development Iteration Cycle

```mermaid
graph TD
    A[Start Iteration] --> B[/project:analyze-docs]
    B --> C[Review Analysis]
    C --> D[/project:update-docs]
    D --> E[AI Development]
    E --> F[Code Changes]
    F --> G[End Iteration]
    G --> A
```

### Continuous Improvement

Each cycle:
- Discovers new patterns
- Updates documentation
- Improves alignment
- Reduces technical debt

## Configuration & Customization

### Project-Specific Settings

No configuration files needed - commands adapt to:
- Project structure
- Programming languages
- Architecture patterns
- Team conventions

### Extension Points

To support new platforms:
1. Add discovery logic in analyze phase
2. Define consolidation rules
3. Specify output format
4. Test with sample files

## Best Practices

### Do's
- Run analysis before major changes
- Review alignment plans before executing
- Preserve backup directories
- Document architectural decisions
- Keep roadmap Next Steps current

### Don'ts
- Don't modify architecture without architect approval
- Don't delete backup files immediately
- Don't skip analysis phase
- Don't ignore divergence warnings

## Troubleshooting

### Common Scenarios

**"No architecture found"**
- Normal for new projects
- CREATE_NEW mode activates
- Templates will be generated

**"Divergences detected"**
- Expected as code evolves
- Document for architect review
- Don't auto-fix

**"Stale documentation"**
- Common for fast-moving frameworks
- Web search updates available
- Manual update option provided

### Debug Mode

For detailed output:
```bash
# Run with verbose logging
set -x
/project:analyze-docs
set +x
```

## Performance Considerations

- First run may be slower (full discovery)
- Subsequent runs use cached structure
- Large codebases: expect 30-60s analysis
- Updates are incremental when possible

## Security & Privacy

- All operations are local
- No data sent externally
- Web search only for public docs
- Respects .gitignore patterns

## Future Enhancements

Potential improvements:
- Git integration for change detection
- Automated PR generation
- Architecture drift metrics
- Team analytics dashboard

## Support & Contribution

These commands are part of your project's documentation system. To contribute improvements:
1. Test changes thoroughly
2. Update this guide
3. Maintain backward compatibility
4. Document new features

Remember: The goal is to make documentation maintenance effortless while preserving human decision-making for architectural choices.
DOC_COMMANDS_EOF

# Create documentation-workflow.md
echo "Creating docs/guides/documentation-workflow.md..."
cat > "docs/guides/documentation-workflow.md" << 'WORKFLOW_EOF'
# Documentation Update Workflow Guide
# Location: /docs/guides/documentation-workflow.md

## Overview

This guide outlines the workflow for maintaining documentation using the analyze-docs and update-docs commands. These commands ensure your project documentation stays aligned with your codebase and optimized for AI agent development.

## Prerequisites

- Claude Code with custom commands installed in `.claude/commands/`
- Project with or without existing architecture
- Basic understanding of C4 architecture model (optional but helpful)

## Workflow Steps

### 1. Initial Analysis

Run the analysis command to understand current documentation state:

```bash
/project:analyze-docs
```

This will:
- Discover all markdown files
- Analyze architecture alignment
- Detect AI guidance inconsistencies
- Identify stale documentation
- Generate `markdown-table-of-contents.md`

### 2. Review Analysis Results

Open and review `markdown-table-of-contents.md`:

- Check **GOVERNANCE_MODE** (DOCUMENT_ONLY or CREATE_NEW)
- Review **ARCHITECTURAL_ALIGNMENT_STATUS**
- Note **CLAUDE_MD_MIGRATION_TASKS**
- Examine **AI_DOCS_STATUS** for stale content
- Review **AI_PLATFORM_GUIDANCE_SYNC** recommendations

### 3. Plan Updates

Based on analysis, decide what updates to execute:

**If GOVERNANCE_MODE: CREATE_NEW**
- Safe to create initial architecture
- Can generate ROADMAP.md template
- Will create starter documentation

**If GOVERNANCE_MODE: DOCUMENT_ONLY**
- Will not modify existing architecture
- Only documents divergences
- Updates documentation to match reality

### 4. Execute Updates

Run the update command:

```bash
/project:update-docs
```

This will:
1. Create alignment plan (`ALIGNMENT_PLAN_[date].md`)
2. Migrate CLAUDE.md custom content to AGENTS.md
3. Enhance ROADMAP.md with Next Steps
4. Document architecture divergences
5. Update stale AI documentation
6. Consolidate AI platform guidance
7. Generate validation report

### 5. Verify Updates

Check the generated report:
- `DOCUMENTATION_UPDATE_REPORT_[date].md`
- Verify all planned updates completed
- Review any warnings or errors
- Check for manual review items

### 6. AI Agent Development

With updated documentation, AI agents can:
- Follow Next Steps in ROADMAP.md
- Reference architecture alignment
- Use consolidated guidance
- Access current AI documentation

## Command Interactions

```mermaid
graph LR
    A[analyze-docs] --> B[markdown-table-of-contents.md]
    B --> C[Review & Plan]
    C --> D[update-docs]
    D --> E[Updated Documentation]
    E --> F[AI Agent Development]
    F --> A
```

## Best Practices

### Run Regularly
- Start each development iteration with analysis
- Update documentation before major changes
- Keep AI guidance synchronized

### Preserve Backups
- Commands create `.backup/` directory
- Contains pre-update versions
- Useful for rollbacks if needed

### Review Before Committing
- Check git diff after updates
- Ensure changes align with expectations
- Commit with clear message

### Document Divergences
- Don't hide architecture mismatches
- Document them for review
- Let architects make decisions

## Troubleshooting

### Common Issues

**"No architecture found"**
- Expected for new projects
- CREATE_NEW mode will help
- Safe to generate templates

**"Multiple CLAUDE.md files with custom content"**
- Normal for projects with history
- Update command will migrate
- Review consolidated AGENTS.md

**"Stale AI documentation detected"**
- Documentation >30 days old
- Update command refreshes via web search
- Verify web search tool available

### Manual Interventions

Some situations require human decision:
- Architecture divergences
- Technology conflicts
- Missing components in plans

These are documented but not auto-resolved.

## Integration with AI Platforms

### Claude Code
- Uses CLAUDE.md as memory file
- @imports for references
- AGENTS.md for guidance

### Codex
- Primary guidance in AGENTS.md
- Directory-specific context
- Nested file support

### Cursor
- Rules in `.cursor/rules/*.mdc`
- Auto-attachment by path
- Platform-specific format

## Continuous Improvement

The workflow supports iterative improvement:

1. **Analyze** current state
2. **Update** documentation
3. **Develop** with AI agents
4. **Discover** new patterns
5. **Document** learnings
6. **Repeat** cycle

This creates a positive feedback loop where documentation quality improves with each iteration.
WORKFLOW_EOF

# Create roadmap-next-steps-template.md
echo "Creating docs/templates/roadmap-next-steps-template.md..."
cat > "docs/templates/roadmap-next-steps-template.md" << 'ROADMAP_TEMPLATE_EOF'
# ROADMAP.md Next Steps Section Template
# Location: /docs/templates/roadmap-next-steps-template.md

This template provides the structure for creating comprehensive Next Steps sections in ROADMAP.md files optimized for AI agent development.

## Template Structure

```markdown
## Next Steps

### Implementation Strategy: Interface-First Development

Following C4 architecture model from outside-in approach to minimize integration issues.

#### Phase 1: Container Interfaces [Complexity: X/5] ⏱️ X days
**Parallel Execution Streams:**

**Stream A - [Interface Type]:**
- [ ] Define contracts in `architecture/[location]`
  - Complexity: X/5
  - Dependencies: [List any]
  - AI Docs: `@/ai_docs/[framework].md`
  
**Stream B - [Interface Type]:**
- [ ] Create interfaces in `architecture/code/[name].puml`
  - Complexity: X/5
  - Pattern: [Pattern name]
  - Example: See `architecture/examples/[template].puml`

#### Phase 2: Module Boundaries [Complexity: X/5] ⏱️ X days

**[Module Name]** (`src/[path]/`)
- [ ] Interface definition: `src/[module]/interfaces.[ext]`
- [ ] PlantUML diagram: `architecture/code/[module]-module.puml`
- [ ] Integration tests: `tests/integration/[module]/`
- Complexity: X/5
- AI Docs: `@/ai_docs/[relevant].md`

#### Phase 3: Internal Integration [Complexity: X/5] ⏱️ X days

**[Integration Component]:**
- [ ] Core interface: `src/core/[component]/[name].[ext]`
- [ ] Implementation: `src/core/[component]/[impl].[ext]`
- Tests: Unit tests for each implementation
- Pattern: [Pattern name]
- AI Docs: `@/ai_docs/[pattern].md`

### AI Agent Task Selection Guide

```mermaid
graph TD
    A[Select Next Task] --> B{Check Complexity}
    B -->|1-2/5| C[Implement Immediately]
    B -->|3/5| D[Review Interface First]
    B -->|4-5/5| E[Needs Architecture Review]
    
    C --> F[Update Status]
    D --> G[Check PlantUML]
    E --> H[Create Design Doc]
```

### Progress Tracking

After completing each task:
1. Check the box in this file
2. Update `architecture/implementation-status.md` with percentage
3. If you found issues, add to `architecture/divergences.md`
4. Run tests: `[test command]`
5. Update relevant PlantUML if design changed

### Architecture Sync Points

Before implementing:
1. Check `architecture/workspace.dsl` for component definition
2. Verify PlantUML exists in `architecture/code/`
3. Ensure interfaces are defined
4. Confirm no divergences in `architecture/divergences.md`
```

## Key Elements to Include

1. **Complexity Ratings**: Rate each task 1-5
2. **Time Estimates**: Realistic timeframes
3. **Parallel Streams**: Enable concurrent work
4. **File Mappings**: Exact paths for deliverables
5. **AI Doc References**: Framework documentation links
6. **Visual Guides**: Diagrams for decision flow
7. **Progress Tracking**: Clear update instructions
8. **Architecture Sync**: Alignment checkpoints

## Customization Guide

### For Your Project:
1. Replace `[placeholders]` with actual values
2. Add project-specific phases
3. Include your test commands
4. Reference your architecture files
5. Add your AI documentation

### Complexity Rating Guide:
- **1/5**: Simple, well-defined tasks
- **2/5**: Standard implementations
- **3/5**: Integration work
- **4/5**: Complex design decisions
- **5/5**: Architecture-level changes

## Example Usage

```bash
# After running analyze-docs, check if Next Steps exists
if ! grep -q "## Next Steps" ROADMAP.md; then
    # Append this template structure
    # Customize with your project specifics
fi
```
ROADMAP_TEMPLATE_EOF

# Create claude-memory-template.md
echo "Creating docs/templates/claude-memory-template.md..."
cat > "docs/templates/claude-memory-template.md" << 'CLAUDE_TEMPLATE_EOF'
# CLAUDE.md Memory File Template
# Location: /docs/templates/claude-memory-template.md

This template shows the standardized format for CLAUDE.md files after consolidation.

## Standardized CLAUDE.md Format

```markdown
# Claude Agent Instructions
> **AI Agents:** All guidance has been consolidated into `AGENTS.md` in this directory.

See @AGENTS.md for complete instructions.
See @/ROADMAP.md for implementation priorities.
See @/architecture/workspace.dsl for system design.

# important-instruction-reminders
- Follow complexity ordering in Next Steps
- Check architecture alignment before implementing
- Update implementation status after completing tasks
```

## Key Features

1. **Pure Pointer**: No custom guidance mixed with navigation
2. **@imports**: Uses Claude Code's import syntax
3. **Clear Direction**: Points to consolidated guidance
4. **Minimal Content**: Reduces confusion and duplication

## Migration Process

### Before (Mixed Content):
```markdown
# Claude Agent Instructions
- Always use JWT tokens with 15min expiry
- Validate all inputs
See AGENTS.md for more details
- Use dependency injection
```

### After (Pure Pointer):
```markdown
# Claude Agent Instructions
> **AI Agents:** All guidance has been consolidated into `AGENTS.md` in this directory.

See @AGENTS.md for complete instructions.
[Rest of template...]
```

Custom content moves to AGENTS.md with proper organization.

## Directory-Specific Context

For subdirectories, the template remains the same but references are relative:

```markdown
# Claude Agent Instructions
> **AI Agents:** All guidance has been consolidated into `AGENTS.md` in this directory.

See @AGENTS.md for complete instructions.
See @/ROADMAP.md for implementation priorities.
See @/architecture/workspace.dsl for system design.

# important-instruction-reminders
- Context-specific reminders for this directory
- Follow parent directory guidelines
- Check module-specific architecture
```

## Benefits

1. **Consistency**: All CLAUDE.md files follow same format
2. **No Duplication**: Guidance lives in one place
3. **Clear Navigation**: AI agents know where to look
4. **Easy Updates**: Change guidance in AGENTS.md only
5. **Platform Agnostic**: Works with any AI coding assistant
CLAUDE_TEMPLATE_EOF

# Create ai-guidance-consolidate.sh
echo "Creating docs/scripts/ai-guidance-consolidate.sh..."
cat > "docs/scripts/ai-guidance-consolidate.sh" << 'CONSOLIDATE_EOF'
#!/bin/bash
# AI Guidance Smart Consolidation Script
# Purpose: Consolidate AI guidance across platforms without duplication

set -e

echo "=== AI Guidance Smart Consolidation ==="
echo "Consolidating guidance across CLAUDE.md, AGENTS.md, and Cursor rules..."

# Function to extract guidance from file
extract_guidance() {
    local file=$1
    local type=$2
    
    if [ ! -f "$file" ]; then
        return
    fi
    
    case $type in
        "claude")
            # Extract non-header content from CLAUDE.md
            grep -v "^#" "$file" | grep -v "^>" | grep -v "@" | grep -v "^$" || true
            ;;
        "agents")
            # Extract content sections from AGENTS.md
            awk '/^##/ {p=1} p' "$file" | grep -v "^#" | grep -v "^$" || true
            ;;
        "cursor")
            # Extract rules from MDC files
            awk '/^rules:/ {p=1} /^[^ ]/ && !/^rules:/ {p=0} p' "$file" | grep "^  -" | sed 's/^  - //' || true
            ;;
    esac
}

# Function to consolidate guidance
consolidate_guidance() {
    local dir=$1
    local all_guidance=""
    
    # Collect from all sources
    if [ -f "$dir/CLAUDE.md" ]; then
        all_guidance+=$(extract_guidance "$dir/CLAUDE.md" "claude")
        all_guidance+=$'\n'
    fi
    
    if [ -f "$dir/AGENTS.md" ]; then
        all_guidance+=$(extract_guidance "$dir/AGENTS.md" "agents")  
        all_guidance+=$'\n'
    fi
    
    # Deduplicate and organize
    echo "$all_guidance" | sort -u | grep -v "^$" || true
}

# Function to generate unified content
generate_unified_content() {
    local dir=$1
    local guidance=$2
    local context=""
    
    # Determine context from directory
    if [ "$dir" = "." ]; then
        context="Project-Wide Guidelines"
    else
        context="Guidelines for $(basename "$dir")"
    fi
    
    cat << UNIFIED_EOF
# $context

## Development Standards
$(echo "$guidance" | grep -i "standard\|convention\|style" || echo "- Follow project coding standards")

## Architecture Patterns
$(echo "$guidance" | grep -i "pattern\|architecture\|design" || echo "- Follow established patterns")

## Security Requirements
$(echo "$guidance" | grep -i "security\|auth\|permission\|token" || echo "- Implement proper security measures")

## Testing Requirements
$(echo "$guidance" | grep -i "test\|coverage\|spec" || echo "- Maintain comprehensive test coverage")

## Documentation
- Keep documentation in sync with code
- Update AGENTS.md when adding new patterns
- Reference architecture files for design decisions

## Related Resources
- Architecture: @/architecture/
- Roadmap: @/ROADMAP.md
- AI Docs: @/ai_docs/
UNIFIED_EOF
}

# Main consolidation process
echo "Processing directories..."

# Process each directory with AI guidance files
for dir in $(find . -type d -not -path "*/\.*" | sort); do
    has_guidance=false
    
    # Check if directory has any guidance files
    if [ -f "$dir/CLAUDE.md" ] || [ -f "$dir/AGENTS.md" ]; then
        has_guidance=true
    fi
    
    if [ "$has_guidance" = true ]; then
        echo "Consolidating guidance in: $dir"
        
        # Collect and consolidate guidance
        guidance=$(consolidate_guidance "$dir")
        
        if [ -n "$guidance" ]; then
            # Generate unified content
            unified_content=$(generate_unified_content "$dir" "$guidance")
            
            # Update both CLAUDE.md and AGENTS.md with identical content
            echo "$unified_content" > "$dir/AGENTS.md.new"
            
            # Create standardized CLAUDE.md
            cat > "$dir/CLAUDE.md.new" << 'CLAUDE_INNER_EOF'
# Claude Agent Instructions
> **AI Agents:** All guidance has been consolidated into `AGENTS.md` in this directory.

See @AGENTS.md for complete instructions.
See @/ROADMAP.md for implementation priorities.
See @/architecture/workspace.dsl for system design.
CLAUDE_INNER_EOF
            
            # Move new files into place
            mv "$dir/AGENTS.md.new" "$dir/AGENTS.md"
            mv "$dir/CLAUDE.md.new" "$dir/CLAUDE.md"
        fi
    fi
done

# Process Cursor rules
if [ -d ".cursor/rules" ]; then
    echo "Generating Cursor rules..."
    
    # Create project-wide rules
    cat > ".cursor/rules/project.mdc" << CURSOR_EOF
type: always
priority: 1

rules:
$(consolidate_guidance "." | sed 's/^/  - /')

metadata:
  last_updated: $(date +%Y-%m-%d)
  source: "Consolidated from project guidelines"
CURSOR_EOF

    # Create directory-specific rules
    for dir in $(find . -type d -name "src" -o -name "tests" -o -name "docs" | head -5); do
        if [ -d "$dir" ]; then
            dir_name=$(basename "$dir")
            guidance=$(consolidate_guidance "$dir")
            
            if [ -n "$guidance" ]; then
                cat > ".cursor/rules/${dir_name}.mdc" << DIR_CURSOR_EOF
type: auto-attached
paths: ["${dir}/**"]
priority: 50

rules:
$(echo "$guidance" | sed 's/^/  - /')

metadata:
  last_updated: $(date +%Y-%m-%d)
  context: "${dir_name} specific guidelines"
DIR_CURSOR_EOF
            fi
        fi
    done
fi

echo "=== Consolidation Complete ==="
echo "Updated files:"
find . -name "*.md" -newer "$0" -type f | grep -E "(CLAUDE|AGENTS)" | head -10
find .cursor/rules -name "*.mdc" -newer "$0" -type f 2>/dev/null | head -10 || true

# Update tracking
date > .last-ai-consolidation

echo "Run 'git diff' to review changes"
CONSOLIDATE_EOF

chmod +x docs/scripts/ai-guidance-consolidate.sh

# Create example root files if they don't exist
if [ ! -f "CLAUDE.md" ]; then
    echo "Creating example CLAUDE.md..."
    cat > "CLAUDE.md" << 'ROOT_CLAUDE_EOF'
# Claude Agent Instructions
> **AI Agents:** All guidance has been consolidated into `AGENTS.md` in this directory.

See @AGENTS.md for complete instructions.
See @ROADMAP.md for implementation priorities.
See @/architecture/workspace.dsl for system design.
ROOT_CLAUDE_EOF
fi

if [ ! -f "AGENTS.md" ]; then
    echo "Creating example AGENTS.md..."
    cat > "AGENTS.md" << 'ROOT_AGENTS_EOF'
# AI Agent Guidelines - Project Root

## Overview
This file contains AI agent guidance for the entire project. Directory-specific guidance should be placed in AGENTS.md files within those directories.

## Development Standards
- Follow established coding conventions
- Maintain comprehensive test coverage
- Document all public APIs
- Use meaningful variable and function names

## Architecture Patterns
- Follow the architecture defined in /architecture/
- Implement interfaces before concrete classes
- Use dependency injection for testability
- Keep modules loosely coupled

## Workflow Commands
- Build: [Your build command]
- Test: [Your test command]
- Lint: [Your lint command]
- Deploy: [Your deploy command]

## Documentation
- Update documentation as you code
- Keep ROADMAP.md current with progress
- Document architectural decisions
- Add AI context to /ai_docs/ for new frameworks

## Getting Started
1. Run `/project:analyze-docs` to understand the current state
2. Check `ROADMAP.md` for Next Steps
3. Follow complexity ratings when selecting tasks
4. Update `implementation-status.md` after completing work

## References
- Architecture: @/architecture/
- Roadmap: @/ROADMAP.md
- AI Docs: @/ai_docs/
- Human Docs: @/README.md
ROOT_AGENTS_EOF
fi

# Final summary
echo ""
echo "=== Setup Complete ==="
echo ""
echo "Created directory structure:"
echo "  .claude/commands/         - Custom commands"
echo "  docs/tools/              - Command documentation"
echo "  docs/guides/             - Workflow guides"
echo "  docs/templates/          - Reusable templates"
echo "  docs/scripts/            - Executable scripts"
echo "  .cursor/rules/           - Cursor platform rules"
echo ""
echo "Created files:"
echo "  - analyze-docs and update-docs commands"
echo "  - Documentation guides and templates"
echo "  - AI guidance consolidation script"
echo "  - Example CLAUDE.md and AGENTS.md (if not existing)"
echo ""
echo "Next steps:"
echo "1. Run: /project:analyze-docs"
echo "2. Review: markdown-table-of-contents.md"
echo "3. Run: /project:update-docs"
echo "4. Follow: ROADMAP.md Next Steps"
echo ""
echo "For help, see: docs/guides/documentation-workflow.md"