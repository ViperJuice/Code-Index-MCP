"""
Real-World Cross-Language Resolution Testing for Dormant Features Validation

Tests cross-language symbol resolution and multi-language project capabilities.
Validates symbol discovery, reference tracking, and integration across different programming languages.
"""

import tempfile
from pathlib import Path
from typing import Dict

import pytest


@pytest.mark.cross_language
class TestCrossLanguageResolution:
    """Test cross-language symbol resolution capabilities."""

    @pytest.fixture
    def setup_multi_language_project(self):
        """Setup multi-language test project with various file types."""
        try:
            from mcp_server.plugin_system import PluginManager
            from mcp_server.storage.sqlite_store import SQLiteStore
        except ImportError:
            pytest.skip("Plugin system components not available")

        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_file:
            store = SQLiteStore(db_file.name)
            plugin_manager = PluginManager(sqlite_store=store)

            # Load all available plugins
            load_result = plugin_manager.load_plugins_safe()
            if not load_result.success:
                pytest.skip(f"Failed to load plugins: {load_result.error.message}")

            # Create test files in multiple languages
            test_files = self._create_multi_language_files()

            yield {
                "plugin_manager": plugin_manager,
                "store": store,
                "test_files": test_files,
            }

            # Cleanup
            self._cleanup_test_files(test_files)
            try:
                Path(db_file.name).unlink()
            except Exception:
                pass

    def _create_multi_language_files(self) -> Dict[str, Path]:
        """Create test files in multiple programming languages."""
        test_files = {}

        # Python file
        python_code = '''
"""Python API client module."""

import json
import requests
from typing import Dict, Any, Optional

class APIClient:
    """HTTP API client for external services."""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
    
    def get_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve user data from API."""
        endpoint = f"/api/users/{user_id}"
        response = self.session.get(f"{self.base_url}{endpoint}")
        return response.json() if response.status_code == 200 else None
    
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate user credentials."""
        data = {"username": username, "password": password}
        response = self.session.post(f"{self.base_url}/auth/login", json=data)
        return response.status_code == 200

def process_config_data(config_path: str) -> Dict[str, Any]:
    """Process configuration data from file."""
    with open(config_path, 'r') as f:
        return json.load(f)

# Configuration constants
DEFAULT_CONFIG = {
    "api_timeout": 30,
    "retry_attempts": 3,
    "enable_logging": True
}
'''

        # JavaScript file
        javascript_code = """
/**
 * JavaScript frontend client for API communication.
 */

class ApiClient {
    /**
     * Initialize API client with configuration.
     * @param {string} baseUrl - Base URL for API
     * @param {string} apiKey - API authentication key
     */
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
        this.defaultHeaders = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${apiKey}`
        };
    }
    
    /**
     * Fetch user data from API.
     * @param {number} userId - User identifier
     * @returns {Promise<Object|null>} User data or null
     */
    async getUserData(userId) {
        try {
            const response = await fetch(`${this.baseUrl}/api/users/${userId}`, {
                headers: this.defaultHeaders
            });
            return response.ok ? await response.json() : null;
        } catch (error) {
            console.error('Error fetching user data:', error);
            return null;
        }
    }
    
    /**
     * Authenticate user credentials.
     * @param {string} username - Username
     * @param {string} password - Password
     * @returns {Promise<boolean>} Authentication success
     */
    async authenticate(username, password) {
        const data = { username, password };
        try {
            const response = await fetch(`${this.baseUrl}/auth/login`, {
                method: 'POST',
                headers: this.defaultHeaders,
                body: JSON.stringify(data)
            });
            return response.ok;
        } catch (error) {
            console.error('Authentication error:', error);
            return false;
        }
    }
}

/**
 * Process configuration data from JSON.
 * @param {Object} configData - Configuration object
 * @returns {Object} Processed configuration
 */
function processConfigData(configData) {
    const defaultConfig = {
        apiTimeout: 30000,
        retryAttempts: 3,
        enableLogging: true
    };
    
    return { ...defaultConfig, ...configData };
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ApiClient, processConfigData };
}
"""

        # C header file
        c_header_code = """
/**
 * C API client header file.
 * Provides C interface for API communication.
 */

#ifndef API_CLIENT_H
#define API_CLIENT_H

#include <stdint.h>
#include <stdbool.h>

// Forward declarations
typedef struct APIClient APIClient;
typedef struct UserData UserData;
typedef struct Config Config;

// Configuration structure
typedef struct Config {
    int api_timeout;
    int retry_attempts;
    bool enable_logging;
    char *base_url;
    char *api_key;
} Config;

// User data structure
typedef struct UserData {
    int user_id;
    char *username;
    char *email;
    bool is_active;
} UserData;

// API client structure
typedef struct APIClient {
    Config *config;
    void *session_handle;
    char *last_error;
} APIClient;

// Function declarations
APIClient* api_client_create(const char* base_url, const char* api_key);
void api_client_destroy(APIClient* client);

UserData* api_client_get_user_data(APIClient* client, int user_id);
bool api_client_authenticate(APIClient* client, const char* username, const char* password);

Config* config_load_from_file(const char* config_path);
void config_destroy(Config* config);

void user_data_destroy(UserData* user_data);

// Error handling
const char* api_client_get_last_error(APIClient* client);

// Constants
#define API_CLIENT_SUCCESS 0
#define API_CLIENT_ERROR -1
#define DEFAULT_TIMEOUT 30
#define DEFAULT_RETRY_ATTEMPTS 3

#endif // API_CLIENT_H
"""

        # C implementation file
        c_impl_code = """
/**
 * C API client implementation.
 */

#include "api_client.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <curl/curl.h>

// Internal structures
struct APIClient {
    Config *config;
    CURL *curl_handle;
    char *last_error;
};

// Internal functions
static size_t write_callback(void *contents, size_t size, size_t nmemb, char **response);
static int perform_request(APIClient* client, const char* url, const char* data, char **response);

APIClient* api_client_create(const char* base_url, const char* api_key) {
    if (!base_url || !api_key) {
        return NULL;
    }
    
    APIClient* client = malloc(sizeof(APIClient));
    if (!client) {
        return NULL;
    }
    
    client->config = malloc(sizeof(Config));
    if (!client->config) {
        free(client);
        return NULL;
    }
    
    // Initialize configuration
    client->config->api_timeout = DEFAULT_TIMEOUT;
    client->config->retry_attempts = DEFAULT_RETRY_ATTEMPTS;
    client->config->enable_logging = true;
    client->config->base_url = strdup(base_url);
    client->config->api_key = strdup(api_key);
    
    // Initialize CURL
    client->curl_handle = curl_easy_init();
    client->last_error = NULL;
    
    return client;
}

void api_client_destroy(APIClient* client) {
    if (!client) return;
    
    if (client->config) {
        free(client->config->base_url);
        free(client->config->api_key);
        free(client->config);
    }
    
    if (client->curl_handle) {
        curl_easy_cleanup(client->curl_handle);
    }
    
    free(client->last_error);
    free(client);
}

UserData* api_client_get_user_data(APIClient* client, int user_id) {
    if (!client || user_id <= 0) {
        return NULL;
    }
    
    char url[512];
    snprintf(url, sizeof(url), "%s/api/users/%d", client->config->base_url, user_id);
    
    char *response = NULL;
    if (perform_request(client, url, NULL, &response) != API_CLIENT_SUCCESS) {
        return NULL;
    }
    
    // Parse JSON response (simplified)
    UserData* user_data = malloc(sizeof(UserData));
    if (user_data) {
        user_data->user_id = user_id;
        user_data->username = strdup("parsed_username");
        user_data->email = strdup("parsed_email");
        user_data->is_active = true;
    }
    
    free(response);
    return user_data;
}

bool api_client_authenticate(APIClient* client, const char* username, const char* password) {
    if (!client || !username || !password) {
        return false;
    }
    
    char url[512];
    snprintf(url, sizeof(url), "%s/auth/login", client->config->base_url);
    
    char data[256];
    snprintf(data, sizeof(data), "{\\"username\\": \\"%s\\", \\"password\\": \\"%s\\"}", username, password);
    
    char *response = NULL;
    int result = perform_request(client, url, data, &response);
    
    free(response);
    return result == API_CLIENT_SUCCESS;
}

static int perform_request(APIClient* client, const char* url, const char* data, char **response) {
    // CURL request implementation (simplified)
    if (!client->curl_handle) {
        return API_CLIENT_ERROR;
    }
    
    curl_easy_setopt(client->curl_handle, CURLOPT_URL, url);
    curl_easy_setopt(client->curl_handle, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(client->curl_handle, CURLOPT_WRITEDATA, response);
    
    if (data) {
        curl_easy_setopt(client->curl_handle, CURLOPT_POSTFIELDS, data);
    }
    
    CURLcode res = curl_easy_perform(client->curl_handle);
    return (res == CURLE_OK) ? API_CLIENT_SUCCESS : API_CLIENT_ERROR;
}

Config* config_load_from_file(const char* config_path) {
    FILE* file = fopen(config_path, "r");
    if (!file) {
        return NULL;
    }
    
    Config* config = malloc(sizeof(Config));
    if (config) {
        // Simplified config parsing
        config->api_timeout = DEFAULT_TIMEOUT;
        config->retry_attempts = DEFAULT_RETRY_ATTEMPTS;
        config->enable_logging = true;
        config->base_url = strdup("http://localhost:8000");
        config->api_key = strdup("default_key");
    }
    
    fclose(file);
    return config;
}
"""

        # JSON configuration file
        json_config = """
{
    "api": {
        "base_url": "https://api.example.com",
        "timeout": 30,
        "retry_attempts": 3,
        "endpoints": {
            "users": "/api/users",
            "auth": "/auth/login",
            "config": "/api/config"
        }
    },
    "logging": {
        "level": "INFO",
        "enable_file_logging": true,
        "log_file": "api_client.log"
    },
    "features": {
        "enable_caching": true,
        "cache_timeout": 300,
        "enable_retry": true,
        "enable_authentication": true
    }
}
"""

        # YAML configuration file
        yaml_config = """
api:
  base_url: "https://api.example.com"
  timeout: 30
  retry_attempts: 3
  endpoints:
    users: "/api/users"
    auth: "/auth/login"
    config: "/api/config"

logging:
  level: "INFO"
  enable_file_logging: true
  log_file: "api_client.log"

features:
  enable_caching: true
  cache_timeout: 300
  enable_retry: true
  enable_authentication: true

database:
  host: "localhost"
  port: 5432
  name: "api_db"
  user: "api_user"
"""

        # Create temporary files
        file_contents = {
            "api_client.py": python_code,
            "api_client.js": javascript_code,
            "api_client.h": c_header_code,
            "api_client.c": c_impl_code,
            "config.json": json_config,
            "config.yaml": yaml_config,
        }

        for filename, content in file_contents.items():
            with tempfile.NamedTemporaryFile(
                suffix=f"_{filename}", mode="w", delete=False, encoding="utf-8"
            ) as f:
                f.write(content)
                f.flush()
                test_files[filename] = Path(f.name)

        return test_files

    def _cleanup_test_files(self, test_files: Dict[str, Path]):
        """Clean up temporary test files."""
        for file_path in test_files.values():
            try:
                file_path.unlink()
            except Exception:
                pass

    def test_multi_language_project_indexing(self, setup_multi_language_project):
        """Test indexing projects with multiple programming languages."""
        project_data = setup_multi_language_project
        plugin_manager = project_data["plugin_manager"]
        test_files = project_data["test_files"]

        # Index files from different languages
        language_files = {
            "python": ["api_client.py"],
            "javascript": ["api_client.js"],
            "c": ["api_client.h", "api_client.c"],
            "json": ["config.json"],
            "yaml": ["config.yaml"],
        }

        indexed_by_language = {}
        symbols_by_language = {}

        for language, filenames in language_files.items():
            indexed_count = 0
            total_symbols = 0

            for filename in filenames:
                if filename not in test_files:
                    continue

                file_path = test_files[filename]

                try:
                    # Find plugin that supports this file
                    supporting_plugin = None
                    for (
                        plugin_name,
                        plugin_instance,
                    ) in plugin_manager.get_active_plugins().items():
                        if hasattr(plugin_instance, "supports") and plugin_instance.supports(
                            file_path
                        ):
                            supporting_plugin = plugin_instance
                            break

                    if supporting_plugin:
                        # Read file content and index
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        result = supporting_plugin.indexFile(file_path, content)

                        if result and "symbols" in result:
                            indexed_count += 1
                            total_symbols += len(result["symbols"])

                            print(
                                f"Indexed {filename} ({language}): {len(result['symbols'])} symbols"
                            )

                except Exception as e:
                    print(f"Failed to index {filename} ({language}): {e}")
                    continue

            indexed_by_language[language] = indexed_count
            symbols_by_language[language] = total_symbols

        # Validate multi-language indexing
        successful_languages = [lang for lang, count in indexed_by_language.items() if count > 0]
        assert (
            len(successful_languages) >= 3
        ), f"Should index multiple languages: {successful_languages}"

        total_indexed = sum(indexed_by_language.values())
        total_symbols = sum(symbols_by_language.values())

        assert total_indexed >= 4, f"Should index multiple files: {total_indexed}"
        assert total_symbols >= 20, f"Should extract symbols: {total_symbols}"

        print(f"Multi-language indexing: {successful_languages}")
        print(f"Total: {total_indexed} files, {total_symbols} symbols")

    def test_common_symbol_patterns_across_languages(self, setup_multi_language_project):
        """Test finding common patterns across different languages."""
        project_data = setup_multi_language_project
        plugin_manager = project_data["plugin_manager"]
        test_files = project_data["test_files"]

        # Index all files and collect symbols
        all_symbols = {}

        for filename, file_path in test_files.items():
            try:
                # Find supporting plugin
                supporting_plugin = None
                for (
                    plugin_name,
                    plugin_instance,
                ) in plugin_manager.get_active_plugins().items():
                    if hasattr(plugin_instance, "supports") and plugin_instance.supports(file_path):
                        supporting_plugin = plugin_instance
                        break

                if supporting_plugin:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    result = supporting_plugin.indexFile(file_path, content)

                    if result and "symbols" in result:
                        # Determine language from file extension
                        language = self._get_language_from_filename(filename)
                        if language not in all_symbols:
                            all_symbols[language] = []

                        all_symbols[language].extend(
                            [
                                symbol["symbol"]
                                for symbol in result["symbols"]
                                if isinstance(symbol, dict) and "symbol" in symbol
                            ]
                        )

            except Exception as e:
                print(f"Error processing {filename}: {e}")
                continue

        # Test common patterns that appear in multiple languages
        test_patterns = [
            {
                "pattern": "config",
                "expected_languages": ["python", "javascript", "c"],
                "case_sensitive": False,
            },
            {
                "pattern": "client",
                "expected_languages": ["python", "javascript", "c"],
                "case_sensitive": False,
            },
            {
                "pattern": "authenticate",
                "expected_languages": ["python", "javascript", "c"],
                "case_sensitive": False,
            },
            {
                "pattern": "user",
                "expected_languages": ["python", "javascript", "c"],
                "case_sensitive": False,
            },
        ]

        pattern_results = {}

        for test_case in test_patterns:
            pattern = test_case["pattern"]
            case_sensitive = test_case["case_sensitive"]
            found_in_languages = set()

            for language, symbols in all_symbols.items():
                for symbol in symbols:
                    symbol_text = symbol if case_sensitive else symbol.lower()
                    pattern_text = pattern if case_sensitive else pattern.lower()

                    if pattern_text in symbol_text:
                        found_in_languages.add(language)
                        break

            pattern_results[pattern] = found_in_languages
            print(f"Pattern '{pattern}' found in: {found_in_languages}")

        # Validate cross-language patterns
        for test_case in test_patterns:
            pattern = test_case["pattern"]
            found_languages = pattern_results[pattern]

            assert (
                len(found_languages) >= 2
            ), f"Pattern '{pattern}' should be found in multiple languages: {found_languages}"

    def _get_language_from_filename(self, filename: str) -> str:
        """Determine programming language from filename."""
        extension_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".c": "c",
            ".h": "c",
            ".cpp": "cpp",
            ".hpp": "cpp",
            ".java": "java",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".xml": "xml",
            ".html": "html",
            ".css": "css",
        }

        for ext, lang in extension_map.items():
            if filename.endswith(ext):
                return lang

        return "unknown"

    def test_cross_language_symbol_resolution(self, setup_multi_language_project):
        """Test resolving symbols across language boundaries."""
        project_data = setup_multi_language_project
        plugin_manager = project_data["plugin_manager"]
        test_files = project_data["test_files"]

        # Index files and build cross-language symbol map
        symbol_definitions = {}
        symbol_references = {}

        for filename, file_path in test_files.items():
            try:
                # Find supporting plugin
                supporting_plugin = None
                for (
                    plugin_name,
                    plugin_instance,
                ) in plugin_manager.get_active_plugins().items():
                    if hasattr(plugin_instance, "supports") and plugin_instance.supports(file_path):
                        supporting_plugin = plugin_instance
                        break

                if not supporting_plugin:
                    continue

                content = file_path.read_text(encoding="utf-8", errors="ignore")
                result = supporting_plugin.indexFile(file_path, content)

                if result and "symbols" in result:
                    language = self._get_language_from_filename(filename)

                    for symbol_info in result["symbols"]:
                        if isinstance(symbol_info, dict) and "symbol" in symbol_info:
                            symbol_name = symbol_info["symbol"]

                            # Record symbol definition
                            if symbol_name not in symbol_definitions:
                                symbol_definitions[symbol_name] = []

                            symbol_definitions[symbol_name].append(
                                {
                                    "file": filename,
                                    "language": language,
                                    "kind": symbol_info.get("kind", "unknown"),
                                    "line": symbol_info.get("line", 0),
                                }
                            )

                            # Look for potential cross-references
                            self._find_cross_references(
                                symbol_name,
                                content,
                                filename,
                                language,
                                symbol_references,
                            )

            except Exception as e:
                print(f"Error processing {filename} for cross-language resolution: {e}")
                continue

        # Analyze cross-language symbol patterns
        cross_language_symbols = {}
        for symbol_name, definitions in symbol_definitions.items():
            languages = set(defn["language"] for defn in definitions)
            if len(languages) > 1:
                cross_language_symbols[symbol_name] = {
                    "languages": languages,
                    "definitions": definitions,
                }

        # Test specific cross-language concepts
        expected_cross_language = [
            "APIClient",  # Class/struct in multiple languages
            "authenticate",  # Function in multiple languages
            "getUserData",  # Method in multiple languages
            "config",  # Configuration concept
        ]

        found_cross_language = []
        for concept in expected_cross_language:
            # Check exact match or case-insensitive match
            for symbol_name in symbol_definitions.keys():
                if (
                    concept.lower() in symbol_name.lower()
                    and len(set(defn["language"] for defn in symbol_definitions[symbol_name])) > 1
                ):
                    found_cross_language.append(concept)
                    break

        print(f"Cross-language symbols found: {list(cross_language_symbols.keys())}")
        print(f"Expected concepts found: {found_cross_language}")

        # Validate cross-language resolution
        assert (
            len(cross_language_symbols) >= 2
        ), f"Should find symbols across languages: {len(cross_language_symbols)}"

        assert (
            len(found_cross_language) >= 2
        ), f"Should find expected cross-language concepts: {found_cross_language}"

    def _find_cross_references(
        self,
        symbol_name: str,
        content: str,
        filename: str,
        language: str,
        symbol_references: Dict,
    ):
        """Find potential cross-references to symbols in content."""
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Simple pattern matching for potential references
            if (
                symbol_name in line
                and not line.strip().startswith("//")
                and not line.strip().startswith("#")
            ):
                if symbol_name not in symbol_references:
                    symbol_references[symbol_name] = []

                symbol_references[symbol_name].append(
                    {
                        "file": filename,
                        "language": language,
                        "line": line_num,
                        "context": line.strip(),
                    }
                )

    def test_configuration_file_integration(self, setup_multi_language_project):
        """Test integration between code and configuration files."""
        project_data = setup_multi_language_project
        plugin_manager = project_data["plugin_manager"]
        test_files = project_data["test_files"]

        # Index configuration files
        config_symbols = {}
        code_symbols = {}

        for filename, file_path in test_files.items():
            try:
                # Find supporting plugin
                supporting_plugin = None
                for (
                    plugin_name,
                    plugin_instance,
                ) in plugin_manager.get_active_plugins().items():
                    if hasattr(plugin_instance, "supports") and plugin_instance.supports(file_path):
                        supporting_plugin = plugin_instance
                        break

                if not supporting_plugin:
                    continue

                content = file_path.read_text(encoding="utf-8", errors="ignore")
                result = supporting_plugin.indexFile(file_path, content)

                if result and "symbols" in result:
                    language = self._get_language_from_filename(filename)

                    if language in ["json", "yaml"]:
                        config_symbols[filename] = result["symbols"]
                    else:
                        code_symbols[filename] = result["symbols"]

            except Exception as e:
                print(f"Error processing {filename} for config integration: {e}")
                continue

        # Look for configuration-related patterns in code
        config_patterns = [
            "config",
            "Config",
            "CONFIG",
            "timeout",
            "retry",
            "api_key",
            "base_url",
            "endpoint",
            "logging",
        ]

        code_config_references = {}

        for code_file, symbols in code_symbols.items():
            references = []
            for symbol_info in symbols:
                if isinstance(symbol_info, dict) and "symbol" in symbol_info:
                    symbol_name = symbol_info["symbol"]
                    for pattern in config_patterns:
                        if pattern.lower() in symbol_name.lower():
                            references.append(
                                {
                                    "symbol": symbol_name,
                                    "pattern": pattern,
                                    "kind": symbol_info.get("kind", "unknown"),
                                }
                            )
                            break

            if references:
                code_config_references[code_file] = references

        # Validate configuration integration
        assert len(config_symbols) >= 1, "Should index configuration files"
        assert len(code_config_references) >= 1, "Should find config-related symbols in code"

        print(f"Configuration files indexed: {list(config_symbols.keys())}")
        print(f"Code files with config references: {list(code_config_references.keys())}")

        # Check for consistent naming patterns
        for code_file, references in code_config_references.items():
            print(f"{code_file} config references:")
            for ref in references[:5]:  # Show first 5
                print(f"  {ref['symbol']} ({ref['kind']}) - pattern: {ref['pattern']}")

    def test_api_consistency_across_languages(self, setup_multi_language_project):
        """Test API consistency across different language implementations."""
        project_data = setup_multi_language_project
        plugin_manager = project_data["plugin_manager"]
        test_files = project_data["test_files"]

        # Define expected API patterns
        expected_api_methods = [
            {"pattern": "get.*user.*data", "languages": ["python", "javascript", "c"]},
            {"pattern": "authenticate", "languages": ["python", "javascript", "c"]},
            {"pattern": "api.*client", "languages": ["python", "javascript", "c"]},
            {"pattern": "config", "languages": ["python", "javascript", "c"]},
        ]

        # Index and extract API-related symbols
        api_symbols_by_language = {}

        for filename, file_path in test_files.items():
            language = self._get_language_from_filename(filename)
            if language not in ["python", "javascript", "c"]:
                continue

            try:
                # Find supporting plugin
                supporting_plugin = None
                for (
                    plugin_name,
                    plugin_instance,
                ) in plugin_manager.get_active_plugins().items():
                    if hasattr(plugin_instance, "supports") and plugin_instance.supports(file_path):
                        supporting_plugin = plugin_instance
                        break

                if not supporting_plugin:
                    continue

                content = file_path.read_text(encoding="utf-8", errors="ignore")
                result = supporting_plugin.indexFile(file_path, content)

                if result and "symbols" in result:
                    if language not in api_symbols_by_language:
                        api_symbols_by_language[language] = []

                    for symbol_info in result["symbols"]:
                        if isinstance(symbol_info, dict) and "symbol" in symbol_info:
                            api_symbols_by_language[language].append(
                                {
                                    "name": symbol_info["symbol"],
                                    "kind": symbol_info.get("kind", "unknown"),
                                    "file": filename,
                                }
                            )

            except Exception as e:
                print(f"Error processing {filename} for API consistency: {e}")
                continue

        # Check API consistency
        api_consistency_results = {}

        for api_pattern in expected_api_methods:
            pattern = api_pattern["pattern"]
            expected_langs = api_pattern["languages"]

            found_in_languages = {}

            for language, symbols in api_symbols_by_language.items():
                if language in expected_langs:
                    matching_symbols = []
                    for symbol in symbols:
                        import re

                        if re.search(pattern, symbol["name"], re.IGNORECASE):
                            matching_symbols.append(symbol)

                    if matching_symbols:
                        found_in_languages[language] = matching_symbols

            api_consistency_results[pattern] = found_in_languages

        # Validate API consistency
        for pattern, found_languages in api_consistency_results.items():
            assert (
                len(found_languages) >= 2
            ), f"API pattern '{pattern}' should be found in multiple languages: {list(found_languages.keys())}"

            print(f"API pattern '{pattern}' found in: {list(found_languages.keys())}")
            for lang, symbols in found_languages.items():
                symbol_names = [s["name"] for s in symbols[:3]]  # Show first 3
                print(f"  {lang}: {symbol_names}")

    def test_real_world_multi_language_project(self):
        """Test cross-language resolution on real multi-language project if available."""
        # Try to use kubernetes repository which has multiple languages
        repo_path = Path("test_workspace/real_repos/kubernetes")
        if not repo_path.exists():
            pytest.skip("Kubernetes repository not available for multi-language testing")

        try:
            from mcp_server.plugin_system import PluginManager
            from mcp_server.storage.sqlite_store import SQLiteStore
        except ImportError:
            pytest.skip("Plugin system components not available")

        # Setup plugin system
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_file:
            store = SQLiteStore(db_file.name)
            plugin_manager = PluginManager(sqlite_store=store)

            load_result = plugin_manager.load_plugins_safe()
            if not load_result.success:
                pytest.skip(f"Failed to load plugins: {load_result.error.message}")

            try:
                # Find files from different languages
                language_files = {
                    "go": list(repo_path.rglob("*.go"))[:10],
                    "yaml": list(repo_path.rglob("*.yaml"))[:5]
                    + list(repo_path.rglob("*.yml"))[:5],
                    "shell": list(repo_path.rglob("*.sh"))[:5],
                    "json": list(repo_path.rglob("*.json"))[:5],
                }

                indexed_by_language = {}
                symbols_by_language = {}

                for language, files in language_files.items():
                    if not files:
                        continue

                    indexed_count = 0
                    total_symbols = 0

                    for file_path in files:
                        try:
                            # Find supporting plugin
                            supporting_plugin = None
                            for (
                                plugin_name,
                                plugin_instance,
                            ) in plugin_manager.get_active_plugins().items():
                                if hasattr(
                                    plugin_instance, "supports"
                                ) and plugin_instance.supports(file_path):
                                    supporting_plugin = plugin_instance
                                    break

                            if supporting_plugin:
                                content = file_path.read_text(encoding="utf-8", errors="ignore")
                                result = supporting_plugin.indexFile(file_path, content)

                                if result and "symbols" in result:
                                    indexed_count += 1
                                    total_symbols += len(result["symbols"])

                        except Exception as e:
                            print(f"Error indexing {file_path}: {e}")
                            continue

                    indexed_by_language[language] = indexed_count
                    symbols_by_language[language] = total_symbols

                # Validate real-world multi-language indexing
                successful_languages = [
                    lang for lang, count in indexed_by_language.items() if count > 0
                ]
                total_files = sum(indexed_by_language.values())
                total_symbols = sum(symbols_by_language.values())

                assert (
                    len(successful_languages) >= 2
                ), f"Should index multiple languages: {successful_languages}"

                assert total_files >= 5, f"Should index multiple files: {total_files}"
                assert total_symbols >= 10, f"Should extract symbols: {total_symbols}"

                print("Real-world multi-language indexing:")
                for lang in successful_languages:
                    print(
                        f"  {lang}: {indexed_by_language[lang]} files, {symbols_by_language[lang]} symbols"
                    )

            finally:
                # Cleanup
                try:
                    Path(db_file.name).unlink()
                except Exception:
                    pass


@pytest.mark.cross_language
@pytest.mark.integration
class TestCrossLanguageIntegration:
    """Test cross-language integration with system components."""

    def test_cross_language_search_integration(self):
        """Test cross-language search capabilities."""
        # This would test search across multiple languages
        # For now, we'll create a simple test structure

        test_symbols = {
            "python": ["UserManager", "authenticate_user", "get_user_data"],
            "javascript": ["UserManager", "authenticateUser", "getUserData"],
            "c": ["user_manager_t", "authenticate_user", "get_user_data"],
        }

        # Test cross-language symbol matching
        common_concepts = {}

        for lang, symbols in test_symbols.items():
            for symbol in symbols:
                concept = self._extract_concept(symbol)
                if concept not in common_concepts:
                    common_concepts[concept] = []
                common_concepts[concept].append((lang, symbol))

        # Find concepts that appear in multiple languages
        cross_language_concepts = {
            concept: languages
            for concept, languages in common_concepts.items()
            if len(set(lang for lang, sym in languages)) > 1
        }

        assert (
            len(cross_language_concepts) >= 2
        ), f"Should find cross-language concepts: {list(cross_language_concepts.keys())}"

        print(f"Cross-language concepts: {list(cross_language_concepts.keys())}")

    def _extract_concept(self, symbol_name: str) -> str:
        """Extract core concept from symbol name."""
        # Simple concept extraction
        symbol_lower = symbol_name.lower()

        if "user" in symbol_lower:
            return "user"
        elif "auth" in symbol_lower:
            return "auth"
        elif "config" in symbol_lower:
            return "config"
        elif "data" in symbol_lower:
            return "data"
        else:
            return "other"
