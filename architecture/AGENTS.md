# Architecture Agent Configuration

> **Context**: Architecture-specific agent guidance for Code-Index-MCP
> **Focus**: C4 model, DSL files, PlantUML diagrams, architecture validation
> **Last Updated**: 2025-06-03

## ESSENTIAL_COMMANDS

```bash
# Architecture Visualization
./tools/structurizr.sh validate code-index-mcp-architecture.dsl  # Validate DSL
./tools/structurizr.sh export -workspace code-index-mcp-architecture.dsl -format plantuml  # Export diagrams
./tools/structurizr.sh inspect code-index-mcp-architecture.dsl  # Inspect workspace

# PlantUML Generation
java -jar plantuml.jar architecture/exports/*.puml  # Generate PNG diagrams
make diagrams                                        # Generate all diagrams (if available)

# Architecture Validation
python scripts/validate_architecture.py              # Validate implementation vs design
grep -r "implementation\." architecture/*.dsl        # Check implementation status
```

## ARCHITECTURE_CONTEXT

### C4 Model Structure
1. **Level 1 - System Context**: Shows MCP server in ecosystem
2. **Level 2 - Container**: Major components (Gateway, Storage, Plugins)
3. **Level 3 - Component**: Detailed component interactions
4. **Level 4 - Code**: Class-level implementation details

### Key Architecture Files
- `code-index-mcp-architecture.dsl` - Main architecture definition
- `exports/` - Generated PlantUML diagrams
- `level4/` - Detailed component diagrams

### DSL Conventions
- Use `implementation.status` tag for completion tracking
- Tag with `implementation.complete` when fully implemented
- Include percentage in description for partial completion

## CODE_STYLE_PREFERENCES

### DSL Formatting
- 4-space indentation
- Group related elements
- Comment major sections
- Use consistent naming

### Diagram Standards
- Use official C4 colors
- Include legends
- Show implementation status
- Keep diagrams focused

## ARCHITECTURAL_PATTERNS

### MCP Architecture
1. **Gateway Pattern**: FastAPI gateway handles all MCP requests
2. **Plugin System**: Dynamic language support via plugin interface
3. **Storage Abstraction**: SQLite/PostgreSQL via common interface
4. **Transport Layer**: Stdio and WebSocket implementations

### Component Communication
- **Async First**: Use asyncio for all I/O operations
- **Message Passing**: JSON-RPC 2.0 for protocol
- **Event-Driven**: File watcher triggers indexing
- **Registry Pattern**: Tools, resources, plugins use registries

## DEVELOPMENT_ENVIRONMENT

### Architecture Tools
- **Structurizr CLI**: In `tools/` directory
- **PlantUML**: For diagram generation
- **Python Scripts**: Architecture validation tools
- **VS Code Extensions**: PlantUML preview, DSL syntax

### Validation Process
1. Update DSL files with changes
2. Run `structurizr validate`
3. Export and review diagrams
4. Check implementation alignment
5. Update status percentages

## RECENT_ARCHITECTURE_CHANGES

### Phase 4 Completion (2025-06-02)
- All components marked 100% complete
- Added production monitoring components
- Implemented distributed processing stubs
- Enhanced security components

### Documentation Updates (2025-06-03)
- Consolidated architecture docs
- Updated implementation status
- Added validation scripts
- Improved diagram exports

## STRUCTURIZR_CLI_REFERENCE

Below is the Structurizr CLI documentation for reference:

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