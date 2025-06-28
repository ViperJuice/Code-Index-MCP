#!/bin/bash
set -e

# Configuration defaults
SEARCH_DIRS="."
EXIT_CODE=0
VERBOSE=false
EXPORT_TEST=false
RECURSIVE=false

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Flexible Structurizr DSL validation - works from any directory"
    echo ""
    echo "Options:"
    echo "  -v, --verbose         Verbose output"
    echo "  --export             Test export capabilities"
    echo "  --search DIR         Search directory (default: current directory)"
    echo "  --recursive          Search recursively in all subdirectories"
    echo "  --skip-broken        Skip files with known issues"
    echo "  -h, --help           Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 --recursive --export      # Find all .dsl files and test exports"
    echo "  $0 --search docs --verbose   # Search only in docs directory"
    echo "  $0 --skip-broken             # Skip files in architecture/ directory"
}

# Parse command line arguments
SKIP_BROKEN=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --export)
            EXPORT_TEST=true
            shift
            ;;
        --search)
            SEARCH_DIRS="$2"
            shift 2
            ;;
        --recursive)
            RECURSIVE=true
            shift
            ;;
        --skip-broken)
            SKIP_BROKEN=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

echo "Structurizr DSL CLI Validation (Flexible Mode)"
echo "=============================================="
echo "Working directory: $(pwd)"
echo "Search directories: $SEARCH_DIRS"
echo "Recursive search: $RECURSIVE"
echo "Skip broken files: $SKIP_BROKEN"

# Test Structurizr CLI
echo ""
echo "Testing Structurizr Environment"
echo "==============================="

if ! command -v structurizr &> /dev/null; then
    echo "ERROR: Structurizr CLI not found"
    echo "Please install Structurizr CLI first"
    exit 1
fi

echo -n "Structurizr CLI: "
structurizr version 2>/dev/null || echo "Version info not available"

echo -n "Java version: "
java -version 2>&1 | head -1

# Discover DSL files flexibly
echo ""
echo "Discovering DSL Files"
echo "===================="

# Build find command
FIND_CMD="find"
for dir in $SEARCH_DIRS; do
    if [ ! -d "$dir" ]; then
        echo "WARNING: Directory $dir not found, skipping"
        continue
    fi
    FIND_CMD="$FIND_CMD $dir"
done

if [ "$RECURSIVE" = true ]; then
    FIND_CMD="$FIND_CMD -name '*.dsl'"
else
    FIND_CMD="$FIND_CMD -maxdepth 1 -name '*.dsl'"
fi

# Execute find and collect results
ALL_DSL_FILES=($(eval "$FIND_CMD" 2>/dev/null | sort))

# Filter out broken files if requested
DSL_FILES=()
SKIPPED_FILES=()

for file in "${ALL_DSL_FILES[@]}"; do
    if [ "$SKIP_BROKEN" = true ]; then
        # Skip known problematic files
        if [[ "$file" == *"/architecture/"* ]] || [[ "$file" == *"broken"* ]]; then
            SKIPPED_FILES+=("$file")
            continue
        fi
    fi
    DSL_FILES+=("$file")
done

if [ ${#DSL_FILES[@]} -eq 0 ]; then
    echo "INFO: No DSL files found"
    echo "   Searched in: $SEARCH_DIRS"
    echo "   Recursive: $RECURSIVE"
    echo "   Looking for: *.dsl"
    if [ ${#SKIPPED_FILES[@]} -gt 0 ]; then
        echo "   Skipped ${#SKIPPED_FILES[@]} files due to --skip-broken"
    fi
    exit 0
fi

echo "Found ${#DSL_FILES[@]} DSL files:"
for file in "${DSL_FILES[@]}"; do
    rel_path=$(realpath --relative-to="$(pwd)" "$file" 2>/dev/null || echo "$file")
    echo "   - $rel_path"
done

if [ ${#SKIPPED_FILES[@]} -gt 0 ]; then
    echo ""
    echo "Skipped ${#SKIPPED_FILES[@]} files:"
    for file in "${SKIPPED_FILES[@]}"; do
        rel_path=$(realpath --relative-to="$(pwd)" "$file" 2>/dev/null || echo "$file")
        echo "   - $rel_path (skipped)"
    done
fi

# Validation function
validate_dsl_syntax() {
    local file="$1"
    echo -n "  Syntax validation: "
    
    if structurizr validate -workspace "$file" 2>/dev/null; then
        echo "Valid"
        return 0
    else
        echo "Invalid"
        if [ "$VERBOSE" = true ]; then
            echo "    Error details:"
            structurizr validate -workspace "$file" 2>&1 | sed 's/^/      /'
        fi
        return 1
    fi
}

test_exports() {
    local file="$1"
    local filename=$(basename "$file" .dsl)
    local file_dir=$(dirname "$file")
    
    echo -n "  JSON export: "
    temp_json="/tmp/${filename}_$(date +%s).json"
    if structurizr export -workspace "$file" -format json -output "$temp_json" 2>/dev/null; then
        echo "OK"
        rm -rf "$temp_json"
    else
        echo "Failed"
        EXIT_CODE=1
    fi
    
    echo -n "  PlantUML export: "
    # Change to file directory to control where .puml files are generated
    pushd "$file_dir" >/dev/null
    if structurizr export -workspace "$(basename "$file")" -format plantuml 2>/dev/null; then
        echo "OK"
        # Clean up generated .puml files
        rm -f *.puml
    else
        echo "Failed"
        EXIT_CODE=1
    fi
    popd >/dev/null
    
    echo -n "  Mermaid export: "
    pushd "$file_dir" >/dev/null
    if structurizr export -workspace "$(basename "$file")" -format mermaid 2>/dev/null; then
        echo "OK"
        # Clean up generated .mmd files
        rm -f *.mmd
    else
        echo "Failed"
        EXIT_CODE=1
    fi
    popd >/dev/null
}

# Main validation loop
echo ""
echo "Validating DSL Files"
echo "==================="

VALID_FILES=0
for file in "${DSL_FILES[@]}"; do
    echo ""
    rel_path=$(realpath --relative-to="$(pwd)" "$file" 2>/dev/null || echo "$file")
    echo "File: $(basename "$file")"
    echo "  Path: $rel_path"
    
    if validate_dsl_syntax "$file"; then
        VALID_FILES=$((VALID_FILES + 1))
        
        if [ "$EXPORT_TEST" = true ]; then
            test_exports "$file"
        fi
    else
        EXIT_CODE=1
    fi
done

echo ""
echo "Validation Summary"
echo "=================="
echo "Total files processed: ${#DSL_FILES[@]}"
echo "Valid files: $VALID_FILES"
echo "Invalid files: $((${#DSL_FILES[@]} - VALID_FILES))"

if [ ${#SKIPPED_FILES[@]} -gt 0 ]; then
    echo "Skipped files: ${#SKIPPED_FILES[@]}"
fi

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "SUCCESS: All processed DSL files passed validation!"
else
    echo ""
    echo "ERROR: Some files failed validation"
    echo ""
    echo "Suggestions:"
    echo "   - Run with --verbose for detailed error information"
    echo "   - Run with --export to test all export formats"
    echo "   - Use --skip-broken to skip known problematic files"
    echo "   - Fix syntax errors in DSL files"
fi

exit $EXIT_CODE
