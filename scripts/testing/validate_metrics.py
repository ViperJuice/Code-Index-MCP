#!/usr/bin/env python3
"""
Metrics Validation Script
Validates that Prometheus metrics are being collected correctly
"""

import os
import sys
import httpx
import json
from typing import Dict, List, Set

# Configuration
METRICS_URL = os.getenv("METRICS_URL", "https://mcp-server.example.com/metrics")

# Required metrics that must be present
REQUIRED_METRICS = {
    # Request metrics
    "mcp_requests_total",
    "mcp_request_duration_seconds",
    
    # Plugin metrics
    "mcp_plugin_load_duration_seconds",
    "mcp_plugin_status",
    "mcp_plugin_errors_total",
    
    # Indexing metrics
    "mcp_symbols_indexed_total",
    "mcp_files_indexed_total",
    "mcp_indexing_duration_seconds",
    
    # Search metrics
    "mcp_search_requests_total",
    "mcp_search_duration_seconds",
    "mcp_search_results_count",
    
    # Cache metrics
    "mcp_cache_hits_total",
    "mcp_cache_misses_total",
    
    # System metrics
    "mcp_memory_usage_bytes",
    "mcp_cpu_usage_percent",
    "mcp_active_threads",
    
    # Build info
    "mcp_build_info"
}

# Expected labels for certain metrics
EXPECTED_LABELS = {
    "mcp_requests_total": ["method", "endpoint", "status"],
    "mcp_plugin_status": ["plugin", "language"],
    "mcp_search_requests_total": ["search_type", "language"],
    "mcp_cache_hits_total": ["cache_type"]
}


def parse_prometheus_metrics(text: str) -> Dict[str, List[Dict[str, any]]]:
    """Parse Prometheus text format into structured data."""
    metrics = {}
    current_metric = None
    
    for line in text.strip().split('\n'):
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
            
        # Handle HELP lines
        if line.startswith('# HELP'):
            parts = line.split(' ', 3)
            if len(parts) >= 4:
                metric_name = parts[2]
                if metric_name not in metrics:
                    metrics[metric_name] = []
                    
        # Handle TYPE lines
        elif line.startswith('# TYPE'):
            continue
            
        # Handle metric lines
        elif not line.startswith('#'):
            # Parse metric line
            if ' ' in line:
                metric_part, value_part = line.rsplit(' ', 1)
                
                # Extract metric name and labels
                if '{' in metric_part:
                    metric_name, labels_str = metric_part.split('{', 1)
                    labels_str = labels_str.rstrip('}')
                    
                    # Parse labels
                    labels = {}
                    for label_pair in labels_str.split(','):
                        if '=' in label_pair:
                            key, value = label_pair.split('=', 1)
                            labels[key.strip()] = value.strip('"')
                else:
                    metric_name = metric_part
                    labels = {}
                
                # Store metric
                if metric_name not in metrics:
                    metrics[metric_name] = []
                
                try:
                    value = float(value_part)
                    metrics[metric_name].append({
                        'labels': labels,
                        'value': value
                    })
                except ValueError:
                    pass
    
    return metrics


def validate_metrics(metrics: Dict[str, List[Dict[str, any]]]) -> Dict[str, any]:
    """Validate that all required metrics are present and correct."""
    validation_results = {
        'valid': True,
        'missing_metrics': [],
        'invalid_labels': {},
        'warnings': [],
        'metric_count': len(metrics),
        'total_series': sum(len(series) for series in metrics.values())
    }
    
    # Check for missing metrics
    for required_metric in REQUIRED_METRICS:
        if required_metric not in metrics:
            validation_results['missing_metrics'].append(required_metric)
            validation_results['valid'] = False
    
    # Check label correctness
    for metric_name, expected_labels in EXPECTED_LABELS.items():
        if metric_name in metrics:
            series_list = metrics[metric_name]
            if series_list:
                # Check first series for labels
                actual_labels = set(series_list[0]['labels'].keys())
                expected_set = set(expected_labels)
                
                if actual_labels != expected_set:
                    validation_results['invalid_labels'][metric_name] = {
                        'expected': sorted(expected_labels),
                        'actual': sorted(list(actual_labels)),
                        'missing': sorted(list(expected_set - actual_labels)),
                        'extra': sorted(list(actual_labels - expected_set))
                    }
                    validation_results['valid'] = False
    
    # Check for high cardinality
    for metric_name, series_list in metrics.items():
        if len(series_list) > 1000:
            validation_results['warnings'].append(
                f"High cardinality warning: {metric_name} has {len(series_list)} series"
            )
    
    # Check specific metric values
    if 'mcp_plugin_status' in metrics:
        active_plugins = sum(1 for s in metrics['mcp_plugin_status'] if s['value'] == 1)
        if active_plugins == 0:
            validation_results['warnings'].append("No active plugins detected")
    
    if 'mcp_memory_usage_bytes' in metrics:
        for series in metrics['mcp_memory_usage_bytes']:
            if series['labels'].get('type') == 'rss':
                memory_mb = series['value'] / 1024 / 1024
                if memory_mb > 2048:
                    validation_results['warnings'].append(
                        f"High memory usage: {memory_mb:.2f}MB"
                    )
    
    return validation_results


def print_results(validation_results: Dict[str, any]):
    """Print validation results in a readable format."""
    print("=" * 60)
    print("METRICS VALIDATION RESULTS")
    print("=" * 60)
    
    print(f"\nMetric Count: {validation_results['metric_count']}")
    print(f"Total Series: {validation_results['total_series']}")
    
    if validation_results['missing_metrics']:
        print(f"\n❌ Missing Metrics ({len(validation_results['missing_metrics'])}):")
        for metric in validation_results['missing_metrics']:
            print(f"   - {metric}")
    else:
        print("\n✅ All required metrics present")
    
    if validation_results['invalid_labels']:
        print(f"\n❌ Invalid Labels:")
        for metric, label_info in validation_results['invalid_labels'].items():
            print(f"\n   {metric}:")
            print(f"     Expected: {label_info['expected']}")
            print(f"     Actual: {label_info['actual']}")
            if label_info['missing']:
                print(f"     Missing: {label_info['missing']}")
            if label_info['extra']:
                print(f"     Extra: {label_info['extra']}")
    else:
        print("\n✅ All metric labels correct")
    
    if validation_results['warnings']:
        print(f"\n⚠️  Warnings:")
        for warning in validation_results['warnings']:
            print(f"   - {warning}")
    
    print("\n" + "=" * 60)
    print(f"OVERALL: {'✅ VALID' if validation_results['valid'] else '❌ INVALID'}")
    print("=" * 60)


def main():
    """Main entry point."""
    try:
        # Fetch metrics
        print(f"Fetching metrics from: {METRICS_URL}")
        response = httpx.get(METRICS_URL, timeout=30.0)
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch metrics: HTTP {response.status_code}")
            sys.exit(1)
        
        # Parse metrics
        metrics = parse_prometheus_metrics(response.text)
        
        # Validate metrics
        validation_results = validate_metrics(metrics)
        
        # Print results
        print_results(validation_results)
        
        # Save detailed results
        with open("metrics_validation_results.json", "w") as f:
            json.dump({
                'validation': validation_results,
                'metrics_summary': {
                    metric: len(series) for metric, series in metrics.items()
                }
            }, f, indent=2)
        
        print(f"\nDetailed results saved to: metrics_validation_results.json")
        
        # Exit with appropriate code
        sys.exit(0 if validation_results['valid'] else 1)
        
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()