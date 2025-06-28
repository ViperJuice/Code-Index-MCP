#!/bin/bash
set -e

# Configuration defaults - now flexible
SEARCH_DIRS="."
INCLUDES_DIRS=""
EXIT_CODE=0
VERBOSE=false
FIX_MODE=false
GENERATE_IMAGES=false
OUTPUT_DIR="generated"

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Flexible PlantUML validation - works from any directory"
    echo ""
    echo "Options:"
    echo "  -v, --verbose         Verbose output"
    echo "  --fix                Auto-fix common issues"
    echo "  --generate           Generate PNG/SVG images"
    echo "  --search DIR         Search directory (default: current directory)"
    echo "  --includes DIR       Additional includes directory"
    echo "  --output DIR         Output directory for generated images (default: generated)"
    echo "  --recursive          Search recursively in all subdirectories"
    echo "  -h, --help           Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 --recursive --generate    # Find all .puml files and generate images"
    echo "  $0 --search docs --verbose   # Search only in docs directory"
    echo "  $0 --includes styles         # Use styles directory for includes"
}

# Parse command line arguments
RECURSIVE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --fix)
            FIX_MODE=true
            shift
            ;;
        --generate)
            GENERATE_IMAGES=true
            shift
            ;;
        --search)
            SEARCH_DIRS="$2"
            shift 2
            ;;
        --includes)
            INCLUDES_DIRS="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --recursive)
            RECURSIVE=true
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

echo "PlantUML CLI Validation (Flexible Mode)"
echo "======================================"
echo "Working directory: $(pwd)"
echo "Search directories: $SEARCH_DIRS"
echo "Includes directories: $INCLUDES_DIRS"
echo "Output directory: $OUTPUT_DIR"
echo "Recursive search: $RECURSIVE"

# Test PlantUML installation
echo ""
echo "Testing PlantUML Environment"
echo "============================"

if ! command -v plantuml &> /dev/null; then
    echo "ERROR: PlantUML command not found"
    echo "Please install PlantUML first"
    exit 1
fi

echo -n "PlantUML version: "
plantuml -version 2>&1 | head -1

echo -n "GraphViz test: "
if plantuml -testdot 2>&1 | grep -q "Installation seems OK"; then
    echo "OK"
else
    echo "Issues detected"
    if [ "$VERBOSE" = true ]; then
        plantuml -testdot
    fi
fi

echo -n "Java version: "
java -version 2>&1 | head -1

# Discover PlantUML files flexibly
echo ""
echo "Discovering PlantUML Files"
echo "========================="

# Build find command based on options
FIND_CMD="find"
for dir in $SEARCH_DIRS; do
    if [ ! -d "$dir" ]; then
        echo "WARNING: Directory $dir not found, skipping"
        continue
    fi
    FIND_CMD="$FIND_CMD $dir"
done

if [ "$RECURSIVE" = true ]; then
    FIND_CMD="$FIND_CMD -name '*.puml' -o -name '*.plantuml'"
else
    FIND_CMD="$FIND_CMD -maxdepth 1 -name '*.puml' -o -name '*.plantuml'"
fi

# Execute find and collect results
PUML_FILES=($(eval "$FIND_CMD" 2>/dev/null | sort))

if [ ${#PUML_FILES[@]} -eq 0 ]; then
    echo "INFO: No PlantUML files found"
    echo "   Searched in: $SEARCH_DIRS"
    echo "   Recursive: $RECURSIVE"
    echo "   Looking for: *.puml, *.plantuml"
    exit 0
fi

echo "Found ${#PUML_FILES[@]} PlantUML files:"
for file in "${PUML_FILES[@]}"; do
    # Show relative path from current directory
    rel_path=$(realpath --relative-to="$(pwd)" "$file" 2>/dev/null || echo "$file")
    echo "   - $rel_path"
done

# Auto-discover include directories
echo ""
echo "Auto-discovering include directories..."
DISCOVERED_INCLUDES=()

# Look for common include directory names
for search_dir in $SEARCH_DIRS; do
    for include_name in "includes" "include" "styles" "style" "shared" "common"; do
        if [ -d "$search_dir/$include_name" ]; then
            DISCOVERED_INCLUDES+=("$search_dir/$include_name")
            echo "   Found: $search_dir/$include_name"
        fi
    done
done

# Look for .puml files that might be includes (in any subdirectory)
POTENTIAL_INCLUDES=($(find $SEARCH_DIRS -name "*.puml" -path "*/include*" -o -name "*.puml" -path "*/style*" 2>/dev/null))
for inc_file in "${POTENTIAL_INCLUDES[@]}"; do
    inc_dir=$(dirname "$inc_file")
    if [[ ! " ${DISCOVERED_INCLUDES[@]} " =~ " ${inc_dir} " ]]; then
        DISCOVERED_INCLUDES+=("$inc_dir")
        echo "   Found include files in: $inc_dir"
    fi
done

# Combine manual and discovered includes
ALL_INCLUDES=("${DISCOVERED_INCLUDES[@]}")
if [ -n "$INCLUDES_DIRS" ]; then
    IFS=' ' read -ra MANUAL_INCLUDES <<< "$INCLUDES_DIRS"
    ALL_INCLUDES+=("${MANUAL_INCLUDES[@]}")
fi

# Validation functions
validate_syntax() {
    local file="$1"
    local filename=$(basename "$file")
    
    echo -n "  Syntax check: "
    
    if plantuml -checkonly "$file" 2>/dev/null; then
        echo "Valid"
        return 0
    else
        echo "Invalid"
        if [ "$VERBOSE" = true ]; then
            echo "    Error details:"
            plantuml -checkonly "$file" 2>&1 | sed 's/^/      /'
        fi
        return 1
    fi
}

validate_includes() {
    local file="$1"
    
    if grep -q "!include" "$file"; then
        echo -n "  Include check: "
        
        # Build include arguments
        local include_args=""
        for inc_dir in "${ALL_INCLUDES[@]}"; do
            if [ -d "$inc_dir" ]; then
                include_args="$include_args -I$inc_dir"
            fi
        done
        
        if plantuml $include_args -checkonly "$file" 2>/dev/null; then
            echo "OK"
        else
            echo "Include errors"
            if [ "$VERBOSE" = true ]; then
                echo "    Include error details:"
                plantuml $include_args -checkonly "$file" 2>&1 | sed 's/^/      /'
                echo "    Available include directories:"
                for inc_dir in "${ALL_INCLUDES[@]}"; do
                    echo "      - $inc_dir"
                done
            fi
            return 1
        fi
    else
        echo "  Include check: No includes"
    fi
    return 0
}

generate_image() {
    local file="$1"
    local file_dir=$(dirname "$file")
    local filename=$(basename "$file" .puml)
    
    if [ "$GENERATE_IMAGES" = true ]; then
        echo -n "  Generate: "
        
        # Create output directory relative to file location or use specified output
        local output_path
        if [[ "$OUTPUT_DIR" = /* ]]; then
            # Absolute path
            output_path="$OUTPUT_DIR"
        else
            # Relative path - create relative to file location
            output_path="$file_dir/$OUTPUT_DIR"
        fi
        
        mkdir -p "$output_path"
        
        # Build include arguments for generation
        local include_args=""
        for inc_dir in "${ALL_INCLUDES[@]}"; do
            if [ -d "$inc_dir" ]; then
                include_args="$include_args -I$inc_dir"
            fi
        done
        
        # Generate PNG
        if plantuml $include_args -tpng -o "$output_path" "$file" 2>/dev/null; then
            echo -n "PNG "
        else
            echo -n "PNG-Failed "
        fi
        
        # Generate SVG
        if plantuml $include_args -tsvg -o "$output_path" "$file" 2>/dev/null; then
            echo "SVG"
        else
            echo "SVG-Failed"
        fi
        
        # Show generated files
        if [ "$VERBOSE" = true ]; then
            echo "    Generated in: $output_path"
            ls -la "$output_path"/${filename}.* 2>/dev/null | sed 's/^/      /' || true
        fi
    fi
}

# Main validation loop
echo ""
echo "Validating PlantUML Files"
echo "========================"

VALID_FILES=0
TOTAL_FILES=${#PUML_FILES[@]}

for file in "${PUML_FILES[@]}"; do
    echo ""
    rel_path=$(realpath --relative-to="$(pwd)" "$file" 2>/dev/null || echo "$file")
    echo "File: $(basename "$file")"
    echo "  Path: $rel_path"
    
    file_valid=true
    
    if ! validate_syntax "$file"; then
        file_valid=false
        EXIT_CODE=1
    fi
    
    if ! validate_includes "$file"; then
        file_valid=false
        EXIT_CODE=1
    fi
    
    generate_image "$file"
    
    if [ "$file_valid" = true ]; then
        VALID_FILES=$((VALID_FILES + 1))
    fi
done

# Final report
echo ""
echo "Validation Summary"
echo "=================="
echo "Total files: $TOTAL_FILES"
echo "Valid files: $VALID_FILES"
echo "Invalid files: $((TOTAL_FILES - VALID_FILES))"

if [ "$GENERATE_IMAGES" = true ]; then
    echo ""
    echo "Generated Images Summary:"
    find . -name "*.png" -o -name "*.svg" -newer "$0" 2>/dev/null | wc -l | xargs echo "  Total images generated:"
fi

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "SUCCESS: All PlantUML files passed validation!"
else
    echo ""
    echo "ERROR: Some files failed validation"
    echo ""
    echo "Suggestions:"
    echo "   - Run with --verbose for detailed error information"
    echo "   - Run with --fix to auto-repair common issues"
    echo "   - Use --includes DIR to specify include directories"
    echo "   - Check that include paths are correct"
fi

exit $EXIT_CODE
