#!/bin/bash
# ai-guidance-sync.sh - Bidirectional sync for AI guidance files

LAST_SYNC_FILE=".last-ai-sync"
SYNC_LOG="ai-guidance-sync.log"

# Initialize sync tracking
init_sync() {
    if [ ! -f "$LAST_SYNC_FILE" ]; then
        echo "1970-01-01 00:00:00" > "$LAST_SYNC_FILE"
        echo "Initialized AI guidance sync tracking"
    fi
}

# Find all AI guidance files with their directory context
find_guidance_files() {
    echo "=== Finding AI Guidance Files ===" >> "$SYNC_LOG"
    
    # Find all CLAUDE.md files
    find . -name "CLAUDE.md" -type f | while read file; do
        echo "CLAUDE:$file:$(stat -c %Y "$file" 2>/dev/null || stat -f %m "$file")"
    done > .guidance-files-claude
    
    # Find all AGENTS.md files
    find . -name "AGENTS.md" -type f | while read file; do
        echo "AGENTS:$file:$(stat -c %Y "$file" 2>/dev/null || stat -f %m "$file")"
    done > .guidance-files-agents
    
    # Find Cursor rules (only at root)
    if [ -d ".cursor/rules" ]; then
        find .cursor/rules -name "*.mdc" -type f | while read file; do
            echo "CURSOR:$file:$(stat -c %Y "$file" 2>/dev/null || stat -f %m "$file")"
        done > .guidance-files-cursor
    else
        touch .guidance-files-cursor
    fi
}

# Detect changes since last sync
detect_changes() {
    local last_sync=$(cat "$LAST_SYNC_FILE")
    echo "=== Detecting Changes Since $last_sync ===" >> "$SYNC_LOG"
    
    # Find changed files
    find . \( -name "CLAUDE.md" -o -name "AGENTS.md" \) -newer "$LAST_SYNC_FILE" > .changed-files
    
    if [ -d ".cursor/rules" ]; then
        find .cursor/rules -name "*.mdc" -newer "$LAST_SYNC_FILE" >> .changed-files
    fi
    
    local change_count=$(wc -l < .changed-files)
    echo "Found $change_count changed files" >> "$SYNC_LOG"
    
    return $change_count
}

# Extract new content from CLAUDE.md
extract_claude_additions() {
    local file=$1
    local temp_file=".claude-extract-$"
    
    # Extract bullet points that might be from # shortcut
    grep "^- " "$file" | grep -v "Synced from" > "$temp_file"
    
    # Also extract any @imports
    grep "^.*@[^ ]*" "$file" | grep -v "^#" >> "$temp_file"
    
    echo "$temp_file"
}

# Extract new content from AGENTS.md
extract_agents_additions() {
    local file=$1
    local temp_file=".agents-extract-$"
    
    # Extract sections that aren't sync markers
    awk '
        /^## / && !/Synced from/ { in_section=1; print }
        in_section && /^## / { in_section=0 }
        in_section && /^[^#]/ && NF { print }
    ' "$file" > "$temp_file"
    
    echo "$temp_file"
}

# Extract new content from Cursor MDC files
extract_cursor_additions() {
    local file=$1
    local temp_file=".cursor-extract-$"
    
    # Extract content after metadata
    awk '
        /^---$/ { if (++dash == 2) { in_content=1; next } }
        in_content && !/Synced from/ { print }
    ' "$file" > "$temp_file"
    
    echo "$temp_file"
}

# Sync content between files in the same directory
sync_directory_pair() {
    local dir=$1
    local claude_file="$dir/CLAUDE.md"
    local agents_file="$dir/AGENTS.md"
    
    echo "Syncing directory: $dir" >> "$SYNC_LOG"
    
    # Check which files exist and need syncing
    if [ -f "$claude_file" ] && [ -f "$agents_file" ]; then
        # Both exist - check for changes
        if [ "$claude_file" -nt "$agents_file" ]; then
            echo "  Claude → Agents sync needed" >> "$SYNC_LOG"
            sync_claude_to_agents "$claude_file" "$agents_file"
        elif [ "$agents_file" -nt "$claude_file" ]; then
            echo "  Agents → Claude sync needed" >> "$SYNC_LOG"
            sync_agents_to_claude "$agents_file" "$claude_file"
        fi
    elif [ -f "$claude_file" ] && [ ! -f "$agents_file" ]; then
        echo "  Creating missing AGENTS.md" >> "$SYNC_LOG"
        create_agents_from_claude "$claude_file" "$dir"
    elif [ ! -f "$claude_file" ] && [ -f "$agents_file" ]; then
        echo "  Creating missing CLAUDE.md" >> "$SYNC_LOG"
        create_claude_from_agents "$agents_file" "$dir"
    fi
}

# Sync from CLAUDE.md to AGENTS.md
sync_claude_to_agents() {
    local claude_file=$1
    local agents_file=$2
    local date_marker=$(date +"%Y-%m-%d")
    
    # Extract new content
    local extract=$(extract_claude_additions "$claude_file")
    
    if [ -s "$extract" ]; then
        # Check if sync section exists
        if ! grep -q "## Synced from Claude Code" "$agents_file"; then
            echo "" >> "$agents_file"
            echo "## Synced from Claude Code" >> "$agents_file"
            echo "*Last sync: $date_marker*" >> "$agents_file"
            echo "" >> "$agents_file"
        else
            # Update sync date
            sed -i "s/*Last sync: .*/*Last sync: $date_marker*/" "$agents_file"
        fi
        
        # Add new content
        cat "$extract" >> "$agents_file"
    fi
    
    rm -f "$extract"
}

# Sync from AGENTS.md to CLAUDE.md
sync_agents_to_claude() {
    local agents_file=$1
    local claude_file=$2
    local date_marker=$(date +"%Y-%m-%d")
    
    # For CLAUDE.md, we need to maintain memory format
    local extract=$(extract_agents_additions "$agents_file")
    
    if [ -s "$extract" ]; then
        # Add before the "Note" section if it exists
        if grep -q "^# Note" "$claude_file"; then
            # Insert before Note
            local line_num=$(grep -n "^# Note" "$claude_file" | head -1 | cut -d: -f1)
            {
                head -n $((line_num - 1)) "$claude_file"
                echo ""
                echo "# Synced from Codex ($date_marker)"
                sed 's/^/- /' "$extract" | grep -v "^- $"
                echo ""
                tail -n +$line_num "$claude_file"
            } > "$claude_file.tmp" && mv "$claude_file.tmp" "$claude_file"
        else
            # Append at end
            echo "" >> "$claude_file"
            echo "# Synced from Codex ($date_marker)" >> "$claude_file"
            sed 's/^/- /' "$extract" | grep -v "^- $" >> "$claude_file"
        fi
    fi
    
    rm -f "$extract"
}

# Create missing AGENTS.md from CLAUDE.md
create_agents_from_claude() {
    local claude_file=$1
    local dir=$2
    
    cat > "$dir/AGENTS.md" << EOAGENTS
# AI Agent Instructions for $dir

## CONTEXT
This directory contains $(basename "$dir")-specific components.

## Synced from Claude Code
*Created from CLAUDE.md on $(date +"%Y-%m-%d")*

EOAGENTS
    
    # Extract relevant content from CLAUDE.md
    extract_claude_additions "$claude_file" >> "$dir/AGENTS.md"
}

# Create missing CLAUDE.md from AGENTS.md
create_claude_from_agents() {
    local agents_file=$1
    local dir=$2
    
    cat > "$dir/CLAUDE.md" << EOCLAUDE
# $(basename "$dir") Instructions

See @../CLAUDE.md for project-wide standards.

# Component-Specific Guidance
EOCLAUDE
    
    # Extract key points from AGENTS.md
    local extract=$(extract_agents_additions "$agents_file")
    if [ -s "$extract" ]; then
        echo "" >> "$dir/CLAUDE.md"
        echo "# Synced from Codex ($(date +"%Y-%m-%d"))" >> "$dir/CLAUDE.md"
        sed 's/^/- /' "$extract" | grep -v "^- $" >> "$dir/CLAUDE.md"
    fi
    
    echo "" >> "$dir/CLAUDE.md"
    echo "# Note" >> "$dir/CLAUDE.md"
    echo "For detailed AI agent instructions, see AGENTS.md in this directory." >> "$dir/CLAUDE.md"
}

# Sync to Cursor rules
sync_to_cursor_rules() {
    local source_type=$1
    local content_file=$2
    local rule_name=${3:-"project"}
    local mdc_file=".cursor/rules/${rule_name}.mdc"
    
    if [ ! -d ".cursor/rules" ]; then
        mkdir -p .cursor/rules
    fi
    
    # Create or update MDC file
    if [ ! -f "$mdc_file" ]; then
        cat > "$mdc_file" << EOMDC
---
type: always
created: $(date +"%Y-%m-%d")
sources: ["$source_type"]
---

# $rule_name Rules

EOMDC
    fi
    
    # Add synced content
    echo "" >> "$mdc_file"
    echo "## Synced from $source_type ($(date +"%Y-%m-%d"))" >> "$mdc_file"
    cat "$content_file" >> "$mdc_file"
}

# Main sync process
main() {
    echo "=== AI Guidance Sync Started at $(date) ===" > "$SYNC_LOG"
    
    init_sync
    find_guidance_files
    
    if ! detect_changes; then
        echo "No changes detected since last sync" >> "$SYNC_LOG"
        exit 0
    fi
    
    # Process each directory
    find . -type d | while read dir; do
        if [ -f "$dir/CLAUDE.md" ] || [ -f "$dir/AGENTS.md" ]; then
            sync_directory_pair "$dir"
        fi
    done
    
    # Handle root-level Cursor sync
    if grep -q "^\./" .changed-files | grep -E "(CLAUDE|AGENTS)\.md$"; then
        echo "Syncing root guidance to Cursor rules" >> "$SYNC_LOG"
        
        # Extract root guidance
        if [ -f "./CLAUDE.md" ]; then
            extract_claude_additions "./CLAUDE.md" > .claude-root-extract
            if [ -s .claude-root-extract ]; then
                sync_to_cursor_rules "claude-code" .claude-root-extract "project"
            fi
            rm -f .claude-root-extract
        fi
        
        if [ -f "./AGENTS.md" ]; then
            extract_agents_additions "./AGENTS.md" > .agents-root-extract
            if [ -s .agents-root-extract ]; then
                sync_to_cursor_rules "codex" .agents-root-extract "project"
            fi
            rm -f .agents-root-extract
        fi
    fi
    
    # Update sync timestamp
    date > "$LAST_SYNC_FILE"
    
    # Cleanup
    rm -f .guidance-files-* .changed-files .*-extract-*
    
    echo "=== AI Guidance Sync Completed at $(date) ===" >> "$SYNC_LOG"
    echo "Sync complete. See $SYNC_LOG for details."
}

# Run main process
main "$@"
