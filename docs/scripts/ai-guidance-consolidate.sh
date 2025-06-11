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
