# update-documents

Execute comprehensive documentation synchronization and maintenance for any codebase, with dynamic discovery and adaptation. Use markdown-table-of-contents.md as the primary reference for all operations.

## PRIMARY_OBJECTIVES

1. **Align all documentation with current codebase state** (dynamically assessed)
2. **Maintain consistent AI agent navigation patterns** (CLAUDE.md → AGENTS.md)
3. **Ensure AGENTS.md files are purpose-specific and non-redundant**
4. **Consolidate and minimize markdown files** while preserving essential information
5. **Update markdown-table-of-contents.md** to reflect all changes

## EXECUTION_SEQUENCE

### PHASE_1: CODEBASE_DISCOVERY_AND_ANALYSIS

#### **Dynamic file discovery:**
```bash
# Get overall project structure
find . -type f -name "*.md" | head -20

# Find all CLAUDE.md files dynamically
find . -name "CLAUDE.md" -type f

# Find all AGENTS.md files dynamically  
find . -name "AGENTS.md" -type f

# Discover architecture files
find . -name "*.dsl" -o -name "*.puml" -o -name "*.plantuml" | grep -E "(architecture|arch|design)"

# Get project tree structure (first 3 levels)
tree -L 3 -I 'node_modules|.git|__pycache__|*.pyc|venv|.venv|htmlcov'
```

#### **Implementation status discovery:**
```bash
# Check for implemented features by scanning code
find . -name "*.py" -type f | wc -l
find . -path "*/plugins/*/plugin.py" -type f | wc -l
find . -name "*test*.py" -o -name "test_*.py" | wc -l

# Check for operational components
ls -la mcp_server/ 2>/dev/null | grep -E "(security|metrics|cache|benchmark)"

# Check for configuration files
find . -name "*.yaml" -o -name "*.yml" -o -name "pyproject.toml" -o -name "requirements.txt"
```

### PHASE_2: GUIDANCE_INGESTION

#### **Read primary guidance files:**
1. **Read** `/markdown-table-of-contents.md` (if exists) for current documentation structure analysis
2. **Read** primary README.md file (discovered via `find . -maxdepth 2 -name "README.md"`)
3. **Scan** for ROADMAP files via `find . -iname "*roadmap*" -name "*.md"`
4. **Analyze** architecture directory structure via `find . -type d -name "*arch*"`

### PHASE_3: CURRENT_STATE_VERIFICATION

#### **Assess implementation completion dynamically:**
```bash
# Count implemented language plugins
plugin_count=$(find . -path "*/plugins/*/plugin.py" -type f | wc -l)

# Check for advanced features by scanning directories
feature_dirs=$(ls mcp_server/ 2>/dev/null | grep -E "(security|metrics|cache|indexer|benchmark)" | wc -l)

# Assess test coverage
test_files=$(find . -name "*test*.py" -o -name "test_*.py" | wc -l)

# Check for operational readiness
operational_files=$(find . -name "Dockerfile" -o -name "docker-compose*" -o -name "Makefile" | wc -l)
```

#### **Calculate completion percentage:**
```bash
# Base calculation on discovered components
total_expected_components=10
actual_components=$((plugin_count + feature_dirs + (test_files > 0 ? 1 : 0) + (operational_files > 0 ? 1 : 0)))
completion_percentage=$((actual_components * 100 / total_expected_components))
```

### PHASE_4: CLAUDE_MD_NAVIGATION_STANDARDIZATION

#### **Discover and update all CLAUDE.md files:**
```bash
# Find all CLAUDE.md files dynamically
claude_files=$(find . -name "CLAUDE.md" -type f)

# For each CLAUDE.md file found, verify it contains standardized navigation content
for file in $claude_files; do
    echo "Processing: $file"
    # Check if corresponding AGENTS.md exists in same directory
    agents_file=$(dirname "$file")/AGENTS.md
    if [ -f "$agents_file" ]; then
        echo "Found corresponding AGENTS.md: $agents_file"
    else
        echo "Missing AGENTS.md for: $file"
    fi
done
```

#### **Standardized CLAUDE.md content template:**
```markdown
# Claude Agent Instructions
> **AI Agents:** Do not modify this file directly. Add any updates to `AGENTS.md` in this directory.

This repository uses `AGENTS.md` for all agent guidance and configuration.
Please refer to the adjacent `AGENTS.md` file in this directory for full
instructions and notes.

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
```

### PHASE_5: AGENTS_MD_PURPOSE_SPECIFIC_UPDATES

#### **Discover AGENTS.md files and determine their context:**
```bash
# Find all AGENTS.md files and analyze their directory context
agents_files=$(find . -name "AGENTS.md" -type f)

for file in $agents_files; do
    dir_path=$(dirname "$file")
    dir_name=$(basename "$dir_path")
    
    echo "AGENTS.md found in: $dir_path"
    echo "Directory context: $dir_name"
    
    # Determine context type based on directory structure
    if [ "$dir_path" = "." ]; then
        echo "Context: Root - Primary Agent Config"
    elif echo "$dir_path" | grep -q "architecture"; then
        echo "Context: Architecture-specific"
    elif echo "$dir_path" | grep -q "mcp_server"; then
        if echo "$dir_path" | grep -q "plugins"; then
            plugin_name=$(echo "$dir_path" | sed 's/.*plugins\///' | sed 's/\/.*//')
            echo "Context: Plugin-specific ($plugin_name)"
        else
            echo "Context: Implementation-specific"
        fi
    else
        echo "Context: Other ($dir_name)"
    fi
done
```

#### **Enhance each AGENTS.md with essential sections (based on Claude Code best practices):**

**For ALL AGENTS.md files, add these required sections:**

```bash
# Dynamically discover and add essential commands
discover_essential_commands() {
    local file_path=$1
    
    # Discover build/test commands from project files
    if [ -f "Makefile" ]; then
        build_cmd=$(grep -E "^build:" Makefile | head -1 | cut -d: -f1)
        test_cmd=$(grep -E "^test:" Makefile | head -1 | cut -d: -f1)
        lint_cmd=$(grep -E "^lint:" Makefile | head -1 | cut -d: -f1)
    elif [ -f "pyproject.toml" ]; then
        build_cmd="pip install -e ."
        test_cmd="pytest"
        lint_cmd="ruff check ."
    fi
    
    # Add ESSENTIAL_COMMANDS section to AGENTS.md
    echo "Adding essential commands to: $file_path"
}

# Discover code style preferences from project
discover_code_style() {
    style_configs=$(find . -name ".pylintrc" -o -name ".flake8" -o -name "pyproject.toml" -o -name "ruff.toml")
    naming_patterns=$(find . -name "*.py" -exec grep -h "^def \|^class " {} \; | head -10)
    
    echo "Found style configs: $style_configs"
    echo "Naming patterns: $naming_patterns"
}

# Apply to each AGENTS.md file
for file in $agents_files; do
    discover_essential_commands "$file"
    discover_code_style
done
```

#### **Update each AGENTS.md based on discovered context:**
- **Root AGENTS.md**: Overall project status, essential commands, team-shared practices, architectural patterns
- **Architecture AGENTS.md**: C4 model usage, PlantUML commands, architecture validation, design patterns
- **MCP Server AGENTS.md**: Implementation patterns, testing requirements, development environment setup
- **Plugin AGENTS.md**: Language-specific commands, Tree-sitter setup, plugin testing, naming conventions

### PHASE_6: ROADMAP_AND_ARCHITECTURE_ALIGNMENT

#### **Discover and update roadmap files:**
```bash
# Find roadmap files dynamically
roadmap_files=$(find . -iname "*roadmap*" -name "*.md")

for file in $roadmap_files; do
    echo "Found roadmap file: $file"
done
```

#### **Dynamic architecture file analysis:**
```bash
# Find architecture files
arch_dsl_files=$(find . -name "*.dsl" -type f)
arch_puml_files=$(find . -name "*.puml" -o -name "*.plantuml" -type f)

echo "Found DSL files: $arch_dsl_files"
echo "Found PlantUML files: $arch_puml_files"

# Analyze architecture directory structure
arch_dirs=$(find . -type d -name "*arch*")
for dir in $arch_dirs; do
    echo "Architecture directory: $dir"
    ls -la "$dir"
done
```

#### **Update status based on discovered implementations:**
- Update implementation percentage based on calculated completion
- Mark discovered language plugins as complete
- Update phase completion based on discovered operational components
- Align architecture files with discovered implementations

### PHASE_7: README_MD_HUMAN_OPTIMIZATION

#### **Discover and update README files:**
```bash
# Find primary README (usually at root)
primary_readme=$(find . -maxdepth 1 -name "README.md" -type f | head -1)

if [ -n "$primary_readme" ]; then
    echo "Primary README found: $primary_readme"
    
    # Check for supported languages by scanning plugins
    supported_languages=$(find . -path "*/plugins/*" -name "plugin.py" -type f | sed 's/.*plugins\///' | sed 's/\/plugin.py//' | sort)
    echo "Discovered supported languages: $supported_languages"
    
    # Check for API endpoints by scanning gateway files
    api_files=$(find . -name "*gateway*" -o -name "*api*" -name "*.py" -type f)
    echo "Found API files: $api_files"
fi
```

### PHASE_8: CLEANUP_AND_CONSOLIDATION

#### **Dynamic discovery of files needing cleanup:**
```bash
# Find summary and analysis files that may need archiving
summary_files=$(find . -maxdepth 1 -name "*SUMMARY*" -o -name "*ANALYSIS*" -o -name "*REPORT*" -name "*.md" -type f)

echo "Found summary files for potential archiving: $summary_files"

# Check if docs/history directory exists, create if needed
if [ ! -d "docs/history" ]; then
    mkdir -p "docs/history"
    echo "Created docs/history directory"
fi

# Find potentially stale documentation
stale_docs=$(find . -name "*.md" -type f -mtime +180 | grep -v "docs/history")
echo "Potentially stale docs (>180 days): $stale_docs"
```

#### **Archive historical files dynamically:**
```bash
# Archive discovered summary files
for file in $summary_files; do
    if [ -f "$file" ]; then
        echo "Archiving: $file"
        mv "$file" "docs/history/"
    fi
done
```

### PHASE_9: CONTENT_GAP_RESOLUTION

#### **Discover missing documentation gaps:**
```bash
# Check for missing plugin documentation
plugin_dirs=$(find . -path "*/plugins/*" -type d -mindepth 3 -maxdepth 3)

for dir in $plugin_dirs; do
    plugin_name=$(basename "$dir")
    echo "Checking plugin: $plugin_name"
    
    if [ ! -f "$dir/AGENTS.md" ]; then
        echo "Missing AGENTS.md for: $plugin_name"
    fi
    
    if [ ! -f "$dir/CLAUDE.md" ]; then
        echo "Missing CLAUDE.md for: $plugin_name"
    fi
done

# Check for missing operational documentation
operational_components=("security" "metrics" "cache" "indexer" "benchmarks")

for component in "${operational_components[@]}"; do
    if [ -d "mcp_server/$component" ] && [ ! -f "mcp_server/$component/README.md" ]; then
        echo "Missing README.md for component: $component"
    fi
done
```

### PHASE_10: ARCHITECTURE_ANALYSIS_OPERATIONS

#### **Dynamic architecture file analysis:**
```bash
# Analyze DSL files for implementation status
for dsl_file in $arch_dsl_files; do
    echo "Analyzing DSL file: $dsl_file"
    
    # Check for implementation status indicators
    grep -n "implementation\." "$dsl_file" || echo "No implementation status found in $dsl_file"
    
    # Check for percentage indicators
    grep -n "%" "$dsl_file" || echo "No percentage indicators found in $dsl_file"
done

# Analyze PlantUML files for actual vs planned
for puml_file in $arch_puml_files; do
    echo "Analyzing PlantUML file: $puml_file"
    
    # Check if it's an "actual" implementation file
    if echo "$puml_file" | grep -q "actual"; then
        echo "Found actual implementation diagram: $puml_file"
    else
        echo "Found planned architecture diagram: $puml_file"
    fi
done
```

### PHASE_11: FINAL_VERIFICATION_PATTERNS

#### **Validate discovered patterns:**
```bash
# Verify CLAUDE.md → AGENTS.md navigation consistency
claude_count=$(find . -name "CLAUDE.md" -type f | wc -l)
agents_count=$(find . -name "AGENTS.md" -type f | wc -l)

echo "Found $claude_count CLAUDE.md files and $agents_count AGENTS.md files"

# Check for orphaned CLAUDE.md files (no corresponding AGENTS.md)
for claude_file in $(find . -name "CLAUDE.md" -type f); do
    agents_file=$(dirname "$claude_file")/AGENTS.md
    if [ ! -f "$agents_file" ]; then
        echo "Orphaned CLAUDE.md (no AGENTS.md): $claude_file"
    fi
done

# Validate internal links (basic check)
md_files=$(find . -name "*.md" -type f)
for file in $md_files; do
    # Check for broken relative links (basic pattern)
    grep -n "\]\(" "$file" | grep -v "http" | head -5
done
```

### PHASE_12: UPDATE_MARKDOWN_TABLE_OF_CONTENTS

#### **Regenerate table of contents based on discoveries:**
```bash
# Count discovered files by type
total_md_files=$(find . -name "*.md" -type f | wc -l)
ai_agent_files=$(find . -name "CLAUDE.md" -o -name "AGENTS.md" -o -path "*/ai_docs/*" -name "*.md" -type f | wc -l)
human_docs=$((total_md_files - ai_agent_files))

echo "Documentation inventory:"
echo "Total markdown files: $total_md_files"
echo "AI agent context files: $ai_agent_files"
echo "Human documentation files: $human_docs"

# Update the table of contents with current state
```

## PARALLEL_TASK_EXECUTION

**Execute** these task groups simultaneously using bash backgrounding:

```bash
# TASK_GROUP_1: File Discovery (run in background)
(
    claude_files=$(find . -name "CLAUDE.md" -type f)
    agents_files=$(find . -name "AGENTS.md" -type f)
    arch_files=$(find . -name "*.dsl" -o -name "*.puml" -type f)
    echo "Discovery complete: $claude_files $agents_files $arch_files"
) &

# TASK_GROUP_2: Implementation Assessment (run in background)
(
    completion_assessment=$(calculate_completion_percentage)
    plugin_discovery=$(find_plugin_implementations)
    echo "Assessment complete: $completion_assessment% with plugins: $plugin_discovery"
) &

# TASK_GROUP_3: Documentation Analysis (run in background)
(
    stale_docs=$(find_stale_documentation)
    missing_docs=$(find_missing_documentation)
    echo "Analysis complete: stale: $stale_docs, missing: $missing_docs"
) &

# Wait for all background tasks
wait
```

## SUCCESS_CRITERIA_CHECKLIST

**Upon completion, verify using dynamic checks:**
```bash
# Dynamic verification script
echo "Verifying documentation update success..."

# Check CLAUDE.md standardization
claude_files=$(find . -name "CLAUDE.md" -type f)
for file in $claude_files; do
    if grep -q "AGENTS.md" "$file"; then
        echo "✓ $file has proper navigation"
    else
        echo "✗ $file missing navigation"
    fi
done

# Check AGENTS.md directory specificity and essential sections
agents_files=$(find . -name "AGENTS.md" -type f)
echo "Found $(echo $agents_files | wc -w) AGENTS.md files"

for file in $agents_files; do
    # Verify essential sections exist (Claude Code best practices)
    essential_sections=("ESSENTIAL_COMMANDS" "CODE_STYLE_PREFERENCES" "ARCHITECTURAL_PATTERNS" "DEVELOPMENT_ENVIRONMENT")
    missing_sections=()
    
    for section in "${essential_sections[@]}"; do
        if ! grep -q "$section" "$file"; then
            missing_sections+=("$section")
        fi
    done
    
    if [ ${#missing_sections[@]} -eq 0 ]; then
        echo "✓ $file has all essential sections"
    else
        echo "✗ $file missing sections: ${missing_sections[*]}"
    fi
    
    # Check for frequently used commands
    if grep -q -E "(build|test|lint|start|install)" "$file"; then
        echo "✓ $file includes workflow commands"
    else
        echo "⚠ $file may need workflow commands"
    fi
done

# Verify no broken internal links
broken_links=$(find_broken_internal_links)
if [ -z "$broken_links" ]; then
    echo "✓ No broken internal links found"
else
    echo "✗ Broken links found: $broken_links"
fi

# Verify status consistency
status_references=$(grep_status_references)
echo "Status references check: $status_references"

# Verify development environment documentation
dev_env_check() {
    for file in $agents_files; do
        if grep -q -E "(python|pip|pytest|requirements|venv)" "$file"; then
            echo "✓ $file documents development setup"
        else
            echo "⚠ $file may need development environment details"
        fi
    done
}
dev_env_check
```

## VALIDATION_REQUIREMENTS

**Dynamic validation using bash commands:**
```bash
# Link integrity check
validate_links() {
    find . -name "*.md" -type f -exec grep -l "\](" {} \; | while read file; do
        echo "Checking links in: $file"
        # Extract and validate relative links
        grep -o "\]([^)]*)" "$file" | grep -v "http" | sed 's/\](\([^)]*\))/\1/' | while read link; do
            if [ ! -f "$(dirname "$file")/$link" ] && [ ! -f "$link" ]; then
                echo "Broken link in $file: $link"
            fi
        done
    done
}

# Configuration consistency check
validate_configs() {
    find . -name "AGENTS.md" -type f | while read file; do
        dir_context=$(dirname "$file")
        echo "Validating config consistency for: $dir_context"
        # Add context-specific validation
    done
}

# Architecture alignment check
validate_architecture() {
    dsl_files=$(find . -name "*.dsl" -type f)
    if [ -n "$dsl_files" ]; then
        echo "Validating architecture alignment..."
        for file in $dsl_files; do
            implementation_refs=$(grep -c "implementation\." "$file" 2>/dev/null || echo "0")
            echo "Implementation references in $file: $implementation_refs"
        done
    fi
}
```

## IMPORTANT_NOTES

- **Dynamic Discovery**: Always use `find`, `grep`, `ls`, and `tree` commands to discover current codebase state
- **Adapt to Changes**: Don't hardcode file paths or counts - discover them dynamically
- **Preserve Patterns**: Maintain established navigation patterns regardless of file locations
- **Validate Dynamically**: Use bash commands to verify success rather than assumptions
- **Background Processing**: Use bash backgrounding for parallel task execution
- **Error Handling**: Check for file existence before operations

## AGENTS_MD_OPTIMIZATION_REQUIREMENTS

**Essential Content for AGENTS.md Files** (based on Claude Code best practices):

### **Developer Workflow Commands**
```bash
# Discover and document frequently used commands
project_commands=$(find . -name "Makefile" -o -name "package.json" -o -name "pyproject.toml" | head -1)

if [ -f "Makefile" ]; then
    build_commands=$(grep -E "^[a-zA-Z_-]+:" Makefile | head -5)
    echo "Build commands found: $build_commands"
elif [ -f "package.json" ]; then
    npm_scripts=$(grep -A 20 '"scripts"' package.json | grep '"' | head -5)
    echo "NPM scripts found: $npm_scripts"
elif [ -f "pyproject.toml" ]; then
    python_commands="pytest, pip install -e ., python -m mcp_server"
    echo "Python commands: $python_commands"
fi
```

### **Required AGENTS.md Sections** (Include in every AGENTS.md file):

#### **1. ESSENTIAL_COMMANDS Section**
```markdown
## ESSENTIAL_COMMANDS
- **Build**: `make build` or discovered build command
- **Test**: `pytest` or discovered test command  
- **Lint**: `make lint` or discovered linting command
- **Start**: Server/application start command
- **Install**: Dependency installation command
```

#### **2. CODE_STYLE_PREFERENCES Section**
```bash
# Dynamically discover code style from existing files
style_configs=$(find . -name ".pylintrc" -o -name ".flake8" -o -name "pyproject.toml" -o -name ".eslintrc*" -o -name "prettier.config.*")

for config in $style_configs; do
    echo "Found style config: $config"
done

# Include discovered preferences in AGENTS.md
```

#### **3. ARCHITECTURAL_PATTERNS Section**
```markdown
## ARCHITECTURAL_PATTERNS
- **Plugin Pattern**: All language plugins inherit from PluginBase
- **MCP Protocol**: FastAPI gateway exposes standardized tool interface
- **Tree-sitter Integration**: Use TreeSitterWrapper for parsing
- **Error Handling**: All functions return Result[T, Error] pattern
- **Testing**: pytest with fixtures, >80% coverage required
```

#### **4. NAMING_CONVENTIONS Section**  
```bash
# Discover naming patterns from codebase
function_patterns=$(find . -name "*.py" -exec grep -h "^def " {} \; | head -10)
class_patterns=$(find . -name "*.py" -exec grep -h "^class " {} \; | head -5)
file_patterns=$(find . -name "*.py" | head -10 | xargs basename)

echo "Function naming: $function_patterns"
echo "Class naming: $class_patterns"  
echo "File naming: $file_patterns"
```

#### **5. DEVELOPMENT_ENVIRONMENT Section**
```markdown
## DEVELOPMENT_ENVIRONMENT
- **Python Version**: 3.8+ (check pyproject.toml)
- **Virtual Environment**: Required (`python -m venv venv`)
- **Dependencies**: `pip install -r requirements.txt`
- **Pre-commit Hooks**: Configured for linting and formatting
- **IDE Setup**: VS Code settings in .vscode/ (if present)
```

### **Context-Specific AGENTS.md Requirements**:

#### **Root AGENTS.md** (Project Overview):
- Project completion status (reference ROADMAP.md)
- High-level architecture decisions
- Cross-component integration patterns
- Development workflow and contribution process

#### **Plugin AGENTS.md** (Language-Specific):
- Language-specific parsing requirements
- Tree-sitter grammar setup commands
- Plugin testing and validation steps
- Integration with Tree-sitter wrapper patterns

#### **Architecture AGENTS.md** (Design Documentation):
- C4 model level explanations
- PlantUML generation commands
- Architecture validation requirements
- Component interaction patterns

### **Memory Enhancement Patterns**:

#### **Team-Shared Instructions** (Include in all AGENTS.md):
```markdown
## TEAM_SHARED_PRACTICES
- **Testing**: Always run `pytest` before committing
- **Documentation**: Update AGENTS.md when adding new patterns
- **Plugin Development**: Follow established PluginBase interface
- **Error Messages**: Include context and suggested fixes
- **Performance**: Target <100ms symbol lookup, <500ms search
```

#### **Individual Agent Preferences** (Context-specific):
```markdown
## AGENT_PREFERENCES
- **Code Generation**: Prefer composition over inheritance
- **Testing Strategy**: Unit tests for logic, integration for workflows
- **Documentation Style**: Code examples over theoretical explanations
- **Error Handling**: Explicit error types, no silent failures
```

## OUTPUT_GENERATION

**Generate** comprehensive update summary using discovered data:

```bash
# Generate dynamic summary
cat > "DOCUMENTATION_UPDATE_SUMMARY_$(date +%Y-%m-%d).md" << EOF
# Documentation Update Summary - $(date)

## DYNAMIC_CODEBASE_ANALYSIS
- Total markdown files discovered: $(find . -name "*.md" -type f | wc -l)
- CLAUDE.md navigation stubs found: $(find . -name "CLAUDE.md" -type f | wc -l)
- AGENTS.md configuration files found: $(find . -name "AGENTS.md" -type f | wc -l)
- Language plugins discovered: $(find . -path "*/plugins/*/plugin.py" -type f | wc -l)
- Architecture files found: $(find . -name "*.dsl" -o -name "*.puml" -type f | wc -l)

## IMPLEMENTATION_STATUS_CALCULATED
- Completion percentage: $(calculate_completion_percentage)%
- Operational components: $(ls mcp_server/ 2>/dev/null | grep -E "(security|metrics|cache)" | wc -l)
- Test coverage files: $(find . -name "*test*.py" | wc -l)

## DYNAMIC_UPDATES_EXECUTED
- CLAUDE.md files standardized: $(standardize_claude_files)
- AGENTS.md files updated for context: $(update_agents_files)
- Architecture files aligned: $(align_architecture_files)
- Documentation gaps addressed: $(address_gaps)

## VALIDATION_RESULTS
- Link integrity: $(validate_links | grep "✓" | wc -l) passed, $(validate_links | grep "✗" | wc -l) failed
- Navigation consistency: $(validate_navigation)
- Status alignment: $(validate_status_alignment)
EOF
```

**Execute** all operations dynamically to maintain clean, consistent documentation that adapts to any codebase structure while accurately reflecting the current implementation state.

## CLAUDE_CODE_OPTIMIZATIONS

The updated command now incorporates **Claude Code best practices** for AGENTS.md optimization:

### **Key Enhancements**:
1. **Essential Commands Discovery** - Automatically finds and documents build, test, lint commands
2. **Code Style Detection** - Discovers existing style configs and naming conventions  
3. **Architectural Pattern Documentation** - Ensures patterns specific to the project are documented
4. **Development Environment Setup** - Includes dependencies, virtual environment, and IDE setup
5. **Team-Shared vs Individual Preferences** - Distinguishes between team practices and agent-specific preferences

### **Memory Enhancement Benefits**:
- **Reduced Command Searches** - Frequently used commands documented in every AGENTS.md
- **Consistent Code Style** - Style preferences discovered and documented automatically
- **Better Agent Performance** - Configured dev environments and clear patterns improve agent effectiveness
- **Team Alignment** - Shared practices documented consistently across all AGENTS.md files

### **Dynamic Adaptation**:
- Commands discovered from Makefile, package.json, or pyproject.toml
- Style configs found automatically (.pylintrc, .flake8, pyproject.toml)  
- Naming patterns extracted from existing codebase
- Development setup tailored to discovered technology stack

This ensures that **every AGENTS.md file** becomes a comprehensive guide that helps both human developers and AI agents navigate the codebase effectively.