#!/usr/bin/env python3
"""
Performance Baseline Generator

This script generates comprehensive performance baselines for the MCP Server
by running the full benchmark suite and validating against SLO requirements.

Usage:
    python -m mcp_server.benchmarks.run_baseline [options]

    Options:
        --output-dir DIR    Output directory for reports (default: ./benchmark_results)
        --file-count NUM    Number of test files to generate (default: 1000)
        --iterations NUM    Number of benchmark iterations (default: 100)
        --validate-slo      Validate against SLO requirements (default: True)
        --save-baseline     Save results as new baseline (default: True)
        --compare-previous  Compare with previous baseline (default: True)
        --verbose          Enable verbose logging
        --format FORMAT    Report format: text|json|html|all (default: all)
"""

import argparse
import asyncio
import logging
import sys
import tempfile
from pathlib import Path
from typing import List

# Import MCP Server components
from ..plugin_base import IPlugin
from .benchmark_runner import BenchmarkRunner
from .benchmark_suite import BenchmarkResult


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=level, format=format_str)


def load_available_plugins() -> List[IPlugin]:
    """Load all available plugins for benchmarking."""
    plugins = []

    try:
        from ..plugins.python_plugin import PythonPlugin

        plugins.append(PythonPlugin())
        logging.info("Loaded Python plugin")
    except ImportError as e:
        logging.warning(f"Could not load Python plugin: {e}")

    try:
        from ..plugins.js_plugin import JSPlugin

        plugins.append(JSPlugin())
        logging.info("Loaded JavaScript plugin")
    except ImportError as e:
        logging.warning(f"Could not load JavaScript plugin: {e}")

    try:
        from ..plugins.c_plugin import CPlugin

        plugins.append(CPlugin())
        logging.info("Loaded C plugin")
    except ImportError as e:
        logging.warning(f"Could not load C plugin: {e}")

    # Try to load additional plugins if available
    try:
        from ..plugins.cpp_plugin import CppPlugin

        plugins.append(CppPlugin())
        logging.info("Loaded C++ plugin")
    except ImportError:
        logging.debug("C++ plugin not available")

    try:
        from ..plugins.html_css_plugin import HtmlCssPlugin

        plugins.append(HtmlCssPlugin())
        logging.info("Loaded HTML/CSS plugin")
    except ImportError:
        logging.debug("HTML/CSS plugin not available")

    try:
        from ..plugins.dart_plugin import DartPlugin

        plugins.append(DartPlugin())
        logging.info("Loaded Dart plugin")
    except ImportError:
        logging.debug("Dart plugin not available")

    if not plugins:
        logging.error("No plugins available for benchmarking!")
        sys.exit(1)

    logging.info(f"Loaded {len(plugins)} plugins for benchmarking")
    return plugins


def generate_comprehensive_test_data(base_path: Path, file_count: int) -> List[Path]:
    """Generate comprehensive test data for benchmarking."""
    files_created = []

    # Calculate distribution of file types
    python_count = int(file_count * 0.4)  # 40% Python
    js_count = int(file_count * 0.3)  # 30% JavaScript
    c_count = int(file_count * 0.2)  # 20% C
    other_count = file_count - python_count - js_count - c_count  # 10% other

    logging.info(
        f"Generating test data: {python_count} Python, {js_count} JS, {c_count} C, {other_count} other files"
    )

    # Generate Python files
    python_dir = base_path / "python"
    python_dir.mkdir(parents=True)
    for i in range(python_count):
        file_path = python_dir / f"module_{i}.py"
        content = f'''
"""Module {i} for performance testing."""

import logging
import json
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class DataModel{i}:
    """Data model for module {i}."""
    id: int
    name: str
    value: float
    metadata: Dict[str, Any]
    created_at: datetime
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {{
            "id": self.id,
            "name": self.name,
            "value": self.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }}

class DataProcessor{i}:
    """Data processor for module {i}."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cache = {{}}
        self.stats = {{
            "processed": 0,
            "errors": 0,
            "cache_hits": 0
        }}
    
    def process_data(self, data: List[Dict[str, Any]]) -> List[DataModel{i}]:
        """Process raw data into models."""
        results = []
        for item in data:
            try:
                model = self._process_item(item)
                if model:
                    results.append(model)
                    self.stats["processed"] += 1
            except Exception as e:
                logger.error(f"Processing error: {{e}}")
                self.stats["errors"] += 1
        return results
    
    def _process_item(self, item: Dict[str, Any]) -> Optional[DataModel{i}]:
        """Process a single item."""
        cache_key = f"{{item.get('id', '')}}_{i}"
        if cache_key in self.cache:
            self.stats["cache_hits"] += 1
            return self.cache[cache_key]
        
        try:
            model = DataModel{i}(
                id=item.get("id", {i}),
                name=item.get("name", f"item_{i}"),
                value=float(item.get("value", {i} * 1.5)),
                metadata=item.get("metadata", {{}}) if isinstance(item.get("metadata"), dict) else {{}},
                created_at=datetime.now()
            )
            self.cache[cache_key] = model
            return model
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid data format: {{e}}")
            return None
    
    def get_statistics(self) -> Dict[str, int]:
        """Get processing statistics."""
        return self.stats.copy()
    
    def clear_cache(self) -> None:
        """Clear the internal cache."""
        self.cache.clear()
        logger.info(f"Cache cleared for processor {i}")

def utility_function_{i}(x: float, y: float, operation: str = "add") -> float:
    """Utility function {i} for mathematical operations."""
    operations = {{
        "add": lambda a, b: a + b + {i},
        "multiply": lambda a, b: a * b * {i},
        "divide": lambda a, b: (a / b) + {i} if b != 0 else {i},
        "power": lambda a, b: (a ** b) % ({i} + 100)
    }}
    
    return operations.get(operation, operations["add"])(x, y)

def async_operation_{i}(data: List[Any]) -> List[Any]:
    """Async operation {i} for data processing."""
    import asyncio
    
    async def process_async(item):
        # Simulate async processing
        await asyncio.sleep(0.001)
        return {{
            "original": item,
            "processed": f"processed_{{item}}_{i}",
            "timestamp": datetime.now().isoformat()
        }}
    
    async def main():
        tasks = [process_async(item) for item in data[:10]]  # Limit for performance
        return await asyncio.gather(*tasks)
    
    try:
        return asyncio.run(main())
    except RuntimeError:
        # Event loop already running
        return [{{
            "original": item,
            "processed": f"sync_processed_{{item}}_{i}",
            "timestamp": datetime.now().isoformat()
        }} for item in data[:10]]

# Constants and configuration
CONFIG_{i} = {{
    "name": "Module{i}",
    "version": "1.0.{i % 100}",
    "description": "Test module {i} for performance benchmarking",
    "max_cache_size": {i * 100},
    "processing_timeout": {i % 10 + 5},
    "enabled_features": ["caching", "logging", "async_processing"]
}}

if __name__ == "__main__":
    processor = DataProcessor{i}(CONFIG_{i})
    test_data = [
        {{"id": j, "name": f"test_{{j}}", "value": j * 1.5, "metadata": {{"test": True}}}}
        for j in range(10)
    ]
    results = processor.process_data(test_data)
    print(f"Processed {{len(results)}} items with processor {i}")
'''
        file_path.write_text(content)
        files_created.append(file_path)

    # Generate JavaScript files
    js_dir = base_path / "javascript"
    js_dir.mkdir(parents=True)
    for i in range(js_count):
        file_path = js_dir / f"component_{i}.js"
        content = f"""
/**
 * Component {i} for frontend performance testing.
 * @module Component{i}
 */

import {{ EventEmitter }} from 'events';
import {{ performance }} from 'perf_hooks';

/**
 * Data model for component {i}
 */
class DataModel{i} {{
    constructor(id, name, value, metadata = {{}}) {{
        this.id = id;
        this.name = name;
        this.value = value;
        this.metadata = metadata;
        this.createdAt = new Date();
        this.updatedAt = new Date();
    }}
    
    /**
     * Serialize the model to JSON
     * @returns {{Object}} Serialized data
     */
    toJSON() {{
        return {{
            id: this.id,
            name: this.name,
            value: this.value,
            metadata: this.metadata,
            createdAt: this.createdAt.toISOString(),
            updatedAt: this.updatedAt.toISOString()
        }};
    }}
    
    /**
     * Update the model with new data
     * @param {{Object}} updates - Updates to apply
     */
    update(updates) {{
        Object.assign(this, updates);
        this.updatedAt = new Date();
    }}
}}

/**
 * Component {i} for data processing
 */
class Component{i} extends EventEmitter {{
    constructor(options = {{}}) {{
        super();
        this.options = {{
            maxCacheSize: {i * 50},
            processingTimeout: {i % 10 + 5}000,
            enableLogging: true,
            enableMetrics: true,
            ...options
        }};
        
        this.cache = new Map();
        this.stats = {{
            processed: 0,
            errors: 0,
            cacheHits: 0,
            avgProcessingTime: 0
        }};
        
        this.state = {{
            isProcessing: false,
            lastProcessedAt: null,
            activeJobs: 0
        }};
        
        this.setupEventHandlers();
    }}
    
    /**
     * Setup event handlers
     * @private
     */
    setupEventHandlers() {{
        this.on('dataProcessed', (data) => {{
            this.stats.processed++;
            this.state.lastProcessedAt = new Date();
            
            if (this.options.enableLogging) {{
                console.log(`Component{i}: Processed data item ${{data.id}}`);
            }}
        }});
        
        this.on('error', (error) => {{
            this.stats.errors++;
            console.error(`Component{i} error:`, error);
        }});
    }}
    
    /**
     * Process a batch of data
     * @param {{Array}} data - Data to process
     * @returns {{Promise<Array>}} Processed results
     */
    async processData(data) {{
        const startTime = performance.now();
        this.state.isProcessing = true;
        this.state.activeJobs++;
        
        try {{
            const results = [];
            
            for (const item of data) {{
                try {{
                    const processed = await this.processItem(item);
                    if (processed) {{
                        results.push(processed);
                        this.emit('dataProcessed', processed);
                    }}
                }} catch (error) {{
                    this.emit('error', error);
                }}
            }}
            
            const endTime = performance.now();
            const processingTime = endTime - startTime;
            this.updateMetrics(processingTime);
            
            return results;
        }} finally {{
            this.state.isProcessing = false;
            this.state.activeJobs--;
        }}
    }}
    
    /**
     * Process a single data item
     * @param {{Object}} item - Data item to process
     * @returns {{Promise<DataModel{i}>}} Processed model
     */
    async processItem(item) {{
        const cacheKey = `${{item.id || 'unknown'}}_{i}`;
        
        if (this.cache.has(cacheKey)) {{
            this.stats.cacheHits++;
            return this.cache.get(cacheKey);
        }}
        
        // Simulate async processing
        await new Promise(resolve => setTimeout(resolve, 1));
        
        const model = new DataModel{i}(
            item.id || {i},
            item.name || `item_{i}`,
            parseFloat(item.value) || {i} * 1.5,
            item.metadata || {{}}
        );
        
        // Enhanced processing
        model.processed = true;
        model.componentId = {i};
        model.processingTimestamp = Date.now();
        model.hash = this.generateHash(model);
        
        // Cache management
        if (this.cache.size >= this.options.maxCacheSize) {{
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }}
        
        this.cache.set(cacheKey, model);
        return model;
    }}
    
    /**
     * Generate a simple hash for the model
     * @param {{Object}} model - Model to hash
     * @returns {{string}} Hash string
     */
    generateHash(model) {{
        const str = JSON.stringify({{
            id: model.id,
            name: model.name,
            value: model.value
        }});
        
        let hash = 0;
        for (let i = 0; i < str.length; i++) {{
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }}
        
        return hash.toString(16);
    }}
    
    /**
     * Update performance metrics
     * @param {{number}} processingTime - Time taken for processing
     * @private
     */
    updateMetrics(processingTime) {{
        const totalProcessed = this.stats.processed + 1;
        this.stats.avgProcessingTime = (
            (this.stats.avgProcessingTime * (totalProcessed - 1)) + processingTime
        ) / totalProcessed;
    }}
    
    /**
     * Get component statistics
     * @returns {{Object}} Statistics object
     */
    getStats() {{
        return {{
            ...this.stats,
            cacheSize: this.cache.size,
            state: {{ ...this.state }}
        }};
    }}
    
    /**
     * Clear cache and reset stats
     */
    reset() {{
        this.cache.clear();
        this.stats = {{
            processed: 0,
            errors: 0,
            cacheHits: 0,
            avgProcessingTime: 0
        }};
        this.emit('reset');
    }}
}}

/**
 * Utility function {i}
 * @param {{Array}} arr - Array to process
 * @param {{Function}} fn - Processing function
 * @returns {{Array}} Processed array
 */
function utilityFunction{i}(arr, fn) {{
    return arr
        .filter(item => item != null)
        .map((item, index) => {{
            try {{
                return fn(item, index, {i});
            }} catch (error) {{
                console.warn(`Error processing item at index ${{index}}:`, error);
                return null;
            }}
        }})
        .filter(result => result != null);
}}

/**
 * Async utility function {i}
 * @param {{Array}} data - Data to process asynchronously
 * @returns {{Promise<Array>}} Processed results
 */
async function asyncUtility{i}(data) {{
    const results = await Promise.allSettled(
        data.map(async (item, index) => {{
            await new Promise(resolve => setTimeout(resolve, 1));
            return {{
                original: item,
                processed: `async_processed_${{item}}_{i}`,
                index,
                timestamp: Date.now()
            }};
        }})
    );
    
    return results
        .filter(result => result.status === 'fulfilled')
        .map(result => result.value);
}}

// Configuration and exports
const CONFIG_{i} = {{
    name: 'Component{i}',
    version: '1.0.{i % 100}',
    description: 'Test component {i} for performance benchmarking',
    features: ['caching', 'async_processing', 'event_handling', 'metrics'],
    performance: {{
        maxCacheSize: {i * 50},
        processingTimeout: {i % 10 + 5}000,
        batchSize: {i % 20 + 10}
    }}
}};

export {{
    Component{i},
    DataModel{i},
    utilityFunction{i},
    asyncUtility{i},
    CONFIG_{i}
}};

// For CommonJS compatibility
if (typeof module !== 'undefined' && module.exports) {{
    module.exports = {{
        Component{i},
        DataModel{i},
        utilityFunction{i},
        asyncUtility{i},
        CONFIG_{i}
    }};
}}
"""
        file_path.write_text(content)
        files_created.append(file_path)

    # Generate C files
    c_dir = base_path / "c"
    c_dir.mkdir(parents=True)
    for i in range(c_count):
        file_path = c_dir / f"module_{i}.c"
        content = f"""
/**
 * Module {i} for C performance testing
 * Contains various data structures and functions for benchmarking
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <stdint.h>

#define MAX_CACHE_SIZE {i * 50 + 100}
#define BUFFER_SIZE {i * 10 + 512}
#define MODULE_ID {i}

// Data structures
typedef struct {{
    int id;
    char name[64];
    double value;
    time_t created_at;
    int is_valid;
}} data_model_{i}_t;

typedef struct {{
    data_model_{i}_t* items;
    size_t size;
    size_t capacity;
    size_t processed_count;
    size_t error_count;
}} data_collection_{i}_t;

typedef struct cache_entry_{i} {{
    char key[32];
    data_model_{i}_t data;
    struct cache_entry_{i}* next;
    time_t access_time;
}} cache_entry_{i}_t;

typedef struct {{
    cache_entry_{i}_t* buckets[MAX_CACHE_SIZE];
    size_t size;
    size_t hit_count;
    size_t miss_count;
}} cache_{i}_t;

// Global variables
static cache_{i}_t g_cache_{i} = {{0}};
static uint64_t g_processing_stats_{i}[10] = {{0}};

/**
 * Initialize data model {i}
 * @param model Pointer to the model to initialize
 * @param id Model ID
 * @param name Model name
 * @param value Model value
 * @return 0 on success, -1 on error
 */
int init_data_model_{i}(data_model_{i}_t* model, int id, const char* name, double value) {{
    if (!model || !name) {{
        return -1;
    }}
    
    model->id = id;
    strncpy(model->name, name, sizeof(model->name) - 1);
    model->name[sizeof(model->name) - 1] = '\\0';
    model->value = value * {i} + 0.5;
    model->created_at = time(NULL);
    model->is_valid = 1;
    
    return 0;
}}

/**
 * Process data item {i}
 * @param input Input data
 * @param output Output data
 * @return Processing result code
 */
int process_data_item_{i}(const data_model_{i}_t* input, data_model_{i}_t* output) {{
    if (!input || !output || !input->is_valid) {{
        return -1;
    }}
    
    // Copy input to output
    *output = *input;
    
    // Apply transformations
    output->value = input->value * 1.{i % 10};
    output->id = input->id + MODULE_ID;
    
    // Update name with processing marker
    char processed_name[64];
    snprintf(processed_name, sizeof(processed_name), "processed_%s_{i}", input->name);
    strncpy(output->name, processed_name, sizeof(output->name) - 1);
    output->name[sizeof(output->name) - 1] = '\\0';
    
    g_processing_stats_{i}[0]++; // Increment processed count
    return 0;
}}

/**
 * Hash function for cache {i}
 * @param key Key to hash
 * @return Hash value
 */
static size_t hash_key_{i}(const char* key) {{
    size_t hash = 5381;
    int c;
    
    while ((c = *key++)) {{
        hash = ((hash << 5) + hash) + c + MODULE_ID;
    }}
    
    return hash % MAX_CACHE_SIZE;
}}

/**
 * Get data from cache {i}
 * @param key Cache key
 * @param result Output result
 * @return 1 if found, 0 if not found
 */
int cache_get_{i}(const char* key, data_model_{i}_t* result) {{
    if (!key || !result) {{
        return 0;
    }}
    
    size_t index = hash_key_{i}(key);
    cache_entry_{i}_t* entry = g_cache_{i}.buckets[index];
    
    while (entry) {{
        if (strcmp(entry->key, key) == 0) {{
            *result = entry->data;
            entry->access_time = time(NULL);
            g_cache_{i}.hit_count++;
            return 1;
        }}
        entry = entry->next;
    }}
    
    g_cache_{i}.miss_count++;
    return 0;
}}

/**
 * Put data into cache {i}
 * @param key Cache key
 * @param data Data to cache
 * @return 0 on success, -1 on error
 */
int cache_put_{i}(const char* key, const data_model_{i}_t* data) {{
    if (!key || !data) {{
        return -1;
    }}
    
    size_t index = hash_key_{i}(key);
    
    // Check if key already exists
    cache_entry_{i}_t* entry = g_cache_{i}.buckets[index];
    while (entry) {{
        if (strcmp(entry->key, key) == 0) {{
            entry->data = *data;
            entry->access_time = time(NULL);
            return 0;
        }}
        entry = entry->next;
    }}
    
    // Create new entry
    cache_entry_{i}_t* new_entry = malloc(sizeof(cache_entry_{i}_t));
    if (!new_entry) {{
        return -1;
    }}
    
    strncpy(new_entry->key, key, sizeof(new_entry->key) - 1);
    new_entry->key[sizeof(new_entry->key) - 1] = '\\0';
    new_entry->data = *data;
    new_entry->access_time = time(NULL);
    new_entry->next = g_cache_{i}.buckets[index];
    
    g_cache_{i}.buckets[index] = new_entry;
    g_cache_{i}.size++;
    
    return 0;
}}

/**
 * Process data collection {i}
 * @param collection Data collection to process
 * @return Number of items processed
 */
size_t process_collection_{i}(data_collection_{i}_t* collection) {{
    if (!collection || !collection->items) {{
        return 0;
    }}
    
    size_t processed = 0;
    
    for (size_t i = 0; i < collection->size; i++) {{
        data_model_{i}_t* item = &collection->items[i];
        
        if (!item->is_valid) {{
            collection->error_count++;
            continue;
        }}
        
        // Generate cache key
        char cache_key[32];
        snprintf(cache_key, sizeof(cache_key), "item_%d_{i}", item->id);
        
        // Check cache first
        data_model_{i}_t cached_result;
        if (cache_get_{i}(cache_key, &cached_result)) {{
            *item = cached_result;
        }} else {{
            // Process item
            data_model_{i}_t result;
            if (process_data_item_{i}(item, &result) == 0) {{
                *item = result;
                cache_put_{i}(cache_key, &result);
            }} else {{
                collection->error_count++;
                continue;
            }}
        }}
        
        processed++;
        collection->processed_count++;
    }}
    
    return processed;
}}

/**
 * Utility function {i}
 * @param a First operand
 * @param b Second operand
 * @param operation Operation type
 * @return Result of operation
 */
double utility_function_{i}(double a, double b, int operation) {{
    switch (operation) {{
        case 0: return a + b + MODULE_ID;
        case 1: return a * b + MODULE_ID;
        case 2: return (b != 0) ? (a / b) + MODULE_ID : MODULE_ID;
        case 3: return a - b + MODULE_ID;
        default: return MODULE_ID;
    }}
}}

/**
 * Get statistics for module {i}
 * @param stats Output statistics array
 * @param size Size of statistics array
 * @return Number of statistics copied
 */
size_t get_statistics_{i}(uint64_t* stats, size_t size) {{
    if (!stats) {{
        return 0;
    }}
    
    size_t count = (size < 10) ? size : 10;
    memcpy(stats, g_processing_stats_{i}, count * sizeof(uint64_t));
    
    return count;
}}

/**
 * Clear cache {i}
 */
void clear_cache_{i}(void) {{
    for (size_t i = 0; i < MAX_CACHE_SIZE; i++) {{
        cache_entry_{i}_t* entry = g_cache_{i}.buckets[i];
        while (entry) {{
            cache_entry_{i}_t* next = entry->next;
            free(entry);
            entry = next;
        }}
        g_cache_{i}.buckets[i] = NULL;
    }}
    
    g_cache_{i}.size = 0;
    g_cache_{i}.hit_count = 0;
    g_cache_{i}.miss_count = 0;
}}

/**
 * Initialize module {i}
 * @return 0 on success, -1 on error
 */
int init_module_{i}(void) {{
    // Clear any existing state
    clear_cache_{i}();
    memset(g_processing_stats_{i}, 0, sizeof(g_processing_stats_{i}));
    
    printf("Module {i} initialized successfully\\n");
    return 0;
}}

/**
 * Cleanup module {i}
 */
void cleanup_module_{i}(void) {{
    clear_cache_{i}();
    printf("Module {i} cleaned up\\n");
}}

// Module constants
const int MODULE_VERSION_{i} = {i % 100 + 1};
const char MODULE_NAME_{i}[] = "Module{i}";
const double MODULE_CONSTANT_{i} = {i} * 3.14159;
"""
        file_path.write_text(content)
        files_created.append(file_path)

    # Generate other file types if needed
    if other_count > 0:
        other_dir = base_path / "other"
        other_dir.mkdir(parents=True)
        for i in range(other_count):
            # Mix of different file types
            if i % 3 == 0:
                # C++ file
                file_path = other_dir / f"class_{i}.cpp"
                content = f"""
#include <iostream>
#include <vector>
#include <memory>
#include <algorithm>
#include <chrono>

namespace Module{i} {{

class DataProcessor{{i}} {{
private:
    std::vector<int> data_;
    size_t processed_count_;

public:
    DataProcessor{i}() : processed_count_(0) {{}}
    
    void processData(const std::vector<int>& input) {{
        data_.reserve(input.size());
        std::transform(input.begin(), input.end(), std::back_inserter(data_),
                      [](int x) {{ return x * {i} + 1; }});
        processed_count_ += input.size();
    }}
    
    size_t getProcessedCount() const {{ return processed_count_; }}
}};

}}
"""
            elif i % 3 == 1:
                # HTML file
                file_path = other_dir / f"page_{i}.html"
                content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Page {i}</title>
</head>
<body>
    <div id="container-{i}">
        <h1>Test Component {i}</h1>
        <div class="content" data-id="{i}">
            <p>This is test content for page {i}</p>
        </div>
    </div>
</body>
</html>
"""
            else:
                # CSS file
                file_path = other_dir / f"styles_{i}.css"
                content = f"""
.component-{i} {{
    display: flex;
    flex-direction: column;
    padding: {i}px;
    margin: {i % 20}px;
    background-color: rgb({i % 255}, {(i * 2) % 255}, {(i * 3) % 255});
}}

.component-{i} .header {{
    font-size: {i % 10 + 12}px;
    font-weight: bold;
    color: #{i % 16:x}{i % 16:x}{i % 16:x};
}}

#element-{i} {{
    position: relative;
    width: {i * 2}px;
    height: {i}px;
    border: {i % 5 + 1}px solid #ccc;
}}
"""

            file_path.write_text(content)
            files_created.append(file_path)

    logging.info(f"Generated {len(files_created)} test files")
    return files_created


async def run_comprehensive_benchmarks(
    plugins: List[IPlugin],
    output_dir: Path,
    file_count: int = 1000,
    iterations: int = 100,
    validate_slo: bool = True,
) -> BenchmarkResult:
    """Run comprehensive performance benchmarks."""

    logging.info("Starting comprehensive benchmark suite...")

    # Initialize benchmark runner
    runner = BenchmarkRunner(output_dir)

    # Generate test data
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir)
        test_files = generate_comprehensive_test_data(test_path, file_count)
        file_paths = [str(f) for f in test_files]

        logging.info(f"Running indexing benchmark on {len(file_paths)} files...")
        _ = await runner.run_indexing_benchmark(file_paths)

        logging.info("Running search benchmark...")
        search_queries = [
            "DataProcessor",
            "Component",
            "process",
            "function",
            "class",
            "async",
            "init",
            "cache",
            "stats",
            "utility",
            "model",
            "data",
            "config",
            "module",
            "test",
            "performance",
            "benchmark",
        ]
        _ = await runner.run_search_benchmark(search_queries)

        logging.info("Running memory benchmark...")
        _ = await runner.run_memory_benchmark(min(file_count, 5000))

    # Run full benchmark suite
    logging.info("Running full benchmark suite...")
    full_result = runner.run_benchmarks(plugins, save_results=True, compare_with_previous=True)

    # Generate comprehensive report
    logging.info("Generating comprehensive report...")
    report_result = await runner.generate_benchmark_report()

    if report_result.success:
        logging.info("Benchmark report generated successfully")
        print("\n" + "=" * 80)
        print("PERFORMANCE BENCHMARK REPORT")
        print("=" * 80)
        print(report_result.value)
        print("=" * 80)
    else:
        logging.error(f"Failed to generate report: {report_result.error}")

    # Validate SLOs if requested
    if validate_slo and hasattr(full_result, "validations"):
        logging.info("Validating SLO compliance...")

        passed = sum(1 for v in full_result.validations.values() if v)
        total = len(full_result.validations)

        print("\nSLO VALIDATION RESULTS:")
        print(f"Overall: {passed}/{total} SLOs passed")

        for slo_name, status in full_result.validations.items():
            status_str = "PASS" if status else "FAIL"
            print(f"  {slo_name:<35} [{status_str}]")

        if passed < total:
            logging.warning(f"SLO validation failed: {passed}/{total} SLOs passed")
            return full_result
        else:
            logging.info("All SLOs passed!")

    return full_result


def main():
    """Main entry point for the baseline generator."""
    parser = argparse.ArgumentParser(
        description="Generate MCP Server performance baselines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./benchmark_results"),
        help="Output directory for reports (default: ./benchmark_results)",
    )
    parser.add_argument(
        "--file-count",
        type=int,
        default=1000,
        help="Number of test files to generate (default: 1000)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        help="Number of benchmark iterations (default: 100)",
    )
    parser.add_argument(
        "--validate-slo",
        action="store_true",
        default=True,
        help="Validate against SLO requirements (default: True)",
    )
    parser.add_argument(
        "--no-validate-slo",
        action="store_false",
        dest="validate_slo",
        help="Disable SLO validation",
    )
    parser.add_argument(
        "--save-baseline",
        action="store_true",
        default=True,
        help="Save results as new baseline (default: True)",
    )
    parser.add_argument(
        "--compare-previous",
        action="store_true",
        default=True,
        help="Compare with previous baseline (default: True)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--format",
        choices=["text", "json", "html", "all"],
        default="all",
        help="Report format (default: all)",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    try:
        # Load plugins
        plugins = load_available_plugins()

        # Create output directory
        args.output_dir.mkdir(parents=True, exist_ok=True)

        # Run benchmarks
        result = asyncio.run(
            run_comprehensive_benchmarks(
                plugins=plugins,
                output_dir=args.output_dir,
                file_count=args.file_count,
                iterations=args.iterations,
                validate_slo=args.validate_slo,
            )
        )

        # Report final status
        if hasattr(result, "validations"):
            passed = sum(1 for v in result.validations.values() if v)
            total = len(result.validations)

            if passed == total:
                logging.info("✅ All performance requirements met!")
                sys.exit(0)
            else:
                logging.error(f"❌ Performance requirements not met: {passed}/{total} SLOs passed")
                sys.exit(1)
        else:
            logging.info("✅ Benchmarks completed successfully")
            sys.exit(0)

    except KeyboardInterrupt:
        logging.info("Benchmark interrupted by user")
        sys.exit(130)
    except Exception as e:
        logging.error(f"Benchmark failed: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
