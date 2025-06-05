"""
Comprehensive tests for the Bash/Shell plugin.

Tests various shell script patterns, syntax variations, and plugin functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from .plugin import Plugin
from .plugin import BashTreeSitterWrapper, ShellType
from ...storage.sqlite_store import SQLiteStore


class TestBashTreeSitterWrapper:
    """Test the shell parser functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = BashTreeSitterWrapper()
    
    def test_detect_shell_type_from_shebang(self):
        """Test shell type detection from shebang."""
        test_cases = [
            ("#!/bin/bash\necho hello", ShellType.BASH),
            ("#!/usr/bin/env bash\necho hello", ShellType.BASH),
            ("#!/bin/zsh\necho hello", ShellType.ZSH),
            ("#!/usr/bin/fish\necho hello", ShellType.FISH),
            ("#!/bin/ksh\necho hello", ShellType.KSH),
            ("#!/bin/csh\necho hello", ShellType.CSH),
            ("#!/bin/sh\necho hello", ShellType.SH),
        ]
        
        for content, expected_type in test_cases:
            result = self.parser.detect_shell_type(content)
            assert result == expected_type, f"Expected {expected_type}, got {result}"
    
    def test_detect_shell_type_from_extension(self):
        """Test shell type detection from file extension."""
        test_cases = [
            ("script.bash", ShellType.BASH),
            ("config.zsh", ShellType.ZSH),
            ("setup.fish", ShellType.FISH),
            ("old.ksh", ShellType.KSH),
            ("legacy.csh", ShellType.CSH),
            ("generic.sh", ShellType.BASH),  # Default for .sh
        ]
        
        for filename, expected_type in test_cases:
            result = self.parser.detect_shell_type("echo hello", filename)
            assert result == expected_type, f"Expected {expected_type}, got {result}"
    
    def test_parse_bash_functions(self):
        """Test parsing of Bash function definitions."""
        content = '''#!/bin/bash
        
function hello_world() {
    echo "Hello, World!"
}

goodbye() {
    echo "Goodbye!"
}

function complex_func {
    local var="test"
    echo "$var"
}
'''
        
        result = self.parser.parse_shell_file(content)
        functions = result['functions']
        
        assert len(functions) == 3
        assert functions[0]['name'] == 'hello_world'
        assert functions[0]['line'] == 3
        assert functions[1]['name'] == 'goodbye'
        assert functions[2]['name'] == 'complex_func'
    
    def test_parse_variables_and_exports(self):
        """Test parsing of variable declarations and exports."""
        content = '''#!/bin/bash
        
# Basic variables
NAME="John Doe"
AGE=30
readonly VERSION="1.0.0"

# Exports
export PATH="/usr/local/bin:$PATH"
export DATABASE_URL="postgresql://localhost/mydb"

# Declarations
declare -i COUNT=10
local temp_var="temporary"
typeset -r CONSTANT="immutable"
'''
        
        result = self.parser.parse_shell_file(content)
        variables = result['variables']
        exports = result['exports']
        
        # Check variables
        var_names = [v['name'] for v in variables]
        assert 'NAME' in var_names
        assert 'AGE' in var_names
        assert 'VERSION' in var_names
        assert 'COUNT' in var_names
        assert 'temp_var' in var_names
        assert 'CONSTANT' in var_names
        
        # Check exports
        export_names = [e['name'] for e in exports]
        assert 'PATH' in export_names
        assert 'DATABASE_URL' in export_names
        
        # Check flags
        version_var = next(v for v in variables if v['name'] == 'VERSION')
        assert version_var['is_readonly']
        
        temp_var = next(v for v in variables if v['name'] == 'temp_var')
        assert temp_var['is_local']
    
    def test_parse_aliases(self):
        """Test parsing of alias definitions."""
        content = '''#!/bin/bash
        
alias ll='ls -la'
alias la="ls -A"
alias grep='grep --color=auto'
alias ..='cd ..'
'''
        
        result = self.parser.parse_shell_file(content)
        aliases = result['aliases']
        
        assert len(aliases) == 4
        
        ll_alias = next(a for a in aliases if a['name'] == 'll')
        assert ll_alias['value'] == 'ls -la'
        
        grep_alias = next(a for a in aliases if a['name'] == 'grep')
        assert 'grep --color=auto' in grep_alias['value']
    
    def test_parse_control_structures(self):
        """Test parsing of control flow structures."""
        content = '''#!/bin/bash
        
if [[ "$USER" == "root" ]]; then
    echo "Running as root"
fi

for file in *.txt; do
    echo "Processing $file"
done

while read -r line; do
    echo "$line"
done < input.txt

case "$1" in
    start)
        echo "Starting..."
        ;;
    stop)
        echo "Stopping..."
        ;;
esac

until ping -c1 google.com &>/dev/null; do
    echo "Waiting for network..."
    sleep 1
done
'''
        
        result = self.parser.parse_shell_file(content)
        control_structures = result['control_structures']
        
        assert len(control_structures) == 5
        
        structure_types = [s['type'] for s in control_structures]
        assert 'if' in structure_types
        assert 'for' in structure_types
        assert 'while' in structure_types
        assert 'case' in structure_types
        assert 'until' in structure_types
    
    def test_parse_sourcing_inclusion(self):
        """Test parsing of source/include statements."""
        content = '''#!/bin/bash
        
source /etc/profile
. ~/.bashrc
include utils.sh
source ./config/settings.conf
'''
        
        result = self.parser.parse_shell_file(content)
        sources = result['sources']
        
        assert len(sources) == 4
        
        source_files = [s['file'] for s in sources]
        assert '/etc/profile' in source_files
        assert '~/.bashrc' in source_files
        assert 'utils.sh' in source_files
        assert './config/settings.conf' in source_files
    
    def test_parse_command_substitutions(self):
        """Test parsing of command substitutions and parameter expansions."""
        content = '''#!/bin/bash
        
# Command substitutions
CURRENT_DATE=$(date +%Y-%m-%d)
USER_COUNT=`who | wc -l`

# Parameter expansions
echo "Hello ${USER}"
echo "Path: ${PATH}"
echo "Default: ${VAR:-default_value}"

# Simple variables
echo "User: $USER"
echo "Home: $HOME"
'''
        
        result = self.parser.parse_shell_file(content)
        substitutions = result['substitutions']
        
        command_subs = [s for s in substitutions if s['type'] == 'command_substitution']
        param_expansions = [s for s in substitutions if s['type'] == 'parameter_expansion']
        
        assert len(command_subs) >= 2
        assert len(param_expansions) >= 5
        
        # Check command substitutions
        commands = [s['command'] for s in command_subs]
        assert 'date +%Y-%m-%d' in commands
        assert 'who | wc -l' in commands
    
    def test_parse_pipes_and_redirections(self):
        """Test parsing of pipes and redirection operators."""
        content = '''#!/bin/bash
        
# Pipes
cat file.txt | grep "pattern" | sort | uniq
ps aux | grep nginx

# Redirections
echo "Hello" > output.txt
cat input.txt >> log.txt
command 2> error.log
command &> all_output.log
command < input.txt
'''
        
        result = self.parser.parse_shell_file(content)
        pipes_redirections = result['pipes_redirections']
        
        pipe_ops = [p for p in pipes_redirections if p['type'] == 'pipe']
        redirect_ops = [r for r in pipes_redirections if r['type'] == 'redirection']
        
        assert len(pipe_ops) >= 3  # Multiple pipes in the commands
        assert len(redirect_ops) >= 5
    
    def test_parse_comments_and_documentation(self):
        """Test parsing of comments and documentation."""
        content = '''#!/bin/bash

# Main configuration script
# Author: John Doe
# Description: This script configures the system

# TODO: Add error handling
# FIXME: Handle edge cases
# NOTE: This function is deprecated
function old_function() {
    # This is a regular comment
    echo "deprecated"
}

# @param name The name parameter
# @return status code
function documented_function() {
    echo "documented"
}
'''
        
        result = self.parser.parse_shell_file(content)
        comments = result['comments']
        
        assert len(comments) >= 8
        
        # Check for documentation comments
        doc_comments = [c for c in comments if c['is_documentation']]
        assert len(doc_comments) >= 3  # TODO, FIXME, NOTE, @param, @return
    
    def test_calculate_metadata(self):
        """Test calculation of script metadata."""
        content = '''#!/bin/bash

set -euo pipefail  # Error handling
trap 'echo "Error occurred"' ERR

export DATABASE_URL="postgres://localhost/db"
source ./config.sh

function deploy() {
    echo "Deploying application..."
    docker build -t app:latest .
    kubectl apply -f deployment.yaml
}

function monitor() {
    logger "Starting monitoring"
    while true; do
        echo "System status: OK"
        sleep 60
    done
}

# Main execution
if [[ "$#" -eq 0 ]]; then
    echo "Usage: $0 {deploy|monitor}"
    exit 1
fi

case "$1" in
    deploy)
        deploy
        ;;
    monitor)
        monitor
        ;;
    *)
        echo "Unknown command: $1"
        exit 1
        ;;
esac
'''
        
        result = self.parser.parse_shell_file(content)
        metadata = result['metadata']
        
        assert metadata['has_error_handling']
        assert metadata['has_logging']
        assert metadata['complexity_score'] > 0
        assert 'docker' in metadata['external_deps']
        assert 'kubectl' in metadata['external_deps']
        assert 'DATABASE_URL' in metadata['environment_vars']


class TestBashPlugin:
    """Test the main plugin functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = Plugin()
    
    def test_supports_shell_files(self):
        """Test file support detection."""
        # Test supported extensions
        assert self.plugin.supports("script.sh")
        assert self.plugin.supports("config.bash")
        assert self.plugin.supports("setup.zsh")
        assert self.plugin.supports("init.fish")
        assert self.plugin.supports("legacy.ksh")
        assert self.plugin.supports("old.csh")
        
        # Test unsupported extensions
        assert not self.plugin.supports("document.txt")
        assert not self.plugin.supports("code.py")
        assert not self.plugin.supports("config.json")
    
    def test_supports_shebang_detection(self):
        """Test shebang-based file detection."""
        # Create a temporary file with shebang
        test_file = Path("/tmp/test_script")
        test_file.write_text("#!/bin/bash\necho 'Hello World'")
        
        try:
            assert self.plugin.supports(test_file)
        finally:
            test_file.unlink(missing_ok=True)
    
    def test_index_simple_script(self):
        """Test indexing a simple shell script."""
        content = '''#!/bin/bash

# Simple test script
export APP_NAME="test-app"
VERSION="1.0.0"

function setup() {
    echo "Setting up $APP_NAME"
}

function cleanup() {
    echo "Cleaning up"
}

alias ll='ls -la'

setup
cleanup
'''
        
        result = self.plugin.indexFile("test.sh", content)
        
        assert result["language"] == "shell"
        assert result["shell_type"] == "bash"
        assert result["shebang"] == "/bin/bash"
        
        symbols = result["symbols"]
        symbol_names = [s["symbol"] for s in symbols]
        
        # Check for functions
        assert "setup" in symbol_names
        assert "cleanup" in symbol_names
        
        # Check for variables and exports
        assert "APP_NAME" in symbol_names
        assert "VERSION" in symbol_names
        
        # Check for aliases
        assert "ll" in symbol_names
        
        # Check symbol kinds
        symbol_kinds = {s["symbol"]: s["kind"] for s in symbols}
        assert symbol_kinds["setup"] == "function"
        assert symbol_kinds["APP_NAME"] == "export"
        assert symbol_kinds["VERSION"] == "variable"
        assert symbol_kinds["ll"] == "alias"
    
    def test_get_definition(self):
        """Test symbol definition lookup."""
        # Index a script first
        content = '''#!/bin/bash

function test_function() {
    # Test function documentation
    echo "This is a test function"
}

export TEST_VAR="test_value"
'''
        
        self.plugin.indexFile("test.sh", content)
        
        # Test function definition
        func_def = self.plugin.getDefinition("test_function")
        assert func_def is not None
        assert func_def["symbol"] == "test_function"
        assert func_def["kind"] == "function"
        assert func_def["language"] == "shell"
        assert "test.sh" in func_def["defined_in"]
        
        # Test variable definition
        var_def = self.plugin.getDefinition("TEST_VAR")
        assert var_def is not None
        assert var_def["symbol"] == "TEST_VAR"
        assert var_def["kind"] == "export"
        assert "test_value" in var_def["doc"]
    
    def test_find_references(self):
        """Test finding symbol references."""
        # Create multiple files with references
        content1 = '''#!/bin/bash
function shared_function() {
    echo "Shared function"
}

shared_function
'''
        
        content2 = '''#!/bin/bash
source script1.sh

shared_function
echo "Calling shared_function again"
'''
        
        self.plugin.indexFile("script1.sh", content1)
        self.plugin.indexFile("script2.sh", content2)
        
        references = self.plugin.findReferences("shared_function")
        
        assert len(references) >= 2  # At least definition and one usage
        
        ref_files = [ref.file for ref in references]
        assert any("script1.sh" in f for f in ref_files)
        assert any("script2.sh" in f for f in ref_files)
    
    def test_search_functionality(self):
        """Test search functionality."""
        content = '''#!/bin/bash

function deploy_application() {
    echo "Deploying application to production"
    docker build -t app:latest .
}

function test_application() {
    echo "Running tests"
    pytest tests/
}
'''
        
        self.plugin.indexFile("deploy.sh", content)
        
        # Search for functions
        results = self.plugin.search("deploy")
        assert len(results) > 0
        
        # Search for commands
        results = self.plugin.search("docker")
        assert len(results) > 0
    
    def test_get_shell_analysis(self):
        """Test comprehensive shell analysis."""
        content = '''#!/bin/bash

set -euo pipefail

export DATABASE_URL="postgres://localhost/db"
export API_KEY="secret"

source ./config.sh
source ./utils.sh

function deploy() {
    echo "Deploying..."
    docker build -t app .
    kubectl apply -f deployment.yaml
}

function monitor() {
    logger "Starting monitor"
    while true; do
        echo "Monitoring..."
        sleep 30
    done
}

if [[ "$1" == "deploy" ]]; then
    deploy
elif [[ "$1" == "monitor" ]]; then
    monitor
else
    echo "Usage: $0 {deploy|monitor}"
fi
'''
        
        analysis = self.plugin.get_shell_analysis("deploy.sh", content)
        
        assert analysis["shell_type"] == "bash"
        assert analysis["shebang"] == "/bin/bash"
        assert analysis["function_count"] == 2
        assert analysis["export_count"] == 2
        assert analysis["has_error_handling"]
        assert analysis["has_logging"]
        assert analysis["complexity_score"] > 0
        
        # Check dependencies
        assert "docker" in analysis["external_dependencies"]
        assert "kubectl" in analysis["external_dependencies"]
        
        # Check environment variables
        assert "DATABASE_URL" in analysis["environment_variables"]
        assert "API_KEY" in analysis["environment_variables"]
        
        # Check sourced files
        sources = analysis["sources_includes"]
        source_files = [s["file"] for s in sources]
        assert "./config.sh" in source_files
        assert "./utils.sh" in source_files
    
    def test_fish_shell_parsing(self):
        """Test Fish shell specific syntax."""
        content = '''#!/usr/bin/fish

set -gx EDITOR vim
set -l local_var "test"

function fish_function --description "A Fish function"
    echo "This is Fish syntax"
    
    for item in (seq 1 10)
        echo $item
    end
end

if test -f ~/.config/fish/config.fish
    source ~/.config/fish/config.fish
end
'''
        
        result = self.plugin.indexFile("config.fish", content)
        
        assert result["shell_type"] == "fish"
        assert result["shebang"] == "/usr/bin/fish"
        
        symbols = result["symbols"]
        symbol_names = [s["symbol"] for s in symbols]
        
        assert "fish_function" in symbol_names
        assert "EDITOR" in symbol_names
        assert "local_var" in symbol_names
    
    def test_zsh_shell_parsing(self):
        """Test ZSH shell specific syntax."""
        content = '''#!/usr/bin/zsh

typeset -A assoc_array
assoc_array[key1]="value1"
assoc_array[key2]="value2"

function zsh_function() {
    local -a array_var
    array_var=(item1 item2 item3)
    
    for item in "${array_var[@]}"; do
        echo "$item"
    done
}

# ZSH completion
compdef _files zsh_function
'''
        
        result = self.plugin.indexFile("script.zsh", content)
        
        assert result["shell_type"] == "zsh"
        assert result["shebang"] == "/usr/bin/zsh"
        
        symbols = result["symbols"]
        symbol_names = [s["symbol"] for s in symbols]
        
        assert "zsh_function" in symbol_names
        assert "assoc_array" in symbol_names
    
    @patch('pathlib.Path.rglob')
    def test_preindexing(self, mock_rglob):
        """Test pre-indexing of shell files."""
        # Mock shell files
        mock_files = [
            Mock(spec=Path, suffix='.sh', is_file=Mock(return_value=True)),
            Mock(spec=Path, suffix='.bash', is_file=Mock(return_value=True)),
            Mock(spec=Path, suffix='.zsh', is_file=Mock(return_value=True)),
        ]
        
        for i, mock_file in enumerate(mock_files):
            mock_file.read_text.return_value = f"#!/bin/bash\necho 'script {i}'"
            mock_file.__str__ = Mock(return_value=f"script{i}{mock_file.suffix}")
        
        mock_rglob.return_value = mock_files
        
        # Create plugin (triggers preindexing)
        plugin = Plugin()
        
        # Verify that files were indexed
        stats = plugin.get_indexed_count()
        assert stats >= 0  # Should have indexed something


class TestShellScriptPatterns:
    """Test various shell scripting patterns and edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = BashTreeSitterWrapper()
    
    def test_complex_function_patterns(self):
        """Test complex function definition patterns."""
        content = '''#!/bin/bash

# Different function definition styles
function style1() {
    echo "style1"
}

style2() {
    echo "style2"
}

function style3 {
    echo "style3"
}

# Function with arguments
function process_args() {
    local arg1="$1"
    local arg2="$2"
    echo "Processing $arg1 and $arg2"
}

# Function with complex body
function complex_function() {
    local result=""
    
    if [[ -n "$1" ]]; then
        result=$(echo "$1" | tr '[:lower:]' '[:upper:]')
    else
        result="DEFAULT"
    fi
    
    echo "$result"
    return 0
}
'''
        
        result = self.parser.parse_shell_file(content)
        functions = result['functions']
        
        assert len(functions) == 5
        
        function_names = [f['name'] for f in functions]
        assert 'style1' in function_names
        assert 'style2' in function_names
        assert 'style3' in function_names
        assert 'process_args' in function_names
        assert 'complex_function' in function_names
    
    def test_advanced_variable_patterns(self):
        """Test advanced variable declaration patterns."""
        content = '''#!/bin/bash

# Array declarations
declare -a simple_array=("item1" "item2" "item3")
declare -A assoc_array=(["key1"]="value1" ["key2"]="value2")

# Integer variables
declare -i counter=0
declare -r readonly_var="immutable"

# Exported variables with default values
export PATH="${PATH:-/usr/bin}"
export HOME="${HOME:-/tmp}"

# Complex assignments
DATABASE_URL="postgresql://${DB_USER:-admin}:${DB_PASS:-secret}@${DB_HOST:-localhost}/${DB_NAME:-mydb}"

# Command substitution in assignment
CURRENT_USER=$(whoami)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
'''
        
        result = self.parser.parse_shell_file(content)
        variables = result['variables']
        exports = result['exports']
        
        var_names = [v['name'] for v in variables]
        export_names = [e['name'] for e in exports]
        
        assert 'simple_array' in var_names
        assert 'assoc_array' in var_names
        assert 'counter' in var_names
        assert 'readonly_var' in var_names
        assert 'DATABASE_URL' in var_names
        assert 'CURRENT_USER' in var_names
        assert 'SCRIPT_DIR' in var_names
        
        assert 'PATH' in export_names
        assert 'HOME' in export_names
    
    def test_here_documents_and_strings(self):
        """Test here documents and complex string patterns."""
        content = '''#!/bin/bash

# Here document
cat <<EOF > output.txt
This is a here document
with multiple lines
and variables: $USER
EOF

# Here string
grep "pattern" <<< "$input_string"

# Multi-line strings
sql_query="
SELECT *
FROM users
WHERE active = true
AND created_at > '$(date -d '30 days ago' +%Y-%m-%d)'
"

# Complex quoting
echo 'Single quotes preserve everything: $USER $(date)'
echo "Double quotes expand: $USER $(date)"
echo $'ANSI-C quoting: \n\t'
'''
        
        result = self.parser.parse_shell_file(content)
        
        # Should parse variables and recognize patterns
        variables = result['variables']
        var_names = [v['name'] for v in variables]
        assert 'sql_query' in var_names
    
    def test_conditional_and_loop_patterns(self):
        """Test various conditional and loop patterns."""
        content = '''#!/bin/bash

# Complex conditionals
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Linux system"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "macOS system"
elif [[ "$OSTYPE" == "cygwin" ]]; then
    echo "Cygwin"
else
    echo "Unknown system"
fi

# For loops with different patterns
for file in *.txt; do
    echo "Processing $file"
done

for ((i=1; i<=10; i++)); do
    echo "Number: $i"
done

for user in $(cut -d: -f1 /etc/passwd); do
    echo "User: $user"
done

# While and until loops
while IFS= read -r line; do
    echo "Line: $line"
done < /etc/hosts

until ping -c1 google.com &>/dev/null; do
    echo "Waiting for network..."
    sleep 5
done

# Case statements
case "$1" in
    start|START)
        echo "Starting service"
        ;;
    stop|STOP)
        echo "Stopping service"
        ;;
    restart|RESTART)
        echo "Restarting service"
        ;;
    status|STATUS)
        echo "Service status"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

# Select loop
select option in "Option 1" "Option 2" "Option 3" "Quit"; do
    case $option in
        "Option 1")
            echo "You chose option 1"
            ;;
        "Option 2")
            echo "You chose option 2"
            ;;
        "Option 3")
            echo "You chose option 3"
            ;;
        "Quit")
            break
            ;;
        *)
            echo "Invalid option"
            ;;
    esac
done
'''
        
        result = self.parser.parse_shell_file(content)
        control_structures = result['control_structures']
        
        assert len(control_structures) >= 6  # if, for (3 types), while, until, case, select
        
        structure_types = [s['type'] for s in control_structures]
        assert 'if' in structure_types
        assert 'for' in structure_types
        assert 'while' in structure_types
        assert 'until' in structure_types
        assert 'case' in structure_types
        assert 'select' in structure_types
    
    def test_error_handling_patterns(self):
        """Test error handling and debugging patterns."""
        content = '''#!/bin/bash

set -euo pipefail  # Strict error handling

# Error traps
trap 'echo "Error on line $LINENO"' ERR
trap 'cleanup; exit' INT TERM
trap cleanup EXIT

# Logging function
log() {
    local level="$1"
    shift
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$level] $*" >&2
}

# Function with error handling
safe_operation() {
    local file="$1"
    
    if [[ ! -f "$file" ]]; then
        log ERROR "File not found: $file"
        return 1
    fi
    
    if ! cp "$file" "$file.backup"; then
        log ERROR "Failed to backup $file"
        return 1
    fi
    
    log INFO "Successfully backed up $file"
    return 0
}

# Cleanup function
cleanup() {
    log INFO "Cleaning up temporary files"
    rm -f /tmp/script.$$.*
    
    # Kill background processes
    jobs -p | xargs -r kill
}

# Debug mode
if [[ "${DEBUG:-0}" == "1" ]]; then
    set -x  # Enable debug tracing
fi
'''
        
        result = self.parser.parse_shell_file(content)
        
        # Should detect error handling
        assert result['metadata']['has_error_handling']
        assert result['metadata']['has_logging']
        
        # Should parse functions
        functions = result['functions']
        function_names = [f['name'] for f in functions]
        assert 'log' in function_names
        assert 'safe_operation' in function_names
        assert 'cleanup' in function_names