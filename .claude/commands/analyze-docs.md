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
