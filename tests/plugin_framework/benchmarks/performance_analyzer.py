"""
Performance analysis utilities for benchmark results.

This module provides tools for analyzing benchmark results, detecting
performance regressions, and generating detailed performance reports.
"""

import json
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

# Optional dependencies - imported when needed
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


@dataclass
class PerformanceBaseline:
    """Baseline performance metrics for comparison."""
    test_name: str
    language: str
    plugin_name: str
    baseline_metrics: Dict[str, float]
    timestamp: str
    confidence_interval: float = 0.95


@dataclass
class RegressionAlert:
    """Alert for detected performance regression."""
    test_name: str
    metric_name: str
    baseline_value: float
    current_value: float
    regression_ratio: float
    severity: str  # "minor", "moderate", "severe"
    timestamp: str


class PerformanceAnalyzer:
    """
    Analyzes benchmark results for performance trends and regressions.
    
    Features:
    - Performance trend analysis
    - Regression detection
    - Statistical analysis of benchmark results
    - Performance report generation
    - Baseline management
    """
    
    def __init__(self):
        """Initialize performance analyzer."""
        self.baselines: Dict[str, PerformanceBaseline] = {}
        self.regression_alerts: List[RegressionAlert] = []
        
    # ===== Baseline Management =====
    
    def create_baseline(self, 
                       benchmark_results: List[Dict[str, Any]], 
                       baseline_name: str) -> PerformanceBaseline:
        """Create performance baseline from benchmark results."""
        if not benchmark_results:
            raise ValueError("Cannot create baseline from empty results")
        
        # Extract key metrics from results
        combined_metrics = {}
        
        for result in benchmark_results:
            test_name = result.get("test_name", "unknown")
            metrics = result.get("summary", {})
            
            for metric_name, metric_value in metrics.items():
                if isinstance(metric_value, (int, float)):
                    key = f"{test_name}.{metric_name}"
                    combined_metrics[key] = metric_value
        
        # Get common attributes
        language = benchmark_results[0].get("language", "unknown")
        plugin_name = benchmark_results[0].get("plugin_name", "unknown")
        
        baseline = PerformanceBaseline(
            test_name=baseline_name,
            language=language,
            plugin_name=plugin_name,
            baseline_metrics=combined_metrics,
            timestamp=datetime.now().isoformat()
        )
        
        self.baselines[baseline_name] = baseline
        return baseline
    
    def load_baseline(self, baseline_file: Path) -> PerformanceBaseline:
        """Load baseline from JSON file."""
        with open(baseline_file, 'r') as f:
            baseline_data = json.load(f)
        
        baseline = PerformanceBaseline(**baseline_data)
        self.baselines[baseline.test_name] = baseline
        return baseline
    
    def save_baseline(self, baseline: PerformanceBaseline, output_file: Path):
        """Save baseline to JSON file."""
        with open(output_file, 'w') as f:
            json.dump(asdict(baseline), f, indent=2)
    
    # ===== Regression Detection =====
    
    def detect_regressions(self, 
                          current_results: List[Dict[str, Any]], 
                          baseline_name: str,
                          regression_threshold: float = 1.2) -> List[RegressionAlert]:
        """Detect performance regressions against baseline."""
        if baseline_name not in self.baselines:
            raise ValueError(f"Baseline '{baseline_name}' not found")
        
        baseline = self.baselines[baseline_name]
        alerts = []
        
        # Extract current metrics
        current_metrics = {}
        for result in current_results:
            test_name = result.get("test_name", "unknown")
            metrics = result.get("summary", {})
            
            for metric_name, metric_value in metrics.items():
                if isinstance(metric_value, (int, float)):
                    key = f"{test_name}.{metric_name}"
                    current_metrics[key] = metric_value
        
        # Compare with baseline
        for metric_key, baseline_value in baseline.baseline_metrics.items():
            if metric_key in current_metrics:
                current_value = current_metrics[metric_key]
                
                # Calculate regression ratio
                if baseline_value > 0:
                    ratio = current_value / baseline_value
                    
                    # Check for regression (higher values are worse for time/memory metrics)
                    if "time" in metric_key.lower() or "memory" in metric_key.lower():
                        if ratio >= regression_threshold:
                            severity = self._determine_severity(ratio, regression_threshold)
                            alerts.append(RegressionAlert(
                                test_name=metric_key.split('.')[0],
                                metric_name=metric_key.split('.', 1)[1],
                                baseline_value=baseline_value,
                                current_value=current_value,
                                regression_ratio=ratio,
                                severity=severity,
                                timestamp=datetime.now().isoformat()
                            ))
                    
                    # For throughput/accuracy metrics, lower values are worse
                    elif "throughput" in metric_key.lower() or "accuracy" in metric_key.lower():
                        if ratio <= (1.0 / regression_threshold):
                            severity = self._determine_severity(1.0 / ratio, regression_threshold)
                            alerts.append(RegressionAlert(
                                test_name=metric_key.split('.')[0],
                                metric_name=metric_key.split('.', 1)[1],
                                baseline_value=baseline_value,
                                current_value=current_value,
                                regression_ratio=1.0 / ratio,  # Show as degradation ratio
                                severity=severity,
                                timestamp=datetime.now().isoformat()
                            ))
        
        self.regression_alerts.extend(alerts)
        return alerts
    
    def _determine_severity(self, ratio: float, threshold: float) -> str:
        """Determine regression severity based on ratio."""
        if ratio >= threshold * 2:
            return "severe"
        elif ratio >= threshold * 1.5:
            return "moderate"
        else:
            return "minor"
    
    # ===== Statistical Analysis =====
    
    def analyze_performance_trends(self, 
                                  historical_results: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Analyze performance trends over time."""
        if len(historical_results) < 2:
            return {"error": "Need at least 2 result sets for trend analysis"}
        
        trends = {}
        
        # Extract time series data for each metric
        metrics_over_time = {}
        
        for result_set in historical_results:
            timestamp = result_set[0].get("timestamp", datetime.now().isoformat())
            
            for result in result_set:
                test_name = result.get("test_name", "unknown")
                metrics = result.get("summary", {})
                
                for metric_name, metric_value in metrics.items():
                    if isinstance(metric_value, (int, float)):
                        key = f"{test_name}.{metric_name}"
                        
                        if key not in metrics_over_time:
                            metrics_over_time[key] = []
                        
                        metrics_over_time[key].append((timestamp, metric_value))
        
        # Analyze trends for each metric
        for metric_key, time_series in metrics_over_time.items():
            if len(time_series) >= 2:
                values = [point[1] for point in time_series]
                
                # Calculate trend statistics
                trend_stats = {
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                    "min": min(values),
                    "max": max(values),
                    "trend_direction": self._calculate_trend_direction(values),
                    "stability": self._calculate_stability(values),
                    "data_points": len(values)
                }
                
                trends[metric_key] = trend_stats
        
        return {
            "analysis_timestamp": datetime.now().isoformat(),
            "datasets_analyzed": len(historical_results),
            "metrics_analyzed": len(trends),
            "trends": trends
        }
    
    def _calculate_trend_direction(self, values: List[float]) -> str:
        """Calculate overall trend direction."""
        if len(values) < 2:
            return "insufficient_data"
        
        if HAS_NUMPY:
            # Use linear regression to determine trend
            x = list(range(len(values)))
            slope = np.polyfit(x, values, 1)[0]
        else:
            # Simple slope calculation without numpy
            n = len(values)
            x_mean = (n - 1) / 2
            y_mean = statistics.mean(values)
            
            numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            
            slope = numerator / denominator if denominator > 0 else 0
        
        if abs(slope) < 0.01 * statistics.mean(values):
            return "stable"
        elif slope > 0:
            return "increasing"
        else:
            return "decreasing"
    
    def _calculate_stability(self, values: List[float]) -> str:
        """Calculate metric stability."""
        if len(values) < 2:
            return "insufficient_data"
        
        cv = statistics.stdev(values) / statistics.mean(values) if statistics.mean(values) > 0 else 0
        
        if cv < 0.05:
            return "very_stable"
        elif cv < 0.15:
            return "stable"
        elif cv < 0.30:
            return "moderately_variable"
        else:
            return "highly_variable"
    
    # ===== Statistical Comparison =====
    
    def compare_distributions(self, 
                             results_a: List[Dict[str, Any]], 
                             results_b: List[Dict[str, Any]],
                             test_name: str) -> Dict[str, Any]:
        """Compare two sets of benchmark results statistically."""
        try:
            from scipy import stats
        except ImportError:
            return {"error": "scipy required for statistical comparison"}
        
        # Extract metrics for comparison
        metrics_a = self._extract_metrics(results_a, test_name)
        metrics_b = self._extract_metrics(results_b, test_name)
        
        comparisons = {}
        
        for metric_name in set(metrics_a.keys()) & set(metrics_b.keys()):
            values_a = metrics_a[metric_name]
            values_b = metrics_b[metric_name]
            
            if len(values_a) >= 2 and len(values_b) >= 2:
                # Perform t-test
                t_stat, p_value = stats.ttest_ind(values_a, values_b)
                
                # Calculate effect size (Cohen's d)
                if HAS_NUMPY:
                    pooled_std = np.sqrt(((len(values_a) - 1) * np.var(values_a) + 
                                        (len(values_b) - 1) * np.var(values_b)) / 
                                       (len(values_a) + len(values_b) - 2))
                    
                    effect_size = (np.mean(values_a) - np.mean(values_b)) / pooled_std if pooled_std > 0 else 0
                else:
                    import math
                    var_a = statistics.variance(values_a) if len(values_a) > 1 else 0
                    var_b = statistics.variance(values_b) if len(values_b) > 1 else 0
                    
                    pooled_std = math.sqrt(((len(values_a) - 1) * var_a + 
                                          (len(values_b) - 1) * var_b) / 
                                         (len(values_a) + len(values_b) - 2))
                    
                    effect_size = (statistics.mean(values_a) - statistics.mean(values_b)) / pooled_std if pooled_std > 0 else 0
                
                comparisons[metric_name] = {
                    "mean_a": statistics.mean(values_a),
                    "mean_b": statistics.mean(values_b),
                    "std_a": statistics.stdev(values_a) if len(values_a) > 1 else 0,
                    "std_b": statistics.stdev(values_b) if len(values_b) > 1 else 0,
                    "t_statistic": t_stat,
                    "p_value": p_value,
                    "effect_size": effect_size,
                    "significant": p_value < 0.05,
                    "interpretation": self._interpret_comparison(p_value, effect_size)
                }
        
        return {
            "test_name": test_name,
            "comparisons": comparisons,
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def _extract_metrics(self, results: List[Dict[str, Any]], test_name: str) -> Dict[str, List[float]]:
        """Extract metrics for a specific test."""
        metrics = {}
        
        for result in results:
            if result.get("test_name") == test_name:
                for metric in result.get("metrics", []):
                    metric_name = metric.get("name", "unknown")
                    metric_value = metric.get("value")
                    
                    if isinstance(metric_value, (int, float)):
                        if metric_name not in metrics:
                            metrics[metric_name] = []
                        metrics[metric_name].append(metric_value)
        
        return metrics
    
    def _interpret_comparison(self, p_value: float, effect_size: float) -> str:
        """Interpret statistical comparison results."""
        if p_value >= 0.05:
            return "no_significant_difference"
        
        abs_effect = abs(effect_size)
        if abs_effect < 0.2:
            return "significant_small_effect"
        elif abs_effect < 0.5:
            return "significant_medium_effect"
        else:
            return "significant_large_effect"
    
    # ===== Report Generation =====
    
    def generate_performance_report(self, 
                                  results: List[Dict[str, Any]], 
                                  baseline_name: Optional[str] = None) -> str:
        """Generate comprehensive performance report."""
        report_lines = []
        
        # Header
        report_lines.append("=" * 80)
        report_lines.append("PERFORMANCE ANALYSIS REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Summary
        if results:
            language = results[0].get("language", "unknown")
            plugin_name = results[0].get("plugin_name", "unknown")
            
            report_lines.append("SUMMARY")
            report_lines.append("-" * 40)
            report_lines.append(f"Language: {language}")
            report_lines.append(f"Plugin: {plugin_name}")
            report_lines.append(f"Total Tests: {len(results)}")
            report_lines.append("")
        
        # Performance metrics summary
        report_lines.append("PERFORMANCE METRICS")
        report_lines.append("-" * 40)
        
        for result in results:
            test_name = result.get("test_name", "unknown")
            summary = result.get("summary", {})
            
            report_lines.append(f"\n{test_name}:")
            
            for metric_name, metric_value in summary.items():
                if isinstance(metric_value, (int, float)):
                    if "time" in metric_name.lower():
                        report_lines.append(f"  {metric_name}: {metric_value:.4f}s")
                    elif "memory" in metric_name.lower():
                        report_lines.append(f"  {metric_name}: {metric_value:.2f}MB")
                    elif "rate" in metric_name.lower() or "throughput" in metric_name.lower():
                        report_lines.append(f"  {metric_name}: {metric_value:.2f}")
                    else:
                        report_lines.append(f"  {metric_name}: {metric_value}")
        
        # Regression analysis
        if baseline_name and baseline_name in self.baselines:
            regressions = self.detect_regressions(results, baseline_name)
            
            report_lines.append("\n" + "REGRESSION ANALYSIS")
            report_lines.append("-" * 40)
            
            if regressions:
                report_lines.append(f"Detected {len(regressions)} potential regressions:")
                
                for alert in regressions:
                    report_lines.append(f"\n  {alert.severity.upper()}: {alert.test_name}.{alert.metric_name}")
                    report_lines.append(f"    Baseline: {alert.baseline_value:.4f}")
                    report_lines.append(f"    Current:  {alert.current_value:.4f}")
                    report_lines.append(f"    Ratio:    {alert.regression_ratio:.2f}x")
            else:
                report_lines.append("No performance regressions detected.")
        
        # Recommendations
        report_lines.append("\n" + "RECOMMENDATIONS")
        report_lines.append("-" * 40)
        
        recommendations = self._generate_recommendations(results)
        for rec in recommendations:
            report_lines.append(f"• {rec}")
        
        report_lines.append("\n" + "=" * 80)
        
        return "\n".join(report_lines)
    
    def _generate_recommendations(self, results: List[Dict[str, Any]]) -> List[str]:
        """Generate performance recommendations based on results."""
        recommendations = []
        
        for result in results:
            summary = result.get("summary", {})
            test_name = result.get("test_name", "")
            
            # Check for slow performance
            avg_time = summary.get("duration_mean", 0)
            if avg_time > 5.0:
                recommendations.append(f"Consider optimizing {test_name} - average time {avg_time:.2f}s is high")
            
            # Check for high memory usage
            memory_peak = summary.get("memory_peak_max", 0)
            if memory_peak > 100 * 1024 * 1024:  # 100MB
                recommendations.append(f"High memory usage in {test_name} - peak {memory_peak/1024/1024:.1f}MB")
            
            # Check for low success rate
            success_rate = result.get("success_rate", 1.0)
            if success_rate < 0.95:
                recommendations.append(f"Low success rate in {test_name} - {success_rate:.1%} may indicate issues")
            
            # Check for high variability
            std_dev = summary.get("stdev_execution_time", 0)
            mean_time = summary.get("duration_mean", 1)
            if std_dev > 0 and mean_time > 0:
                cv = std_dev / mean_time
                if cv > 0.3:
                    recommendations.append(f"High variability in {test_name} - consider investigating consistency")
        
        if not recommendations:
            recommendations.append("Performance looks good - no specific recommendations")
        
        return recommendations
    
    # ===== Visualization =====
    
    def plot_performance_trends(self, 
                               historical_results: List[List[Dict[str, Any]]], 
                               output_file: Path,
                               metric_filter: Optional[str] = None):
        """Generate performance trend plots."""
        if not HAS_MATPLOTLIB:
            raise ImportError("matplotlib required for plotting - install with: pip install matplotlib")
        
        import matplotlib.dates as mdates
        from datetime import datetime as dt
        
        # Extract time series data
        metrics_over_time = {}
        timestamps = []
        
        for result_set in historical_results:
            if result_set:
                timestamp_str = result_set[0].get("timestamp", datetime.now().isoformat())
                try:
                    timestamp = dt.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except:
                    timestamp = dt.now()
                
                timestamps.append(timestamp)
                
                for result in result_set:
                    test_name = result.get("test_name", "unknown")
                    summary = result.get("summary", {})
                    
                    for metric_name, metric_value in summary.items():
                        if isinstance(metric_value, (int, float)):
                            if metric_filter and metric_filter not in metric_name:
                                continue
                            
                            key = f"{test_name}.{metric_name}"
                            
                            if key not in metrics_over_time:
                                metrics_over_time[key] = []
                            
                            if len(metrics_over_time[key]) < len(timestamps):
                                metrics_over_time[key].extend([None] * (len(timestamps) - len(metrics_over_time[key]) - 1))
                                metrics_over_time[key].append(metric_value)
        
        # Create plots
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        axes = axes.flatten()
        
        plot_idx = 0
        for metric_key, values in metrics_over_time.items():
            if plot_idx >= 4:
                break
            
            # Fill missing values
            while len(values) < len(timestamps):
                values.append(None)
            
            # Plot
            ax = axes[plot_idx]
            valid_data = [(ts, val) for ts, val in zip(timestamps, values) if val is not None]
            
            if valid_data:
                plot_timestamps, plot_values = zip(*valid_data)
                ax.plot(plot_timestamps, plot_values, marker='o', linewidth=2)
                ax.set_title(metric_key, fontsize=10)
                ax.grid(True, alpha=0.3)
                
                # Format x-axis
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            plot_idx += 1
        
        # Hide unused subplots
        for i in range(plot_idx, 4):
            axes[i].set_visible(False)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_file)