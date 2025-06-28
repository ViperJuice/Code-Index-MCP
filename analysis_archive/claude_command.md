# Flexible Diagram Validation

**Command:** `validate-diagrams-flexible`

**Description:** Validates all PlantUML and Structurizr diagrams in the workspace. This command offers flexible options for searching, generating images, and handling errors. It works from any directory.

**Usage:**
```
validate-diagrams-flexible [OPTIONS]
```

**Arguments:**

*   `--search <DIR>`: Specify a directory to search for diagrams. (Default: current directory)
*   `--recursive`: Search for diagrams recursively in all subdirectories.
*   `--generate`: Generate diagram images (e.g., PNG, SVG).
*   `--verbose`: Enable verbose output for detailed logging.
*   `--fix`: Attempt to automatically fix common diagram issues.
*   `--skip-broken`: Skip files with known issues during validation.
*   `--help`: Show the help message.

**Examples:**

*   `validate-diagrams-flexible --recursive --generate`: Find all diagrams in the project and generate corresponding images.
*   `validate-diagrams-flexible --search docs/diagrams --verbose`: Validate only the diagrams found in the `docs/diagrams` directory with verbose output.
*   `validate-diagrams-flexible --recursive --skip-broken`: Validate all diagrams, skipping any that are known to be problematic.

**Script:**
```bash
#!/bin/bash
# Wrapper to call the main validation script

# Find project root by looking for a sentinel file (e.g., Makefile)
find_project_root() {
    local dir="$PWD"
    while [ "$dir" != "/" ]; do
        if [ -f "$dir/Makefile" ]; then
            echo "$dir"
            return
        fi
        dir=$(dirname "$dir")
    done
    echo ""
}

PROJECT_ROOT=$(find_project_root)

if [ -z "$PROJECT_ROOT" ]; then
    echo "Error: Could not find project root. Make sure you are in the project directory."
    exit 1
fi

# Call the main validation script with all arguments
bash "$PROJECT_ROOT/scripts/validate-all-diagrams.sh" "$@"
```
