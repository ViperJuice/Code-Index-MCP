#!/bin/bash
set -e

# Get the directory where this script is located
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

echo "Complete Diagram Validation (Flexible Mode)"
echo "==========================================="

# Parse arguments
VERBOSE=false
FIX_MODE=false
GENERATE=false
RECURSIVE=false
SEARCH_DIR="."
SKIP_BROKEN=false

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Complete validation of all diagram files - works from any directory"
    echo ""
    echo "Options:"
    echo "  -v, --verbose         Verbose output"
    echo "  --fix                Auto-fix common issues"
    echo "  --generate           Generate diagram images"
    echo "  --recursive          Search recursively in all subdirectories"
    echo "  --search DIR         Search in specific directory"
    echo "  --skip-broken        Skip files with known issues"
    echo "  -h, --help           Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 --recursive --generate     # Find all diagrams and generate images"
    echo "  $0 --search docs --verbose    # Validate only docs directory"
    echo "  $0 --skip-broken --recursive  # Skip problematic files, search all"
}

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
            GENERATE=true
            shift
            ;;
        --recursive)
            RECURSIVE=true
            shift
            ;;
        --search)
            SEARCH_DIR="$2"
            shift 2
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

echo "Working directory: $(pwd)"
echo "Search directory: $SEARCH_DIR"
echo "Recursive search: $RECURSIVE"
echo "Skip broken files: $SKIP_BROKEN"

# Build argument lists for sub-scripts
PLANTUML_ARGS="--search $SEARCH_DIR"
STRUCTURIZR_ARGS="--search $SEARCH_DIR"

if [ "$VERBOSE" = true ]; then
    PLANTUML_ARGS="$PLANTUML_ARGS --verbose"
    STRUCTURIZR_ARGS="$STRUCTURIZR_ARGS --verbose"
fi

if [ "$FIX_MODE" = true ]; then
    PLANTUML_ARGS="$PLANTUML_ARGS --fix"
fi

if [ "$GENERATE" = true ]; then
    PLANTUML_ARGS="$PLANTUML_ARGS --generate"
    STRUCTURIZR_ARGS="$STRUCTURIZR_ARGS --export"
fi

if [ "$RECURSIVE" = true ]; then
    PLANTUML_ARGS="$PLANTUML_ARGS --recursive"
    STRUCTURIZR_ARGS="$STRUCTURIZR_ARGS --recursive"
fi

if [ "$SKIP_BROKEN" = true ]; then
    STRUCTURIZR_ARGS="$STRUCTURIZR_ARGS --skip-broken"
fi

# Run PlantUML validation
echo ""
echo "PlantUML Validation"
echo "=================="

PLANTUML_SCRIPT="$SCRIPT_DIR/plantuml-validate.sh"
if [ ! -f "$PLANTUML_SCRIPT" ]; then
    echo "ERROR: PlantUML validation script not found"
    echo "   Expected: $PLANTUML_SCRIPT"
    exit 1
fi
"$PLANTUML_SCRIPT" $PLANTUML_ARGS

# Run Structurizr validation
echo ""
echo "Structurizr DSL Validation"
echo "========================="

STRUCTURIZR_SCRIPT="$SCRIPT_DIR/structurizr-validate.sh"
if [ ! -f "$STRUCTURIZR_SCRIPT" ]; then
    echo "ERROR: Structurizr validation script not found"
    echo "   Expected: $STRUCTURIZR_SCRIPT"
    exit 1
fi
"$STRUCTURIZR_SCRIPT" $STRUCTURIZR_ARGS

# Final summary
echo ""
echo "Final Summary"
echo "============="
echo "SUCCESS: All diagram validations passed!"
echo ""
echo "Diagram files found:"
if [ "$RECURSIVE" = true ]; then
    find "$SEARCH_DIR" -name "*.puml" -o -name "*.plantuml" -o -name "*.dsl" | head -10
else
    find "$SEARCH_DIR" -maxdepth 1 -name "*.puml" -o -name "*.plantuml" -o -name "*.dsl" | head -10
fi

if [ "$GENERATE" = true ]; then
    echo ""
    echo "Generated files:"
    find "$SEARCH_DIR" -name "*.png" -o -name "*.svg" -newer "$SCRIPT_DIR/validate-all-diagrams.sh" 2>/dev/null | head -10 || echo "   No new files generated"
fi

exit 0
