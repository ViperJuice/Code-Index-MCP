# MCP Server Architecture Agent Configuration

This file defines the capabilities and constraints for AI agents working with the MCP server architecture.

## Agent Capabilities

### Architecture Understanding
- Interpret C4 model diagrams
- Understand system boundaries
- Analyze component relationships
- Evaluate architecture decisions

### Documentation
- Update architecture diagrams
- Maintain documentation
- Add new views
- Document decisions

### Analysis
- Review architecture changes
- Validate design decisions
- Check consistency
- Identify improvements

### Visualization
- Generate diagrams
- Update views
- Maintain consistency
- Export formats

## Agent Constraints

1. **C4 Model Compliance**
   - Follow C4 model conventions
   - Maintain level separation
   - Use correct notation
   - Keep diagrams focused

2. **Documentation**
   - Keep docs up to date
   - Document decisions
   - Explain rationale
   - Maintain clarity

3. **Consistency**
   - Align with code
   - Match implementation
   - Update all levels
   - Maintain relationships

4. **Quality**
   - Clear diagrams
   - Accurate representation
   - Complete documentation
   - Valid DSL syntax

## ESSENTIAL_COMMANDS

```bash
# Architecture Visualization
docker run --rm -p 8080:8080 \
  -v "$(pwd)/architecture":/usr/local/structurizr \
  structurizr/lite
# Then open: http://localhost:8080

# PlantUML Generation (if needed)
plantuml architecture/level4/*.puml

# DSL Validation
# Edit .dsl files and check browser refresh for syntax errors

# Architecture Documentation
find architecture/ -name "*.dsl" -o -name "*.puml" | sort
```

## CODE_STYLE_PREFERENCES

```dsl
# Structurizr DSL Style (discovered patterns)
# - Use descriptive identifiers
# - Consistent indentation (2 spaces)
# - Group related elements
# - Document relationships clearly

workspace "MCP Server" {
    model {
        person = person "Developer" "Uses Code-Index-MCP"
        softwareSystem = softwareSystem "Code-Index-MCP" {
            // Components follow snake_case
            apiGateway = container "API Gateway"
            dispatcher = container "Dispatcher"
        }
    }
}

# PlantUML Style (discovered patterns)
@startuml
!theme plain
skinparam componentStyle rectangle
skinparam linetype ortho
@enduml
```

## ARCHITECTURAL_PATTERNS

```bash
# C4 Model Levels
# Level 1: System Context - External interactions
# Level 2: Container - High-level technology choices  
# Level 3: Component - Internal structure
# Level 4: Code - Implementation details (PlantUML)

# Architecture File Patterns
level1_context.dsl          # System boundaries
level2_containers.dsl       # Container architecture
level3_mcp_components.dsl   # Component details
level4/*.puml              # Detailed component designs

# Dual Pattern: Planned vs Actual
api_gateway.puml           # Planned architecture
api_gateway_actual.puml    # Current implementation
```

## NAMING_CONVENTIONS

```bash
# DSL Files: level{N}_{purpose}.dsl
level1_context.dsl
level2_containers.dsl  
level3_mcp_components.dsl

# PlantUML Files: {component}.puml, {component}_actual.puml
api_gateway.puml, api_gateway_actual.puml
dispatcher.puml, dispatcher_actual.puml
plugin_system.puml, plugin_system_actual.puml

# Identifiers: camelCase in DSL
apiGateway, pluginSystem, storageLayer

# Documentation: {topic}.md
data_model.md, security_model.md, performance_requirements.md
```

## DEVELOPMENT_ENVIRONMENT

```bash
# Docker: Required for Structurizr visualization
docker --version

# PlantUML: Optional for direct diagram generation
java -jar plantuml.jar

# Browser: View Structurizr diagrams
# Navigate to: http://localhost:8080

# File Organization
architecture/
├── level1_context.dsl
├── level2_containers.dsl  
├── level3_mcp_components.dsl
├── level4/
│   ├── {component}.puml
│   └── {component}_actual.puml
└── *.md
```

## TEAM_SHARED_PRACTICES

```bash
# Architecture Updates: Always update both planned and actual diagrams
# DSL Editing: Validate syntax by checking browser refresh
# Documentation: Keep architecture docs in sync with implementation
# Version Control: Commit architecture changes with code changes

# Diagram Guidelines:
# - Clear component boundaries
# - Consistent styling across diagrams
# - Document technology choices
# - Show data flow and dependencies

# Architecture Reviews:
# - Verify planned vs actual alignment
# - Check for missing components
# - Validate security boundaries
# - Ensure scalability considerations
``` 

#Use the Structurizr CLI for linting and other *.dsl debugging and verification. See documentation below 

---
layout: default
title: Structurizr CLI
nav_order: 18
has_children: true
permalink: /cli
has_toc: false
---

# Structurizr CLI

The Structurizr CLI is a command line utility designed to be used in conjunction with the [Structurizr DSL](/dsl), and supports the following commands/functionality:

- [push](/cli/push) content to the Structurizr cloud service/on-premises installation
- [pull](/cli/pull) workspace content as JSON
- [lock](/cli/lock) a workspace
- [unlock](/cli/unlock) a workspace
- [export](/cli/export) diagrams to PlantUML, Mermaid, WebSequenceDiagrams, DOT, and Ilograph; or a DSL workspace to JSON
- [merge](/cli/merge) layout information from one workspace into another
- [list](/cli/list) elements within a workspace
- [validate](/cli/validate) a JSON/DSL workspace
- [inspect](/cli/inspect) a JSON/DSL workspace

## Links

- [GitHub](https://github.com/structurizr/cli)

---
layout: default
title: Installation
parent: Structurizr CLI
nav_order: 0
permalink: /cli/installation
---

# Installation

## Local installation

1. Download the Structurizr CLI from [https://github.com/structurizr/cli/releases](https://github.com/structurizr/cli/releases), and unzip. You will need Java (version 17+) installed, and available to use from your command line.
2. Unzip into a directory of your choice.
3. Add the directory to your operating system's path (optional).
4. Use the `structurizr.sh` or `structurizr.bat` file as appropriate for your operating system.

## Docker

A prebuilt Docker image is available at [Docker Hub](https://hub.docker.com/r/structurizr/cli). To use it, for example:

```
docker pull structurizr/cli:latest
docker run -it --rm -v $PWD:/usr/local/structurizr structurizr/cli <parameters>
```

In this example, `$PWD` will mount the current local directory as the CLI working directory (`/usr/local/structurizr` in the Docker container).

Alternative images are available via:

- [aidmax/structurizr-cli-docker](https://github.com/aidmax/structurizr-cli-docker) (GitHub Actions compatible)
- [sebastienfi/structurizr-cli-with-bonus](https://github.com/sebastienfi/structurizr-cli-with-bonus/) (GitHub Actions compatible; includes PlantUML)

## Package managers

### Homebrew (MacOS only)

The Structurizr CLI can be installed via [Homebrew](https://brew.sh) as follows:

```
brew install structurizr-cli
```

And to upgrade:

```
brew update
brew upgrade structurizr-cli
```

### Scoop (Windows only)

The Structurizr CLI can be installed via [Scoop](https://scoop.sh) as follows:

```
scoop bucket add extras
scoop install structurizr-cli
```

And to upgrade:

```
scoop update structurizr-cli
```

## GitHub Actions

Some pre-built GitHub Actions are available on the [GitHub Actions marketplace](https://github.com/marketplace?category=&type=actions&query=structurizr).

## GitLab

To export your diagrams to Mermaid format in gitlab-ci, add the `workspace.dsl` to your repo and add this job to your `.gitlab-ci.yml`:

```yml
job_name:
  stage: stage_name
  image:
    name: structurizr/cli
    entrypoint: [""]
  script:
    - /usr/local/structurizr-cli/structurizr.sh export --workspace workspace.dsl --format mermaid
  artifacts:
    paths:
      - "*.mmd"
```

## Gradle

A pre-built Gradle plugin is available from [jakzal/gradle-structurizr-cli](https://github.com/jakzal/gradle-structurizr-cli).

---
layout: default
title: Building from source
parent: Structurizr CLI
nav_order: 70
permalink: /cli/building
---

# Building from source

To build the Structurizr CLI from source, you'll need `git` and Java 17+ installed.
The Structurizr UI is required for the CLI to export a static site, 
so you will need to additionally clone the [structurizr/ui](https://github.com/structurizr/ui) repo.

## Build

```
git clone https://github.com/structurizr/cli.git structurizr-cli
git clone https://github.com/structurizr/ui.git structurizr-ui
cd structurizr-cli
./ui.sh
./gradlew clean build getDeps buildZip
```

> To use early access/preview features, change the value of `PREVIEW_FEATURES` to `true` in the [Configuration](https://github.com/structurizr/cli/blob/master/src/main/java/com/structurizr/cli/Configuration.java) class.

If you see an error message of the form `Could not find com.structurizr:structurizr-dsl:x.y.z`, you will need to
[build the Structurizr for Java repo from source, and publish to your local Maven repository](/java/building).

## Run

If successful, The `build/distributions` directory will contain a `structurizr-cli.zip` file.
To run the Structurizr CLI, you can then:

1. Unzip into a directory of your choice.
2. Add the directory to your operating system's path (optional).
3. Use the `structurizr.sh` or `structurizr.bat` file as appropriate for your operating system.

Alternatively you can run the CLI directly from the build directory, with a command like the following:

```
java -cp "build/libs/*:build/dependencies/*" com.structurizr.cli.StructurizrCliApplication 
```

## Docker 

To build a Docker image:

```
docker build . -t mytag
```

---
layout: default
title: export
parent: Structurizr CLI
nav_order: 5
permalink: /cli/export
---

# export

The ```export``` command allows you to export the views within a Structurizr workspace to a number of different formats.
It is essentially a command line interface to the [export formats](/export).
Files will be created one per view that has been exported.
If output directory is not specified, files will be created in the same directory as the workspace.
Please note that the export formats do not support all available shapes/features when compared to
the Structurizr cloud service/on-premises installation/Lite - see [Exporters - Comparison](/export/comparison) for more details.

Exporting PNG/SVG diagrams from the Structurizr cloud service/on-premises installation/Lite is not supported from the CLI.
This is because the CLI is a Java application, whereas the PNG/SVG diagrams are rendered in your web browser.
PNG/SVG diagram exports can instead be automated using headless Chrome and Puppeteer -
please see [https://github.com/structurizr/puppeteer](https://github.com/structurizr/puppeteer) for some example scripts.

The CLI will require Internet access if you are making use of any themes.

## Options

- -workspace: The path or URL to the workspace JSON/DSL file (required)
- -format (required):
  - plantuml: the same as `plantuml/structurizr`
  - plantuml/structurizr: exports views to PlantUML using the [StructurizrPlantUMLExporter](/export/plantuml#structurizrplantumlexporter)
  - plantuml/c4plantuml: exports views to PlantUML using the [C4PlantUMLExporter](https://docs.structurizr.com/export/plantuml#c4plantumlexporter)
  - mermaid: exports views to Mermaid using the [MermaidExporter](/export/mermaid) (your Mermaid configuration will need to include `"securityLevel": "loose"` to render the diagrams correctly. See [Mermaid - Configuration - securityLevel](https://mermaid-js.github.io/mermaid/#/./Setup?id=securitylevel) for more details)
  - websequencediagrams: exports dynamic views to WebSequenceDiagrams using the [WebSequenceDiagramsExporter](/export/websequencediagrams)
  - dot: exports views to DOT format (for use with Graphviz) using the [DOTExporter](/export/dot)
  - ilograph: exports the workspace to a YAML format for use with Ilograph using the [IlographExporter](/export/ilograph)
  - d2: export views to D2 format using the [D2Exporter](https://github.com/goto1134/structurizr-d2-exporter)
  - json: exports the workspace to the Structurizr JSON format
  - theme: creates a JSON theme based upon the styles and tags defined in the workspace
  - static: creates a static HTML site - see [Structurizr static site](/static) for details
  - fully qualified class name: provides a way to use a custom exporter; this needs to implement [WorkspaceExporter](https://github.com/structurizr/java/blob/master/structurizr-export/src/main/java/com/structurizr/export/WorkspaceExporter.java) or [DiagramExporter](https://github.com/structurizr/java/blob/master/structurizr-export/src/main/java/com/structurizr/export/DiagramExporter.java), with the compiled class(es) being available on the CLI classpath or packaged as a JAR file in a directory named `plugins` next to your workspace file
- -output: Relative or absolute path to an output directory (optional)

## Examples

To export all views in a JSON workspace to PlantUML format under folder named `diagrams`:

```
./structurizr.sh export -workspace workspace.json -format plantuml -output diagrams
```

To export all views in a JSON workspace to PlantUML format, using C4-PlantUML, under folder named `diagrams`:

```
./structurizr.sh export -workspace workspace.json -format plantuml/c4plantuml -output diagrams
```

To export all views in a JSON workspace to Mermaid format:

```
./structurizr.sh export -workspace workspace.json -format mermaid
```

To export all dynamic views in a DSL workspace to WebSequenceDiagrams format:

```
./structurizr.sh export -workspace workspace.dsl -format websequencediagrams
```

To export a DSL workspace to the JSON workspace format:

```
./structurizr.sh export -workspace workspace.dsl -format json
```

To export all views in a DSL workspace using a custom exporter:

```
./structurizr.sh export -workspace workspace.dsl -format com.example.MyCustomDiagramExporter
```

---
layout: default
title: inspect
parent: Structurizr CLI
nav_order: 9
permalink: /cli/inspect
---

# inspect

The ```inspect``` command allows you to inspect a JSON/DSL workspace via the [workspace inspection feature](/workspaces/inspections).
The return code indicates the number of violations that were shown.

## Options

- -workspace: The path or URL to the workspace JSON/DSL file (required)
- -inspector: Provides a way to use a custom inspector; this needs to extend [Inspector](https://github.com/structurizr/java/blob/master/structurizr-inspection/src/main/java/com/structurizr/inspection/Inspector.java), with the compiled class(es) being available on the CLI classpath or packaged as a JAR file in a directory named `plugins` next to your workspace file (optional)
- -severity: A comma separated list of violation severities to show (optional; defaults to `error,warning,info,ignore`)

## Example

To inspect a JSON workspace definition:

```
./structurizr.sh inspect -workspace workspace.json
```

To inspect a JSON workspace definition, showing only errors and warnings:

```
./structurizr.sh inspect -workspace workspace.json -severity error,warning
```

---
layout: default
title: list
parent: Structurizr CLI
nav_order: 7
permalink: /cli/list
---

# list

The `list` command lists the elements within a workspace.

## Options

- -workspace: The path or URL to the workspace JSON/DSL file (required)

## Example

To list the elements in a JSON workspace definition:

```
./structurizr.sh list -workspace workspace.json
```

---
layout: default
title: lock
parent: Structurizr CLI
nav_order: 3
permalink: /cli/lock
---

# lock

The ```lock``` command allows you to lock a Structurizr workspace (the cloud service or an on-premises installation).

## Options

- -id: The workspace ID (required)
- -key: The workspace API key (required)
- -secret: The workspace API secret (required)
- -url: The Structurizr API URL (optional; defaults to ```https://api.structurizr.com```)

## Example

To lock a Structurizr workspace:

```
./structurizr.sh lock -id 123456 -key 1a130d2b... -secret a9daaf3e...```

---
layout: default
title: merge
parent: Structurizr CLI
nav_order: 6
permalink: /cli/merge
---

# merge

The `merge` command allows you to merge the layout information from one workspace into another.

## Options

- -workspace: The path or URL to the workspace JSON/DSL file (required)
- -layout: The path or URL to the workspace JSON file that includes layout information (required)
- -view: The key of the view to merge layout information for (optional; default is all views in workspace)
- -output: Path and name of an output file (required)

## Examples

To merge the layout from one JSON workspace into another:

```
./structurizr.sh merge -workspace workspace-without-layout.json -layout workspace-with-layout.json -output workspace.json
```

---
layout: default
title: pull
parent: Structurizr CLI
nav_order: 2
permalink: /cli/pull
---

# pull

The ```pull``` command allows you to pull content from a Structurizr workspace (the cloud service or an on-premises installation), as a JSON document. A file will created with the name ```structurizr-<id>-workspace.json``` in the current directory.

## Options

- -id: The workspace ID (required)
- -key: The workspace API key (required)
- -secret: The workspace API secret (required)
- -url: The Structurizr API URL (optional; defaults to ```https://api.structurizr.com```)
- -branch: Branch name
- -passphrase: The passphrase to use (optional; only required if client-side encryption enabled on the workspace)

## Example

To pull the content of a Structurizr workspace:

```
./structurizr.sh pull -id 123456 -key 1a130d2b... -secret a9daaf3e...
```

---
layout: default
title: push
parent: Structurizr CLI
nav_order: 1
permalink: /cli/push
---

# push

The ```push``` command allows you to push the specified DSL/JSON file to a Structurizr workspace (the cloud service or an on-premises installation).

## Options

- -id: The workspace ID (required)
- -key: The workspace API key (required)
- -secret: The workspace API secret (required)
- -workspace: The path or URL to the workspace JSON/DSL file (required)
- -url: The Structurizr API URL (optional; defaults to ```https://api.structurizr.com```)
- -branch: Branch name
- -passphrase: The passphrase to use (optional; only required if client-side encryption enabled on the workspace)
- -merge: Whether to merge layout information from the remote workspace (optional; defaults to `true`)
- -archive: Whether to store the previous version of the remote workspace (optional; default to `true`)

## Examples

To push a new version of a workspace defined using the DSL:

```
./structurizr.sh push -id 123456 -key 1a130d2b... -secret a9daaf3e... -workspace workspace.dsl
```

---
layout: default
title: unlock
parent: Structurizr CLI
nav_order: 4
permalink: /cli/unlock
---

# unlock

The ```unlock``` command allows you to unlock a Structurizr workspace (the cloud service or an on-premises installation).

## Options

- -id: The workspace ID (required)
- -key: The workspace API key (required)
- -secret: The workspace API secret (required)
- -url: The Structurizr API URL (optional; defaults to ```https://api.structurizr.com```)

## Example

To unlock a Structurizr workspace:

```
./structurizr.sh unlock -id 123456 -key 1a130d2b... -secret a9daaf3e...
```

---
layout: default
title: validate
parent: Structurizr CLI
nav_order: 8
permalink: /cli/validate
---

# validate

The ```validate``` command allows you to validate a JSON/DSL workspace, using the same rules that are implemented by the Structurizr web API.

## Options

- -workspace: The path or URL to the workspace JSON/DSL file (required)

## Example

To validate a JSON workspace definition:

```
./structurizr.sh validate -workspace workspace.json
```