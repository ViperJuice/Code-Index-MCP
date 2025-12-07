"""Test data generator for indexing system comparisons.

Generates synthetic codebases and test queries for benchmarking different
indexing approaches.
"""

import json
import os
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class TestQuery:
    """Represents a test query with expected results."""

    query: str
    query_type: str  # 'symbol', 'semantic', 'pattern'
    expected_files: List[str]
    expected_symbols: Optional[List[str]] = None
    description: Optional[str] = None


@dataclass
class CodebaseSpec:
    """Specification for a generated codebase."""

    name: str
    size: str  # 'small', 'medium', 'large'
    file_count: int
    languages: List[str]
    seed: int


class TestDataGenerator:
    """Generates synthetic codebases and test queries."""

    # Code templates for different languages
    PYTHON_TEMPLATES = [
        '''"""Module for {purpose}."""

import {import1}
import {import2}
from typing import List, Dict, Optional


class {ClassName}:
    """Handles {purpose} operations."""
    
    def __init__(self, config: Dict[str, any]):
        self.config = config
        self._cache = {{}}
    
    def {method1}(self, data: List[str]) -> Optional[str]:
        """Process {purpose} data."""
        result = []
        for item in data:
            if self._validate_{purpose}(item):
                result.append(self._transform_{purpose}(item))
        return result[0] if result else None
    
    def _validate_{purpose}(self, item: str) -> bool:
        """Validate {purpose} item."""
        return len(item) > 0 and item.startswith("{prefix}")
    
    def _transform_{purpose}(self, item: str) -> str:
        """Transform {purpose} item."""
        return item.upper().replace("{old}", "{new}")


def {function1}(input_data: List[Dict]) -> Dict[str, any]:
    """Main {purpose} processing function."""
    processor = {ClassName}({{"mode": "fast"}})
    results = {{}}
    
    for item in input_data:
        key = item.get("id", "unknown")
        value = processor.{method1}(item.get("values", []))
        if value:
            results[key] = value
    
    return results
''',
        '''"""Service for {purpose} management."""

from dataclasses import dataclass
from enum import Enum
import logging


class {EnumName}(Enum):
    """States for {purpose}."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class {DataClassName}:
    """Data model for {purpose}."""
    id: str
    name: str
    status: {EnumName}
    metadata: dict


class {ServiceName}Service:
    """Service for managing {purpose}."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.items = {{}}
    
    async def create_{purpose}(self, name: str) -> {DataClassName}:
        """Create new {purpose} item."""
        item = {DataClassName}(
            id=f"{purpose}_{{len(self.items)}}",
            name=name,
            status={EnumName}.PENDING,
            metadata={{}}
        )
        self.items[item.id] = item
        self.logger.info(f"Created {purpose}: {{item.id}}")
        return item
    
    async def update_{purpose}_status(self, id: str, status: {EnumName}) -> bool:
        """Update {purpose} status."""
        if id in self.items:
            self.items[id].status = status
            return True
        return False
''',
    ]

    JAVASCRIPT_TEMPLATES = [
        """// {purpose} module implementation

const {{ {import1}, {import2} }} = require('./utils');

class {ClassName} {{
    constructor(options = {{}}) {{
        this.options = options;
        this.cache = new Map();
        this.initialized = false;
    }}
    
    async initialize() {{
        // Initialize {purpose} resources
        this.initialized = true;
        console.log('{ClassName} initialized');
    }}
    
    async {method1}(data) {{
        if (!this.initialized) {{
            await this.initialize();
        }}
        
        const results = [];
        for (const item of data) {{
            const processed = await this.process{Purpose}Item(item);
            if (processed) {{
                results.push(processed);
            }}
        }}
        
        return results;
    }}
    
    async process{Purpose}Item(item) {{
        // Process individual {purpose} item
        const key = `${{item.type}}_${{item.id}}`;
        
        if (this.cache.has(key)) {{
            return this.cache.get(key);
        }}
        
        const result = {{
            ...item,
            processed: true,
            timestamp: Date.now()
        }};
        
        this.cache.set(key, result);
        return result;
    }}
}}

module.exports = {{ {ClassName} }};
""",
        """// {purpose} controller with Express

const express = require('express');
const {{ {ServiceName} }} = require('../services/{purpose}Service');

class {ControllerName}Controller {{
    constructor() {{
        this.router = express.Router();
        this.service = new {ServiceName}();
        this.setupRoutes();
    }}
    
    setupRoutes() {{
        this.router.get('/{purpose}', this.getAll{Purpose}.bind(this));
        this.router.get('/{purpose}/:id', this.get{Purpose}ById.bind(this));
        this.router.post('/{purpose}', this.create{Purpose}.bind(this));
        this.router.put('/{purpose}/:id', this.update{Purpose}.bind(this));
        this.router.delete('/{purpose}/:id', this.delete{Purpose}.bind(this));
    }}
    
    async getAll{Purpose}(req, res) {{
        try {{
            const items = await this.service.findAll();
            res.json({{ success: true, data: items }});
        }} catch (error) {{
            res.status(500).json({{ success: false, error: error.message }});
        }}
    }}
    
    async get{Purpose}ById(req, res) {{
        try {{
            const item = await this.service.findById(req.params.id);
            if (!item) {{
                return res.status(404).json({{ success: false, error: 'Not found' }});
            }}
            res.json({{ success: true, data: item }});
        }} catch (error) {{
            res.status(500).json({{ success: false, error: error.message }});
        }}
    }}
    
    async create{Purpose}(req, res) {{
        try {{
            const item = await this.service.create(req.body);
            res.status(201).json({{ success: true, data: item }});
        }} catch (error) {{
            res.status(400).json({{ success: false, error: error.message }});
        }}
    }}
    
    async update{Purpose}(req, res) {{
        try {{
            const item = await this.service.update(req.params.id, req.body);
            res.json({{ success: true, data: item }});
        }} catch (error) {{
            res.status(400).json({{ success: false, error: error.message }});
        }}
    }}
    
    async delete{Purpose}(req, res) {{
        try {{
            await this.service.delete(req.params.id);
            res.json({{ success: true }});
        }} catch (error) {{
            res.status(400).json({{ success: false, error: error.message }});
        }}
    }}
}}

module.exports = {ControllerName}Controller;
""",
    ]

    JAVA_TEMPLATES = [
        """package com.example.{package};

import java.util.*;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * {Purpose} manager implementation.
 */
public class {ClassName} {{
    private static final Logger logger = LoggerFactory.getLogger({ClassName}.class);
    
    private final Map<String, {DataType}> cache;
    private final {ConfigType} config;
    
    public {ClassName}({ConfigType} config) {{
        this.config = config;
        this.cache = new HashMap<>();
    }}
    
    /**
     * Process {purpose} data.
     * @param items List of items to process
     * @return Processed results
     */
    public List<{ResultType}> {method1}(List<{DataType}> items) {{
        logger.info("Processing {{}} {purpose} items", items.size());
        
        return items.stream()
            .filter(this::isValid{Purpose})
            .map(this::transform{Purpose})
            .collect(Collectors.toList());
    }}
    
    private boolean isValid{Purpose}({DataType} item) {{
        return item != null && 
               item.getId() != null && 
               item.getStatus().equals("{status}");
    }}
    
    private {ResultType} transform{Purpose}({DataType} item) {{
        String cacheKey = generateCacheKey(item);
        
        if (cache.containsKey(cacheKey)) {{
            return cache.get(cacheKey);
        }}
        
        {ResultType} result = new {ResultType}();
        result.setId(item.getId());
        result.setProcessedData(processData(item.getData()));
        result.setTimestamp(System.currentTimeMillis());
        
        cache.put(cacheKey, result);
        return result;
    }}
    
    private String generateCacheKey({DataType} item) {{
        return String.format("%s_%s", item.getType(), item.getId());
    }}
    
    private String processData(String data) {{
        // Complex {purpose} processing logic
        return data.toUpperCase().replaceAll("{pattern}", "{replacement}");
    }}
}}
""",
        """package com.example.{package}.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.annotation.Transactional;
import java.util.Optional;
import java.util.List;

/**
 * Service for {purpose} operations.
 */
@Service
@Transactional
public class {ServiceName}Service {{
    
    private final {RepositoryName}Repository repository;
    private final {MapperName}Mapper mapper;
    
    @Autowired
    public {ServiceName}Service({RepositoryName}Repository repository, 
                               {MapperName}Mapper mapper) {{
        this.repository = repository;
        this.mapper = mapper;
    }}
    
    /**
     * Find all {purpose} entities.
     * @return List of {purpose} DTOs
     */
    public List<{DtoName}DTO> findAll{Purpose}() {{
        return repository.findAll().stream()
            .map(mapper::toDTO)
            .collect(Collectors.toList());
    }}
    
    /**
     * Find {purpose} by ID.
     * @param id The entity ID
     * @return Optional {purpose} DTO
     */
    public Optional<{DtoName}DTO> find{Purpose}ById(Long id) {{
        return repository.findById(id)
            .map(mapper::toDTO);
    }}
    
    /**
     * Create new {purpose}.
     * @param dto The {purpose} data
     * @return Created {purpose} DTO
     */
    public {DtoName}DTO create{Purpose}({DtoName}DTO dto) {{
        {EntityName} entity = mapper.toEntity(dto);
        entity = repository.save(entity);
        return mapper.toDTO(entity);
    }}
    
    /**
     * Update existing {purpose}.
     * @param id The entity ID
     * @param dto The updated data
     * @return Updated {purpose} DTO
     */
    public {DtoName}DTO update{Purpose}(Long id, {DtoName}DTO dto) {{
        {EntityName} entity = repository.findById(id)
            .orElseThrow(() -> new EntityNotFoundException("{Purpose} not found"));
        
        mapper.updateEntity(dto, entity);
        entity = repository.save(entity);
        return mapper.toDTO(entity);
    }}
    
    /**
     * Delete {purpose} by ID.
     * @param id The entity ID
     */
    public void delete{Purpose}(Long id) {{
        repository.deleteById(id);
    }}
}}
""",
    ]

    # Common programming concepts for realistic code
    PURPOSES = [
        "authentication",
        "authorization",
        "validation",
        "transformation",
        "serialization",
        "caching",
        "logging",
        "monitoring",
        "notification",
        "scheduling",
        "routing",
        "filtering",
        "sorting",
        "pagination",
        "encryption",
        "compression",
        "parsing",
        "formatting",
        "indexing",
        "queuing",
        "batching",
        "streaming",
        "synchronization",
        "migration",
    ]

    IMPORTS = {
        "python": [
            "os",
            "sys",
            "json",
            "datetime",
            "asyncio",
            "requests",
            "pathlib",
            "collections",
        ],
        "javascript": ["fs", "path", "http", "crypto", "events", "stream", "util", "querystring"],
        "java": ["util", "io", "nio", "net", "security", "concurrent", "annotation", "reflection"],
    }

    def __init__(self, base_path: str = "test_codebases"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)

    def generate_codebase(self, spec: CodebaseSpec) -> str:
        """Generate a synthetic codebase based on specification."""
        random.seed(spec.seed)

        codebase_path = self.base_path / spec.name
        codebase_path.mkdir(exist_ok=True)

        # Calculate files per language
        files_per_language = spec.file_count // len(spec.languages)
        extra_files = spec.file_count % len(spec.languages)

        generated_files = []

        for i, language in enumerate(spec.languages):
            count = files_per_language + (1 if i < extra_files else 0)
            files = self._generate_language_files(codebase_path, language, count)
            generated_files.extend(files)

        # Generate metadata file
        metadata = {
            "spec": asdict(spec),
            "generated_files": generated_files,
            "timestamp": str(Path(codebase_path).stat().st_mtime),
        }

        with open(codebase_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        return str(codebase_path)

    def _generate_language_files(self, base_path: Path, language: str, count: int) -> List[str]:
        """Generate files for a specific language."""
        generated = []

        if language == "python":
            templates = self.PYTHON_TEMPLATES
            extension = ".py"
            subdir = "src"
        elif language == "javascript":
            templates = self.JAVASCRIPT_TEMPLATES
            extension = ".js"
            subdir = "lib"
        elif language == "java":
            templates = self.JAVA_TEMPLATES
            extension = ".java"
            subdir = "src/main/java/com/example"
        else:
            raise ValueError(f"Unsupported language: {language}")

        # Create language-specific directory structure
        lang_path = base_path / subdir
        lang_path.mkdir(parents=True, exist_ok=True)

        for i in range(count):
            purpose = random.choice(self.PURPOSES)
            template = random.choice(templates)

            # Generate file name
            if language == "python":
                filename = f"{purpose}_handler_{i}{extension}"
            elif language == "javascript":
                filename = f"{purpose}Module{i}{extension}"
            else:  # java
                filename = f"{purpose.title()}Manager{i}{extension}"

            # Fill template with random values
            content = self._fill_template(template, language, purpose, i)

            # Write file
            file_path = lang_path / filename
            with open(file_path, "w") as f:
                f.write(content)

            generated.append(str(file_path.relative_to(base_path)))

        return generated

    def _fill_template(self, template: str, language: str, purpose: str, index: int) -> str:
        """Fill template with contextual values."""
        replacements = {
            "{purpose}": purpose,
            "{Purpose}": purpose.title(),
            "{PURPOSE}": purpose.upper(),
            "{ClassName}": f"{purpose.title()}Handler",
            "{ServiceName}": f"{purpose.title()}",
            "{ControllerName}": f"{purpose.title()}",
            "{DataClassName}": f"{purpose.title()}Data",
            "{EnumName}": f"{purpose.title()}Status",
            "{method1}": f"process_{purpose}",
            "{function1}": f"handle_{purpose}_batch",
            "{import1}": random.choice(self.IMPORTS.get(language, ["module"])),
            "{import2}": random.choice(self.IMPORTS.get(language, ["another_module"])),
            "{package}": purpose.lower(),
            "{DataType}": f"{purpose.title()}Data",
            "{ResultType}": f"{purpose.title()}Result",
            "{ConfigType}": f"{purpose.title()}Config",
            "{RepositoryName}": f"{purpose.title()}",
            "{MapperName}": f"{purpose.title()}",
            "{DtoName}": f"{purpose.title()}",
            "{EntityName}": f"{purpose.title()}Entity",
            "{prefix}": purpose[:3].upper(),
            "{old}": "OLD",
            "{new}": "NEW",
            "{status}": "ACTIVE",
            "{pattern}": "[0-9]+",
            "{replacement}": "X",
        }

        result = template
        for key, value in replacements.items():
            result = result.replace(key, value)

        return result

    def generate_test_queries(self, codebase_path: str) -> List[TestQuery]:
        """Generate test queries for a codebase."""
        queries = []

        # Symbol search queries
        queries.extend(
            [
                TestQuery(
                    query="Handler",
                    query_type="symbol",
                    expected_files=["src/*.py"],
                    expected_symbols=["*Handler", "handle_*"],
                    description="Find all handler classes and functions",
                ),
                TestQuery(
                    query="process_",
                    query_type="symbol",
                    expected_files=["src/*.py", "lib/*.js"],
                    expected_symbols=["process_*"],
                    description="Find all processing methods",
                ),
                TestQuery(
                    query="Service",
                    query_type="symbol",
                    expected_files=["src/main/java/**/*.java", "lib/*.js"],
                    expected_symbols=["*Service", "*ServiceImpl"],
                    description="Find all service classes",
                ),
            ]
        )

        # Semantic search queries
        queries.extend(
            [
                TestQuery(
                    query="authentication and validation logic",
                    query_type="semantic",
                    expected_files=["*authentication*", "*validation*"],
                    description="Find code related to authentication and validation",
                ),
                TestQuery(
                    query="error handling and logging",
                    query_type="semantic",
                    expected_files=["*.py", "*.js", "*.java"],
                    description="Find error handling patterns",
                ),
                TestQuery(
                    query="data transformation and processing",
                    query_type="semantic",
                    expected_files=["*transform*", "*process*"],
                    description="Find data transformation code",
                ),
            ]
        )

        # Pattern search queries
        queries.extend(
            [
                TestQuery(
                    query=r"async\s+def\s+\w+",
                    query_type="pattern",
                    expected_files=["src/*.py"],
                    description="Find async Python functions",
                ),
                TestQuery(
                    query=r"@(Service|Component|Repository)",
                    query_type="pattern",
                    expected_files=["src/main/java/**/*.java"],
                    description="Find Spring annotations",
                ),
                TestQuery(
                    query=r"class\s+\w+\s*{",
                    query_type="pattern",
                    expected_files=["*.js", "*.java"],
                    description="Find class definitions",
                ),
            ]
        )

        return queries

    def generate_all_test_data(self) -> Dict[str, any]:
        """Generate complete test dataset."""
        specs = [
            CodebaseSpec("small_mixed", "small", 10, ["python", "javascript"], 42),
            CodebaseSpec("medium_mixed", "medium", 100, ["python", "javascript", "java"], 42),
            CodebaseSpec("large_mixed", "large", 1000, ["python", "javascript", "java"], 42),
            CodebaseSpec("python_only_medium", "medium", 100, ["python"], 42),
            CodebaseSpec("polyglot_small", "small", 15, ["python", "javascript", "java"], 42),
        ]

        test_data = {"codebases": {}, "queries": {}}

        for spec in specs:
            print(f"Generating {spec.name} codebase ({spec.file_count} files)...")
            codebase_path = self.generate_codebase(spec)
            queries = self.generate_test_queries(codebase_path)

            test_data["codebases"][spec.name] = {"path": codebase_path, "spec": asdict(spec)}
            test_data["queries"][spec.name] = [asdict(q) for q in queries]

        # Save test data manifest
        with open(self.base_path / "test_data.json", "w") as f:
            json.dump(test_data, f, indent=2)

        return test_data


def main():
    """Generate test data for comparison benchmarks."""
    generator = TestDataGenerator()
    test_data = generator.generate_all_test_data()

    print("\nGenerated test data:")
    for codebase_name, info in test_data["codebases"].items():
        print(f"  - {codebase_name}: {info['spec']['file_count']} files at {info['path']}")

    print(f"\nTotal queries generated: {sum(len(q) for q in test_data['queries'].values())}")
    print(f"Test data saved to: {generator.base_path}")


if __name__ == "__main__":
    main()
