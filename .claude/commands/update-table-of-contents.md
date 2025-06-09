# AI Agent Markdown Documentation Index Generator

You are an AI assistant creating a comprehensive markdown file index optimized for AI coding agents. The output will be referenced in CLAUDE.md stubs (which point to AGENTS.md) to help agents quickly locate, read, consolidate, or remove markdown documentation.

## Agent-Optimized Analysis

1. **File Discovery and Classification**
   - Locate all markdown files (*.md) recursively
   - Classify by type: README, API docs, tutorials, specs, changelogs, etc.
   -- Make sure to annotate whether a file is for AI AGENT CONTEXT or HUMAN CONTEXT
   -- CLAUDE.md stubs, AGENTS.md, items in .cursor/rules, and .claude/commands directories are all AI AGENT CONTEXT
   -- README.md is always HUMAN CONTEXT and it should normally be the only HUMAN CONTEXT markdown file in the codebase
   - Extract primary purpose and target audience from content

2. **Architecture and Roadmap Integration Analysis**
   - **C4 Model Alignment Discovery**: 
     -- Locate Structurizr DSL files (*.dsl) for C4 Levels 1-3 (Context, Container, Component)
     -- Locate PlantUML files (*.puml) for C4 Level 4 (Code/Implementation)
     -- Cross-reference architectural elements with actual codebase structure
   - **Roadmap Implementation Mapping**:
     -- Parse ROADMAP.md for defined steps/phases
     -- Map roadmap items to architectural components
     -- Assess implementation status for each roadmap item
     -- Identify gaps between planned architecture and current implementation
   - **Complexity Assessment Framework**:
     -- Assign complexity scores (1-5) to roadmap items based on architectural impact
     -- Annotate dependencies between roadmap items
     -- Track implementation effort estimates vs actual completion

3. **Content Fingerprinting**
   - Generate content hash for duplicate detection
   - Extract key topics, code examples, and referenced technologies
   - Identify semantic similarity between files (>70% overlap flagged)
   - **NEW**: Cross-reference architectural concepts between files
   - **NEW**: Map roadmap items mentioned across documentation

4. **Actionability Assessment**
   For each file, determine:
   - **CURRENT**: Active, referenced, up-to-date content
   - **STALE**: Last modified >6 months with version-specific references
   - **DUPLICATE**: Content similarity >70% with another file
   - **ORPHANED**: No references from code or other docs
   - **OBSOLETE**: References deprecated APIs, tools, or processes
   - **MERGEABLE**: Small file (<500 words) that could be consolidated
   - **NEW - MISALIGNED**: Architecture/roadmap content not matching implementation
   - **NEW - COMPLEXITY_MISMATCH**: Roadmap complexity not reflected in architecture

5. **Agent Action Mapping**
   For each flagged file, provide specific agent instructions:
   - Files to read for context
   - Files to merge or consolidate
   - Files to delete with confirmation
   - Files requiring content updates
   - **NEW**: Architecture alignment requirements
   - **NEW**: Roadmap synchronization tasks
   - **NEW**: Next development iteration steps

## Output Format (markdown-table-of-contents.md)

```markdown
# Markdown Documentation Index
# This file is auto-generated for AI agent reference - do not edit manually
# Last updated: [TIMESTAMP]

## AGENT_INSTRUCTIONS
- Use this index to locate relevant documentation before making changes
- Always check MERGE_CANDIDATES before creating new documentation
- Execute CLEANUP_ACTIONS to maintain documentation hygiene
- Reference FILE_PURPOSES when deciding where to add new content
- **NEW**: Consult ARCHITECTURE_ALIGNMENT before modifying system design
- **NEW**: Check ROADMAP_STATUS before planning development iterations

## EXPECTED_FILES_VERIFICATION

## EXPECTED_FILES_VERIFICATION

### MISSING_CRITICAL_FILES
```
# Core project documentation files that should exist
/README.md | status:MISSING | action:CREATE_PROJECT_OVERVIEW | priority:CRITICAL
/ROADMAP.md | status:MISSING | action:CREATE_WITH_TEMPLATE | priority:CRITICAL
/CONTRIBUTING.md | status:MISSING | action:CREATE_CONTRIBUTION_GUIDE | priority:HIGH
/LICENSE | status:MISSING | action:CREATE_LICENSE_FILE | priority:HIGH
/CHANGELOG.md | status:MISSING | action:CREATE_VERSION_HISTORY | priority:MEDIUM
/CODE_OF_CONDUCT.md | status:MISSING | action:CREATE_COMMUNITY_STANDARDS | priority:MEDIUM
/SECURITY.md | status:MISSING | action:CREATE_SECURITY_POLICY | priority:MEDIUM
/.gitignore | status:MISSING | action:CREATE_VCS_EXCLUSIONS | priority:HIGH
/architecture/workspace.dsl | status:MISSING | action:CREATE_STRUCTURIZR_WORKSPACE | priority:HIGH
/architecture/model.dsl | status:MISSING | action:CREATE_MODEL_FRAGMENT | priority:HIGH
/architecture/views.dsl | status:MISSING | action:CREATE_VIEWS_FRAGMENT | priority:HIGH
/CLAUDE.md | status:MISSING | action:CREATE_NAVIGATION_STUB | priority:CRITICAL
/AGENTS.md | status:MISSING | action:CREATE_ROOT_AGENT_CONFIG | priority:CRITICAL
```

### MISSING_DIRECTORIES
```
/docs/ | status:MISSING | action:CREATE_DOCUMENTATION_STRUCTURE | priority:HIGH
/ai_docs/ | status:MISSING | action:CREATE_AI_CONTEXT_DIRECTORY | priority:HIGH
/architecture/ | status:MISSING | action:CREATE_WITH_STRUCTURE | priority:HIGH
/architecture/code/ | status:MISSING | action:CREATE_FOR_LEVEL4_DIAGRAMS | priority:MEDIUM
/architecture/history/ | status:MISSING | action:CREATE_ARCHIVE_DIRECTORY | priority:LOW
/tests/ | status:MISSING | action:CREATE_TESTING_DIRECTORY | priority:HIGH
/scripts/ | status:MISSING | action:CREATE_UTILITY_SCRIPTS_DIR | priority:MEDIUM
/.github/ | status:MISSING | action:CREATE_GITHUB_INTEGRATION | priority:MEDIUM
/.github/workflows/ | status:MISSING | action:CREATE_CI_CD_WORKFLOWS | priority:MEDIUM
/.github/ISSUE_TEMPLATE/ | status:MISSING | action:CREATE_ISSUE_TEMPLATES | priority:LOW
/.cursor/rules/ | status:MISSING | action:CREATE_IF_CURSOR_USED | priority:LOW
```

### EXPECTED_PROJECT_STRUCTURE
```
# Standard software project structure following best practices
/
├── README.md                    # Primary project documentation (HUMAN)
├── ROADMAP.md                   # Development roadmap (HUMAN)
├── CONTRIBUTING.md              # Contribution guidelines (HUMAN)
├── LICENSE                      # License file (LEGAL)
├── CHANGELOG.md                 # Version history (HUMAN)
├── CODE_OF_CONDUCT.md          # Community standards (HUMAN)
├── SECURITY.md                  # Security policy (HUMAN)
├── .gitignore                   # VCS exclusions (TECHNICAL)
├── CLAUDE.md                    # AI agent navigation (AI_AGENT)
├── AGENTS.md                    # AI agent configuration (AI_AGENT)
├── docs/                        # Comprehensive documentation
│   ├── installation.md          # Setup instructions
│   ├── usage.md                 # Usage guide
│   ├── api.md                   # API documentation
│   ├── troubleshooting.md       # Common issues
│   └── examples/                # Code examples
├── ai_docs/                     # AI agent context for libraries/frameworks
│   ├── react.md                 # React framework context (AI_AGENT)
│   ├── nodejs.md                # Node.js context (AI_AGENT)
│   ├── postgres.md              # PostgreSQL context (AI_AGENT)
│   └── README.md                # AI docs directory guide (AI_AGENT)
├── architecture/                # Architectural documentation
│   ├── workspace.dsl            # Main Structurizr workspace (AI_AGENT)
│   ├── model.dsl               # Model fragment (AI_AGENT)
│   ├── views.dsl               # Views fragment (AI_AGENT)
│   ├── code/                   # Level 4 implementation diagrams
│   └── history/                # Archived architecture versions
├── tests/                       # Testing files
├── scripts/                     # Build/utility scripts
└── .github/                     # GitHub integration
    ├── workflows/               # CI/CD workflows
    └── ISSUE_TEMPLATE/         # Issue templates
```

### CONSOLIDATION_OPPORTUNITIES
```
# Files that should be consolidated to follow best practices
MULTIPLE_READMES: /README.md, /docs/README.md, /src/README.md → CONSOLIDATE_TO: /README.md
SCATTERED_INSTALL_GUIDES: /INSTALL.md, /docs/setup.md, /SETUP.md → CONSOLIDATE_TO: /docs/installation.md
DUPLICATE_GETTING_STARTED: /GETTING_STARTED.md, /docs/quickstart.md → CONSOLIDATE_TO: README.md#getting-started
API_DOCUMENTATION_SPRAWL: /API.md, /docs/api/*.md → CONSOLIDATE_TO: /docs/api.md
CHANGELOG_VARIANTS: /HISTORY.md, /RELEASES.md, /NEWS.md → CONSOLIDATE_TO: /CHANGELOG.md
MULTIPLE_CONTRIBUTION_GUIDES: /CONTRIBUTE.md, /docs/contributing.md → CONSOLIDATE_TO: /CONTRIBUTING.md
```

### DOCUMENTATION_CLEANUP_RECOMMENDATIONS
```
# Files that should be relocated or removed
ROOT_CLUTTER: *.md files in root (except standard ones) → MOVE_TO: /docs/ or consolidate
VENDOR_DOCS: Third-party documentation → MOVE_TO: /docs/vendor/ or remove
OUTDATED_GUIDES: Files older than 6 months without updates → REVIEW_FOR_REMOVAL
DUPLICATE_CONTENT: Files with >70% content similarity → CONSOLIDATE
IMPLEMENTATION_NOTES: Developer notes in root → MOVE_TO: /docs/development.md
MEETING_NOTES: Project meeting notes → MOVE_TO: /docs/history/ or remove
```

### C4_MODEL_STATUS
```
Main Workspace: architecture/workspace.dsl | status:CURRENT | includes:[model.dsl,views.dsl] | mapped_to_roadmap:4/5
Model Fragment: architecture/model.dsl | status:CURRENT | elements:12 | mapped_to_roadmap:8/12
Views Fragment: architecture/views.dsl | status:STALE | views:6 | mapped_to_roadmap:4/6
Level 4 (Code): architecture/code/*.puml | status:MISALIGNED | files:8 | implementation_match:60%
```

### ROADMAP_IMPLEMENTATION_STATUS
```
Phase 1: Foundation Setup | status:COMPLETE | complexity:2 | arch_components:[core,database,auth] | completion:100%
Phase 2: Core Features | status:IN_PROGRESS | complexity:3 | arch_components:[api,frontend,services] | completion:65%
Phase 3: Advanced Features | status:PLANNED | complexity:4 | arch_components:[analytics,search,notifications] | completion:20%
Phase 4: Production Ready | status:PLANNED | complexity:3 | arch_components:[deployment,monitoring,scaling] | completion:0%
```

### ALIGNMENT_GAPS
```
CRITICAL: Core service architecture (Level 3) doesn't reflect distributed processing in roadmap Phase 2
MEDIUM: Authentication components missing from architecture but defined in Phase 3 roadmap
LOW: Deployment architecture outdated compared to Phase 4 production plans
```

### COMPLEXITY_ANNOTATIONS
```
High Complexity (5): Real-time data processing, Multi-tenant architecture, Machine learning pipelines
Medium Complexity (3-4): Service integration, Authentication systems, API gateway, Performance optimization
Low Complexity (1-2): Configuration management, Basic CRUD operations, Static file serving
```

## FILE_INVENTORY

### ACTIVE_DOCS
```
/README.md | purpose:project_overview | context:HUMAN | refs:high | status:CURRENT | size:1.2kb | roadmap_refs:[Phase1,Phase2]
/docs/api-reference.md | purpose:api_documentation | context:HUMAN | refs:medium | status:CURRENT | size:8.4kb | arch_level:Level2
/ROADMAP.md | purpose:development_plan | context:HUMAN | refs:high | status:CURRENT | size:3.1kb | phases:4
/architecture/workspace.dsl | purpose:c4_workspace | context:AI_AGENT | refs:high | status:CURRENT | size:2.3kb
/architecture/model.dsl | purpose:c4_model_fragment | context:AI_AGENT | refs:high | status:CURRENT | size:4.7kb
/architecture/views.dsl | purpose:c4_views_fragment | context:AI_AGENT | refs:medium | status:CURRENT | size:1.8kb
/architecture/code/service-layer.puml | purpose:c4_level4 | context:AI_AGENT | refs:medium | status:MISALIGNED | size:1.8kb
```

### MAINTENANCE_REQUIRED
```
/docs/legacy-api.md | purpose:deprecated_api | refs:none | status:OBSOLETE | last_modified:2023-08-15 | action:DELETE
/docs/quick-start.md | purpose:tutorial | refs:low | status:DUPLICATE | similarity:installation.md:85% | action:MERGE_INTO:installation.md
/architecture/old-design.dsl | purpose:c4_outdated | refs:none | status:OBSOLETE | action:ARCHIVE_TO:architecture/history/
/docs/feature-guide-old.md | purpose:feature_guide | status:MISALIGNED | roadmap_phase:Phase2 | action:UPDATE_TO_MATCH:architecture/model.dsl
```

## AGENT_ACTIONS

### IMMEDIATE_CLEANUP
```bash
# Delete obsolete files (no references, deprecated content)
rm docs/legacy-api.md
rm docs/old-deployment-notes.md

# Remove root directory clutter (non-standard markdown files)
rm NOTES.md TODOS.md MEETING_NOTES.md 2>/dev/null

# Archive outdated architecture
mkdir -p architecture/history
mv architecture/old-design.dsl architecture/history/ 2>/dev/null

# Remove duplicate README files
rm src/README.md docs/README.md 2>/dev/null  # Keep only root README.md
```

### CONSOLIDATION_EXECUTION
```bash
# Consolidate installation documentation
cat INSTALL.md SETUP.md docs/setup.md > docs/installation.md 2>/dev/null
rm INSTALL.md SETUP.md docs/setup.md 2>/dev/null

# Consolidate API documentation
mkdir -p docs/
find . -name "*api*.md" -not -path "./docs/api.md" -exec cat {} \; > docs/api.md
find . -name "*api*.md" -not -path "./docs/api.md" -delete

# Consolidate getting started content into README.md
echo -e "\n## Getting Started\n" >> README.md
cat GETTING_STARTED.md docs/quickstart.md >> README.md 2>/dev/null
rm GETTING_STARTED.md docs/quickstart.md 2>/dev/null

# Standardize changelog
if [ -f "HISTORY.md" ] || [ -f "RELEASES.md" ]; then
    cat HISTORY.md RELEASES.md NEWS.md > CHANGELOG.md 2>/dev/null
    rm HISTORY.md RELEASES.md NEWS.md 2>/dev/null
fi
```

### MISSING_STANDARD_FILES_CREATION
```bash
# Create missing standard project files
create_missing_standard_files() {
    [ ! -f "CONTRIBUTING.md" ] && create_contributing_guide
    [ ! -f "CODE_OF_CONDUCT.md" ] && create_code_of_conduct
    [ ! -f "SECURITY.md" ] && create_security_policy
    [ ! -f "CHANGELOG.md" ] && create_changelog_template
    [ ! -f ".gitignore" ] && create_gitignore_template
    [ ! -d ".github" ] && create_github_templates
}
```

### ARCHITECTURE_ALIGNMENT_TASKS
```
SYNC: architecture/model.dsl ↔ ROADMAP.md Phase 2
  REASON: Service layer distributed processing not reflected in model components
  ACTION: Update model.dsl to include message queue and worker components
  COMPLEXITY: Update from 3 to 4 (adds distributed processing)

SYNC: architecture/code/security-*.puml ↔ ROADMAP.md Phase 3  
  REASON: Authentication components planned but not architecturally defined
  ACTION: Create security component diagrams matching roadmap specifications
  COMPLEXITY: 4 (involves authentication, authorization, session management)

UPDATE: architecture/workspace.dsl implementation percentages
  REASON: Service container shows 40% but roadmap Phase 2 is 65% complete
  ACTION: Update implementation annotations to reflect actual progress
```

### ROADMAP_ARCHITECTURE_PROPAGATION
```
ROADMAP_ITEM: "Real-time data processing" (Phase 2)
  → UPDATE: architecture/model.dsl (add ProcessingService component)
  → UPDATE: architecture/code/data-flow.puml (create Level 4 detail)
  → COMPLEXITY: Increase from 3 to 4 (real-time requirements)

ARCHITECTURE_CHANGE: Container split for scalability
  → UPDATE: ROADMAP.md Phase 4 (add container orchestration step)
  → COMPLEXITY: Add new complexity 4 item for container management
```

### CONSOLIDATION_TASKS
```
CONSOLIDATE: docs/quick-start.md + docs/getting-started.md → README.md#getting-started
  REASON: Duplicate getting started content, should be in primary README
  PRESERVE: Code examples and setup commands
  ACTION: Merge into README.md and delete source files

CONSOLIDATE: INSTALL.md + docs/setup.md + SETUP.md → docs/installation.md  
  REASON: Multiple installation guides create confusion
  PRESERVE: Platform-specific instructions
  ACTION: Create comprehensive installation guide

CONSOLIDATE: API.md + docs/api/*.md → docs/api.md
  REASON: API documentation should be centralized
  PRESERVE: All endpoint documentation and examples
  ACTION: Merge into single API reference

CONSOLIDATE: Multiple README files → Single README.md
  REASON: Only one README.md should exist in project root
  PRESERVE: Project-specific information from subdirectory READMEs
  ACTION: Move subdirectory README content to docs/ or consolidate

CONSOLIDATE: HISTORY.md + RELEASES.md + NEWS.md → CHANGELOG.md
  REASON: Version history should follow standard naming
  PRESERVE: All version information and release notes
  ACTION: Create standardized changelog format

RELOCATE: Developer notes from root → docs/development.md
  REASON: Root directory should only contain essential project files
  PRESERVE: All development guidance
  ACTION: Move to docs/ structure
```

### CONTENT_UPDATES_NEEDED
```
docs/deployment.md | STALE | References Docker v19, current is v24
docs/api-examples.md | STALE | Uses deprecated v1 endpoints, update to v2
architecture/code/service-layer.puml | MISALIGNED | Missing distributed processing from roadmap
ROADMAP.md | MISSING_COMPLEXITY | Phase 3 items need complexity scoring
```

## SEMANTIC_CLUSTERS
```
setup_documentation: [README.md, docs/installation.md, docs/quick-start.md]
api_documentation: [docs/api-reference.md, docs/api-examples.md]
deployment_guides: [docs/deployment.md, docs/docker-setup.md]
architecture_docs: [architecture/workspace.dsl, architecture/model.dsl, architecture/views.dsl, architecture/code/*.puml]
roadmap_planning: [ROADMAP.md, docs/project-plan.md]
agent_guidance: [*/CLAUDE.md, */AGENTS.md, .cursor/rules/*.md]
```

## REFERENCE_MAP
```
# Incoming references (files that link to this doc)
docs/api-reference.md ← [src/api/routes.js:12, README.md:45]
docs/installation.md ← [README.md:23, docs/deployment.md:8]
ROADMAP.md ← [architecture/workspace.dsl:15, README.md:67]
architecture/model.dsl ← [ROADMAP.md:34, architecture/workspace.dsl:8]

# Outgoing references (files this doc links to)
README.md → [docs/installation.md, docs/api-reference.md, ROADMAP.md, LICENSE.md]
ROADMAP.md → [architecture/workspace.dsl, docs/api-reference.md]
architecture/workspace.dsl → [architecture/model.dsl, architecture/views.dsl, ROADMAP.md]
```

## CONTENT_GAPS
```
# Missing documentation that should exist based on software development best practices
MISSING: CONTRIBUTING.md (essential for open source projects and team collaboration)
MISSING: CODE_OF_CONDUCT.md (community standards and behavior expectations)
MISSING: SECURITY.md (security vulnerability reporting guidelines)
MISSING: CHANGELOG.md (version history and release notes)
MISSING: LICENSE file (legal requirements and usage rights)
MISSING: .gitignore (version control best practices)
MISSING: docs/installation.md (detailed setup instructions)
MISSING: docs/usage.md (comprehensive usage guide)
MISSING: docs/troubleshooting.md (common issues and solutions)
MISSING: docs/api.md (API reference documentation)

# Missing development infrastructure
MISSING: .github/workflows/ (CI/CD automation)
MISSING: .github/ISSUE_TEMPLATE/ (standardized issue reporting)
MISSING: .github/PULL_REQUEST_TEMPLATE.md (PR guidelines)
MISSING: tests/ directory (testing infrastructure)
MISSING: scripts/ directory (build and utility scripts)

# AI Agent Context Documentation
MISSING: /ai_docs/ directory (AI agent framework/library context)
MISSING: AI docs for detected frameworks (EXPRESS, REDIS, JEST, DOCKER)
STALE: AI docs requiring web search updates (>30 days old)
MISSING: AI docs mapping in roadmap next steps for implementation guidance

# Architecture-Roadmap gaps
MISSING: C4 Level 4 diagrams for Phase 3 authentication components
MISSING: Roadmap complexity justification documentation  
MISSING: Implementation status propagation between architecture levels
MISSING: Feature development guide aligned with current architecture

# Critical structural gaps
MISSING: ROADMAP.md "Next Steps" section with interface hierarchy
MISSING: File-to-architecture mapping in roadmap
MISSING: Parallel execution planning in next steps
MISSING: Container interface specifications before module implementation
MISSING: Interface-first development guidance

# Documentation consolidation needs
CONSOLIDATION_NEEDED: Multiple README files across directories
CONSOLIDATION_NEEDED: Scattered installation/setup guides
CONSOLIDATION_NEEDED: Duplicate API documentation
CONSOLIDATION_NEEDED: Fragmented getting started information
CONSOLIDATION_NEEDED: Multiple changelog/history files
```

## DEVELOPMENT_ITERATION_GUIDANCE
```
# Next steps for AI agent developers (based on roadmap analysis)
PRIORITY_1: Complete Phase 2 distributed processing (architecture misaligned, high impact)
PRIORITY_2: Design Phase 3 authentication architecture (roadmap ready, components undefined)
PRIORITY_3: Update Level 4 diagrams to match current implementation (documentation debt)

# Architectural decisions needed before next iteration
DECISION_NEEDED: Container orchestration strategy (affects Phase 4 complexity)
DECISION_NEEDED: Service communication mechanism (impacts distributed architecture)
DECISION_NEEDED: Caching strategy selection (distributed vs local, complexity varies)
```

## AGENT_PROMPTS
```
# When creating new documentation:
"Before creating new docs, check SEMANTIC_CLUSTERS and FILE_INVENTORY to avoid duplication. Verify alignment with current ROADMAP_IMPLEMENTATION_STATUS. Check CONSOLIDATION_OPPORTUNITIES for existing content that should be merged."

# When modifying architecture:
"Check ARCHITECTURE_ROADMAP_ALIGNMENT section. Update both architecture files AND roadmap complexity annotations. Propagate changes to corresponding C4 levels."

# When planning development iterations:
"Consult DEVELOPMENT_ITERATION_GUIDANCE for prioritized next steps. Ensure architectural decisions are made before implementation begins."

# For maintenance tasks:
"Execute IMMEDIATE_CLEANUP actions first, then CONSOLIDATION_EXECUTION, then ARCHITECTURE_ALIGNMENT_TASKS"

# NEW: For missing file creation:
"Check EXPECTED_FILES_VERIFICATION for missing critical files. Create missing standard project files (CONTRIBUTING.md, LICENSE, etc.) before proceeding with updates."

# NEW: For documentation consolidation:
"Follow software development best practices: single README.md in root, comprehensive docs/ structure, standardized filenames (CONTRIBUTING.md, CHANGELOG.md, etc.). Eliminate documentation sprawl by consolidating duplicate content."

# NEW: For interface-first development:
"Follow ROADMAP Next Steps hierarchy: Container interfaces → Module interfaces → Class interfaces → Implementation. Always define interfaces before implementing logic."

# NEW: For parallel execution planning:
"Structure Next Steps for parallel development streams. Map each step to specific files in both /src and /architecture directories."

# NEW: For project structure compliance:
"Maintain standard project structure: essential files in root, comprehensive docs in docs/, architecture in architecture/, utilities in scripts/. Remove non-standard files from root directory."

# NEW: For AI agent context management:
"Check AI_DOCS_ANALYSIS for stale framework documentation (>30 days). When implementing features, reference corresponding /ai_docs files for framework context. Update stale AI docs using web search before development iterations."

# NEW: For framework detection and documentation:
"Use DETECTED_FRAMEWORKS_MISSING_DOCS to identify technologies that need AI agent context. Create /ai_docs files for commonly used frameworks/libraries. Include source URLs in AI docs for traceability."

# NEW: For roadmap-AI docs integration:
"Check ROADMAP_AI_DOCS_MAPPING when planning implementation. Ensure next steps reference appropriate /ai_docs files for framework guidance. Do not modify roadmap - only document status and implementation plan."
```
```

## Implementation Instructions

1. **Check for existing markdown-table-of-contents.md**
   - If exists, compare timestamps and update incrementally
   - If missing, create complete new index
   - **NEW**: Compare architecture and roadmap timestamps for alignment drift

2. **Content Analysis Depth**
   - Parse first 500 words of each file for classification  
   - Use file path and name patterns for type detection
   - Extract referenced file names, URLs, and version numbers
   - **NEW**: Parse roadmap phases and architectural components
   - **NEW**: Extract complexity indicators and implementation percentages

3. **Architecture-Roadmap Cross-Analysis**
   - **NEW**: Map roadmap items to architectural components across C4 levels
   - **NEW**: Identify implementation gaps between planned and actual architecture
   - **NEW**: Track complexity changes between roadmap versions
   - **NEW**: Validate that each roadmap phase has corresponding architectural representation

4. **Similarity Detection**
   - Compare file content using semantic similarity
   - Flag files with >70% content overlap
   - Prioritize smaller files for merger into larger ones
   - **NEW**: Detect architectural concept duplication across levels
   - **NEW**: Identify roadmap item redundancy

5. **Reference Tracking**
   - Scan all markdown files for internal links
   - Check code files for documentation references
   - Build bidirectional reference map
   - **NEW**: Track roadmap-to-architecture references
   - **NEW**: Map implementation status across documentation types

6. **Action Generation**
   - Generate specific bash commands for file operations
   - Provide merge instructions with content preservation notes
   - Include confirmation prompts for destructive actions
   - **NEW**: Generate architecture alignment commands
   - **NEW**: Create roadmap synchronization instructions
   - **NEW**: Provide next-iteration development guidance

## Agent Usage Examples

```markdown
# In CLAUDE.md stub, reference this index:
"Before modifying documentation, consult markdown-table-of-contents.md for current file inventory, architecture alignment status, and planned changes"

# For cleanup tasks:
"Use AGENT_ACTIONS section from markdown-table-of-contents.md to identify files for removal or consolidation"

# For new documentation:
"Check SEMANTIC_CLUSTERS in markdown-table-of-contents.md to determine optimal file placement"

# NEW: For architecture work:
"Consult ARCHITECTURE_ROADMAP_ALIGNMENT section before modifying any architectural documentation. Ensure changes propagate to corresponding C4 levels and roadmap complexity annotations."

# NEW: For development planning:
"Reference DEVELOPMENT_ITERATION_GUIDANCE for prioritized next steps aligned with current roadmap status and architectural readiness."
```

This command generates a structured, actionable index that AI agents can parse and execute automatically, with clear instructions for maintenance, consolidation, cleanup tasks, and comprehensive architecture-roadmap alignment management.