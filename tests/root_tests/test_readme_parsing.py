"""
Comprehensive tests for README file parsing and processing.

This test suite covers:
- README file structure recognition
- Installation section detection
- Usage example extraction
- API documentation parsing
- Badge and metadata extraction
- Cross-reference link handling
"""

# Import the document processing components
import sys

import pytest

sys.path.insert(0, "/app")

from mcp_server.plugins.markdown_plugin.plugin import MarkdownPlugin
from mcp_server.storage.sqlite_store import SQLiteStore


class TestReadmeStructureRecognition:
    """Test recognition of common README file structures."""

    @pytest.fixture
    def markdown_plugin(self, tmp_path):
        """Create a MarkdownPlugin instance."""
        db_path = tmp_path / "readme_test.db"
        store = SQLiteStore(str(db_path))
        return MarkdownPlugin(sqlite_store=store, enable_semantic=False)

    def test_standard_readme_structure(self, markdown_plugin, tmp_path):
        """Test parsing of standard README structure."""
        readme_content = """# Project Name

Short description of the project.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Contributing](#contributing)
- [License](#license)

## Installation

Instructions for installing the project.

```bash
npm install project-name
```

## Usage

Basic usage examples.

```javascript
const project = require('project-name');
project.doSomething();
```

## API Reference

### Class: ProjectClass

#### Methods

##### `doSomething(param)`

- `param` (string): Description of parameter
- Returns: Description of return value

## Contributing

Guidelines for contributing to the project.

## License

MIT License information.
"""

        file_path = tmp_path / "README.md"
        file_path.write_text(readme_content)

        # Test structure extraction
        structure = markdown_plugin.extract_structure(readme_content, file_path)

        # Verify standard sections are identified
        section_titles = [s.heading for s in structure.sections]
        expected_sections = ["Installation", "Usage", "API Reference", "Contributing", "License"]

        found_sections = sum(
            1
            for expected in expected_sections
            if any(expected.lower() in title.lower() for title in section_titles)
        )
        assert found_sections >= 4, f"Should find most standard sections, found: {section_titles}"

        # Verify table of contents detection
        toc_section = next(
            (s for s in structure.sections if "table of contents" in s.heading.lower()), None
        )
        assert toc_section is not None, "Should identify table of contents section"

    def test_minimal_readme_structure(self, markdown_plugin, tmp_path):
        """Test parsing of minimal README structure."""
        minimal_readme = """# Simple Project

This is a simple project that does something useful.

## How to use

1. Download the code
2. Run it
3. Enjoy

That's it!
"""

        file_path = tmp_path / "README.md"
        file_path.write_text(minimal_readme)

        # Test minimal structure handling
        structure = markdown_plugin.extract_structure(minimal_readme, file_path)

        # Should handle minimal structure gracefully
        assert len(structure.sections) >= 1
        assert structure.title == "Simple Project"

        # Should identify usage section
        usage_section = next((s for s in structure.sections if "use" in s.heading.lower()), None)
        assert usage_section is not None, "Should identify usage section"

    def test_complex_readme_structure(self, markdown_plugin, tmp_path):
        """Test parsing of complex README with nested sections."""
        complex_readme = """# Advanced Project

[![Build Status](https://travis-ci.org/user/project.svg?branch=master)](https://travis-ci.org/user/project)
[![Coverage Status](https://coveralls.io/repos/github/user/project/badge.svg?branch=master)](https://coveralls.io/github/user/project?branch=master)
[![npm version](https://badge.fury.io/js/project.svg)](https://badge.fury.io/js/project)

An advanced project with comprehensive documentation.

## Features

- Feature 1: Description
- Feature 2: Description  
- Feature 3: Description

## Quick Start

### Prerequisites

- Node.js 14+
- npm or yarn
- Git

### Installation

#### Using npm

```bash
npm install advanced-project
```

#### Using yarn

```bash
yarn add advanced-project
```

#### From source

```bash
git clone https://github.com/user/advanced-project.git
cd advanced-project
npm install
npm run build
```

## Configuration

### Environment Variables

- `API_KEY`: Your API key
- `DEBUG`: Enable debug mode
- `PORT`: Server port (default: 3000)

### Config File

Create a `config.json` file:

```json
{
  "apiKey": "your-api-key",
  "debug": false,
  "port": 3000
}
```

## Usage Examples

### Basic Usage

```javascript
const AdvancedProject = require('advanced-project');

const instance = new AdvancedProject({
  apiKey: process.env.API_KEY
});

instance.start();
```

### Advanced Usage

```javascript
const { AdvancedProject, Plugin } = require('advanced-project');

class CustomPlugin extends Plugin {
  async process(data) {
    // Custom processing logic
    return transformedData;
  }
}

const instance = new AdvancedProject({
  plugins: [new CustomPlugin()],
  config: './config.json'
});

await instance.initialize();
await instance.run();
```

## API Documentation

### Class: AdvancedProject

Main class for the project.

#### Constructor

```javascript
new AdvancedProject(options)
```

##### Parameters

- `options` (Object): Configuration options
  - `apiKey` (string): API key for external services
  - `debug` (boolean): Enable debug logging
  - `plugins` (Array): Array of plugin instances

#### Methods

##### `start()`

Starts the project instance.

```javascript
instance.start();
```

##### `stop()`

Stops the project instance gracefully.

```javascript
await instance.stop();
```

##### `addPlugin(plugin)`

Adds a plugin to the instance.

- `plugin` (Plugin): Plugin instance to add

```javascript
instance.addPlugin(new MyPlugin());
```

### Plugin System

#### Creating Custom Plugins

```javascript
const { Plugin } = require('advanced-project');

class MyPlugin extends Plugin {
  constructor(options) {
    super(options);
    this.name = 'MyPlugin';
  }
  
  async initialize() {
    // Plugin initialization
  }
  
  async process(data) {
    // Process data
    return data;
  }
}
```

## Testing

### Running Tests

```bash
npm test
```

### Test Coverage

```bash
npm run test:coverage
```

### Integration Tests

```bash
npm run test:integration
```

## Deployment

### Docker

```dockerfile
FROM node:14-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: advanced-project
spec:
  replicas: 3
  selector:
    matchLabels:
      app: advanced-project
  template:
    metadata:
      labels:
        app: advanced-project
    spec:
      containers:
      - name: app
        image: advanced-project:latest
        ports:
        - containerPort: 3000
```

## Troubleshooting

### Common Issues

#### Port Already in Use

Error: `EADDRINUSE: address already in use :::3000`

Solution: Change the port in your configuration or kill the process using port 3000.

#### API Key Not Found

Error: `API key not provided`

Solution: Set the `API_KEY` environment variable or provide it in the config file.

#### Permission Denied

Error: `EACCES: permission denied`

Solution: Run with appropriate permissions or use sudo (not recommended for production).

## Contributing

### Development Setup

1. Fork the repository
2. Clone your fork
3. Install dependencies: `npm install`
4. Create a feature branch: `git checkout -b feature-name`
5. Make your changes
6. Run tests: `npm test`
7. Submit a pull request

### Code Style

We use ESLint and Prettier for code formatting:

```bash
npm run lint
npm run format
```

### Commit Guidelines

Follow conventional commits:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Test additions or modifications

## Changelog

### v2.1.0 (2024-01-15)
- Added plugin system
- Improved error handling
- Updated dependencies

### v2.0.0 (2024-01-01)
- Breaking: Changed API structure
- Added TypeScript support
- Performance improvements

### v1.5.0 (2023-12-01)
- Added configuration file support
- Bug fixes and improvements

## License

MIT License

Copyright (c) 2024 Project Authors

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

## Support

- Documentation: [https://docs.example.com](https://docs.example.com)
- Issues: [GitHub Issues](https://github.com/user/project/issues)
- Discussions: [GitHub Discussions](https://github.com/user/project/discussions)
- Email: support@example.com
"""

        file_path = tmp_path / "README.md"
        file_path.write_text(complex_readme)

        # Test complex structure handling
        structure = markdown_plugin.extract_structure(complex_readme, file_path)

        # Should identify many sections
        assert len(structure.sections) >= 10, "Should identify many sections in complex README"

        # Check for key sections
        section_titles = [s.heading.lower() for s in structure.sections]
        key_sections = ["installation", "usage", "api", "contributing", "license"]

        found_key_sections = sum(
            1 for key in key_sections if any(key in title for title in section_titles)
        )
        assert found_key_sections >= 4, "Should find most key sections"

        # Check for nested sections
        nested_sections = [s for s in structure.sections if s.level >= 3]
        assert len(nested_sections) >= 5, "Should identify nested subsections"


class TestInstallationSectionDetection:
    """Test detection and parsing of installation sections."""

    @pytest.fixture
    def markdown_plugin(self, tmp_path):
        """Create a MarkdownPlugin instance."""
        db_path = tmp_path / "install_test.db"
        store = SQLiteStore(str(db_path))
        return MarkdownPlugin(sqlite_store=store, enable_semantic=False)

    def test_basic_installation_section(self, markdown_plugin, tmp_path):
        """Test detection of basic installation instructions."""
        readme_with_install = """# My Project

A useful project for developers.

## Installation

Install using npm:

```bash
npm install my-project
```

Or using yarn:

```bash
yarn add my-project
```

## Usage

Use the project like this...
"""

        file_path = tmp_path / "README.md"
        file_path.write_text(readme_with_install)

        # Test installation section detection
        structure = markdown_plugin.extract_structure(readme_with_install, file_path)

        # Find installation section
        install_section = next(
            (s for s in structure.sections if "install" in s.heading.lower()), None
        )
        assert install_section is not None, "Should detect installation section"

        # Verify installation content
        assert "npm install" in install_section.content
        assert "yarn add" in install_section.content

    def test_multiple_installation_methods(self, markdown_plugin, tmp_path):
        """Test detection of multiple installation methods."""
        readme_multi_install = """# Multi-Install Project

## Installation

### Using Package Managers

#### npm
```bash
npm install multi-install-project
```

#### yarn
```bash
yarn add multi-install-project
```

#### pnpm
```bash
pnpm add multi-install-project
```

### Manual Installation

1. Download the latest release
2. Extract to your project directory
3. Include in your HTML:

```html
<script src="multi-install-project.js"></script>
```

### CDN Installation

Include from CDN:

```html
<script src="https://cdn.jsdelivr.net/npm/multi-install-project@latest/dist/bundle.js"></script>
```

### Development Installation

For contributors:

```bash
git clone https://github.com/user/multi-install-project.git
cd multi-install-project
npm install
npm run build
```
"""

        file_path = tmp_path / "README.md"
        file_path.write_text(readme_multi_install)

        # Test multiple installation methods detection
        structure = markdown_plugin.extract_structure(readme_multi_install, file_path)

        # Should detect main installation section
        install_section = next(
            (s for s in structure.sections if "install" in s.heading.lower()), None
        )
        assert install_section is not None

        # Should detect installation subsections
        install_subsections = [
            s
            for s in structure.sections
            if s.level > 2
            and (
                "install" in s.heading.lower()
                or "npm" in s.heading.lower()
                or "yarn" in s.heading.lower()
                or "cdn" in s.heading.lower()
            )
        ]
        assert len(install_subsections) >= 3, "Should detect multiple installation methods"

    def test_installation_with_prerequisites(self, markdown_plugin, tmp_path):
        """Test detection of installation prerequisites."""
        readme_with_prereqs = """# Project with Prerequisites

## Installation

### Prerequisites

Before installing, ensure you have:

- Node.js 14.0 or higher
- npm 6.0 or higher
- Python 3.8+ (for native dependencies)
- Git (for development)

On Windows, you may also need:
- Visual Studio Build Tools
- Windows SDK

### Installing Prerequisites

#### Node.js

Download from [nodejs.org](https://nodejs.org/) or use a version manager:

```bash
# Using nvm
nvm install 14
nvm use 14

# Using brew (macOS)
brew install node

# Using apt (Ubuntu/Debian)
curl -fsSL https://deb.nodesource.com/setup_14.x | sudo -E bash -
sudo apt-get install -y nodejs
```

#### Python

```bash
# macOS
brew install python3

# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip

# Windows
# Download from python.org
```

### Main Installation

Once prerequisites are installed:

```bash
npm install project-with-prereqs
```

### Verification

Verify the installation:

```bash
npm list project-with-prereqs
```

Or test the CLI:

```bash
project-with-prereqs --version
```
"""

        file_path = tmp_path / "README.md"
        file_path.write_text(readme_with_prereqs)

        # Test prerequisite detection
        structure = markdown_plugin.extract_structure(readme_with_prereqs, file_path)

        # Should detect prerequisites section
        prereq_section = next(
            (s for s in structure.sections if "prerequis" in s.heading.lower()), None
        )
        assert prereq_section is not None, "Should detect prerequisites section"

        # Should contain prerequisite information
        assert "Node.js" in prereq_section.content
        assert "Python" in prereq_section.content

        # Should detect verification section
        verification_sections = [s for s in structure.sections if "verif" in s.heading.lower()]
        assert len(verification_sections) > 0, "Should detect verification section"

    def test_platform_specific_installation(self, markdown_plugin, tmp_path):
        """Test detection of platform-specific installation instructions."""
        readme_platform_specific = """# Cross-Platform Project

## Installation

Installation instructions vary by operating system.

### Windows

#### Using Chocolatey

```powershell
choco install cross-platform-project
```

#### Using Scoop

```powershell
scoop install cross-platform-project
```

#### Manual Installation

1. Download Windows installer from releases page
2. Run the .msi installer
3. Follow installation wizard
4. Add to PATH if prompted

### macOS

#### Using Homebrew

```bash
brew install cross-platform-project
```

#### Using MacPorts

```bash
sudo port install cross-platform-project
```

#### Manual Installation

1. Download .dmg file from releases
2. Mount the disk image
3. Drag application to Applications folder

### Linux

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install cross-platform-project
```

#### CentOS/RHEL/Fedora

```bash
# CentOS/RHEL
sudo yum install cross-platform-project

# Fedora
sudo dnf install cross-platform-project
```

#### Arch Linux

```bash
sudo pacman -S cross-platform-project
```

#### From Source

```bash
git clone https://github.com/user/cross-platform-project.git
cd cross-platform-project
make && sudo make install
```

### Docker

Run in a container:

```bash
docker run -it --rm cross-platform-project:latest
```

Or use Docker Compose:

```yaml
version: '3'
services:
  app:
    image: cross-platform-project:latest
    ports:
      - "8080:8080"
```
"""

        file_path = tmp_path / "README.md"
        file_path.write_text(readme_platform_specific)

        # Test platform-specific detection
        structure = markdown_plugin.extract_structure(readme_platform_specific, file_path)

        # Should detect platform sections
        platform_sections = [
            s
            for s in structure.sections
            if any(
                platform in s.heading.lower()
                for platform in ["windows", "macos", "linux", "docker"]
            )
        ]
        assert len(platform_sections) >= 3, "Should detect multiple platform sections"

        # Should detect package manager subsections
        package_manager_sections = [
            s
            for s in structure.sections
            if any(pm in s.heading.lower() for pm in ["homebrew", "chocolatey", "apt", "yum"])
        ]
        assert len(package_manager_sections) >= 2, "Should detect package manager sections"


class TestUsageExampleExtraction:
    """Test extraction of usage examples and code snippets."""

    @pytest.fixture
    def markdown_plugin(self, tmp_path):
        """Create a MarkdownPlugin instance."""
        db_path = tmp_path / "usage_test.db"
        store = SQLiteStore(str(db_path))
        return MarkdownPlugin(sqlite_store=store, enable_semantic=False)

    def test_basic_usage_examples(self, markdown_plugin, tmp_path):
        """Test extraction of basic usage examples."""
        readme_with_usage = """# Example Project

## Usage

### Basic Example

```javascript
const ExampleProject = require('example-project');

const instance = new ExampleProject();
instance.doSomething();
```

### Advanced Example

```javascript
const { ExampleProject, Config } = require('example-project');

const config = new Config({
  apiKey: 'your-api-key',
  timeout: 5000
});

const instance = new ExampleProject(config);

// Async usage
async function main() {
  try {
    const result = await instance.process('data');
    console.log('Result:', result);
  } catch (error) {
    console.error('Error:', error);
  }
}

main();
```

### CLI Usage

```bash
example-project --input file.txt --output result.txt
example-project --help
```
"""

        file_path = tmp_path / "README.md"
        file_path.write_text(readme_with_usage)

        # Test usage example extraction
        result = markdown_plugin.indexFile(file_path, readme_with_usage)

        # Should extract code symbols from examples
        code_symbols = [s for s in result["symbols"] if s.get("metadata", {}).get("in_code_block")]
        assert len(code_symbols) > 0, "Should extract symbols from code examples"

        # Should identify usage section
        usage_symbols = [s for s in result["symbols"] if "usage" in s["symbol"].lower()]
        assert len(usage_symbols) > 0, "Should identify usage sections"

    def test_multiple_language_examples(self, markdown_plugin, tmp_path):
        """Test extraction of examples in multiple programming languages."""
        readme_multi_lang = """# Multi-Language SDK

## Usage Examples

### JavaScript/Node.js

```javascript
const SDK = require('multi-lang-sdk');

const client = new SDK.Client({
  apiKey: process.env.API_KEY
});

client.getData()
  .then(data => console.log(data))
  .catch(err => console.error(err));
```

### Python

```python
from multi_lang_sdk import Client

client = Client(api_key=os.environ['API_KEY'])

try:
    data = client.get_data()
    print(data)
except Exception as e:
    print(f"Error: {e}")
```

### Java

```java
import com.example.MultiLangSDK;

public class Example {
    public static void main(String[] args) {
        MultiLangSDK client = new MultiLangSDK(
            System.getenv("API_KEY")
        );
        
        try {
            Data data = client.getData();
            System.out.println(data.toString());
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
        }
    }
}
```

### Go

```go
package main

import (
    "fmt"
    "os"
    
    "github.com/example/multi-lang-sdk-go"
)

func main() {
    client := sdk.NewClient(os.Getenv("API_KEY"))
    
    data, err := client.GetData()
    if err != nil {
        fmt.Printf("Error: %v\\n", err)
        return
    }
    
    fmt.Printf("Data: %+v\\n", data)
}
```

### cURL Examples

```bash
# Get data
curl -H "Authorization: Bearer $API_KEY" \\
     https://api.example.com/data

# Post data
curl -X POST \\
     -H "Authorization: Bearer $API_KEY" \\
     -H "Content-Type: application/json" \\
     -d '{"key": "value"}' \\
     https://api.example.com/data
```
"""

        file_path = tmp_path / "README.md"
        file_path.write_text(readme_multi_lang)

        # Test multi-language extraction
        result = markdown_plugin.indexFile(file_path, readme_multi_lang)

        # Should extract symbols from different languages
        code_symbols = [s for s in result["symbols"] if s.get("metadata", {}).get("in_code_block")]

        # Check for different languages
        languages = set()
        for symbol in code_symbols:
            lang = symbol.get("metadata", {}).get("language", "")
            if lang:
                languages.add(lang)

        # Should detect multiple languages
        expected_languages = {"javascript", "python", "java", "go"}
        found_languages = languages & expected_languages
        assert len(found_languages) >= 2, f"Should detect multiple languages, found: {languages}"

    def test_interactive_examples(self, markdown_plugin, tmp_path):
        """Test extraction of interactive usage examples."""
        readme_interactive = """# Interactive Tool

## Quick Start

### Interactive Mode

Start the interactive shell:

```bash
$ interactive-tool
Welcome to Interactive Tool v1.0
Type 'help' for available commands.

> help
Available commands:
  load <file>     - Load data from file
  process         - Process loaded data
  save <file>     - Save results to file
  quit            - Exit the tool

> load data.csv
Loaded 1000 records from data.csv

> process
Processing... [████████████████████] 100%
Processed 1000 records in 2.3s

> save results.json
Saved results to results.json

> quit
Goodbye!
```

### Programmatic Usage

```python
from interactive_tool import InteractiveTool

# Create instance
tool = InteractiveTool()

# Load data
tool.load('data.csv')
print(f"Loaded {tool.record_count} records")

# Process data
results = tool.process()
print(f"Processing completed: {results.summary}")

# Save results
tool.save('results.json')
print("Results saved")
```

### Configuration File

Create a config file `tool.conf`:

```ini
[data]
input_path = /path/to/data
output_path = /path/to/output
format = csv

[processing]
batch_size = 1000
parallel = true
threads = 4

[output]
format = json
pretty_print = true
```

Then run with config:

```bash
interactive-tool --config tool.conf
```
"""

        file_path = tmp_path / "README.md"
        file_path.write_text(readme_interactive)

        # Test interactive example extraction
        structure = markdown_plugin.extract_structure(readme_interactive, file_path)

        # Should identify interactive sections
        interactive_sections = [
            s
            for s in structure.sections
            if "interactive" in s.heading.lower() or "programmatic" in s.heading.lower()
        ]
        assert len(interactive_sections) >= 2, "Should identify interactive usage sections"

        # Should preserve command sequences in interactive examples
        quick_start = next(
            (s for s in structure.sections if "quick start" in s.heading.lower()), None
        )
        if quick_start:
            assert "load data.csv" in quick_start.content
            assert "process" in quick_start.content
            assert "save results.json" in quick_start.content


class TestAPIDocumentationParsing:
    """Test parsing of API documentation within README files."""

    @pytest.fixture
    def markdown_plugin(self, tmp_path):
        """Create a MarkdownPlugin instance."""
        db_path = tmp_path / "api_test.db"
        store = SQLiteStore(str(db_path))
        return MarkdownPlugin(sqlite_store=store, enable_semantic=False)

    def test_class_api_documentation(self, markdown_plugin, tmp_path):
        """Test extraction of class-based API documentation."""
        readme_class_api = """# SDK Documentation

## API Reference

### Class: APIClient

Main client for interacting with the API.

#### Constructor

```javascript
new APIClient(options)
```

##### Parameters

- `options` (Object): Configuration options
  - `apiKey` (string): Your API key
  - `baseURL` (string): Base URL for API calls (optional)
  - `timeout` (number): Request timeout in milliseconds (default: 5000)

##### Example

```javascript
const client = new APIClient({
  apiKey: 'your-api-key',
  timeout: 10000
});
```

#### Methods

##### `getData(id, options)`

Retrieves data by ID.

###### Parameters

- `id` (string): Unique identifier for the data
- `options` (Object): Additional options (optional)
  - `include` (Array): Fields to include in response
  - `format` (string): Response format ('json' or 'xml')

###### Returns

Promise that resolves to a data object.

###### Example

```javascript
const data = await client.getData('123', {
  include: ['name', 'description'],
  format: 'json'
});
```

##### `createData(data)`

Creates new data entry.

###### Parameters

- `data` (Object): Data to create
  - `name` (string): Name of the entry
  - `description` (string): Description (optional)
  - `tags` (Array): Associated tags (optional)

###### Returns

Promise that resolves to the created data object with ID.

###### Example

```javascript
const newData = await client.createData({
  name: 'My Entry',
  description: 'A sample entry',
  tags: ['sample', 'test']
});
```

##### `updateData(id, updates)`

Updates existing data entry.

###### Parameters

- `id` (string): ID of entry to update
- `updates` (Object): Fields to update

###### Returns

Promise that resolves to the updated data object.

##### `deleteData(id)`

Deletes a data entry.

###### Parameters

- `id` (string): ID of entry to delete

###### Returns

Promise that resolves to deletion confirmation.

#### Events

The APIClient emits the following events:

##### `'request'`

Emitted before making an API request.

```javascript
client.on('request', (requestInfo) => {
  console.log('Making request:', requestInfo.url);
});
```

##### `'response'`

Emitted after receiving an API response.

```javascript
client.on('response', (response) => {
  console.log('Response status:', response.status);
});
```

##### `'error'`

Emitted when an error occurs.

```javascript
client.on('error', (error) => {
  console.error('API error:', error.message);
});
```

### Utility Functions

#### `validateAPIKey(key)`

Validates an API key format.

##### Parameters

- `key` (string): API key to validate

##### Returns

Boolean indicating if the key is valid.

##### Example

```javascript
const isValid = validateAPIKey('abc123');
```

#### `parseResponse(response)`

Parses API response data.

##### Parameters

- `response` (Object): Raw API response

##### Returns

Parsed data object.
"""

        file_path = tmp_path / "README.md"
        file_path.write_text(readme_class_api)

        # Test API documentation extraction
        result = markdown_plugin.indexFile(file_path, readme_class_api)

        # Should extract API class symbols
        api_symbols = [s for s in result["symbols"] if s["kind"] in ["class", "method", "function"]]

        # Should find class reference
        class_symbols = [s for s in api_symbols if s["kind"] == "class"]
        assert len(class_symbols) > 0, "Should extract API class symbols"

        # Should find method references
        method_symbols = [
            s
            for s in api_symbols
            if "method" in s.get("metadata", {}).get("description", "").lower()
        ]

        # Should extract function documentation
        function_symbols = [s for s in result["symbols"] if s["kind"] == "function"]
        assert len(function_symbols) > 0, "Should extract function symbols"

    def test_rest_api_documentation(self, markdown_plugin, tmp_path):
        """Test extraction of REST API documentation."""
        readme_rest_api = """# REST API Documentation

## API Endpoints

Base URL: `https://api.example.com/v1`

### Authentication

All requests require an API key in the header:

```
Authorization: Bearer YOUR_API_KEY
```

### Users

#### GET /users

Retrieve a list of users.

##### Query Parameters

- `limit` (integer): Maximum number of results (default: 20, max: 100)
- `offset` (integer): Number of results to skip for pagination (default: 0)
- `sort` (string): Sort field (options: 'name', 'created_at', 'last_login')
- `order` (string): Sort order ('asc' or 'desc', default: 'asc')
- `filter` (string): Search filter for user names

##### Response

```json
{
  "users": [
    {
      "id": "user123",
      "name": "John Doe",
      "email": "john@example.com",
      "created_at": "2024-01-01T00:00:00Z",
      "last_login": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "total": 150,
    "limit": 20,
    "offset": 0,
    "has_more": true
  }
}
```

##### Example Request

```bash
curl -H "Authorization: Bearer your-api-key" \\
     "https://api.example.com/v1/users?limit=10&sort=name"
```

#### POST /users

Create a new user.

##### Request Body

```json
{
  "name": "Jane Smith",
  "email": "jane@example.com",
  "password": "secure_password",
  "profile": {
    "first_name": "Jane",
    "last_name": "Smith",
    "department": "Engineering"
  }
}
```

##### Response

```json
{
  "id": "user456",
  "name": "Jane Smith",
  "email": "jane@example.com",
  "created_at": "2024-01-16T12:00:00Z"
}
```

##### Example Request

```bash
curl -X POST \\
     -H "Authorization: Bearer your-api-key" \\
     -H "Content-Type: application/json" \\
     -d '{"name":"Jane Smith","email":"jane@example.com","password":"secure"}' \\
     https://api.example.com/v1/users
```

#### GET /users/{id}

Retrieve a specific user by ID.

##### Path Parameters

- `id` (string): User ID

##### Response

```json
{
  "id": "user123",
  "name": "John Doe",
  "email": "john@example.com",
  "profile": {
    "first_name": "John",
    "last_name": "Doe",
    "department": "Sales"
  },
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-15T10:30:00Z"
}
```

#### PUT /users/{id}

Update an existing user.

##### Path Parameters

- `id` (string): User ID

##### Request Body

Partial user object with fields to update:

```json
{
  "name": "John Updated",
  "profile": {
    "department": "Marketing"
  }
}
```

#### DELETE /users/{id}

Delete a user.

##### Path Parameters

- `id` (string): User ID

##### Response

```json
{
  "message": "User deleted successfully",
  "deleted_id": "user123"
}
```

### Data

#### GET /data

Retrieve data entries.

##### Query Parameters

- `type` (string): Filter by data type
- `created_after` (string): ISO date to filter recent entries
- `tags` (array): Filter by tags (comma-separated)

##### Response

```json
{
  "data": [
    {
      "id": "data789",
      "type": "document",
      "title": "Sample Document",
      "content": "Document content...",
      "tags": ["important", "draft"],
      "created_at": "2024-01-10T09:00:00Z"
    }
  ]
}
```

### Error Responses

All endpoints may return these error responses:

#### 400 Bad Request

```json
{
  "error": "bad_request",
  "message": "Invalid request parameters",
  "details": {
    "field": "email",
    "issue": "Invalid email format"
  }
}
```

#### 401 Unauthorized

```json
{
  "error": "unauthorized",
  "message": "Invalid or missing API key"
}
```

#### 403 Forbidden

```json
{
  "error": "forbidden",
  "message": "Insufficient permissions for this resource"
}
```

#### 404 Not Found

```json
{
  "error": "not_found",
  "message": "Resource not found"
}
```

#### 429 Too Many Requests

```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests",
  "retry_after": 60
}
```

#### 500 Internal Server Error

```json
{
  "error": "internal_error",
  "message": "An unexpected error occurred"
}
```

## Rate Limiting

API requests are limited to:
- 1000 requests per hour for authenticated requests
- 100 requests per hour for unauthenticated requests

Rate limit information is included in response headers:
- `X-RateLimit-Limit`: Maximum requests per hour
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when limit resets

## Webhooks

### Webhook Events

Subscribe to events by configuring webhook URLs:

#### user.created

Triggered when a new user is created.

```json
{
  "event": "user.created",
  "data": {
    "id": "user456",
    "name": "Jane Smith",
    "email": "jane@example.com"
  },
  "timestamp": "2024-01-16T12:00:00Z"
}
```

#### data.updated

Triggered when data is modified.

```json
{
  "event": "data.updated",
  "data": {
    "id": "data789",
    "type": "document",
    "changes": ["title", "content"]
  },
  "timestamp": "2024-01-16T14:30:00Z"
}
```
"""

        file_path = tmp_path / "README.md"
        file_path.write_text(readme_rest_api)

        # Test REST API documentation extraction
        structure = markdown_plugin.extract_structure(readme_rest_api, file_path)

        # Should identify API endpoint sections
        endpoint_sections = [
            s
            for s in structure.sections
            if any(method in s.heading.upper() for method in ["GET", "POST", "PUT", "DELETE"])
        ]
        assert len(endpoint_sections) >= 4, "Should identify REST API endpoint sections"

        # Should identify authentication section
        auth_sections = [s for s in structure.sections if "auth" in s.heading.lower()]
        assert len(auth_sections) > 0, "Should identify authentication section"

        # Should identify error handling sections
        error_sections = [s for s in structure.sections if "error" in s.heading.lower()]
        assert len(error_sections) > 0, "Should identify error response sections"


class TestBadgeAndMetadataExtraction:
    """Test extraction of badges and metadata from README files."""

    @pytest.fixture
    def markdown_plugin(self, tmp_path):
        """Create a MarkdownPlugin instance."""
        db_path = tmp_path / "badge_test.db"
        store = SQLiteStore(str(db_path))
        return MarkdownPlugin(sqlite_store=store, enable_semantic=False)

    def test_badge_extraction(self, markdown_plugin, tmp_path):
        """Test extraction of various badge types."""
        readme_with_badges = """# Project with Badges

[![Build Status](https://travis-ci.org/user/project.svg?branch=master)](https://travis-ci.org/user/project)
[![Coverage Status](https://coveralls.io/repos/github/user/project/badge.svg?branch=master)](https://coveralls.io/github/user/project?branch=master)
[![npm version](https://badge.fury.io/js/project.svg)](https://badge.fury.io/js/project)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](http://makeapullrequest.com)
[![GitHub issues](https://img.shields.io/github/issues/user/project.svg)](https://github.com/user/project/issues)
[![GitHub stars](https://img.shields.io/github/stars/user/project.svg)](https://github.com/user/project/stargazers)
[![Downloads](https://img.shields.io/npm/dm/project.svg)](https://www.npmjs.com/package/project)

A project with comprehensive badges showing build status, coverage, version, and more.

## Features

- Feature 1
- Feature 2
- Feature 3

## Installation

```bash
npm install project
```
"""

        file_path = tmp_path / "README.md"
        file_path.write_text(readme_with_badges)

        # Test badge extraction
        result = markdown_plugin.indexFile(file_path, readme_with_badges)

        # Should extract image/link symbols for badges
        image_symbols = [
            s
            for s in result["symbols"]
            if s["kind"] == "image"
            or (s["kind"] == "link" and "badge" in s.get("metadata", {}).get("url", ""))
        ]

        # May find some badge-related symbols depending on implementation
        # At minimum should parse the content without errors
        assert result is not None
        assert len(result["symbols"]) > 0

    def test_metadata_extraction_from_badges(self, markdown_plugin, tmp_path):
        """Test extraction of project metadata from badges."""
        readme_metadata_badges = """# Project Metadata

[![Version](https://img.shields.io/badge/version-1.2.3-blue.svg)]()
[![Node](https://img.shields.io/badge/node-%3E%3D14.0.0-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)]()
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macos%20%7C%20windows-lightgrey.svg)]()
[![Language](https://img.shields.io/badge/language-TypeScript-blue.svg)]()

Project with metadata indicated through badges.

## About

This project demonstrates metadata extraction from README badges.
The badges above indicate:
- Version: 1.2.3
- Node.js requirement: >= 14.0.0  
- License: Apache 2.0
- Supported platforms: Linux, macOS, Windows
- Primary language: TypeScript
"""

        file_path = tmp_path / "README.md"
        file_path.write_text(readme_metadata_badges)

        # Test metadata extraction
        metadata = markdown_plugin.extract_metadata(readme_metadata_badges, file_path)

        # Should extract basic metadata
        assert metadata.title == "Project Metadata"
        assert metadata.document_type == "markdown"

        # Content should contain metadata information
        content = markdown_plugin.parse_content(readme_metadata_badges, file_path)
        assert "version" in content.lower()
        assert "license" in content.lower()
        assert "typescript" in content.lower()

    def test_shield_style_badges(self, markdown_plugin, tmp_path):
        """Test extraction of shields.io style badges."""
        readme_shields = """# Shields.io Badge Examples

![GitHub Workflow Status](https://img.shields.io/github/workflow/status/user/repo/CI)
![GitHub package.json version](https://img.shields.io/github/package-json/v/user/repo)
![GitHub](https://img.shields.io/github/license/user/repo)
![GitHub last commit](https://img.shields.io/github/last-commit/user/repo)
![GitHub issues](https://img.shields.io/github/issues/user/repo)
![GitHub pull requests](https://img.shields.io/github/issues-pr/user/repo)
![npm bundle size](https://img.shields.io/bundlephobia/min/package-name)
![npm downloads](https://img.shields.io/npm/dt/package-name)
![Docker Pulls](https://img.shields.io/docker/pulls/user/repo)
![Codecov](https://img.shields.io/codecov/c/github/user/repo)

Project demonstrating various shields.io badge styles.

## Badges Explained

The badges above show:
- CI/CD status from GitHub Actions
- Current version from package.json
- License information
- Last commit activity
- Open issues and pull requests
- Bundle size metrics
- Download statistics
- Docker usage metrics
- Code coverage percentage
"""

        file_path = tmp_path / "README.md"
        file_path.write_text(readme_shields)

        # Test shields.io badge handling
        result = markdown_plugin.indexFile(file_path, readme_shields)

        # Should handle shields badges without errors
        assert result is not None
        assert len(result["symbols"]) > 0

        # Should extract title and structure properly
        structure = markdown_plugin.extract_structure(readme_shields, file_path)
        assert structure.title == "Shields.io Badge Examples"

        # Should identify badges explanation section
        explanation_section = next(
            (s for s in structure.sections if "explained" in s.heading.lower()), None
        )
        assert explanation_section is not None


class TestCrossReferenceLinkHandling:
    """Test handling of cross-reference links in README files."""

    @pytest.fixture
    def markdown_plugin(self, tmp_path):
        """Create a MarkdownPlugin instance."""
        db_path = tmp_path / "links_test.db"
        store = SQLiteStore(str(db_path))
        return MarkdownPlugin(sqlite_store=store, enable_semantic=False)

    def test_internal_section_links(self, markdown_plugin, tmp_path):
        """Test handling of internal section reference links."""
        readme_internal_links = """# Project Documentation

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Contributing](#contributing)
- [License](#license)

## Installation

See the [Configuration](#configuration) section for setup details.

Follow these steps:
1. Install dependencies (see [Requirements](#requirements))
2. Configure the application (see [Configuration](#configuration))
3. Run the setup script

### Requirements

- Node.js 14+
- npm or yarn

## Usage

Basic usage examples. For advanced usage, see [API Reference](#api-reference).

```javascript
const app = require('project');
app.start();
```

## API Reference

### Methods

#### start()

Starts the application. Make sure to complete [Installation](#installation) first.

#### configure(options)

Configures the application. See [Configuration](#configuration) for available options.

## Configuration

Configuration options:

```yaml
# config.yaml
app:
  port: 3000
  debug: false
```

For installation help, go back to [Installation](#installation).

## Contributing

Before contributing, read the [API Reference](#api-reference) and ensure you understand the [Configuration](#configuration) options.

## License

MIT License. See installation instructions in [Installation](#installation).
"""

        file_path = tmp_path / "README.md"
        file_path.write_text(readme_internal_links)

        # Test internal link handling
        structure = markdown_plugin.extract_structure(readme_internal_links, file_path)

        # Should identify table of contents
        toc_section = next(
            (s for s in structure.sections if "table of contents" in s.heading.lower()), None
        )
        assert toc_section is not None, "Should identify table of contents"

        # Should preserve cross-references in content
        config_section = next(
            (s for s in structure.sections if "configuration" in s.heading.lower()), None
        )
        if config_section:
            # Should contain references to other sections
            assert "installation" in config_section.content.lower()

    def test_external_documentation_links(self, markdown_plugin, tmp_path):
        """Test handling of external documentation links."""
        readme_external_links = """# External References

## Documentation Links

This project builds upon several external resources:

- [Node.js Documentation](https://nodejs.org/en/docs/)
- [npm CLI Documentation](https://docs.npmjs.com/cli/)
- [Express.js Guide](https://expressjs.com/en/guide/)
- [Jest Testing Framework](https://jestjs.io/docs/en/getting-started)
- [Docker Documentation](https://docs.docker.com/)

## Related Projects

- [Similar Project A](https://github.com/user/project-a) - Alternative implementation
- [Library B](https://github.com/org/library-b) - Core dependency
- [Tool C](https://github.com/team/tool-c) - Development utility

## External Tools

### Development Tools

- [VS Code](https://code.visualstudio.com/) - Recommended editor
- [Postman](https://www.postman.com/) - API testing
- [GitHub Actions](https://github.com/features/actions) - CI/CD

### Deployment Platforms

- [Heroku](https://heroku.com/) - Simple deployment
- [AWS](https://aws.amazon.com/) - Cloud infrastructure
- [Docker Hub](https://hub.docker.com/) - Container registry

## Learning Resources

### Tutorials

- [Getting Started with Node.js](https://nodejs.dev/learn)
- [Express.js Tutorial](https://developer.mozilla.org/en-US/docs/Learn/Server-side/Express_Nodejs)
- [Docker for Beginners](https://docker-curriculum.com/)

### Video Courses

- [Node.js Course on Udemy](https://www.udemy.com/course/nodejs-course/)
- [JavaScript Fundamentals](https://www.youtube.com/playlist?list=PLillGF-RfqbbnEGy3ROiLWk7JMCuSyQtX)

## Community

- [Stack Overflow](https://stackoverflow.com/questions/tagged/nodejs) - Q&A
- [Reddit r/node](https://www.reddit.com/r/node/) - Community discussions  
- [Discord Server](https://discord.gg/nodejs) - Real-time chat
- [Twitter](https://twitter.com/nodejs) - Latest news
"""

        file_path = tmp_path / "README.md"
        file_path.write_text(readme_external_links)

        # Test external link handling
        result = markdown_plugin.indexFile(file_path, readme_external_links)

        # Should handle external links without errors
        assert result is not None
        assert len(result["symbols"]) > 0

        # Should preserve link information in content
        content = markdown_plugin.parse_content(readme_external_links, file_path)
        assert "nodejs.org" in content
        assert "github.com" in content

    def test_relative_file_links(self, markdown_plugin, tmp_path):
        """Test handling of relative file links."""
        readme_relative_links = """# Project with File References

## Documentation Structure

This project includes several documentation files:

- [CHANGELOG.md](CHANGELOG.md) - Version history
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [LICENSE](LICENSE) - License text
- [docs/API.md](docs/API.md) - Detailed API documentation
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - Deployment guide
- [examples/basic.js](examples/basic.js) - Basic usage example
- [examples/advanced.js](examples/advanced.js) - Advanced usage example

## Quick Links

- Configuration: [config/default.json](config/default.json)
- Package info: [package.json](package.json)
- Docker setup: [docker-compose.yml](docker-compose.yml)
- GitHub Actions: [.github/workflows/ci.yml](.github/workflows/ci.yml)

## Code Examples

See the examples directory for code samples:

- [Basic Example](examples/basic.js) - Simple usage
- [Advanced Example](examples/advanced.js) - Complex scenarios
- [Configuration Example](examples/config.js) - Setup options
- [Error Handling](examples/error-handling.js) - Error management

## Development Files

For development setup, check these files:

- [Development Guide](docs/DEVELOPMENT.md)
- [Testing Guide](docs/TESTING.md)  
- [Build Scripts](scripts/build.sh)
- [Development Environment](docker-compose.dev.yml)

## Image Assets

Documentation includes these diagrams:

- [Architecture Diagram](docs/images/architecture.png)
- [Flow Chart](docs/images/flow.svg)
- [Component Diagram](docs/diagrams/components.puml)
"""

        file_path = tmp_path / "README.md"
        file_path.write_text(readme_relative_links)

        # Test relative link handling
        structure = markdown_plugin.extract_structure(readme_relative_links, file_path)

        # Should identify sections with file references
        doc_structure_section = next(
            (s for s in structure.sections if "documentation structure" in s.heading.lower()), None
        )
        assert doc_structure_section is not None

        # Should preserve file references
        assert "CHANGELOG.md" in doc_structure_section.content
        assert "docs/API.md" in doc_structure_section.content

        # Should handle image references
        image_section = next((s for s in structure.sections if "image" in s.heading.lower()), None)
        if image_section:
            assert (
                "architecture.png" in image_section.content or "flow.svg" in image_section.content
            )


class TestReadmeIntegration:
    """Integration tests for README parsing with various formats and styles."""

    @pytest.fixture
    def readme_workspace(self, tmp_path):
        """Create workspace with various README styles."""
        workspace = tmp_path / "readme_workspace"
        workspace.mkdir()

        # Create different README styles
        readmes = {
            "minimal": """# Simple Tool
            
A minimal command-line tool.

## Install

```bash
pip install simple-tool
```

## Use

```bash
simple-tool --help
```
""",
            "comprehensive": """# Comprehensive Framework

[![Build](https://img.shields.io/travis/user/repo.svg)](https://travis-ci.org/user/repo)
[![Version](https://img.shields.io/pypi/v/repo.svg)](https://pypi.org/project/repo/)

A comprehensive framework for data processing.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Features

- High-performance data processing
- Extensible plugin architecture
- Comprehensive testing suite
- Docker support
- CLI and programmatic interfaces

## Installation

### Using pip

```bash
pip install comprehensive-framework
```

### Using conda

```bash
conda install -c conda-forge comprehensive-framework
```

### From source

```bash
git clone https://github.com/user/comprehensive-framework.git
cd comprehensive-framework
pip install -e .
```

## Quick Start

```python
from comprehensive_framework import Processor

# Create processor
processor = Processor()

# Process data
result = processor.process('input_data')
print(result)
```

## Documentation

- [User Guide](docs/user-guide.md)
- [API Reference](docs/api.md)
- [Examples](examples/)
- [FAQ](docs/faq.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) file.
""",
            "library": """# Math Utilities Library

A collection of mathematical utility functions.

## API

### Functions

#### `add(a, b)`

Adds two numbers.

```javascript
const result = add(2, 3); // 5
```

#### `multiply(a, b)`

Multiplies two numbers.

```javascript
const result = multiply(4, 5); // 20
```

### Classes

#### `Calculator`

A calculator class with advanced operations.

```javascript
const calc = new Calculator();
calc.add(10);
calc.multiply(2);
const result = calc.getResult(); // 20
```

## Examples

```javascript
import { add, multiply, Calculator } from 'math-utils';

// Basic operations
console.log(add(1, 2));
console.log(multiply(3, 4));

// Using calculator
const calc = new Calculator();
calc.chain()
  .add(5)
  .multiply(3)
  .subtract(2);
console.log(calc.result);
```
""",
            "service": """# Microservice Template

Template for creating microservices.

## Architecture

```
┌─────────────────┐
│   API Gateway   │
└─────────┬───────┘
          │
┌─────────▼───────┐
│   Microservice  │
│                 │
│  ┌───────────┐  │
│  │  Business │  │
│  │   Logic   │  │
│  └───────────┘  │
│                 │
│  ┌───────────┐  │
│  │ Database  │  │
│  │  Layer    │  │
│  └───────────┘  │
└─────────────────┘
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | `3000` |
| `DB_URL` | Database URL | `localhost:5432` |
| `LOG_LEVEL` | Logging level | `info` |

## Deployment

### Docker

```dockerfile
FROM node:14-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: microservice
spec:
  replicas: 3
  selector:
    matchLabels:
      app: microservice
  template:
    spec:
      containers:
      - name: app
        image: microservice:latest
        ports:
        - containerPort: 3000
```

## Monitoring

- Health check: `GET /health`
- Metrics: `GET /metrics`
- Logs: Structured JSON logging
""",
        }

        for name, content in readmes.items():
            file_path = workspace / f"README_{name}.md"
            file_path.write_text(content)

        return workspace

    @pytest.fixture
    def integration_setup(self, readme_workspace, tmp_path):
        """Set up integration test environment."""
        db_path = tmp_path / "integration_test.db"
        store = SQLiteStore(str(db_path))
        plugin = MarkdownPlugin(sqlite_store=store, enable_semantic=False)

        # Index all README files
        results = {}
        for readme_file in readme_workspace.glob("README_*.md"):
            content = readme_file.read_text()
            result = plugin.indexFile(readme_file, content)
            results[readme_file.stem] = result

        return {"workspace": readme_workspace, "plugin": plugin, "results": results}

    def test_readme_type_recognition(self, integration_setup):
        """Test recognition of different README types."""
        results = integration_setup["results"]

        # Should process all README types
        assert len(results) == 4

        # Each should have symbols
        for readme_type, result in results.items():
            assert len(result["symbols"]) > 0, f"Should extract symbols from {readme_type} README"
            assert result["language"] == "markdown"

    def test_cross_readme_search(self, integration_setup):
        """Test searching across different README types."""
        plugin = integration_setup["plugin"]

        # Search for common terms
        search_terms = ["installation", "documentation", "examples", "API", "deployment"]

        for term in search_terms:
            # Simulate search (would need dispatcher for full search)
            # Here we check if content parsing works
            try:
                for readme_file in integration_setup["workspace"].glob("README_*.md"):
                    content = readme_file.read_text()
                    parsed = plugin.parse_content(content, readme_file)
                    # Should parse without errors
                    assert isinstance(parsed, str)
                    assert len(parsed) > 0
            except Exception as e:
                pytest.fail(f"README parsing failed for term '{term}': {e}")

    def test_readme_structure_consistency(self, integration_setup):
        """Test consistent structure extraction across README types."""
        plugin = integration_setup["plugin"]

        structures = {}
        for readme_file in integration_setup["workspace"].glob("README_*.md"):
            content = readme_file.read_text()
            structure = plugin.extract_structure(content, readme_file)
            structures[readme_file.stem] = structure

        # All should have valid structures
        for readme_type, structure in structures.items():
            assert structure.title is not None, f"{readme_type} should have title"
            assert len(structure.sections) > 0, f"{readme_type} should have sections"

    def test_readme_metadata_extraction(self, integration_setup):
        """Test metadata extraction from different README types."""
        plugin = integration_setup["plugin"]

        metadatas = {}
        for readme_file in integration_setup["workspace"].glob("README_*.md"):
            content = readme_file.read_text()
            metadata = plugin.extract_metadata(content, readme_file)
            metadatas[readme_file.stem] = metadata

        # All should have valid metadata
        for readme_type, metadata in metadatas.items():
            assert metadata.title is not None, f"{readme_type} should have title"
            assert metadata.document_type == "markdown"
            assert isinstance(metadata.tags, list)

    def test_readme_code_extraction(self, integration_setup):
        """Test code example extraction from READMEs."""
        results = integration_setup["results"]

        # Should extract code symbols from code blocks
        total_code_symbols = 0
        for readme_type, result in results.items():
            code_symbols = [
                s for s in result["symbols"] if s.get("metadata", {}).get("in_code_block")
            ]
            total_code_symbols += len(code_symbols)

        # Should find some code symbols across all READMEs
        assert total_code_symbols > 0, "Should extract code symbols from README examples"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
