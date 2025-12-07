#!/usr/bin/env python3
"""Comprehensive test of Kotlin plugin with real Kotlin code analysis."""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_server.plugins.kotlin_plugin import KotlinPlugin
from mcp_server.storage.sqlite_store import SQLiteStore


def analyze_kotlin_file():
    """Analyze a real Kotlin file with the plugin."""
    print("Kotlin Plugin - Comprehensive Analysis")
    print("=" * 60)

    # Create plugin instance
    try:
        sqlite_store = SQLiteStore(":memory:")
        plugin = KotlinPlugin(sqlite_store=sqlite_store, enable_semantic=False)
        print("✓ Kotlin plugin initialized")
    except Exception as e:
        print(f"✗ Failed to create plugin: {e}")
        return False

    # Read the sample Kotlin file
    sample_file = Path("test_files/sample.kt")
    if not sample_file.exists():
        print(f"✗ Sample file {sample_file} not found")
        return False

    content = sample_file.read_text()
    print(f"✓ Loaded sample file ({len(content)} characters)")

    # Extract symbols
    try:
        symbols = plugin.extract_symbols(content, str(sample_file))
        print(f"✓ Extracted {len(symbols)} symbols")

        # Analyze symbol types
        symbol_types = {}
        for symbol in symbols:
            symbol_type = symbol.get("type", "unknown")
            symbol_types[symbol_type] = symbol_types.get(symbol_type, 0) + 1

        print("\nSymbol Type Distribution:")
        for sym_type, count in sorted(symbol_types.items()):
            print(f"  {sym_type}: {count}")

        print("\nFirst 15 symbols:")
        for i, symbol in enumerate(symbols[:15]):
            name = symbol.get("name", "unnamed")
            sym_type = symbol.get("type", "unknown")
            line = symbol.get("line_number", 0)
            print(f"  {i+1:2d}. {name:<25} ({sym_type:<20}) line {line}")

    except Exception as e:
        print(f"✗ Symbol extraction failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("NULL SAFETY ANALYSIS")
    print("=" * 60)

    # Perform null safety analysis
    try:
        null_result = plugin.null_safety_analyzer.analyze(None, content)

        # Display null safety statistics
        stats = null_result.get("statistics", {})
        print(f"Safety Score: {stats.get('safety_score', 'N/A')}/100")
        print(f"Overall Risk Level: {stats.get('overall_risk', 'N/A')}")
        print(f"Total nullable usages: {stats.get('total_nullable_usages', 0)}")
        print(f"Safe call operations: {stats.get('safe_call_count', 0)}")
        print(f"Not-null assertions: {stats.get('not_null_assertion_count', 0)}")
        print(f"Elvis operations: {stats.get('elvis_operation_count', 0)}")
        print(f"Null checks: {stats.get('null_check_count', 0)}")
        print(f"Smart casts: {stats.get('smart_cast_count', 0)}")
        print(f"Late-init properties: {stats.get('lateinit_usage_count', 0)}")
        print(f"Lazy properties: {stats.get('lazy_property_count', 0)}")

        # Show some specific null safety issues
        potential_risks = null_result.get("potential_risks", [])
        if potential_risks:
            print(f"\nPotential Null Safety Risks ({len(potential_risks)}):")
            for i, risk in enumerate(potential_risks[:5]):
                print(
                    f"  {i+1}. Line {risk.get('line', 0)}: {risk.get('description', 'Unknown risk')}"
                )

        # Show safe operations
        safe_calls = null_result.get("safe_call_chains", [])
        if safe_calls:
            print(f"\nSafe Call Operations ({len(safe_calls)}):")
            for i, call in enumerate(safe_calls[:3]):
                print(f"  {i+1}. Line {call.get('line', 0)}: {call.get('name', 'Unknown')}")

        # Get recommendations
        recommendations = plugin.null_safety_analyzer.get_null_safety_recommendations(null_result)
        if recommendations:
            print(f"\nNull Safety Recommendations:")
            for i, rec in enumerate(recommendations):
                print(f"  {i+1}. {rec}")

    except Exception as e:
        print(f"✗ Null safety analysis failed: {e}")

    print("\n" + "=" * 60)
    print("COROUTINES ANALYSIS")
    print("=" * 60)

    # Perform coroutines analysis
    try:
        coroutines_result = plugin.coroutines_analyzer.analyze(None, content)

        # Display coroutines statistics
        stats = coroutines_result.get("statistics", {})
        print(f"Maturity Score: {stats.get('maturity_score', 'N/A')}/100")
        print(f"Performance Impact: {stats.get('performance_impact', 'N/A')}")
        print(f"Suspend functions: {stats.get('suspend_function_count', 0)}")
        print(f"Coroutine builders: {stats.get('coroutine_builder_count', 0)}")
        print(f"Flow operations: {stats.get('flow_operation_count', 0)}")
        print(f"State management: {stats.get('state_management_count', 0)}")
        print(f"Exception handling: {stats.get('exception_handling_count', 0)}")
        print(f"Anti-patterns: {stats.get('anti_pattern_count', 0)}")
        print(f"Best practices: {stats.get('best_practice_count', 0)}")

        # Show specific coroutine usages
        suspend_functions = coroutines_result.get("suspend_functions", [])
        if suspend_functions:
            print(f"\nSuspend Functions ({len(suspend_functions)}):")
            for i, func in enumerate(suspend_functions[:3]):
                print(f"  {i+1}. {func.get('name', 'Unknown')} at line {func.get('line', 0)}")

        flow_ops = coroutines_result.get("flow_operations", [])
        if flow_ops:
            print(f"\nFlow Operations ({len(flow_ops)}):")
            for i, op in enumerate(flow_ops[:3]):
                print(f"  {i+1}. {op.get('name', 'Unknown')} at line {op.get('line', 0)}")

        # Show anti-patterns if any
        anti_patterns = coroutines_result.get("anti_patterns", [])
        if anti_patterns:
            print(f"\nCoroutine Anti-Patterns ({len(anti_patterns)}):")
            for i, pattern in enumerate(anti_patterns):
                print(
                    f"  {i+1}. Line {pattern.get('line', 0)}: {pattern.get('description', 'Unknown')}"
                )

        # Get recommendations
        recommendations = plugin.coroutines_analyzer.get_coroutine_recommendations(
            coroutines_result
        )
        if recommendations:
            print(f"\nCoroutines Recommendations:")
            for i, rec in enumerate(recommendations):
                print(f"  {i+1}. {rec}")

    except Exception as e:
        print(f"✗ Coroutines analysis failed: {e}")

    print("\n" + "=" * 60)
    print("JAVA INTEROP ANALYSIS")
    print("=" * 60)

    # Perform Java interop analysis
    try:
        interop_result = plugin.java_interop_analyzer.analyze(None, content)

        # Display Java interop statistics
        stats = interop_result.get("statistics", {})
        print(f"Interop Quality Score: {stats.get('interop_quality_score', 'N/A')}/100")
        print(f"Java Dependency Level: {stats.get('java_dependency_level', 'N/A')}")
        print(f"JVM annotations: {stats.get('jvm_annotation_count', 0)}")
        print(f"Java imports: {stats.get('java_import_count', 0)}")
        print(f"Platform types: {stats.get('platform_type_count', 0)}")
        print(f"Collection interop: {stats.get('collection_interop_count', 0)}")
        print(f"Null safety issues: {stats.get('null_safety_issue_count', 0)}")
        print(f"Performance considerations: {stats.get('performance_consideration_count', 0)}")

        # Show JVM annotations
        jvm_annotations = interop_result.get("jvm_annotations", [])
        if jvm_annotations:
            print(f"\nJVM Annotations ({len(jvm_annotations)}):")
            for i, annotation in enumerate(jvm_annotations):
                print(
                    f"  {i+1}. {annotation.get('name', 'Unknown')} at line {annotation.get('line', 0)}"
                )

        # Show collection interop
        collection_interop = interop_result.get("collection_interop", [])
        if collection_interop:
            print(f"\nJava Collection Usage ({len(collection_interop)}):")
            for i, usage in enumerate(collection_interop):
                collection_type = usage.get("collection_type", "Unknown")
                kotlin_alt = usage.get("kotlin_alternative", "N/A")
                print(f"  {i+1}. {collection_type} (Kotlin alternative: {kotlin_alt})")

        # Show potential issues
        potential_issues = interop_result.get("potential_issues", [])
        if potential_issues:
            print(f"\nJava Interop Issues ({len(potential_issues)}):")
            for i, issue in enumerate(potential_issues[:3]):
                print(
                    f"  {i+1}. Line {issue.get('line', 0)}: {issue.get('description', 'Unknown')}"
                )

        # Get recommendations
        recommendations = plugin.java_interop_analyzer.get_interop_recommendations(interop_result)
        if recommendations:
            print(f"\nJava Interop Recommendations:")
            for i, rec in enumerate(recommendations):
                print(f"  {i+1}. {rec}")

    except Exception as e:
        print(f"✗ Java interop analysis failed: {e}")

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print("✓ Kotlin plugin comprehensive analysis completed successfully!")

    return True


if __name__ == "__main__":
    success = analyze_kotlin_file()
    sys.exit(0 if success else 1)
