# do-next-steps

Execute the next implementation steps for any codebase using interface-driven parallel development to maximize agent productivity and ensure clean architecture.

## METHODOLOGY: INTERFACE-DRIVEN PARALLEL DEVELOPMENT

This command analyzes any codebase's documentation structure (README.md, ROADMAP.md, architecture/ directory, AGENTS.md files) to create and execute a comprehensive implementation plan that maximizes parallelism through interface-based development.

## DISCOVERY PHASE

### 1. Analyze Project Documentation
```bash
# Discover current project state dynamically
find . -name "README.md" -o -name "ROADMAP.md" -o -name "*.md" | head -20
find . -type d -name "architecture" -o -name "docs" -o -name "design"
find . -name "AGENTS.md" -o -name "CLAUDE.md" | sort
```

**Extract Key Information:**
- **Project purpose and scope** (from README.md)
- **Implementation status and next steps** (from ROADMAP.md)
- **Architecture components and gaps** (from architecture/ directory)
- **Current implementation percentage** (from status indicators)
- **Critical path items** (blocking other work)
- **Parallel execution opportunities** (independent components)

### 2. Identify System Architecture
```bash
# Discover architectural components
find . -name "*.puml" -o -name "*.dsl" -o -name "*architecture*"
ls -la */interfaces/ */contracts/ */api/ 2>/dev/null || echo "No existing interfaces"
find . -name "*interface*" -o -name "*contract*" -o -name "*protocol*"
```

**Analyze Architecture Patterns:**
- **Layered architecture** (API, Business, Data layers)
- **Microservices** (independent services) 
- **Plugin/Extension systems** (dynamic loading)
- **Event-driven** (pub/sub patterns)
- **Modular monolith** (domain boundaries)

### 3. Assess Implementation Gaps
```bash
# Identify implementation vs design gaps
find . -name "*stub*" -o -name "*todo*" -o -name "*placeholder*"
grep -r "NotImplementedError\|TODO\|FIXME\|XXX" --include="*.py" --include="*.js" --include="*.ts"
find . -name "*test*" | wc -l  # Test coverage indicator
```

## INTERFACE ARCHITECTURE DESIGN

### 1. Define Interface Hierarchy

**Level 1: System Boundaries**
- Identify major system components from architecture docs
- Define high-level module interfaces
- Establish communication contracts between modules

**Level 2: Component Interfaces** 
- Break down modules into logical components
- Define service interfaces within each module
- Establish data flow contracts

**Level 3: Implementation Interfaces**
- Define fine-grained interfaces for parallel development
- Create contracts for individual features/functions
- Enable maximum agent independence

### 2. Interface Design Patterns

**Common Interface Patterns:**
```python
# Repository Pattern
interface IRepository<T>:
    find(id) -> Optional<T>
    save(entity: T) -> T
    delete(id) -> bool

# Strategy Pattern  
interface IProcessor:
    process(data) -> Result<T>
    
# Observer Pattern
interface IEventHandler:
    handle(event: Event) -> void

# Factory Pattern
interface IFactory<T>:
    create(config) -> T
```

**Error Handling Pattern:**
```python
# Result/Either Pattern for safe error handling
class Result<T>:
    success: bool
    value: Optional<T>
    error: Optional<Error>
```

### 3. Interface Documentation
```markdown
## Interface: IComponentName
**Purpose:** Brief description
**Dependencies:** List of required interfaces
**Implementations:** Concrete classes that implement this interface
**Usage:** Code examples
**Error Conditions:** Possible errors and handling
```

## PARALLEL EXECUTION STRATEGY

### 1. Critical Path Analysis
```bash
# Identify blocking dependencies
echo "Critical Path Items (blocking other work):"
echo "- Performance validation frameworks"
echo "- Core service interfaces" 
echo "- Authentication/authorization systems"
echo "- Configuration management"
```

### 2. Parallel Work Groups

**Group A: Infrastructure (Independent)**
- Authentication systems
- Metrics and monitoring
- Configuration management
- Error handling frameworks

**Group B: Business Logic (Independent)**
- Core domain implementations
- Business rule engines
- Data processing pipelines
- Integration services

**Group C: Extensions (Independent)**  
- Plugin implementations
- Additional language support
- Optional feature modules
- Third-party integrations

### 3. Agent Assignment Protocol

**Phase 1: Interface Definition**
```bash
# Single agent creates interface framework
mkdir -p interfaces/ contracts/ protocols/
# Define all interface contracts
# Establish type definitions
# Document interaction patterns
```

**Phase 2: Parallel Implementation**
```bash
# Multiple agents work independently
Agent1: "Implement Group A interfaces in parallel"
Agent2: "Implement Group B interfaces in parallel"  
Agent3: "Implement Group C interfaces in parallel"
```

**Phase 3: Integration & Testing**
```bash
# Coordinated integration phase
# Interface compliance testing
# End-to-end system testing
# Performance validation
```

## EXECUTION FRAMEWORK

### 1. Interface Compliance Requirements
**Every agent must:**
- [ ] Implement complete interface (no partial implementations)
- [ ] Follow exact type contracts (input/output types)
- [ ] Use established error handling patterns
- [ ] Include comprehensive tests (>80% coverage)
- [ ] Update relevant documentation
- [ ] Verify integration points

### 2. Cross-Agent Coordination
```bash
# Shared coordination mechanisms
interfaces/README.md          # Interface registry and status
docs/agent-coordination.md    # Handoff protocols
tests/integration/           # Contract verification tests
```

### 3. Quality Gates
```bash
# Automated validation for each interface
make test-interfaces         # Interface compliance tests
make test-integration       # Cross-component integration
make benchmark             # Performance validation
make security-scan         # Security compliance check
```

## DYNAMIC EXECUTION COMMAND

### Step 1: Project Analysis
```bash
# Run discovery commands to understand current state
# Read README.md, ROADMAP.md, architecture/ docs
# Identify implementation gaps and next steps
# Determine critical path and parallel opportunities
```

### Step 2: Interface Architecture  
```bash
# Create interface hierarchy based on discovered architecture
# Define contracts for all major components
# Establish error handling and communication patterns
# Document interface relationships and dependencies
```

### Step 3: Parallel Execution
```bash
# Assign agents to independent interface implementations
# Execute critical path items first (unblock other work)
# Run parallel implementation groups simultaneously
# Maintain coordination through interface contracts
```

### Step 4: Integration & Validation
```bash
# Verify all interface contracts are satisfied
# Run integration tests across component boundaries
# Validate performance requirements are met
# Update documentation with implementation details
```

## ADAPTABILITY FEATURES

### 1. Technology Agnostic
- Works with any programming language
- Adapts to existing architectural patterns
- Leverages existing documentation structure
- Respects current coding conventions

### 2. Scale Adaptive
- Handles small scripts to enterprise systems
- Adjusts complexity based on project size
- Scales agent utilization appropriately
- Adapts interface granularity to project needs

### 3. Domain Flexible
- Web applications, CLI tools, libraries, frameworks
- Adapts to domain-specific patterns and requirements
- Uses appropriate interface abstractions
- Leverages domain expertise from documentation

## SUCCESS CRITERIA

### 1. Parallel Efficiency
- [ ] Maximum agents working simultaneously without conflicts
- [ ] Clear interface boundaries preventing integration issues
- [ ] Independent testing and validation per component
- [ ] Minimal coordination overhead between agents

### 2. Architecture Quality
- [ ] Clean separation of concerns through interfaces
- [ ] Consistent error handling across all components
- [ ] Comprehensive test coverage for all interfaces
- [ ] Documentation updated to reflect implementations

### 3. Project Advancement
- [ ] All identified next steps from ROADMAP.md completed
- [ ] Critical path items resolved (unblocking other work)
- [ ] Implementation percentage significantly increased
- [ ] Production readiness enhanced

Focus on interface-driven development to enable maximum parallelism while ensuring clean architecture and maintainable code. Each agent should work within well-defined interface boundaries to prevent conflicts and enable independent progress.