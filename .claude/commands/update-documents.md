# update-documents

Execute comprehensive documentation synchronization and maintenance for any codebase, with dynamic discovery and adaptation. Use markdown-table-of-contents.md as the primary reference for all operations.

## PRIMARY_OBJECTIVES

1. **Align all documentation with current codebase state** (dynamically assessed)
2. **Maintain consistent AI agent navigation patterns** (CLAUDE.md → AGENTS.md)
3. **Ensure AGENTS.md files are purpose-specific and non-redundant**
4. **Consolidate and minimize markdown files** while preserving essential information
5. **Update markdown-table-of-contents.md** to reflect all changes
6. **NEW: Execute architecture-roadmap alignment with complexity tracking**
7. **NEW: Separate human-centric from AI agent-optimized content**
8. **NEW: Generate next-iteration development guidance for AI agents**

## EXECUTION_SEQUENCE

### PHASE_0: CRITICAL_FILES_AND_STRUCTURE_CREATION

#### **Create missing critical files and directories:**
```bash
# Create architecture directory structure if missing
create_architecture_structure() {
    echo "=== Creating Architecture Directory Structure ==="
    
    if [ ! -d "architecture" ]; then
        mkdir -p architecture/{code,history}
        echo "Created architecture directory structure"
    fi
    
    if [ ! -d "architecture/code" ]; then
        mkdir -p architecture/code
        echo "Created architecture/code directory"
    fi
    
    if [ ! -d "architecture/history" ]; then
        mkdir -p architecture/history
        echo "Created architecture/history directory"
    fi
    
    if [ ! -d "docs" ]; then
        mkdir -p docs
        echo "Created docs directory"
    fi
    
    # Create ai_docs directory structure
    if [ ! -d "ai_docs" ]; then
        mkdir -p ai_docs
        echo "Created ai_docs directory"
        create_ai_docs_readme
    fi
    
    # Create source directory structure based on project type
    if [ -f "package.json" ]; then
        mkdir -p src/{interfaces,components,services,utils} 2>/dev/null
        echo "Created JavaScript/TypeScript source structure"
    elif [ -f "pyproject.toml" ] || [ -f "requirements.txt" ]; then
        mkdir -p src/{interfaces,services,repositories,utils} 2>/dev/null
        echo "Created Python source structure"
    elif [ -f "pom.xml" ]; then
        mkdir -p src/main/java/{interfaces,services,repositories,utils} 2>/dev/null
        echo "Created Java source structure"
    elif [ -f "go.mod" ]; then
        mkdir -p {interfaces,services,repositories,utils} 2>/dev/null
        echo "Created Go source structure"
    else
        mkdir -p src/{interfaces,services,utils} 2>/dev/null
        echo "Created generic source structure"
    fi
}

# Create missing C4 architecture files
create_missing_c4_files() {
    echo "=== Creating Missing Structurizr DSL Files ==="
    
    if [ ! -f "architecture/workspace.dsl" ]; then
        create_workspace_dsl
    fi
    
    if [ ! -f "architecture/model.dsl" ]; then
        create_model_dsl
    fi
    
    if [ ! -f "architecture/views.dsl" ]; then
        create_views_dsl
    fi
    
    # Create Level 4 PlantUML templates
    create_level4_plantuml_templates
}

# Create missing core documentation files
create_missing_core_docs() {
    echo "=== Creating Missing Core Documentation ==="
    
    if [ ! -f "ROADMAP.md" ]; then
        create_roadmap_template
    fi
    
    if [ ! -f "CLAUDE.md" ]; then
        create_root_claude_md
    fi
    
    if [ ! -f "AGENTS.md" ]; then
        create_root_agents_md
    fi
    
    # Create missing standard project files
    create_missing_standard_files
}

# Create standard project files following best practices
create_missing_standard_files() {
    echo "=== Creating Missing Standard Project Files ==="
    
    [ ! -f "CONTRIBUTING.md" ] && create_contributing_guide
    [ ! -f "CODE_OF_CONDUCT.md" ] && create_code_of_conduct
    [ ! -f "SECURITY.md" ] && create_security_policy
    [ ! -f "CHANGELOG.md" ] && create_changelog_template
    [ ! -f "LICENSE" ] && create_license_template
    [ ! -f ".gitignore" ] && create_gitignore_template
    [ ! -d ".github" ] && create_github_templates
    [ ! -d "tests" ] && create_tests_directory
    [ ! -d "scripts" ] && create_scripts_directory
}

create_architecture_structure
create_missing_c4_files
create_missing_core_docs
```

#### **File creation functions:**
```bash
create_workspace_dsl() {
    cat > "architecture/workspace.dsl" << 'EOF'
workspace "System Architecture" "Main C4 architecture workspace" {
    
    !identifiers hierarchical
    !impliedRelationships false
    
    !include model.dsl
    !include views.dsl
    
    configuration {
        scope landscape
        visibility public
    }
}
EOF
    echo "Created architecture/workspace.dsl"
}

create_model_dsl() {
    cat > "architecture/model.dsl" << 'EOF'
model {
    # Define actors/users
    user = person "User" "Primary system user"
    
    # Define the main system
    mainSystem = softwareSystem "Main System" "Core application system" {
        # Implementation status: 0% - Define containers first
        
        # Define containers within the main system
        webApp = container "Web Application" "Frontend application" "React/Vue/Angular" {
            # Implementation: 0% - Create container interface first
        }
        
        apiGateway = container "API Gateway" "API routing and management" "Express/FastAPI/Spring" {
            # Implementation: 0% - Define external API interface
            
            # Define components within API Gateway
            authComponent = component "Authentication" "User authentication and authorization" {
                # Implementation: 0% - Define auth interface first
            }
            
            routingComponent = component "Request Router" "Route requests to appropriate services" {
                # Implementation: 0% - Define routing interface
            }
            
            validationComponent = component "Input Validation" "Validate incoming requests" {
                # Implementation: 0% - Define validation interface
            }
        }
        
        database = container "Database" "Data persistence layer" "PostgreSQL/MongoDB" {
            # Implementation: 0% - Define data access interface
        }
    }
    
    # Define external systems
    externalSystem = softwareSystem "External System" "Third-party integrations" {
        external true
    }
    
    # Define relationships
    user -> webApp "Uses" "HTTPS"
    webApp -> apiGateway "API calls" "JSON/HTTPS"
    apiGateway -> database "Reads/Writes" "SQL/NoSQL"
    mainSystem -> externalSystem "Integrates with"
    
    # Define component relationships
    routingComponent -> authComponent "Authenticates requests"
    routingComponent -> validationComponent "Validates input"
    authComponent -> database "Stores user data"
    
    # Production deployment environment
    live = deploymentEnvironment "Production" {
        deploymentNode "Production Server" "Linux server" "Ubuntu 20.04" {
            webServerInstance = containerInstance webApp
            apiServerInstance = containerInstance apiGateway
        }
        
        deploymentNode "Database Server" "Database server" "Ubuntu 20.04" {
            databaseInstance = containerInstance database
        }
        
        # Define deployment relationships
        webServerInstance -> apiServerInstance "API calls" "HTTPS"
        apiServerInstance -> databaseInstance "Database calls" "SQL"
    }
}
EOF
    echo "Created architecture/model.dsl"
}

create_views_dsl() {
    cat > "architecture/views.dsl" << 'EOF'
views {
    # System landscape view showing all systems
    systemLandscape "SystemLandscape" "System landscape diagram" {
        include *
        autoLayout
    }
    
    # System context view for the main system
    systemContext mainSystem "MainSystemContext" "System context diagram for Main System" {
        include *
        autoLayout
    }
    
    # Container view showing internal structure
    container mainSystem "MainSystemContainers" "Container diagram for Main System" {
        include *
        autoLayout
    }
    
    # Component view for API Gateway
    component apiGateway "APIGatewayComponents" "Component diagram for API Gateway" {
        include *
        autoLayout
    }
    
    # Deployment view for production environment
    deployment mainSystem "live" "ProductionDeployment" "Production deployment diagram" {
        include *
        autoLayout
    }
    
    # Custom styles
    styles {
        element "Person" {
            color #ffffff
            background #08427b
            shape person
        }
        element "Software System" {
            color #ffffff
            background #1168bd
        }
        element "Container" {
            color #ffffff
            background #438dd5
        }
        element "Component" {
            color #000000
            background #85bbf0
        }
        element "External Software System" {
            background #999999
        }
        element "Deployment Node" {
            color #ffffff
            background #5d6e7e
        }
        relationship "Relationship" {
            dashed false
        }
    }
    
    theme default
}
EOF
    echo "Created architecture/views.dsl"
}

create_level4_plantuml_templates() {
    # Container interfaces diagram
    cat > "architecture/code/container-interfaces.puml" << 'EOF'
@startuml Container Interfaces
!theme plain
title C4 Level 4: Container Interface Definitions

package "Container Interfaces" {
    interface IWebApp {
        +renderPage(route: string): Page
        +handleUserInput(input: UserInput): Response
        +authenticateUser(credentials: Credentials): AuthToken
    }
    
    interface IAPIGateway {
        +routeRequest(request: HTTPRequest): Response
        +validateRequest(request: HTTPRequest): ValidationResult
        +authenticateRequest(token: AuthToken): AuthResult
    }
    
    interface IDatabase {
        +create(entity: Entity): Result
        +read(id: ID): Entity
        +update(id: ID, data: Data): Result
        +delete(id: ID): Result
    }
}

note top of IWebApp : Define this interface first\nbefore implementing UI components

note top of IAPIGateway : Critical: External-facing interface\nmust be stable before module work

note top of IDatabase : Data access contract\ndefines persistence layer

@enduml
EOF

    # Module interfaces diagram
    cat > "architecture/code/module-interfaces.puml" << 'EOF'
@startuml Module Interfaces
!theme plain
title C4 Level 4: Module Interface Definitions

package "External Module Interfaces" {
    interface IAuthModule {
        +login(credentials: Credentials): AuthResult
        +logout(token: AuthToken): LogoutResult
        +validateToken(token: AuthToken): ValidationResult
    }
    
    interface IRoutingModule {
        +addRoute(route: Route): void
        +matchRoute(path: string): RouteMatch
        +executeRoute(match: RouteMatch, request: Request): Response
    }
}

package "Internal Module Interfaces" {
    interface IUserService {
        +createUser(userData: UserData): User
        +findUser(criteria: SearchCriteria): User[]
        +updateUser(id: ID, updates: UserUpdates): User
    }
    
    interface ISessionService {
        +createSession(userId: ID): Session
        +validateSession(sessionId: ID): SessionValidation
        +destroySession(sessionId: ID): void
    }
}

note top of IAuthModule : External interface - implement first
note top of IUserService : Internal interface - implement after external

@enduml
EOF

    # Class interfaces diagram
    cat > "architecture/code/class-interfaces.puml" << 'EOF'
@startuml Class Interfaces
!theme plain
title C4 Level 4: Class Interface Definitions

package "Inter-Module Class Interfaces" {
    interface IUserRepository {
        +save(user: User): SaveResult
        +findById(id: ID): User?
        +findByEmail(email: string): User?
        +delete(id: ID): DeleteResult
    }
    
    interface ITokenValidator {
        +validateJWT(token: string): ValidationResult
        +refreshToken(token: string): RefreshResult
        +revokeToken(token: string): RevokeResult
    }
}

package "Intra-Module Class Interfaces" {
    interface IPasswordHasher {
        +hash(password: string): HashedPassword
        +verify(password: string, hash: HashedPassword): boolean
    }
    
    interface IUserValidator {
        +validateEmail(email: string): ValidationResult
        +validatePassword(password: string): ValidationResult
        +validateUserData(userData: UserData): ValidationResult
    }
}

note top of IUserRepository : Cross-module boundary\nimplement before internal classes
note top of IPasswordHasher : Internal to auth module\nimplement after inter-module interfaces

@enduml
EOF

    echo "Created Level 4 PlantUML templates"
}

create_roadmap_template() {
    # Detect project type and create appropriate roadmap
    local project_type="Generic Application"
    local main_tech="Unknown"
    
    if [ -f "package.json" ]; then
        project_type="Web Application"
        main_tech="JavaScript/TypeScript"
    elif [ -f "pyproject.toml" ] || [ -f "requirements.txt" ]; then
        project_type="Python Application"  
        main_tech="Python"
    elif [ -f "pom.xml" ]; then
        project_type="Java Application"
        main_tech="Java"
    elif [ -f "go.mod" ]; then
        project_type="Go Application"
        main_tech="Go"
    fi
    
    cat > "ROADMAP.md" << EOF
# Development Roadmap

## Project Overview
**Type**: $project_type  
**Primary Technology**: $main_tech  
**Architecture**: C4 Model with Interface-First Development

## Development Phases

### Phase 1: Foundation Setup (Complexity: 2)
**Status**: PLANNED  
**Components**: [core, configuration, basic-structure]  
**Completion**: 0%

- [ ] Project structure and configuration
- [ ] Development environment setup
- [ ] Basic CI/CD pipeline
- [ ] Core dependency management

### Phase 2: Core Architecture (Complexity: 3)
**Status**: PLANNED  
**Components**: [containers, interfaces, core-services]  
**Completion**: 0%

- [ ] C4 container interfaces definition
- [ ] External module interfaces design
- [ ] Core service layer architecture
- [ ] Data persistence layer design

### Phase 3: Feature Implementation (Complexity: 4)
**Status**: PLANNED  
**Components**: [features, business-logic, integrations]  
**Completion**: 0%

- [ ] Primary feature development
- [ ] Business logic implementation
- [ ] External system integrations
- [ ] Advanced functionality

### Phase 4: Production Readiness (Complexity: 3)
**Status**: PLANNED  
**Components**: [deployment, monitoring, security]  
**Completion**: 0%

- [ ] Production deployment setup
- [ ] Monitoring and logging
- [ ] Security hardening
- [ ] Performance optimization

## Implementation Complexity Guide
- **Complexity 1**: Configuration, basic file operations
- **Complexity 2**: Simple API integration, basic data processing
- **Complexity 3**: Multi-component coordination, service integration
- **Complexity 4**: Complex business logic, external system integration
- **Complexity 5**: Distributed systems, real-time processing, advanced algorithms

## Next Steps

### Interface-First Development Hierarchy

#### 1. Container Interface Definition (Priority: HIGHEST)
**Parallel Execution Stream A: API Container**
- **Files to Create/Modify**:
  - \`src/interfaces/IAPIContainer.ts\` (or language equivalent)
  - \`architecture/code/container-interfaces.puml\`
- **Implementation Steps**:
  - Define external-facing API contract
  - Specify request/response formats
  - Document authentication requirements
  - Define error handling patterns

**Parallel Execution Stream B: Data Container**
- **Files to Create/Modify**:
  - \`src/interfaces/IDataContainer.ts\`
  - \`src/interfaces/IRepository.ts\`
- **Implementation Steps**:
  - Define data access interface
  - Specify entity schemas
  - Define query contracts
  - Document transaction boundaries

#### 2. External Module Interfaces (Priority: HIGH)
**Stream A: Authentication Module**
- **Files to Create/Modify**:
  - \`src/auth/interfaces/IAuthService.ts\`
  - \`src/auth/interfaces/IUserService.ts\`
  - \`architecture/code/auth-module-interface.puml\`
- **Implementation Steps**:
  - Define authentication flow interface
  - Specify token management contract
  - Document user management operations
  - Define authorization patterns

**Stream B: Business Logic Module**
- **Files to Create/Modify**:
  - \`src/core/interfaces/IBusinessService.ts\`
  - \`src/core/interfaces/IValidationService.ts\`
- **Implementation Steps**:
  - Define core business operations
  - Specify validation contracts
  - Document business rule interfaces
  - Define workflow patterns

#### 3. Intra-Container Module Interfaces (Priority: MEDIUM)
**Stream A: Service Layer Interfaces**
- **Files to Create/Modify**:
  - \`src/services/interfaces/IInternalService.ts\`
  - \`src/services/interfaces/IUtilityService.ts\`
- **Implementation Steps**:
  - Define internal service contracts
  - Specify utility function interfaces
  - Document internal communication patterns
  - Define shared resource access

#### 4. Module Implementation Contracts (Priority: MEDIUM)
**Stream A: Repository Implementation**
- **Files to Create/Modify**:
  - \`src/repositories/BaseRepository.ts\`
  - \`src/repositories/UserRepository.ts\`
- **Implementation Steps**:
  - Implement repository interfaces
  - Create base repository patterns
  - Implement entity-specific repositories
  - Add transaction management

#### 5. Inter-Module Class Interfaces (Priority: MEDIUM-LOW)
**Stream A: Cross-Module Communication**
- **Files to Create/Modify**:
  - \`src/shared/interfaces/ICrossModuleService.ts\`
  - \`src/shared/interfaces/IEventBus.ts\`
- **Implementation Steps**:
  - Define cross-module communication
  - Implement event-driven interfaces
  - Create shared utility interfaces
  - Document dependency injection patterns

#### 6. Intra-Module Class Interfaces (Priority: LOW)
**Stream A: Internal Class Structure**
- **Files to Create/Modify**:
  - \`src/auth/classes/AuthManager.ts\`
  - \`src/auth/classes/TokenValidator.ts\`
- **Implementation Steps**:
  - Define internal class interfaces
  - Implement class interaction patterns
  - Create helper class interfaces
  - Document internal workflows

#### 7. Method Interface Contracts (Priority: LOW)
**Stream A: Method Signatures**
- **Files to Create/Modify**:
  - Individual class files with method signatures
  - \`src/types/MethodContracts.ts\`
- **Implementation Steps**:
  - Define method signatures
  - Specify parameter contracts
  - Document return type patterns
  - Add error handling signatures

#### 8. Internal Logic Implementation (Priority: FINAL)
**Stream A: Business Logic**
- **Files to Create/Modify**:
  - All implementation files
  - Unit test files
- **Implementation Steps**:
  - Implement method bodies
  - Add business logic
  - Create error handling
  - Add comprehensive testing

### Parallel Execution Guidelines

**Week 1-2: Container Interfaces**
- Team A: API container interface design
- Team B: Data container interface design
- Team C: Architecture documentation updates

**Week 3-4: Module Interfaces**
- Team A: Authentication module interfaces
- Team B: Business logic module interfaces  
- Team C: Testing framework setup

**Week 5-6: Implementation Preparation**
- Team A: Repository pattern implementation
- Team B: Service layer interfaces
- Team C: Integration testing setup

**Week 7+: Parallel Implementation**
- All teams: Implement assigned modules following interface contracts
- Daily: Interface compliance validation
- Weekly: Integration testing and alignment checks

### Architecture File Synchronization

Each implementation step above corresponds to updates in:
- \`architecture/workspace.dsl\` - Main workspace configuration
- \`architecture/model.dsl\` - System, container, and component definitions
- \`architecture/views.dsl\` - Diagram views and styling
- \`architecture/code/*.puml\` - Implementation-level diagrams

### Success Criteria

- [ ] All container interfaces defined and documented
- [ ] Module interfaces implemented and tested
- [ ] Class interfaces follow established patterns
- [ ] Method contracts are type-safe and documented
- [ ] Implementation follows interface contracts exactly
- [ ] Architecture files reflect actual implementation
- [ ] Parallel development streams remain synchronized

### Risk Mitigation

- **Interface Changes**: All interface modifications require architecture team approval
- **Dependency Conflicts**: Daily integration testing prevents late-stage conflicts
- **Parallel Development**: Clear interface contracts prevent team collision
- **Technical Debt**: Interface-first approach reduces refactoring needs
EOF
    
    echo "Created ROADMAP.md with interface-first next steps"
}

create_root_claude_md() {
    cat > "CLAUDE.md" << 'EOF'
# Claude Agent Instructions
> **AI Agents:** Do not modify this file directly. Add any updates to `AGENTS.md` in this directory. *EXCEPTION:* Make sure any custom guidance (guidance beyond simply directing you to `AGENTS.md` and telling you not to modify this file) is moved to `AGENTS.md` and removed from this file.

This repository uses `AGENTS.md` for all agent guidance and configuration.
Please refer to the adjacent `AGENTS.md` file in this directory for full
instructions and notes.

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
EOF
    echo "Created root CLAUDE.md"
}

create_root_agents_md() {
    # Auto-detect project characteristics for better initial content
    local project_lang="Unknown"
    local build_system="Unknown"
    local test_framework="Unknown"
    
    if [ -f "package.json" ]; then
        project_lang="JavaScript/TypeScript"
        build_system="npm/yarn"
        test_framework="Jest/Mocha"
    elif [ -f "pyproject.toml" ]; then
        project_lang="Python"
        build_system="pip/poetry"
        test_framework="pytest"
    elif [ -f "pom.xml" ]; then
        project_lang="Java"
        build_system="Maven"
        test_framework="JUnit"
    elif [ -f "go.mod" ]; then
        project_lang="Go"
        build_system="go mod"
        test_framework="go test"
    fi

    cat > "AGENTS.md" << EOF
# AI Agent Instructions for Project Root

## PROJECT_STATUS_AND_ROADMAP
**Current Implementation Status**: 0% complete (Initial setup)
**Primary Language**: $project_lang
**Build System**: $build_system
**Testing Framework**: $test_framework

**Next Priority**: Follow ROADMAP.md Next Steps - Container Interface Definition

**Roadmap Alignment**:
- Phase 1: Foundation Setup - PLANNED (0% complete)
- Phase 2: Core Architecture - PLANNED (0% complete)  
- Phase 3: Feature Implementation - PLANNED (0% complete)
- Phase 4: Production Readiness - PLANNED (0% complete)

**Architecture Status**:
- Structurizr Workspace: Template created, needs project-specific customization
- Model Fragment: Template created, needs entity and relationship definition
- Views Fragment: Template created, needs view customization
- Level 4 (Code): Templates created, ready for interface definition

## ESSENTIAL_COMMANDS
- **Build**: Auto-detected based on project type
- **Test**: $test_framework (when tests are created)
- **Architecture**: View .dsl files in architecture/ directory
- **Development**: Follow ROADMAP.md Next Steps hierarchy

## ARCHITECTURAL_PATTERNS
**Interface-First Development**:
- Always define container interfaces before module implementation
- External module interfaces before intra-container interfaces
- Class interfaces before method implementation
- Method signatures before internal logic

**Structurizr DSL Integration**:
- Main Workspace: Contains configuration and includes
- Model Fragment: System context, containers, and components
- Views Fragment: Diagram definitions and styling
- Level 4: Implementation details and interface contracts

**Parallel Development**:
- Multiple teams can work simultaneously on different interface levels
- Interface contracts prevent integration conflicts
- Architecture files must be updated with implementation progress

## DEVELOPMENT_ITERATION_GUIDANCE
**Immediate Next Steps** (from ROADMAP.md):
1. **Container Interface Definition** - Define external-facing contracts
2. **External Module Interfaces** - Specify module boundaries
3. **Repository Pattern Setup** - Implement data access layer
4. **Service Layer Architecture** - Create business logic contracts

**Interface Hierarchy Enforcement**:
- Never implement internal logic before defining external interfaces
- Always validate interface contracts before proceeding to next level
- Update architecture diagrams when interfaces are defined
- Maintain parallel development synchronization

**File Creation Priority**:
1. \`src/interfaces/\` directory structure
2. Container interface definitions
3. Module interface specifications
4. Class interface contracts
5. Method signature definitions
6. Implementation details

## CODE_STYLE_PREFERENCES
- Interface naming: I[ComponentName] pattern
- File organization: Interfaces in separate files/directories
- Documentation: All interfaces must have comprehensive JSDoc/docstrings
- Type safety: Strict typing for all interface contracts
- Error handling: Explicit error types in interface definitions

## DEVELOPMENT_ENVIRONMENT
**Prerequisites**:
- $project_lang development environment
- $build_system for dependency management
- Structurizr DSL tools (Structurizr Lite/CLI for viewing)
- Architecture visualization tools (PlantUML viewer)
- Git for version control

**Setup Steps**:
1. Clone repository and install dependencies
2. Review ROADMAP.md Next Steps section
3. Examine architecture/workspace.dsl for system overview
4. Follow interface-first development hierarchy
5. Create interface files before any implementation

## TEAM_SHARED_PRACTICES
- **Interface Contracts**: All team members must follow defined interfaces
- **Architecture Updates**: Implementation changes require architecture file updates
- **Parallel Development**: Use interface contracts to prevent team conflicts
- **Code Reviews**: Focus on interface compliance and contract adherence
- **Testing Strategy**: Interface-driven testing with mock implementations

## AGENT_PREFERENCES
- **Development Approach**: Interface-first, top-down architecture
- **Code Organization**: Clear separation between interfaces and implementation
- **Documentation Style**: Architecture-driven documentation with file mapping
- **Error Handling**: Explicit interface contracts for error scenarios
- **Performance**: Interface design should consider performance implications
EOF
    
    echo "Created root AGENTS.md with project-specific guidance"
}

# Create standard project files following software development best practices
create_contributing_guide() {
    cat > "CONTRIBUTING.md" << 'EOF'
# Contributing Guidelines

Thank you for your interest in contributing to this project! Please follow these guidelines to ensure a smooth collaboration process.

## Code of Conduct
Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Getting Started
1. Fork the repository
2. Clone your fork locally
3. Follow the setup instructions in [README.md](README.md)
4. Create a feature branch: `git checkout -b feature/your-feature-name`

## Development Process
1. **Interface-First Development**: Follow the hierarchy defined in [ROADMAP.md](ROADMAP.md)
2. **Architecture Alignment**: Update architecture files when making structural changes
3. **Testing**: Ensure all tests pass before submitting
4. **Documentation**: Update relevant documentation for your changes

## Pull Request Process
1. Update the README.md with details of changes if needed
2. Update architecture documentation if structural changes were made
3. Ensure your PR description clearly describes the problem and solution
4. Link any relevant issues in your PR description

## Development Standards
- Follow the coding standards defined in the project
- Write meaningful commit messages
- Keep changes focused and atomic
- Add tests for new functionality

## Questions?
Feel free to open an issue for any questions about contributing.
EOF
    echo "Created CONTRIBUTING.md"
}

create_code_of_conduct() {
    cat > "CODE_OF_CONDUCT.md" << 'EOF'
# Code of Conduct

## Our Pledge
We are committed to providing a friendly, safe, and welcoming environment for all contributors and users.

## Our Standards
Examples of behavior that contributes to creating a positive environment include:
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

## Unacceptable Behavior
Examples of unacceptable behavior include:
- Harassment of any kind
- Discriminatory language or actions
- Personal attacks or insults
- Public or private harassment
- Publishing others' private information without permission

## Enforcement
Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by contacting the project team. All complaints will be reviewed and investigated promptly and fairly.

## Attribution
This Code of Conduct is adapted from the [Contributor Covenant](https://www.contributor-covenant.org/), version 2.1.
EOF
    echo "Created CODE_OF_CONDUCT.md"
}

create_security_policy() {
    cat > "SECURITY.md" << 'EOF'
# Security Policy

## Supported Versions
Please refer to our release documentation for information about which versions are currently supported with security updates.

## Reporting a Vulnerability
We take security vulnerabilities seriously. If you discover a security vulnerability, please follow these steps:

1. **Do NOT** open a public issue
2. Email the security team at [security@yourproject.com] (replace with actual contact)
3. Include as much information as possible:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

## Response Timeline
- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 7 days
- **Status Updates**: Weekly until resolved
- **Resolution**: Varies based on complexity and severity

## Security Best Practices
When contributing to this project:
- Follow secure coding practices
- Keep dependencies up to date
- Use static analysis tools
- Report any security concerns promptly

## Disclosure Policy
We will coordinate disclosure of security vulnerabilities with reporters to ensure users have adequate time to apply patches.
EOF
    echo "Created SECURITY.md"
}

create_changelog_template() {
    cat > "CHANGELOG.md" << 'EOF'
# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Initial project structure
- Architecture documentation with C4 model
- Interface-first development roadmap

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

## [0.1.0] - $(date +%Y-%m-%d)
### Added
- Initial release
- Basic project structure
- Documentation framework
EOF
    echo "Created CHANGELOG.md"
}

create_license_template() {
    cat > "LICENSE" << 'EOF'
MIT License

Copyright (c) $(date +%Y) [Your Name/Organization]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Note: Please review and update this license as appropriate for your project.
EOF
    echo "Created LICENSE (MIT template - please review and customize)"
}

create_gitignore_template() {
    # Detect project type and create appropriate .gitignore
    local project_type="generic"
    
    if [ -f "package.json" ]; then
        project_type="node"
    elif [ -f "pyproject.toml" ] || [ -f "requirements.txt" ]; then
        project_type="python"
    elif [ -f "pom.xml" ]; then
        project_type="java"
    elif [ -f "go.mod" ]; then
        project_type="go"
    fi
    
    cat > ".gitignore" << EOF
# General
.DS_Store
.vscode/settings.json
.idea/
*.swp
*.swo
*~

# Environment variables
.env
.env.local
.env.*.local

# Logs
logs
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Dependencies and builds
node_modules/
dist/
build/
target/
out/

# Temporary files
*.tmp
*.temp
.cache/

EOF

    # Add language-specific ignores
    case $project_type in
        "node")
            cat >> ".gitignore" << 'EOF'
# Node.js specific
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.npm
.yarn-integrity
coverage/
nyc_output/
EOF
            ;;
        "python")
            cat >> ".gitignore" << 'EOF'
# Python specific
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
pip-log.txt
pip-delete-this-directory.txt
.pytest_cache/
htmlcov/
.coverage
.coverage.*
EOF
            ;;
        "java")
            cat >> ".gitignore" << 'EOF'
# Java specific
*.class
*.jar
*.war
*.ear
*.nar
hs_err_pid*
target/
.mvn/wrapper/maven-wrapper.jar
.settings/
.project
.classpath
EOF
            ;;
        "go")
            cat >> ".gitignore" << 'EOF'
# Go specific
vendor/
*.exe
*.exe~
*.dll
*.so
*.dylib
*.test
*.out
go.work
EOF
            ;;
    esac
    
    echo "Created .gitignore for $project_type project"
}

create_github_templates() {
    mkdir -p .github/{workflows,ISSUE_TEMPLATE}
    
    # Create basic CI workflow
    cat > ".github/workflows/ci.yml" << 'EOF'
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup environment
      run: |
        # Add your setup commands here
        echo "Setting up project dependencies..."
    
    - name: Run tests
      run: |
        # Add your test commands here
        echo "Running tests..."
    
    - name: Run linting
      run: |
        # Add your linting commands here
        echo "Running linting..."
EOF

    # Create issue templates
    cat > ".github/ISSUE_TEMPLATE/bug_report.md" << 'EOF'
---
name: Bug report
about: Create a report to help us improve
title: ''
labels: bug
assignees: ''
---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Environment (please complete the following information):**
- OS: [e.g. iOS]
- Version [e.g. 22]

**Additional context**
Add any other context about the problem here.
EOF

    cat > ".github/ISSUE_TEMPLATE/feature_request.md" << 'EOF'
---
name: Feature request
about: Suggest an idea for this project
title: ''
labels: enhancement
assignees: ''
---

**Is your feature request related to a problem? Please describe.**
A clear and concise description of what the problem is. Ex. I'm always frustrated when [...]

**Describe the solution you'd like**
A clear and concise description of what you want to happen.

**Describe alternatives you've considered**
A clear and concise description of any alternative solutions or features you've considered.

**Additional context**
Add any other context or screenshots about the feature request here.
EOF

    cat > ".github/PULL_REQUEST_TEMPLATE.md" << 'EOF'
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Architecture update

## Testing
- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Architecture documentation updated if needed

## Checklist
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] Any dependent changes have been merged and published in downstream modules
EOF

    echo "Created GitHub templates and workflows"
}

create_tests_directory() {
    mkdir -p tests
    
    cat > "tests/README.md" << 'EOF'
# Tests

This directory contains test files for the project.

## Structure
- Unit tests: Test individual components in isolation
- Integration tests: Test component interactions
- End-to-end tests: Test complete user workflows

## Running Tests
Follow the instructions in the main README.md for running tests.

## Test Conventions
- Test files should be named `test_*.{ext}` or `*_test.{ext}`
- Each module should have corresponding test coverage
- Tests should be clear, focused, and maintainable
EOF

    echo "Created tests directory with README"
}

create_scripts_directory() {
    mkdir -p scripts
    
    cat > "scripts/README.md" << 'EOF'
# Scripts

This directory contains utility scripts for the project.

## Common Scripts
- `build.sh`: Build the project
- `test.sh`: Run all tests
- `deploy.sh`: Deployment scripts
- `setup.sh`: Development environment setup

## Usage
Make scripts executable: `chmod +x scripts/*.sh`
Run scripts from project root: `./scripts/script-name.sh`

## Guidelines
- Scripts should be idempotent when possible
- Include error handling and validation
- Document script parameters and usage
- Use consistent naming conventions
EOF

    echo "Created scripts directory with README"
}

create_ai_docs_readme() {
    cat > "ai_docs/README.md" << 'EOF'
# AI Agent Context Documentation

This directory contains AI agent context documentation for libraries, frameworks, and technologies used in this project.

## Purpose
- Provide up-to-date context for AI agents during development
- Include best practices, common patterns, and gotchas for each technology
- Reference official documentation and reliable sources
- Track last update dates to ensure information freshness

## File Naming Convention
- Use lowercase technology names: `react.md`, `nodejs.md`, `postgres.md`
- For multi-word technologies use hyphens: `react-router.md`, `styled-components.md`
- Include version information when relevant: `node-18.md` for version-specific context

## Content Structure
Each AI docs file should include:
1. **Technology Overview** - Brief description and primary use case
2. **Current Version** - Version being documented
3. **Key Concepts** - Core concepts AI agents should understand
4. **Common Patterns** - Frequently used patterns in this project
5. **Best Practices** - Recommended approaches and conventions
6. **Common Issues** - Known gotchas and how to avoid them
7. **Useful Resources** - Links to official docs, guides, and references
8. **Last Updated** - Date and source URLs used for updates

## Maintenance
- Files older than 30 days should be reviewed for updates
- Web search should be used to update stale documentation
- Include source URLs for traceability
- Update when major version changes occur

## Usage by AI Agents
AI agents should reference these files when:
- Implementing features using specific technologies
- Debugging issues related to frameworks
- Following project-specific patterns and conventions
- Understanding version-specific requirements
EOF
    echo "Created ai_docs/README.md"
}
```

### PHASE_1: ALIGNMENT_PLANNING_AND_ANALYSIS

#### **Pre-execution alignment assessment:**
```bash
# Read the current markdown table of contents for guidance
if [ -f "markdown-table-of-contents.md" ]; then
    echo "Reading existing documentation index..."
    
    # Extract architecture alignment status
    arch_gaps=$(grep -A 10 "ALIGNMENT_GAPS" markdown-table-of-contents.md || echo "No alignment gaps section found")
    roadmap_status=$(grep -A 10 "ROADMAP_IMPLEMENTATION_STATUS" markdown-table-of-contents.md || echo "No roadmap status found")
    complexity_data=$(grep -A 10 "COMPLEXITY_ANNOTATIONS" markdown-table-of-contents.md || echo "No complexity data found")
    
    echo "Architecture gaps identified: $arch_gaps"
    echo "Roadmap status: $roadmap_status"
    echo "Complexity annotations: $complexity_data"
else
    echo "No markdown-table-of-contents.md found. Creating fresh analysis..."
fi

# Create alignment execution plan
cat > "alignment-execution-plan.md" << 'EOF'
# Architecture-Roadmap Alignment Execution Plan
# Generated: $(date)

## ALIGNMENT_PRIORITIES
- [ ] Critical gaps (architecture misalignment affecting current development)
- [ ] Medium gaps (documentation drift, complexity mismatches) 
- [ ] Low gaps (minor inconsistencies, outdated annotations)

## EXECUTION_ORDER
1. Architecture file updates (DSL and PlantUML)
2. Roadmap complexity annotation updates
3. Implementation status propagation
4. Human documentation alignment
5. AI agent guidance updates

## ROLLBACK_PLAN
- Backup all files before changes
- Track change timestamps for reversion capability
EOF
```

#### **Architecture-Roadmap dependency mapping:**
```bash
# Discover architecture files and their relationships
arch_dsl_files=$(find . -path "*/architecture/*" -name "*.dsl" -type f | sort)
arch_puml_files=$(find . -path "*/architecture/*" -name "*.puml" -o -name "*.plantuml" -type f | sort)
roadmap_files=$(find . -maxdepth 2 -iname "*roadmap*" -name "*.md" -type f)

echo "Architecture DSL files (C4 Levels 1-3): $arch_dsl_files"
echo "Architecture PlantUML files (C4 Level 4): $arch_puml_files"  
echo "Roadmap files: $roadmap_files"

# Create dependency map
create_dependency_map() {
    echo "## ARCHITECTURE_DEPENDENCY_MAP" >> alignment-execution-plan.md
    
    for dsl_file in $arch_dsl_files; do
        level=$(basename "$dsl_file" .dsl)
        echo "DSL: $level → Implementation impact: $(assess_implementation_impact "$dsl_file")" >> alignment-execution-plan.md
        
        # Find related PlantUML files
        related_puml=$(find $(dirname "$dsl_file") -name "*$level*.puml" 2>/dev/null)
        if [ -n "$related_puml" ]; then
            echo "  ↳ Related PlantUML: $related_puml" >> alignment-execution-plan.md
        fi
    done
    
    echo "## ROADMAP_DEPENDENCY_MAP" >> alignment-execution-plan.md
    for roadmap in $roadmap_files; do
        phases=$(grep -E "Phase [0-9]|Step [0-9]" "$roadmap" | head -5)
        echo "Roadmap: $roadmap → Phases: $phases" >> alignment-execution-plan.md
    done
}

assess_implementation_impact() {
    local file=$1
    # Count components/containers/systems in DSL file
    local components=$(grep -c -E "(container|component|person|system)" "$file" 2>/dev/null || echo "0")
    if [ $components -gt 20 ]; then
        echo "HIGH"
    elif [ $components -gt 10 ]; then
        echo "MEDIUM" 
    else
        echo "LOW"
    fi
}

create_dependency_map
```

### PHASE_1: CODEBASE_DISCOVERY_AND_ANALYSIS

#### **Dynamic file discovery (enhanced for architecture):**
```bash
# Get overall project structure
find . -type f -name "*.md" | head -20

# Find all CLAUDE.md files dynamically
find . -name "CLAUDE.md" -type f

# Find all AGENTS.md files dynamically  
find . -name "AGENTS.md" -type f

# Enhanced architecture discovery with C4 level identification
echo "=== C4 Architecture Discovery ==="
find . -name "*.dsl" -type f | while read dsl_file; do
    level=$(grep -o -E "(Context|Container|Component)" "$dsl_file" | head -1)
    echo "DSL: $dsl_file → C4 Level: ${level:-Unknown}"
done

find . -name "*.puml" -o -name "*.plantuml" -type f | while read puml_file; do
    if grep -q "@startuml" "$puml_file"; then
        diagram_type=$(grep -o -E "(class|component|sequence|deployment)" "$puml_file" | head -1)
        echo "PlantUML: $puml_file → Type: ${diagram_type:-Code}, C4 Level: 4"
    fi
done

# Get project tree structure (first 3 levels)
tree -L 3 -I 'node_modules|.git|__pycache__|*.pyc|venv|.venv|htmlcov'
```

#### **Implementation status discovery (enhanced with complexity tracking):**
```bash
# Check for implemented features by scanning code
implementation_files=$(find . -name "*.py" -type f | wc -l)
plugin_implementations=$(find . -path "*/plugins/*/plugin.py" -type f | wc -l)
test_coverage=$(find . -name "*test*.py" -o -name "test_*.py" | wc -l)

# Check for operational components
operational_components=$(ls mcp_server/ 2>/dev/null | grep -E "(security|metrics|cache|benchmark)" | wc -l)

# Enhanced complexity assessment
assess_codebase_complexity() {
    local total_lines=$(find . \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.java" -o -name "*.go" -o -name "*.cpp" -o -name "*.c" \) -exec wc -l {} \; | awk '{sum += $1} END {print sum}' 2>/dev/null || echo "0")
    local async_usage=$(find . \( -name "*.py" -o -name "*.js" -o -name "*.ts" \) -exec grep -l "async \|await \|Promise\|asyncio" {} \; | wc -l)
    local external_deps=$(find . \( -name "requirements*.txt" -o -name "package.json" -o -name "pom.xml" -o -name "go.mod" -o -name "Cargo.toml" \) | xargs cat 2>/dev/null | wc -l)
    
    echo "Codebase complexity metrics:"
    echo "  Total lines: $total_lines"
    echo "  Async components: $async_usage (complexity +1 if >5)"
    echo "  External dependencies: $external_deps (complexity +1 if >20)"
    
    # Calculate overall complexity score
    local complexity=1
    [ $total_lines -gt 10000 ] && complexity=$((complexity + 1))
    [ $async_usage -gt 5 ] && complexity=$((complexity + 1))
    [ $external_deps -gt 20 ] && complexity=$((complexity + 1))
    [ $implementation_count -gt 50 ] && complexity=$((complexity + 1))
    
    echo "  Overall complexity score: $complexity/5"
    
    # Store for later use in roadmap updates
    echo "CODEBASE_COMPLEXITY=$complexity" > .complexity_assessment
}

assess_codebase_complexity
```

### PHASE_5: GUIDANCE_INGESTION_AND_ALIGNMENT_PLANNING

#### **Read primary guidance files with alignment focus:**
```bash
read_guidance_files() {
    echo "=== Guidance File Analysis ==="
    
    # Primary guidance reading
    if [ -f "markdown-table-of-contents.md" ]; then
        echo "Reading documentation index..."
        alignment_tasks=$(grep -A 20 "ARCHITECTURE_ALIGNMENT_TASKS" markdown-table-of-contents.md)
        development_guidance=$(grep -A 10 "DEVELOPMENT_ITERATION_GUIDANCE" markdown-table-of-contents.md)
        consolidation_tasks=$(grep -A 20 "CONSOLIDATION_OPPORTUNITIES" markdown-table-of-contents.md)
        
        echo "Alignment tasks found: $alignment_tasks"
        echo "Development guidance found: $development_guidance"
        echo "Consolidation opportunities: $consolidation_tasks"
    fi
    
    # Primary README analysis for human-centric content
    primary_readme=$(find . -maxdepth 2 -name "README.md" | head -1)
    if [ -f "$primary_readme" ]; then
        human_sections=$(grep -E "^#+ " "$primary_readme" | head -10)
        echo "Human-centric README sections: $human_sections"
    fi
    
    # Roadmap phase analysis
    for roadmap in $roadmap_files; do
        echo "Analyzing roadmap: $roadmap"
        phases=$(grep -E "^#.*Phase|^#.*Step" "$roadmap")
        implementations=$(grep -E "(implemented|complete|done)" "$roadmap" -i)
        planned_items=$(grep -E "(planned|future|todo)" "$roadmap" -i)
        
        echo "  Phases: $phases"
        echo "  Implemented: $implementations"
        echo "  Planned: $planned_items"
    done
}

read_guidance_files
```

### PHASE_6: ARCHITECTURE_ALIGNMENT_PLANNING

#### **Create comprehensive alignment plan:**
```bash
create_alignment_plan() {
    echo "=== Creating Architecture Alignment Plan ===" 
    
    cat >> "alignment-execution-plan.md" << 'EOF'

## ARCHITECTURE_ALIGNMENT_PLAN

### SYNCHRONIZATION_PRIORITIES
1. **Critical Misalignments** (affects current development)
   - Architecture components missing from roadmap
   - Roadmap items without architectural representation
   - Implementation status inconsistencies

2. **Complexity Propagation** (affects planning accuracy)
   - Roadmap items lacking complexity scores
   - Architecture complexity not reflecting implementation
   - Dependencies not captured in complexity calculations

3. **Documentation Drift** (affects team coordination)
   - Outdated implementation percentages
   - Stale architectural diagrams
   - Missing next-step guidance for agents

### ALIGNMENT_EXECUTION_STEPS
EOF

    # Analyze each architecture file for alignment needs
    for dsl_file in $arch_dsl_files; do
        echo "Analyzing alignment needs for: $dsl_file"
        
        # Check if roadmap references this architectural level
        roadmap_refs=$(grep -l "$(basename "$dsl_file" .dsl)" $roadmap_files 2>/dev/null || echo "No roadmap references")
        
        # Check implementation annotations
        impl_annotations=$(grep -E "(implementation|status|complete)" "$dsl_file" 2>/dev/null || echo "No implementation annotations")
        
        cat >> "alignment-execution-plan.md" << EOF

#### $(basename "$dsl_file") Alignment
- Roadmap references: $roadmap_refs
- Implementation annotations: $impl_annotations  
- Action needed: $(determine_alignment_action "$dsl_file")
EOF
    done
    
    # Plan roadmap updates
    for roadmap in $roadmap_files; do
        echo "Planning roadmap updates for: $roadmap"
        
        missing_complexity=$(grep -L "complexity:" "$roadmap" 2>/dev/null || echo "$roadmap needs complexity annotations")
        
        cat >> "alignment-execution-plan.md" << EOF

#### $(basename "$roadmap") Updates
- Complexity annotations needed: $missing_complexity
- Architecture mapping: $(check_architecture_mapping "$roadmap")
- Implementation status: $(check_implementation_status "$roadmap")
EOF
    done
}

determine_alignment_action() {
    local file=$1
    local impl_count=$(grep -c "implementation\." "$file" 2>/dev/null || echo "0")
    local percent_count=$(grep -c "%" "$file" 2>/dev/null || echo "0")
    
    if [ $impl_count -eq 0 ] && [ $percent_count -eq 0 ]; then
        echo "ADD_IMPLEMENTATION_ANNOTATIONS"
    elif [ $impl_count -gt 0 ] && [ $percent_count -eq 0 ]; then
        echo "ADD_PERCENTAGE_TRACKING"
    else
        echo "UPDATE_EXISTING_ANNOTATIONS"
    fi
}

check_architecture_mapping() {
    local roadmap=$1
    local arch_refs=$(grep -c -E "(architecture|component|container|system)" "$roadmap" 2>/dev/null || echo "0")
    
    if [ $arch_refs -gt 3 ]; then
        echo "WELL_MAPPED"
    elif [ $arch_refs -gt 0 ]; then
        echo "PARTIALLY_MAPPED"
    else
        echo "NOT_MAPPED"
    fi
}

check_implementation_status() {
    local roadmap=$1
    local status_markers=$(grep -c -E "(✓|✗|DONE|TODO|IN_PROGRESS)" "$roadmap" 2>/dev/null || echo "0")
    
    if [ $status_markers -gt 5 ]; then
        echo "TRACKED"
    elif [ $status_markers -gt 0 ]; then
        echo "PARTIAL_TRACKING"
    else
        echo "NO_TRACKING"
    fi
}

create_alignment_plan
```

### PHASE_7: ARCHITECTURE_SYNCHRONIZATION_EXECUTION

#### **Execute architecture-roadmap synchronization:**
```bash
execute_architecture_sync() {
    echo "=== Executing Architecture Synchronization ==="
    
    # Load codebase complexity assessment
    source .complexity_assessment 2>/dev/null || CODEBASE_COMPLEXITY=1
    
    # Update each DSL file with implementation status
    for dsl_file in $arch_dsl_files; do
        echo "Updating architecture file: $dsl_file"
        
        # Backup original
        cp "$dsl_file" "${dsl_file}.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Add implementation annotations if missing
        if ! grep -q "Implementation:" "$dsl_file"; then
            echo "Adding implementation annotations to $dsl_file"
            
            # Calculate implementation percentage based on codebase analysis
            local impl_percentage=$(calculate_implementation_percentage "$dsl_file")
            
            # Add implementation status comment based on file type
            if [[ "$dsl_file" == *"workspace.dsl" ]]; then
                sed -i '/^workspace/a # Implementation Status: '"$impl_percentage"'% complete\n# Complexity Score: '"$CODEBASE_COMPLEXITY"'/5\n# Last Updated: '"$(date)"'\n' "$dsl_file"
            elif [[ "$dsl_file" == *"model.dsl" ]]; then
                sed -i '/^model/a # Implementation Status: '"$impl_percentage"'% complete\n# Complexity Score: '"$CODEBASE_COMPLEXITY"'/5\n# Last Updated: '"$(date)"'\n' "$dsl_file"
            elif [[ "$dsl_file" == *"views.dsl" ]]; then
                sed -i '/^views/a # Implementation Status: '"$impl_percentage"'% complete\n# Complexity Score: '"$CODEBASE_COMPLEXITY"'/5\n# Last Updated: '"$(date)"'\n' "$dsl_file"
            fi
        fi
        
        # Update existing percentages based on current state
        update_implementation_percentages "$dsl_file"
    done
    
    # Update PlantUML files to reflect current implementation
    for puml_file in $arch_puml_files; do
        echo "Updating PlantUML file: $puml_file"
        
        # Backup original
        cp "$puml_file" "${puml_file}.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Add implementation status notes
        if ! grep -q "Implementation:" "$puml_file"; then
            # Add implementation status as comments
            sed -i '/^@startuml/a \
'\''Implementation Status: '"$(calculate_implementation_percentage "$puml_file")"'% complete\
'\''Complexity: '"$CODEBASE_COMPLEXITY"'/5\
'\''Last Updated: '"$(date)"
            "$puml_file"
        fi
    done
}

calculate_implementation_percentage() {
    local arch_file=$1
    local base_name=$(basename "$arch_file" .dsl .puml)
    
    # Look for corresponding implementation directories/files
    local impl_dirs=$(find . -type d -iname "*$base_name*" | grep -v architecture | wc -l)
    local impl_files=$(find . -name "*.py" -exec grep -l "$base_name" {} \; | wc -l)
    
    # Calculate based on presence of implementation
    local percentage=0
    [ $impl_dirs -gt 0 ] && percentage=$((percentage + 30))
    [ $impl_files -gt 0 ] && percentage=$((percentage + 40))
    [ $impl_files -gt 3 ] && percentage=$((percentage + 30))
    
    echo $percentage
}

update_implementation_percentages() {
    local file=$1
    local new_percentage=$(calculate_implementation_percentage "$file")
    
    # Update existing implementation comments
    sed -i 's/Implementation Status: [0-9]*%/Implementation Status: '"$new_percentage"'%/' "$file"
    sed -i 's/Last Updated: .*/Last Updated: '"$(date)"'/' "$file"
}

execute_architecture_sync
```

### PHASE_8: ROADMAP_COMPLEXITY_ANNOTATION

#### **Add complexity annotations to roadmap files:**
```bash
annotate_roadmap_complexity() {
    echo "=== Annotating Roadmap Complexity ==="
    
    source .complexity_assessment 2>/dev/null || CODEBASE_COMPLEXITY=1
    
    for roadmap in $roadmap_files; do
        echo "Annotating complexity in: $roadmap"
        
        # Backup original
        cp "$roadmap" "${roadmap}.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Add complexity metadata section if missing
        if ! grep -q "COMPLEXITY_LEGEND" "$roadmap"; then
            cat >> "$roadmap" << 'EOF'

## COMPLEXITY_LEGEND
- **Complexity 1**: Basic configuration, file operations
- **Complexity 2**: Simple API integration, basic data processing  
- **Complexity 3**: Multi-component coordination, moderate algorithms
- **Complexity 4**: Async processing, external system integration
- **Complexity 5**: Distributed systems, real-time processing, ML/AI

## IMPLEMENTATION_STATUS_ANNOTATIONS
- ✅ **COMPLETE**: Fully implemented and tested
- 🔄 **IN_PROGRESS**: Currently being developed
- 📋 **PLANNED**: Designed but not started
- ❓ **NEEDS_ANALYSIS**: Requires further architectural planning
EOF
        fi
        
        # Annotate phases/steps with complexity scores
        annotate_phases_with_complexity "$roadmap"
    done
}

annotate_phases_with_complexity() {
    local roadmap=$1
    
    # Find phase/step headers and add complexity annotations
    while IFS= read -r line; do
        if echo "$line" | grep -q -E "^#+.*Phase|^#+.*Step"; then
            # Calculate complexity based on content keywords
            local complexity=$(calculate_phase_complexity "$line" "$roadmap")
            
            # Update the line with complexity annotation
            local updated_line="$line (Complexity: $complexity/5)"
            sed -i "s|$line|$updated_line|" "$roadmap"
        fi
    done < "$roadmap"
}

calculate_phase_complexity() {
    local phase_line=$1
    local roadmap=$2
    local complexity=1
    
    # Extract phase content (next 10 lines after phase header)
    local phase_content=$(grep -A 10 "$phase_line" "$roadmap")
    
    # Complexity indicators
    echo "$phase_content" | grep -q -i "async\|distributed\|real-time" && complexity=$((complexity + 2))
    echo "$phase_content" | grep -q -i "integration\|api\|external" && complexity=$((complexity + 1))
    echo "$phase_content" | grep -q -i "security\|authentication\|encryption" && complexity=$((complexity + 1))
    echo "$phase_content" | grep -q -i "performance\|optimization\|scale" && complexity=$((complexity + 1))
    echo "$phase_content" | grep -q -i "ml\|ai\|machine learning" && complexity=$((complexity + 2))
    
    # Cap at 5
    [ $complexity -gt 5 ] && complexity=5
    
    echo $complexity
}

annotate_roadmap_complexity
```

### PHASE_9: ROADMAP_NEXT_STEPS_ENHANCEMENT

#### **Enhance existing ROADMAP.md with interface-first Next Steps section:**
```bash
enhance_roadmap_next_steps() {
    echo "=== Enhancing ROADMAP.md with Interface-First Next Steps ==="
    
    for roadmap in $roadmap_files; do
        echo "Enhancing roadmap: $roadmap"
        
        # Check if Next Steps section exists
        if ! grep -q "## Next Steps" "$roadmap"; then
            echo "Adding Next Steps section to $roadmap"
            add_next_steps_section "$roadmap"
        else
            echo "Enhancing existing Next Steps section in $roadmap"
            enhance_existing_next_steps "$roadmap"
        fi
        
        # Ensure interface hierarchy is documented
        ensure_interface_hierarchy_documentation "$roadmap"
        
        # Add file mapping if missing
        add_file_mapping_to_roadmap "$roadmap"
    done
}

add_next_steps_section() {
    local roadmap=$1
    
    # Backup the original
    cp "$roadmap" "${roadmap}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Detect project structure for file paths
    local src_dir="src"
    local interface_ext=".ts"
    
    if [ -f "pyproject.toml" ]; then
        interface_ext=".py"
    elif [ -f "pom.xml" ]; then
        interface_ext=".java"
    elif [ -f "go.mod" ]; then
        interface_ext=".go"
    fi
    
    # Add comprehensive Next Steps section
    cat >> "$roadmap" << EOF

## Next Steps

### Interface-First Development Hierarchy

#### 1. Container Interface Definition (Priority: HIGHEST)
**Parallel Execution Stream A: Primary Container**
- **Files to Create/Modify**:
  - \`$src_dir/interfaces/IMainContainer$interface_ext\`
  - \`architecture/code/container-interfaces.puml\`
- **Implementation Steps**:
  - Define external-facing API contract
  - Specify request/response formats
  - Document authentication requirements
  - Define error handling patterns

**Parallel Execution Stream B: Data Container**
- **Files to Create/Modify**:
  - \`$src_dir/interfaces/IDataContainer$interface_ext\`
  - \`$src_dir/interfaces/IRepository$interface_ext\`
- **Implementation Steps**:
  - Define data access interface
  - Specify entity schemas
  - Define query contracts
  - Document transaction boundaries

#### 2. External Module Interfaces (Priority: HIGH)
**Stream A: Core Business Module**
- **Files to Create/Modify**:
  - \`$src_dir/core/interfaces/ICoreService$interface_ext\`
  - \`$src_dir/core/interfaces/IBusinessLogic$interface_ext\`
  - \`architecture/code/core-module-interface.puml\`
- **Implementation Steps**:
  - Define core business operations
  - Specify validation contracts
  - Document business rule interfaces
  - Define workflow patterns

**Stream B: Integration Module**
- **Files to Create/Modify**:
  - \`$src_dir/integrations/interfaces/IExternalService$interface_ext\`
  - \`$src_dir/integrations/interfaces/IDataTransform$interface_ext\`
- **Implementation Steps**:
  - Define external system interfaces
  - Specify data transformation contracts
  - Document integration patterns
  - Define retry and error handling

#### 3. Intra-Container Module Interfaces (Priority: MEDIUM)
**Stream A: Service Layer Interfaces**
- **Files to Create/Modify**:
  - \`$src_dir/services/interfaces/IInternalService$interface_ext\`
  - \`$src_dir/services/interfaces/IUtilityService$interface_ext\`
- **Implementation Steps**:
  - Define internal service contracts
  - Specify utility function interfaces
  - Document internal communication patterns
  - Define shared resource access

#### 4. Module Implementation Contracts (Priority: MEDIUM)
**Stream A: Repository Implementation**
- **Files to Create/Modify**:
  - \`$src_dir/repositories/BaseRepository$interface_ext\`
  - \`$src_dir/repositories/EntityRepository$interface_ext\`
- **Implementation Steps**:
  - Implement repository interfaces
  - Create base repository patterns
  - Implement entity-specific repositories
  - Add transaction management

#### 5. Inter-Module Class Interfaces (Priority: MEDIUM-LOW)
**Stream A: Cross-Module Communication**
- **Files to Create/Modify**:
  - \`$src_dir/shared/interfaces/ICrossModuleService$interface_ext\`
  - \`$src_dir/shared/interfaces/IEventBus$interface_ext\`
- **Implementation Steps**:
  - Define cross-module communication
  - Implement event-driven interfaces
  - Create shared utility interfaces
  - Document dependency injection patterns

#### 6. Intra-Module Class Interfaces (Priority: LOW)
**Stream A: Internal Class Structure**
- **Files to Create/Modify**:
  - \`$src_dir/core/classes/BusinessManager$interface_ext\`
  - \`$src_dir/core/classes/DataValidator$interface_ext\`
- **Implementation Steps**:
  - Define internal class interfaces
  - Implement class interaction patterns
  - Create helper class interfaces
  - Document internal workflows

#### 7. Method Interface Contracts (Priority: LOW)
**Stream A: Method Signatures**
- **Files to Create/Modify**:
  - Individual class files with method signatures
  - \`$src_dir/types/MethodContracts$interface_ext\`
- **Implementation Steps**:
  - Define method signatures
  - Specify parameter contracts
  - Document return type patterns
  - Add error handling signatures

#### 8. Internal Logic Implementation (Priority: FINAL)
**Stream A: Business Logic**
- **Files to Create/Modify**:
  - All implementation files
  - Unit test files
- **Implementation Steps**:
  - Implement method bodies
  - Add business logic
  - Create error handling
  - Add comprehensive testing

### Parallel Execution Guidelines

**Week 1-2: Container Interfaces**
- Team A: Primary container interface design
- Team B: Data container interface design
- Team C: Architecture documentation updates

**Week 3-4: Module Interfaces**
- Team A: Core business module interfaces
- Team B: Integration module interfaces  
- Team C: Testing framework setup

**Week 5-6: Implementation Preparation**
- Team A: Repository pattern implementation
- Team B: Service layer interfaces
- Team C: Integration testing setup

**Week 7+: Parallel Implementation**
- All teams: Implement assigned modules following interface contracts
- Daily: Interface compliance validation
- Weekly: Integration testing and alignment checks

### Architecture File Synchronization

Each implementation step above corresponds to updates in:
- \`architecture/context.dsl\` - System-level changes
- \`architecture/containers.dsl\` - Container-level changes
- \`architecture/components.dsl\` - Component-level changes
- \`architecture/code/*.puml\` - Implementation-level diagrams

### Success Criteria

- [ ] All container interfaces defined and documented
- [ ] Module interfaces implemented and tested
- [ ] Class interfaces follow established patterns
- [ ] Method contracts are type-safe and documented
- [ ] Implementation follows interface contracts exactly
- [ ] Architecture files reflect actual implementation
- [ ] Parallel development streams remain synchronized

### Risk Mitigation

- **Interface Changes**: All interface modifications require architecture team approval
- **Dependency Conflicts**: Daily integration testing prevents late-stage conflicts
- **Parallel Development**: Clear interface contracts prevent team collision
- **Technical Debt**: Interface-first approach reduces refactoring needs
EOF
}

enhance_existing_next_steps() {
    local roadmap=$1
    
    # Check if the existing Next Steps section has interface hierarchy
    if ! grep -q "Container Interface" "$roadmap"; then
        echo "Existing Next Steps found but missing interface hierarchy - enhancing..."
        
        # Replace or enhance the existing Next Steps section
        sed -i '/## Next Steps/,$d' "$roadmap"
        add_next_steps_section "$roadmap"
    else
        echo "Next Steps section already has interface hierarchy"
    fi
}

ensure_interface_hierarchy_documentation() {
    local roadmap=$1
    
    # Ensure the roadmap explains the hierarchy approach
    if ! grep -q "Interface-First Development" "$roadmap"; then
        echo "Adding interface-first development explanation to $roadmap"
        
        # Add explanation section if missing
        sed -i '/## Next Steps/i \
## Interface-First Development Approach\
\
This project follows a top-down, interface-first development methodology:\
\
1. **Container Interfaces**: Define external-facing contracts first\
2. **Module Interfaces**: Specify module boundaries and responsibilities\
3. **Class Interfaces**: Define class interaction patterns\
4. **Method Interfaces**: Specify method contracts\
5. **Implementation**: Fill in the business logic\
\
This approach enables parallel development while maintaining system integrity.\
' "$roadmap"
    fi
}

add_file_mapping_to_roadmap() {
    local roadmap=$1
    
    # Ensure file mappings are comprehensive
    if ! grep -q "Files to Create/Modify" "$roadmap"; then
        echo "Adding file mapping section to $roadmap"
        # File mappings are included in the add_next_steps_section function
    fi
}

### PHASE_10: CLAUDE_MD_NAVIGATION_STANDARDIZATION

#### **Discover and update all CLAUDE.md files with enhanced guidance transfer:**
```bash
# Find all CLAUDE.md files dynamically
claude_files=$(find . -name "CLAUDE.md" -type f)

# Enhanced CLAUDE.md standardization with guidance migration
for file in $claude_files; do
    echo "Processing CLAUDE.md: $file"
    
    # Check if corresponding AGENTS.md exists
    agents_file=$(dirname "$file")/AGENTS.md
    
    # Extract any custom guidance from CLAUDE.md before standardizing
    custom_guidance=$(extract_custom_guidance "$file")
    
    if [ -f "$agents_file" ]; then
        echo "Found corresponding AGENTS.md: $agents_file"
        
        # Migrate custom guidance to AGENTS.md if found
        if [ -n "$custom_guidance" ]; then
            echo "Migrating custom guidance from CLAUDE.md to AGENTS.md"
            migrate_custom_guidance "$file" "$agents_file"
        fi
    else
        echo "Creating missing AGENTS.md for: $file"
        create_agents_md_from_claude "$file" "$agents_file"
    fi
    
    # Standardize CLAUDE.md content
    standardize_claude_md "$file"
done

extract_custom_guidance() {
    local claude_file=$1
    
    # Extract content that's not standard navigation
    local custom_content=$(grep -v -E "(AGENTS\.md|Do not modify|refer to)" "$claude_file" | grep -E "^[^#]" | head -10)
    
    if [ ${#custom_content} -gt 50 ]; then
        echo "$custom_content"
    fi
}

migrate_custom_guidance() {
    local claude_file=$1
    local agents_file=$2
    local custom_content=$(extract_custom_guidance "$claude_file")
    
    # Add custom guidance to AGENTS.md under MIGRATED_FROM_CLAUDE section
    if [ -n "$custom_content" ]; then
        echo "" >> "$agents_file"
        echo "## MIGRATED_FROM_CLAUDE_MD" >> "$agents_file"
        echo "# The following guidance was moved from CLAUDE.md on $(date)" >> "$agents_file"
        echo "$custom_content" >> "$agents_file"
        echo "" >> "$agents_file"
    fi
}

create_agents_md_from_claude() {
    local claude_file=$1
    local agents_file=$2
    local custom_content=$(extract_custom_guidance "$claude_file")
    
    # Create basic AGENTS.md structure with any custom content from CLAUDE.md
    cat > "$agents_file" << EOF
# AI Agent Instructions for $(dirname "$claude_file")

## CONTEXT
This directory contains $(determine_directory_context "$(dirname "$claude_file")").

$(if [ -n "$custom_content" ]; then
    echo "## MIGRATED_FROM_CLAUDE_MD"
    echo "# The following guidance was extracted from CLAUDE.md on $(date)"
    echo "$custom_content"
fi)

## ESSENTIAL_COMMANDS
# Commands will be auto-discovered and added by update-documents

## ARCHITECTURAL_PATTERNS  
# Patterns will be auto-discovered and added by update-documents

## DEVELOPMENT_ENVIRONMENT
# Environment details will be auto-discovered and added by update-documents
EOF
}

determine_directory_context() {
    local dir_path=$1
    
    if [ "$dir_path" = "." ]; then
        echo "project root configuration"
    elif echo "$dir_path" | grep -q "architecture"; then
        echo "architectural documentation and design files"
    elif echo "$dir_path" | grep -q -E "(src|lib|app)"; then
        echo "source code implementation details"
    elif echo "$dir_path" | grep -q -E "(test|spec)"; then
        echo "testing and validation configuration"
    else
        echo "$(basename "$dir_path")-specific configuration"
    fi
}

standardize_claude_md() {
    local file=$1
    
    cat > "$file" << 'EOF'
# Claude Agent Instructions
> **AI Agents:** Do not modify this file directly. Add any updates to `AGENTS.md` in this directory. *EXCEPTION:* Make sure any custom guidance (guidance beyond simply directing you to `AGENTS.md` and telling you not to modify this file) is moved to `AGENTS.md` and removed from this file.

This repository uses `AGENTS.md` for all agent guidance and configuration.
Please refer to the adjacent `AGENTS.md` file in this directory for full
instructions and notes.

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
EOF
}
```

### PHASE_11: AGENTS_MD_PURPOSE_SPECIFIC_UPDATES

#### **Enhanced AGENTS.md updates with architecture and roadmap integration:**
```bash
# Find all AGENTS.md files and analyze their directory context
agents_files=$(find . -name "AGENTS.md" -type f)

for file in $agents_files; do
    dir_path=$(dirname "$file")
    dir_name=$(basename "$dir_path")
    
    echo "Enhancing AGENTS.md in: $dir_path"
    
    # Backup original
    cp "$file" "${file}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Determine context and update accordingly
    if [ "$dir_path" = "." ]; then
        update_root_agents_md "$file"
    elif echo "$dir_path" | grep -q "architecture"; then
        update_architecture_agents_md "$file"
    elif echo "$dir_path" | grep -q -E "(src|lib|app)"; then
        component_name=$(echo "$dir_path" | sed 's/.*[\/]\([^\/]*\)$/\1/')
        update_component_agents_md "$file" "$component_name"
    else
        update_context_specific_agents_md "$file" "$dir_name"
    fi
done

update_root_agents_md() {
    local file=$1
    
    # Add or update essential sections
    ensure_section_exists "$file" "PROJECT_STATUS_AND_ROADMAP" "$(generate_project_status_section)"
    ensure_section_exists "$file" "ARCHITECTURE_OVERVIEW" "$(generate_architecture_overview_section)"
    ensure_section_exists "$file" "DEVELOPMENT_ITERATION_GUIDANCE" "$(generate_development_iteration_section)"
    ensure_section_exists "$file" "ESSENTIAL_COMMANDS" "$(discover_essential_commands)"
}

update_architecture_agents_md() {
    local file=$1
    
    ensure_section_exists "$file" "C4_MODEL_LEVELS" "$(generate_c4_levels_section)"
    ensure_section_exists "$file" "ARCHITECTURE_ALIGNMENT_STATUS" "$(generate_alignment_status_section)"
    ensure_section_exists "$file" "PLANTUML_COMMANDS" "$(generate_plantuml_commands_section)"
    ensure_section_exists "$file" "STRUCTURIZR_DSL_PATTERNS" "$(generate_dsl_patterns_section)"
}

update_component_agents_md() {
    local file=$1
    local component_name=$2
    
    ensure_section_exists "$file" "COMPONENT_SPECIFIC_COMMANDS" "$(generate_component_commands_section "$component_name")"
    ensure_section_exists "$file" "TESTING_SETUP" "$(generate_testing_section "$component_name")"
    ensure_section_exists "$file" "INTEGRATION_PATTERNS" "$(generate_integration_patterns_section "$component_name")"
}

ensure_section_exists() {
    local file=$1
    local section_name=$2
    local section_content=$3
    
    if ! grep -q "## $section_name" "$file"; then
        echo "" >> "$file"
        echo "## $section_name" >> "$file"
        echo "$section_content" >> "$file"
    else
        # Update existing section
        sed -i "/## $section_name/,/## /{/## $section_name/!{/## /!d}}" "$file"
        sed -i "/## $section_name/a\\$section_content" "$file"
    fi
}

generate_project_status_section() {
    source .complexity_assessment 2>/dev/null || CODEBASE_COMPLEXITY=1
    
    cat << EOF
**Current Implementation Status**: $(calculate_overall_completion)% complete
**Complexity Score**: $CODEBASE_COMPLEXITY/5
**Next Priority**: $(determine_next_priority)

**Roadmap Alignment**:
$(for roadmap in $roadmap_files; do
    echo "- $(basename "$roadmap"): $(check_implementation_status "$roadmap")"
done)

**Architecture Status**:
$(for dsl_file in $arch_dsl_files; do
    echo "- $(basename "$dsl_file"): $(calculate_implementation_percentage "$dsl_file")% implemented"
done)
EOF
}

generate_architecture_overview_section() {
    cat << EOF
**Structurizr DSL Architecture**:
- Main Workspace: $(echo $arch_dsl_files | grep -o "workspace\.dsl" | head -1 || echo "Not found")
- Model Fragment: $(echo $arch_dsl_files | grep -o "model\.dsl" | head -1 || echo "Not found")  
- Views Fragment: $(echo $arch_dsl_files | grep -o "views\.dsl" | head -1 || echo "Not found")
- Level 4 (Code): $(echo $arch_puml_files | wc -w) PlantUML files

**Integration Points**:
$(analyze_integration_points)

**Key Architectural Decisions**:
$(extract_architectural_decisions)
EOF
}

generate_development_iteration_section() {
    cat << EOF
**Immediate Next Steps** (based on current alignment analysis):
$(get_immediate_next_steps)

**Architectural Work Needed**:
$(get_architecture_work_needed)

**Documentation Updates Required**:
$(get_documentation_updates_needed)

**Complexity Considerations**:
$(get_complexity_considerations)
EOF
}

calculate_overall_completion() {
    local total_plugins=$(find . -path "*/plugins/*" -name "plugin.py" | wc -l)
    local total_components=$(ls mcp_server/ 2>/dev/null | wc -l)
    local total_tests=$(find . -name "*test*.py" | wc -l)
    
    # Simple completion calculation
    local completion=0
    [ $total_plugins -gt 0 ] && completion=$((completion + 30))
    [ $total_components -gt 3 ] && completion=$((completion + 40))
    [ $total_tests -gt 5 ] && completion=$((completion + 30))
    
    echo $completion
}

determine_next_priority() {
    # Analyze alignment-execution-plan.md for priorities
    if [ -f "alignment-execution-plan.md" ]; then
        local critical_items=$(grep -A 5 "Critical Misalignments" alignment-execution-plan.md | head -1)
        if [ -n "$critical_items" ]; then
            echo "Address critical architecture misalignments"
        else
            echo "Continue planned development iterations"
        fi
    else
        echo "Complete architecture alignment analysis"
    fi
}

analyze_integration_points() {
    # Find integration patterns in architecture files
    for dsl_file in $arch_dsl_files; do
        local integrations=$(grep -E "(uses|calls|depends)" "$dsl_file" 2>/dev/null | wc -l)
        echo "- $(basename "$dsl_file"): $integrations integration points"
    done
}

extract_architectural_decisions() {
    # Look for decision records or architectural choices
    local decisions=$(find . -name "*decision*" -o -name "*ADR*" -name "*.md" | head -3)
    if [ -n "$decisions" ]; then
        echo "$decisions"
    else
        echo "- Decision records not found (consider creating ADRs)"
    fi
}

get_immediate_next_steps() {
    if [ -f "alignment-execution-plan.md" ]; then
        grep -A 3 "ALIGNMENT_PRIORITIES" alignment-execution-plan.md | tail -3
    else
        echo "1. Complete architecture alignment analysis\n2. Update roadmap complexity annotations\n3. Synchronize implementation status"
    fi
}

get_architecture_work_needed() {
    local missing_puml=$(find . -path "*/architecture/*" -name "*.dsl" | while read dsl; do
        local base=$(basename "$dsl" .dsl)
        if ! find . -name "*$base*.puml" | grep -q .; then
            echo "- Missing PlantUML for $base"
        fi
    done)
    
    echo "${missing_puml:-"No missing architectural diagrams identified"}"
}

get_documentation_updates_needed() {
    local stale_docs=$(find . -name "*.md" -mtime +90 | grep -v backup | head -3)
    if [ -n "$stale_docs" ]; then
        echo "Stale documentation (>90 days): $stale_docs"
    else
        echo "Documentation appears current"
    fi
}

get_complexity_considerations() {
    source .complexity_assessment 2>/dev/null || CODEBASE_COMPLEXITY=1
    
    cat << EOF
- Current codebase complexity: $CODEBASE_COMPLEXITY/5
- Architecture complexity should match implementation complexity
- Roadmap complexity annotations should guide development effort estimation
- Consider complexity impact when adding new features
EOF
}
```

### PHASE_12: HUMAN_DOCUMENTATION_OPTIMIZATION

#### **Update README.md and human-centric documentation:**
```bash
optimize_human_documentation() {
    echo "=== Optimizing Human-Centric Documentation ==="
    
    # Update primary README
    local primary_readme=$(find . -maxdepth 1 -name "README.md" | head -1)
    if [ -f "$primary_readme" ]; then
        echo "Updating primary README: $primary_readme"
        
        # Backup original
        cp "$primary_readme" "${primary_readme}.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Update implementation status and roadmap references
        update_readme_status "$primary_readme"
        update_readme_roadmap_references "$primary_readme"
        add_architecture_overview_to_readme "$primary_readme"
    fi
    
    # Update other human-centric documentation
    local human_docs=$(find . -name "*.md" -not -path "*/.*" -not -name "CLAUDE.md" -not -name "AGENTS.md" -not -name "markdown-table-of-contents.md")
    
    for doc in $human_docs; do
        echo "Checking human doc: $doc"
        update_human_doc_references "$doc"
    done
}

update_readme_status() {
    local readme=$1
    local completion=$(calculate_overall_completion)
    
    # Update or add implementation status
    if grep -q "Implementation Status" "$readme"; then
        sed -i "s/Implementation Status: [0-9]*%/Implementation Status: $completion%/" "$readme"
    else
        # Add status section after title
        sed -i '/^# /a\\n## Implementation Status\nCurrent completion: '"$completion"'%\n' "$readme"
    fi
}

update_readme_roadmap_references() {
    local readme=$1
    
    # Ensure roadmap is referenced
    if ! grep -q -i "roadmap" "$readme"; then
        echo "" >> "$readme"
        echo "## Development Roadmap" >> "$readme"
        echo "See [ROADMAP.md](ROADMAP.md) for detailed development plans and current progress." >> "$readme"
    fi
}

add_architecture_overview_to_readme() {
    local readme=$1
    
    # Add architecture section if missing
    if ! grep -q -i "architecture" "$readme"; then
        echo "" >> "$readme"
        echo "## Architecture Overview" >> "$readme"
        echo "The system follows C4 model architecture patterns:" >> "$readme"
        
        for dsl_file in $arch_dsl_files; do
            local level=$(basename "$dsl_file" .dsl)
            echo "- **$level**: $(calculate_implementation_percentage "$dsl_file")% implemented" >> "$readme"
        done
        
        echo "" >> "$readme"
        echo "For detailed architectural documentation, see the [architecture/](architecture/) directory." >> "$readme"
    fi
}

update_human_doc_references() {
    local doc=$1
    
    # Update stale references to reflect current structure
    # Update broken links to architecture files
    sed -i 's|docs/architecture/|architecture/|g' "$doc"
    
    # Update outdated roadmap references
    sed -i 's|project-plan\.md|ROADMAP.md|g' "$doc"
    
    # Add last updated timestamp if missing
    if ! grep -q "Last updated:" "$doc"; then
        echo "" >> "$doc"
        echo "*Last updated: $(date)*" >> "$doc"
    fi
}
```

### PHASE_13: FINAL_VERIFICATION_AND_NEXT_ITERATION_GUIDANCE

#### **Generate comprehensive next-iteration guidance:**
```bash
generate_next_iteration_guidance() {
    echo "=== Generating Next Iteration Guidance ==="
    
    cat > "NEXT_ITERATION_GUIDANCE.md" << EOF
# Development Iteration Guidance
# Generated: $(date)
# For AI agent developers

## PRIORITY_MATRIX

### HIGH_PRIORITY (Start immediately)
$(get_high_priority_items)

### MEDIUM_PRIORITY (Next sprint)
$(get_medium_priority_items)

### LOW_PRIORITY (Future iterations)
$(get_low_priority_items)

## ARCHITECTURAL_READINESS_ASSESSMENT

### READY_FOR_IMPLEMENTATION
$(get_ready_components)

### NEEDS_ARCHITECTURAL_WORK
$(get_needs_architecture_components)

### BLOCKED_DEPENDENCIES
$(get_blocked_components)

## COMPLEXITY_IMPACT_ANALYSIS

### HIGH_COMPLEXITY_ITEMS (Complexity 4-5)
$(get_high_complexity_items)

### MEDIUM_COMPLEXITY_ITEMS (Complexity 2-3)
$(get_medium_complexity_items)

### LOW_COMPLEXITY_ITEMS (Complexity 1)
$(get_low_complexity_items)

## DEVELOPMENT_SEQUENCE_RECOMMENDATION
$(generate_development_sequence)

## VALIDATION_CHECKPOINTS
$(generate_validation_checkpoints)
EOF
}

get_high_priority_items() {
    # Extract from alignment plan and roadmap analysis
    if [ -f "alignment-execution-plan.md" ]; then
        grep -A 5 "Critical" alignment-execution-plan.md | grep -E "^\s*-" | head -3
    fi
    
    # Add items based on implementation gaps
    for roadmap in $roadmap_files; do
        local in_progress=$(grep -E "(IN_PROGRESS|Current)" "$roadmap" | head -2)
        if [ -n "$in_progress" ]; then
            echo "- Complete in-progress roadmap items: $in_progress"
        fi
    done
}

get_medium_priority_items() {
    # Items that are planned but not critical
    for roadmap in $roadmap_files; do
        local planned=$(grep -E "(PLANNED|Next)" "$roadmap" | head -3)
        if [ -n "$planned" ]; then
            echo "- $planned"
        fi
    done
}

get_low_priority_items() {
    # Documentation improvements and optimizations
    echo "- Documentation consistency improvements"
    echo "- Performance optimizations"
    echo "- Additional testing coverage"
}

get_ready_components() {
    # Components with complete architectural design
    for dsl_file in $arch_dsl_files; do
        local impl_percent=$(calculate_implementation_percentage "$dsl_file")
        if [ $impl_percent -lt 100 ] && [ $impl_percent -gt 50 ]; then
            echo "- $(basename "$dsl_file" .dsl): $impl_percent% ready for completion"
        fi
    done
}

get_needs_architecture_components() {
    # Components mentioned in roadmap but missing from architecture
    for roadmap in $roadmap_files; do
        local components=$(grep -o -E "[A-Z][a-zA-Z]*Service|[A-Z][a-zA-Z]*Component" "$roadmap" | sort -u)
        for component in $components; do
            if ! grep -r "$component" $arch_dsl_files >/dev/null 2>&1; then
                echo "- $component: Mentioned in roadmap but not in architecture"
            fi
        done
    done
}

get_blocked_components() {
    # Components with dependencies not yet satisfied
    echo "- Components blocked by external dependencies"
    echo "- Items requiring architectural decisions"
}

generate_development_sequence() {
    cat << EOF
**Recommended sequence based on complexity and dependencies:**

1. **Foundation Phase**: Complete low-complexity, high-impact items
2. **Core Features Phase**: Implement medium-complexity architectural components  
3. **Integration Phase**: Connect components and add high-complexity features
4. **Optimization Phase**: Performance, security, and scalability improvements

**Parallel work streams:**
- Documentation updates (ongoing)
- Testing and validation (per component)
- Architecture refinement (as needed)
EOF
}

generate_validation_checkpoints() {
    cat << EOF
**After each development iteration:**

1. **Architecture Alignment Check**:
   - Run markdown table of contents generator
   - Verify architecture-roadmap synchronization
   - Update implementation percentages

2. **Documentation Consistency Check**:
   - Validate CLAUDE.md → AGENTS.md navigation
   - Check for broken internal links
   - Update human-facing documentation

3. **Complexity Assessment Update**:
   - Reassess codebase complexity score
   - Update roadmap complexity annotations
   - Adjust future iteration planning
EOF
}

generate_next_iteration_guidance
```

### PHASE_14: FINAL_UPDATE_MARKDOWN_TABLE_OF_CONTENTS

#### **Regenerate table of contents with all alignment updates:**
```bash
update_final_table_of_contents() {
    echo "=== Updating Final Table of Contents ==="
    
    # Re-run the index generator to capture all changes
    # This should be done by calling the first command again, but we'll update key sections
    
    if [ -f "markdown-table-of-contents.md" ]; then
        # Update timestamps and status
        sed -i "s/Last updated: .*/Last updated: $(date)/" markdown-table-of-contents.md
        
        # Update implementation status based on our analysis
        local new_completion=$(calculate_overall_completion)
        sed -i "s/completion:[0-9]*%/completion:$new_completion%/" markdown-table-of-contents.md
        
        # Add next iteration guidance reference
        if ! grep -q "NEXT_ITERATION_GUIDANCE.md" markdown-table-of-contents.md; then
            echo "" >> markdown-table-of-contents.md
            echo "## NEXT_ITERATION_REFERENCE" >> markdown-table-of-contents.md
            echo "See [NEXT_ITERATION_GUIDANCE.md](NEXT_ITERATION_GUIDANCE.md) for AI agent development priorities." >> markdown-table-of-contents.md
        fi
    fi
}

update_final_table_of_contents
```

## SUCCESS_CRITERIA_CHECKLIST

**Enhanced success verification with alignment validation:**
```bash
echo "=== Final Validation ==="

# Original validations
validate_claude_navigation() {
    local claude_count=$(find . -name "CLAUDE.md" -type f | wc -l)
    local agents_count=$(find . -name "AGENTS.md" -type f | wc -l)
    echo "✓ CLAUDE.md files: $claude_count, AGENTS.md files: $agents_count"
    
    # Check for orphaned CLAUDE.md files
    for claude_file in $(find . -name "CLAUDE.md" -type f); do
        local agents_file=$(dirname "$claude_file")/AGENTS.md
        if [ ! -f "$agents_file" ]; then
            echo "✗ Orphaned CLAUDE.md: $claude_file"
        else
            echo "✓ Paired navigation: $claude_file ↔ $agents_file"
        fi
    done
}

# NEW: Architecture alignment validation  
validate_architecture_alignment() {
    echo "=== Architecture Alignment Validation ==="
    
    # Check DSL implementation annotations
    for dsl_file in $arch_dsl_files; do
        if grep -q "Implementation Status:" "$dsl_file"; then
            echo "✓ $dsl_file has implementation status"
        else
            echo "✗ $dsl_file missing implementation status"
        fi
    done
    
    # Check roadmap complexity annotations
    for roadmap in $roadmap_files; do
        if grep -q "Complexity:" "$roadmap"; then
            echo "✓ $roadmap has complexity annotations"
        else
            echo "✗ $roadmap missing complexity annotations"
        fi
    done
}

# NEW: Roadmap-architecture synchronization validation
validate_roadmap_sync() {
    echo "=== Roadmap Synchronization Validation ==="
    
    for roadmap in $roadmap_files; do
        local arch_refs=$(grep -c -E "(architecture|component|container)" "$roadmap" 2>/dev/null || echo "0")
        local status_tracking=$(grep -c -E "(✓|✗|DONE|IN_PROGRESS)" "$roadmap" 2>/dev/null || echo "0")
        
        echo "Roadmap: $(basename "$roadmap")"
        echo "  Architecture references: $arch_refs"
        echo "  Status tracking: $status_tracking"
        
        if [ $arch_refs -gt 0 ] && [ $status_tracking -gt 0 ]; then
            echo "  ✓ Well-integrated roadmap"
        else
            echo "  ⚠ Needs better integration"
        fi
    done
}

# NEW: Human vs AI content separation validation
validate_content_separation() {
    echo "=== Content Separation Validation ==="
    
    # Check that CLAUDE.md files only have navigation
    for claude_file in $(find . -name "CLAUDE.md" -type f); do
        local line_count=$(wc -l < "$claude_file")
        if [ $line_count -lt 20 ]; then
            echo "✓ $claude_file is properly minimal"
        else
            echo "⚠ $claude_file may have excess content"
        fi
    done
    
    # Check that AGENTS.md files have essential sections
    for agents_file in $(find . -name "AGENTS.md" -type f); do
        local essential_sections=("ESSENTIAL_COMMANDS" "ARCHITECTURAL_PATTERNS")
        local missing_count=0
        
        for section in "${essential_sections[@]}"; do
            if ! grep -q "$section" "$agents_file"; then
                missing_count=$((missing_count + 1))
            fi
        done
        
        if [ $missing_count -eq 0 ]; then
            echo "✓ $agents_file has essential sections"
        else
            echo "⚠ $agents_file missing $missing_count essential sections"
        fi
    done
}

# NEW: Roadmap Next Steps validation
validate_roadmap_next_steps() {
    echo "=== Roadmap Next Steps Validation ==="
    
    for roadmap in $roadmap_files; do
        echo "Validating Next Steps in: $(basename "$roadmap")"
        
        # Check for Next Steps section
        if grep -q "## Next Steps" "$roadmap"; then
            echo "  ✓ Has Next Steps section"
        else
            echo "  ✗ Missing Next Steps section"
        fi
        
        # Check for interface hierarchy
        local hierarchy_items=("Container Interface Definition" "External Module Interfaces" "Intra-Container Module" "Method Interface Contracts")
        local missing_count=0
        
        for item in "${hierarchy_items[@]}"; do
            if ! grep -q "$item" "$roadmap"; then
                missing_count=$((missing_count + 1))
            fi
        done
        
        if [ $missing_count -eq 0 ]; then
            echo "  ✓ Complete interface hierarchy documented"
        else
            echo "  ⚠ Missing $missing_count interface hierarchy items"
        fi
        
        # Check for file mapping
        if grep -q "Files to Create/Modify" "$roadmap"; then
            echo "  ✓ File mappings included"
        else
            echo "  ✗ Missing file mappings"
        fi
        
        # Check for parallel execution guidance
        if grep -q "Parallel Execution" "$roadmap"; then
            echo "  ✓ Parallel execution documented"
        else
            echo "  ✗ Missing parallel execution guidance"
        fi
    done
}

# NEW: Documentation consolidation validation
validate_documentation_best_practices() {
    echo "=== Documentation Best Practices Validation ==="
    
    # Check for single README.md in root
    readme_count=$(find . -name "README.md" | wc -l)
    if [ $readme_count -eq 1 ] && [ -f "README.md" ]; then
        echo "✓ Single README.md in root directory"
    else
        echo "✗ Multiple README files found or missing root README.md"
    fi
    
    # Check for standard project files
    standard_files=("CONTRIBUTING.md" "CODE_OF_CONDUCT.md" "SECURITY.md" "CHANGELOG.md" "LICENSE")
    missing_standard=0
    
    for file in "${standard_files[@]}"; do
        if [ -f "$file" ]; then
            echo "✓ $file exists"
        else
            echo "✗ $file missing"
            missing_standard=$((missing_standard + 1))
        fi
    done
    
    # Check docs/ structure
    if [ -d "docs" ]; then
        echo "✓ docs/ directory exists"
        
        # Check for consolidated documentation
        consolidated_docs=("docs/installation.md" "docs/api.md" "docs/usage.md")
        for doc in "${consolidated_docs[@]}"; do
            if [ -f "$doc" ]; then
                echo "✓ $doc consolidated properly"
            else
                echo "⚠ $doc could be created"
            fi
        done
    else
        echo "⚠ docs/ directory missing"
    fi
    
    # Check for root directory cleanliness
    non_standard_md=$(find . -maxdepth 1 -name "*.md" ! -name "README.md" ! -name "ROADMAP.md" ! -name "CONTRIBUTING.md" ! -name "CHANGELOG.md" ! -name "CODE_OF_CONDUCT.md" ! -name "SECURITY.md" ! -name "CLAUDE.md" ! -name "AGENTS.md" | wc -l)
    
    if [ $non_standard_md -eq 0 ]; then
        echo "✓ Root directory clean of non-standard markdown files"
    else
        echo "⚠ $non_standard_md non-standard markdown files in root"
    fi
    
    # Check GitHub integration
    if [ -d ".github" ]; then
        echo "✓ GitHub integration directory exists"
        
        if [ -f ".github/workflows/ci.yml" ]; then
            echo "✓ CI workflow configured"
        else
            echo "⚠ CI workflow missing"
        fi
        
        if [ -d ".github/ISSUE_TEMPLATE" ]; then
            echo "✓ Issue templates configured"
        else
            echo "⚠ Issue templates missing"
        fi
    else
        echo "⚠ GitHub integration missing"
    fi
    
    # Summary
    if [ $missing_standard -eq 0 ] && [ $non_standard_md -eq 0 ]; then
        echo "✅ Documentation follows software development best practices"
    else
        echo "⚠ Documentation structure needs improvement"
    fi
}
validate_architecture_structure() {
    echo "=== Architecture Structure Validation ==="
    
    local required_files=("architecture/workspace.dsl" "architecture/model.dsl" "architecture/views.dsl")
    local required_dirs=("architecture/code" "architecture/history")
    
    for file in "${required_files[@]}"; do
        if [ -f "$file" ]; then
            echo "✓ $file exists"
        else
            echo "✗ $file missing"
        fi
    done
    
    for dir in "${required_dirs[@]}"; do
        if [ -d "$dir" ]; then
            echo "✓ $dir directory exists"
        else
            echo "✗ $dir directory missing"
        fi
    done
    
    # Check for Level 4 PlantUML templates
    local puml_templates=("architecture/code/container-interfaces.puml" "architecture/code/module-interfaces.puml" "architecture/code/class-interfaces.puml")
    
    for template in "${puml_templates[@]}"; do
        if [ -f "$template" ]; then
            echo "✓ $template exists"
        else
            echo "✗ $template missing"
        fi
    done
    
    # Validate Structurizr DSL syntax
    if [ -f "architecture/workspace.dsl" ]; then
        if grep -q "!include model.dsl" "architecture/workspace.dsl"; then
            echo "✓ workspace.dsl includes model.dsl"
        else
            echo "⚠ workspace.dsl missing model.dsl include"
        fi
        
        if grep -q "!include views.dsl" "architecture/workspace.dsl"; then
            echo "✓ workspace.dsl includes views.dsl"
        else
            echo "⚠ workspace.dsl missing views.dsl include"
        fi
    fi
}

# NEW: AI docs validation
validate_ai_docs_structure() {
    echo "=== AI Docs Structure Validation ==="
    
    if [ -d "ai_docs" ]; then
        echo "✓ ai_docs/ directory exists"
        
        if [ -f "ai_docs/README.md" ]; then
            echo "✓ ai_docs/README.md exists"
        else
            echo "✗ ai_docs/README.md missing"
        fi
        
        # Check for AI docs files
        ai_doc_count=$(find ai_docs/ -name "*.md" ! -name "README.md" ! -name "ROADMAP_MAPPING.md" | wc -l)
        if [ $ai_doc_count -gt 0 ]; then
            echo "✓ Found $ai_doc_count AI context files"
            
            # Check for stale files
            current_date=$(date +%s)
            thirty_days_ago=$((current_date - 30*24*3600))
            stale_count=0
            
            for doc in ai_docs/*.md; do
                if [ -f "$doc" ] && [ "$(basename "$doc")" != "README.md" ] && [ "$(basename "$doc")" != "ROADMAP_MAPPING.md" ]; then
                    file_date=$(stat -c %Y "$doc" 2>/dev/null || stat -f %m "$doc" 2>/dev/null)
                    if [ "$file_date" -lt "$thirty_days_ago" ]; then
                        stale_count=$((stale_count + 1))
                    fi
                fi
            done
            
            if [ $stale_count -eq 0 ]; then
                echo "✓ All AI docs are current (<30 days old)"
            else
                echo "⚠ $stale_count AI docs are stale (>30 days old)"
            fi
        else
            echo "⚠ No AI context files found"
        fi
        
        # Check for roadmap mapping
        if [ -f "ai_docs/ROADMAP_MAPPING.md" ]; then
            echo "✓ AI docs roadmap mapping exists"
        else
            echo "⚠ AI docs roadmap mapping missing"
        fi
    else
        echo "✗ ai_docs/ directory missing"
    fi
}

# Execute all validations
validate_claude_navigation
validate_architecture_alignment  
validate_roadmap_sync
validate_content_separation
validate_roadmap_next_steps
validate_architecture_structure
validate_documentation_best_practices
validate_ai_docs_structure

echo "=== Validation Complete ==="
```

## IMPORTANT_NOTES

**Enhanced with documentation best practices, consolidation, and AI agent context management:**

- **Dynamic Discovery**: Always use `find`, `grep`, `ls`, and `tree` commands to discover current codebase state
- **Architecture-First Approach**: Ensure architectural decisions drive roadmap complexity and implementation priority
- **Documentation Consolidation**: Follow software development best practices - single README.md, standard project files (CONTRIBUTING.md, LICENSE, etc.), organized docs/ structure
- **Root Directory Cleanliness**: Keep only essential project files in root, move everything else to appropriate subdirectories
- **Standard File Creation**: Automatically create missing standard project files (CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, CHANGELOG.md, LICENSE, .gitignore)
- **GitHub Integration**: Set up proper GitHub workflows, issue templates, and PR templates for professional project management
- **AI Agent Context Management**: Maintain up-to-date AI docs for frameworks/libraries, update stale docs (>30 days) via web search, detect missing context for commonly used technologies
- **Framework Detection**: Automatically identify technologies in use and create corresponding AI agent context documentation
- **Roadmap-AI Docs Integration**: Document (but don't modify) mapping between roadmap items and relevant AI context files
- **Web Search Integration**: Use web search to update stale AI docs and create missing framework documentation, include source URLs for traceability
- **Complexity Propagation**: Changes to architecture complexity should update roadmap annotations and vice versa  
- **Status Synchronization**: Implementation status must be consistent across architecture files, roadmap, and documentation
- **AI Agent Optimization**: AGENTS.md files should contain everything AI agents need for effective development
- **Human Documentation Clarity**: README.md and human docs should provide clear project overview without technical implementation details
- **Documentation Elimination**: Remove documentation sprawl, consolidate duplicate content, eliminate outdated files
- **Validation Loops**: Each phase should validate alignment and best practices before proceeding to prevent drift
- **Next-Iteration Planning**: Always generate specific guidance for the next development iteration
- **Non-Modifying Documentation**: Commands document status and implementation plans but do not modify roadmap or architecture (separate commands handle those changes)

**Execute** all operations dynamically to maintain clean, consistent documentation that adapts to any codebase structure while accurately reflecting the current implementation state, following software development best practices, maintaining current AI agent context, and providing clear guidance for continued development.