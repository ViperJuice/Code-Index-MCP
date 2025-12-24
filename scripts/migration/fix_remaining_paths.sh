#!/bin/bash
# Fix remaining hardcoded paths in non-core files
# These files require special permissions or are owned by root

echo "Fixing remaining hardcoded paths in non-core files..."
echo "======================================================="

# Check if running as root when needed
check_sudo() {
    if [ "$EUID" -ne 0 ]; then 
        echo "Some files are owned by root. You may need to run with sudo."
        echo "Usage: sudo bash scripts/fix_remaining_paths.sh"
        echo ""
    fi
}

# Option 1: Fix individual files with sudo
fix_with_sudo() {
    echo "Option 1: Fixing files individually with sudo..."
    
    # Benchmarks (root-owned)
    sudo python scripts/fix_hardcoded_paths.py --file benchmarks/indexing_speed_benchmark.py
    sudo python scripts/fix_hardcoded_paths.py --file benchmarks/semantic_search_benchmark.py
    sudo python scripts/fix_hardcoded_paths.py --file benchmarks/symbol_lookup_benchmark.py
    
    # Scripts utilities (root-owned)
    sudo python scripts/fix_hardcoded_paths.py --file scripts/utilities/debug_plugin_count.py
    sudo python scripts/fix_hardcoded_paths.py --file scripts/utilities/benchmark_reranking_comparison.py
    sudo python scripts/fix_hardcoded_paths.py --file scripts/utilities/index_for_bm25.py
    sudo python scripts/fix_hardcoded_paths.py --file scripts/utilities/create_semantic_plugins.py
    sudo python scripts/fix_hardcoded_paths.py --file scripts/utilities/debug_index_test.py
    
    # Temp cookbook (root-owned)
    sudo python scripts/fix_hardcoded_paths.py --file temp_cookbook/skills/classification/evaluation/vectordb.py
    sudo python scripts/fix_hardcoded_paths.py --file temp_cookbook/skills/text_to_sql/evaluation/vectordb.py
    sudo python scripts/fix_hardcoded_paths.py --file temp_cookbook/skills/text_to_sql/evaluation/prompts.py
    sudo python scripts/fix_hardcoded_paths.py --file temp_cookbook/skills/text_to_sql/evaluation/tests/utils.py
    sudo python scripts/fix_hardcoded_paths.py --file temp_cookbook/skills/retrieval_augmented_generation/evaluation/vectordb.py
    sudo python scripts/fix_hardcoded_paths.py --file temp_cookbook/skills/retrieval_augmented_generation/evaluation/provider_retrieval.py
    sudo python scripts/fix_hardcoded_paths.py --file temp_cookbook/skills/retrieval_augmented_generation/evaluation/prompts.py
    
    # Examples and tests (user-owned, should work without sudo)
    python scripts/fix_hardcoded_paths.py --file examples/demo_reranking_working.py
    python scripts/fix_hardcoded_paths.py --file examples/java_plugin_demo.py
    
    # Tests
    python scripts/fix_hardcoded_paths.py --file tests/root_tests/test_reranking.py
    python scripts/fix_hardcoded_paths.py --file tests/root_tests/test_reranking_quality.py
    python scripts/fix_hardcoded_paths.py --file tests/root_tests/test_complete_index_share_behavior.py
    python scripts/fix_hardcoded_paths.py --file tests/root_tests/test_reranking_simple.py
    python scripts/fix_hardcoded_paths.py --file tests/root_tests/test_reranking_integration.py
    python scripts/fix_hardcoded_paths.py --file tests/root_tests/test_reranking_fixed.py
    python scripts/fix_hardcoded_paths.py --file tests/root_tests/test_mcp_reranking.py
    python scripts/fix_hardcoded_paths.py --file tests/root_tests/test_comprehensive_reranking.py
    python scripts/fix_hardcoded_paths.py --file tests/root_tests/test_index_share_behavior.py
}

# Option 2: Change ownership and fix all at once
fix_with_ownership_change() {
    echo "Option 2: Changing ownership and fixing all files..."
    echo "This will change ownership of benchmarks/, temp_cookbook/, and some utilities to current user"
    echo ""
    read -p "Continue? (y/n) " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Change ownership
        sudo chown -R $(whoami):$(whoami) benchmarks/
        sudo chown -R $(whoami):$(whoami) temp_cookbook/
        sudo chown $(whoami):$(whoami) scripts/utilities/debug_plugin_count.py
        sudo chown $(whoami):$(whoami) scripts/utilities/benchmark_reranking_comparison.py
        sudo chown $(whoami):$(whoami) scripts/utilities/index_for_bm25.py
        sudo chown $(whoami):$(whoami) scripts/utilities/create_semantic_plugins.py
        sudo chown $(whoami):$(whoami) scripts/utilities/debug_index_test.py
        
        echo "Ownership changed. Now running fix script..."
        python scripts/fix_hardcoded_paths.py
    else
        echo "Cancelled."
    fi
}

# Main menu
echo "These files are NOT part of core MCP functionality."
echo "They are benchmarks, examples, tests, and temporary files."
echo ""
echo "Choose an option:"
echo "1. Fix files individually with sudo (preserves ownership)"
echo "2. Change ownership to current user and fix all"
echo "3. Check which files still have hardcoded paths"
echo "4. Exit (files can be fixed later if needed)"
echo ""
read -p "Enter option (1-4): " option

case $option in
    1)
        fix_with_sudo
        ;;
    2)
        fix_with_ownership_change
        ;;
    3)
        echo "Checking for remaining hardcoded paths..."
        python scripts/fix_hardcoded_paths.py --check
        ;;
    4)
        echo "Exiting. These non-core files can be fixed later if needed."
        echo "MCP core functionality is already fully portable."
        ;;
    *)
        echo "Invalid option"
        ;;
esac

echo ""
echo "Done!"