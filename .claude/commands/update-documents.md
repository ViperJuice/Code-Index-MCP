# update-documents

Execute comprehensive documentation synchronization and maintenance for any codebase. Use markdown-table-of-contents.md as the primary reference for all operations.

## EXECUTION_SEQUENCE

1. **Ingest** markdown-table-of-contents.md to understand codebase documentation structure
2. **Execute** IMMEDIATE_CLEANUP actions from the index
3. **Process** CONSOLIDATION_TASKS in parallel where possible
4. **Analyze** architecture files (PlantUML, Structurizr DSL) if present for alignment
5. **Update** hierarchical agent configuration files (AGENTS.md, CLAUDE.md)
6. **Synchronize** IDE configuration files (.cursor/rules, .vscode settings)
7. **Generate** update summary and architecture alignment reports

## DOCUMENTATION_INDEX_INGESTION

**Read** markdown-table-of-contents.md first to understand:
- Current documentation structure and file locations
- Identified maintenance issues (STALE, DUPLICATE, OBSOLETE, ORPHANED)
- Consolidation opportunities and cleanup actions
- Content gaps and missing documentation
- Reference relationships between files

**Execute** operations based on the index data:
- **Run** all IMMEDIATE_CLEANUP bash commands listed
- **Process** CONSOLIDATION_TASKS merge operations
- **Create** missing documentation identified in CONTENT_GAPS
- **Validate** REFERENCE_MAP integrity after changes

## ARCHITECTURE_ANALYSIS_OPERATIONS

**Search** for architecture files in common locations:
- Look for *.puml, *.plantuml files (PlantUML diagrams)
- Look for *.dsl files (Structurizr DSL)
- Check /architecture/, /docs/architecture/, /design/ directories
- Scan /diagrams/, /specs/, /models/ directories

### IF_PLANTUML_FILES_FOUND
**Parse** PlantUML files and:
- **Extract** component definitions and system boundaries
- **Identify** technology stack specifications
- **Map** service relationships and data flows
- **Document** deployment patterns

### IF_STRUCTURIZR_DSL_FOUND
**Parse** Structurizr DSL files and:
- **Extract** system landscape and context boundaries
- **Identify** container and component relationships
- **Catalog** technology choices and constraints
- **Map** external integrations

### GENERATE_ALIGNMENT_REPORT
**Create** architecture alignment report in appropriate directory:
```markdown
# Architecture Documentation Alignment Report
# Auto-generated for AI agent reference

## ARCHITECTURE_FILES_ANALYZED
```
plantuml_files: [list of .puml files found and analyzed]
structurizr_dsl_files: [list of .dsl files found and analyzed]  
architecture_directory: [primary architecture documentation location]
```

## COMPONENT_ANALYSIS
```
defined_components: [components found in architecture files]
documented_components: [components referenced in markdown docs]
missing_documentation: [components in architecture but not documented]
orphaned_documentation: [documented components not in architecture]
```

## TECHNOLOGY_ALIGNMENT
```
architecture_technologies: [tech stack from architecture files]
documentation_technologies: [tech stack mentioned in docs]
mismatches: [inconsistencies between architecture and docs]
```

## AGENT_ACTION_ITEMS
```
config_updates_needed: [agent config files requiring technology alignment]
documentation_gaps: [missing docs for architecture components]
content_corrections: [existing docs needing architecture alignment]
```
```

## AGENT_CONFIGURATION_UPDATES

**Find** and update agent configuration files:
- **Search** for AGENTS.md files throughout directory structure
- **Search** for CLAUDE.md files throughout directory structure
- **Look** for .anthropic/, .claude/ directories with configuration files

**Update** each agent configuration file found:
- **Add** project context from markdown-table-of-contents.md analysis
- **Include** architecture context if architecture files were found
- **Align** technology references with architecture specifications
- **Add** directory-specific development guidance

## IDE_CONFIGURATION_SYNCHRONIZATION

**Search** for IDE configuration directories:
- **Check** for .cursor/rules/ directory and *.mdc files
- **Check** for .vscode/ directory and settings files
- **Check** for .idea/ directory configuration
- **Check** for .anthropic/ or similar AI tool configurations

**Synchronize** found IDE configurations:
- **Align** with agent configuration files
- **Update** technology-specific rules to match architecture
- **Ensure** consistency across configuration files

## CONTENT_CONSOLIDATION

**Execute** consolidation based on markdown-table-of-contents.md analysis:
- **Process** all CONSOLIDATION_TASKS listed in the index
- **Merge** files marked as DUPLICATE with high similarity
- **Integrate** small MERGEABLE files into larger documents
- **Preserve** technical specifications and API references
- **Delete** files marked as OBSOLETE after validation

## CORE_DOCUMENTATION_UPDATES

### UPDATE_PRIMARY_README
**Find** and update main README.md file:
- **Identify** primary README.md (typically at repository root)
- **Sync** architecture overview with any architecture files found
- **Update** technology stack to match architecture specifications
- **Consolidate** setup information from merged documentation
- **Refresh** project status based on current codebase state

### UPDATE_ROADMAP
**Find** and update roadmap documentation:
- **Search** for ROADMAP.md, roadmap.md, or similar files
- **Update** implementation status based on codebase analysis
- **Align** planned features with architecture specifications
- **Focus** next steps on current incomplete phases only
- **Cross-reference** with any implementation gap analysis
- **Update Next-steps section** the roadmap should always end with a next steps section the comprehensively plans the next steps to accomplish in order to complet the last lowest number unfinished phase. It should include a comprehensive plan, including files, classes, methods, .. that need to be modified, added or deleted to complete the phase. It should emphasise using Parallel agentic tools to accomplish this as quickly as possible.

### UPDATE_MASTER_AGENT_CONFIG
**Find** and update primary agent configuration:
- **Identify** root-level CLAUDE.md or primary agent config file
- **Validate** technology stack against architecture files
- **Update** development workflow instructions
- **Sync** integration configurations with system architecture
- **Add** codebase-specific context and conventions

## PARALLEL_TASK_EXECUTION

**Execute** these task groups simultaneously:

**TASK_GROUP_1: Documentation Cleanup**
- **Execute** IMMEDIATE_CLEANUP commands from markdown-table-of-contents.md
- **Process** file deletions and consolidations
- **Validate** link integrity after changes

**TASK_GROUP_2: Architecture Analysis**
- **Search** for and analyze architecture files
- **Extract** component and system specifications
- **Generate** architecture alignment report

**TASK_GROUP_3: Content Consolidation**
- **Execute** merge operations from CONSOLIDATION_TASKS
- **Update** cross-references after merges
- **Preserve** essential technical content

**TASK_GROUP_4: Configuration Synchronization**
- **Update** all found agent configuration files
- **Sync** IDE configuration files
- **Align** configurations with architecture

**TASK_GROUP_5: Core Documentation Updates**
- **Update** primary README and roadmap files
- **Refresh** master agent configuration
- **Generate** comprehensive update summary

## VALIDATION_REQUIREMENTS

**Verify** after all operations:
- **Confirm** no broken internal links in documentation
- **Validate** all agent configuration files are updated and consistent
- **Check** IDE configurations align with agent configs
- **Ensure** architecture files remain unchanged (read-only analysis)
- **Verify** consolidated content preserves essential information
- **Confirm** all cleanup actions completed successfully

## ADAPTIVE_OUTPUT_STRUCTURE

**Maintain** documentation structure based on discovered files:
- **Preserve** existing directory organization
- **Follow** conventions found in markdown-table-of-contents.md
- **Adapt** to project-specific documentation patterns
- **Maintain** hierarchical agent configuration where found

## EXECUTION_TRIGGERS

**Run** this command when:
- Major project changes have been implemented
- Documentation inconsistencies are suspected
- After architectural changes or refactoring
- Before project releases
- When markdown-table-of-contents.md shows maintenance issues
- After adding new features or integrations

## OUTPUT_GENERATION

**Generate** update summary in appropriate location:

```
DOCUMENTATION_UPDATE_SUMMARY.md

CODEBASE_ANALYSIS_COMPLETED:
- Documentation files processed: [count from markdown-table-of-contents.md]
- Agent configuration files updated: [list of AGENTS.md, CLAUDE.md files found]
- IDE configuration files synchronized: [list of config files updated]
- Architecture files analyzed: [list of architecture files found and processed]

CLEANUP_ACTIONS_EXECUTED:
- Files deleted: [list with reasons from IMMEDIATE_CLEANUP]
- Files merged: [consolidation operations performed]
- Broken links fixed: [link integrity improvements]

ARCHITECTURE_ALIGNMENT_RESULTS:
- Architecture files found: [PlantUML, Structurizr DSL, other]
- Documentation gaps identified: [missing docs for architecture components]
- Technology misalignments corrected: [inconsistencies resolved]
- Agent configs updated with architecture context: [list of updates]

VALIDATION_RESULTS:
- Link integrity status: [validation outcome]
- Configuration consistency: [alignment achieved]
- Content preservation: [essential information maintained]
- Structure compliance: [documentation organization maintained]
```

**Execute** all operations to maintain clean, consistent documentation optimized for AI agent consumption while adapting to any codebase structure and conventions.