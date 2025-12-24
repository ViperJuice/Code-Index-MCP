"""Quick chart generation for MCP server metrics visualization."""

from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np


class QuickCharts:
    """Simple chart generator for MCP metrics visualization."""

    def __init__(self, figsize: Tuple[int, int] = (10, 6)):
        """Initialize the chart generator.

        Args:
            figsize: Default figure size (width, height) in inches
        """
        self.figsize = figsize
        plt.style.use("default")  # Use default style for simplicity

    def token_usage_comparison(
        self,
        data: Dict[str, int],
        title: str = "Token Usage Comparison",
        output_path: Optional[str] = None,
        show: bool = True,
    ) -> None:
        """Create a bar chart comparing token usage.

        Args:
            data: Dictionary mapping labels to token counts
            title: Chart title
            output_path: Path to save the chart (PNG format)
            show: Whether to display the chart interactively
        """
        fig, ax = plt.subplots(figsize=self.figsize)

        labels = list(data.keys())
        values = list(data.values())

        bars = ax.bar(labels, values)

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{int(height):,}",
                ha="center",
                va="bottom",
            )

        ax.set_xlabel("Component/Model")
        ax.set_ylabel("Token Count")
        ax.set_title(title)

        # Rotate x labels if many items
        if len(labels) > 5:
            plt.xticks(rotation=45, ha="right")

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches="tight")

        if show:
            plt.show()
        else:
            plt.close()

    def latency_comparison(
        self,
        data: Dict[str, float],
        title: str = "Latency Comparison",
        unit: str = "ms",
        output_path: Optional[str] = None,
        show: bool = True,
    ) -> None:
        """Create a bar chart comparing latencies.

        Args:
            data: Dictionary mapping operation names to latency values
            title: Chart title
            unit: Unit of measurement (ms, s, etc.)
            output_path: Path to save the chart
            show: Whether to display the chart interactively
        """
        fig, ax = plt.subplots(figsize=self.figsize)

        labels = list(data.keys())
        values = list(data.values())

        # Color bars based on latency (green to red gradient)
        colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(values)))
        bars = ax.bar(labels, values, color=colors)

        # Add value labels
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{value:.1f}",
                ha="center",
                va="bottom",
            )

        ax.set_xlabel("Operation")
        ax.set_ylabel(f"Latency ({unit})")
        ax.set_title(title)

        if len(labels) > 5:
            plt.xticks(rotation=45, ha="right")

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches="tight")

        if show:
            plt.show()
        else:
            plt.close()

    def latency_timeline(
        self,
        timestamps: List[float],
        latencies: List[float],
        title: str = "Latency Over Time",
        unit: str = "ms",
        output_path: Optional[str] = None,
        show: bool = True,
    ) -> None:
        """Create a line graph showing latency over time.

        Args:
            timestamps: List of timestamps (seconds or datetime)
            latencies: List of latency values
            title: Chart title
            unit: Unit of measurement
            output_path: Path to save the chart
            show: Whether to display the chart interactively
        """
        fig, ax = plt.subplots(figsize=self.figsize)

        ax.plot(timestamps, latencies, marker="o", linestyle="-", markersize=4)

        ax.set_xlabel("Time")
        ax.set_ylabel(f"Latency ({unit})")
        ax.set_title(title)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches="tight")

        if show:
            plt.show()
        else:
            plt.close()

    def multi_metric_comparison(
        self,
        categories: List[str],
        metrics: Dict[str, List[float]],
        title: str = "Multi-Metric Comparison",
        output_path: Optional[str] = None,
        show: bool = True,
    ) -> None:
        """Create a grouped bar chart comparing multiple metrics.

        Args:
            categories: List of category names (x-axis labels)
            metrics: Dict mapping metric names to lists of values
            title: Chart title
            output_path: Path to save the chart
            show: Whether to display the chart interactively
        """
        fig, ax = plt.subplots(figsize=self.figsize)

        x = np.arange(len(categories))
        width = 0.8 / len(metrics)  # Width of bars

        # Plot each metric
        for i, (metric_name, values) in enumerate(metrics.items()):
            offset = (i - len(metrics) / 2 + 0.5) * width
            bars = ax.bar(x + offset, values, width, label=metric_name)

            # Add value labels on smaller datasets
            if len(categories) <= 10:
                for bar in bars:
                    height = bar.get_height()
                    ax.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height,
                        f"{height:.1f}",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                    )

        ax.set_xlabel("Category")
        ax.set_ylabel("Value")
        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        ax.legend()

        if len(categories) > 5:
            plt.xticks(rotation=45, ha="right")

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches="tight")

        if show:
            plt.show()
        else:
            plt.close()

    def simple_pie_chart(
        self,
        data: Dict[str, float],
        title: str = "Distribution",
        output_path: Optional[str] = None,
        show: bool = True,
    ) -> None:
        """Create a simple pie chart.

        Args:
            data: Dictionary mapping labels to values
            title: Chart title
            output_path: Path to save the chart
            show: Whether to display the chart interactively
        """
        fig, ax = plt.subplots(figsize=(8, 8))

        labels = list(data.keys())
        values = list(data.values())

        # Create pie chart
        wedges, texts, autotexts = ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)

        # Enhance text
        for text in texts:
            text.set_fontsize(10)
        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_fontsize(10)
            autotext.set_weight("bold")

        ax.set_title(title)

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches="tight")

        if show:
            plt.show()
        else:
            plt.close()

    def cost_comparison(self, cost_data, title="Cost Comparison", currency="$", output_path=None):
        """Create cost comparison bar chart."""
        plt.figure(figsize=self.figsize)

        models = list(cost_data.keys())
        costs = list(cost_data.values())

        bars = plt.bar(models, costs)

        # Color bars
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#DDA0DD"]
        for i, bar in enumerate(bars):
            bar.set_color(colors[i % len(colors)])

        # Add value labels
        for bar in bars:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{currency}{height:.4f}",
                ha="center",
                va="bottom",
            )

        plt.title(title)
        plt.xlabel("Model")
        plt.ylabel(f"Cost ({currency})")
        plt.xticks(rotation=45)
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

    def create_stacked_token_chart(
        self, token_data, title="Token Usage: Input vs Output", output_path=None
    ):
        """Create stacked bar chart showing input vs output tokens."""
        plt.figure(figsize=self.figsize)

        labels = list(token_data.keys())
        input_tokens = [data["input"] for data in token_data.values()]
        output_tokens = [data["output"] for data in token_data.values()]

        x = range(len(labels))
        width = 0.6

        # Create stacked bars
        _ = plt.bar(x, input_tokens, width, label="Input Tokens", color="#4ECDC4")
        _ = plt.bar(
            x, output_tokens, width, bottom=input_tokens, label="Output Tokens", color="#FF6B6B"
        )

        # Add value labels
        for i in range(len(labels)):
            # Input token label
            if input_tokens[i] > 0:
                plt.text(
                    i,
                    input_tokens[i] / 2,
                    str(input_tokens[i]),
                    ha="center",
                    va="center",
                    color="white",
                    fontweight="bold",
                )

            # Output token label
            if output_tokens[i] > 0:
                plt.text(
                    i,
                    input_tokens[i] + output_tokens[i] / 2,
                    str(output_tokens[i]),
                    ha="center",
                    va="center",
                    color="white",
                    fontweight="bold",
                )

            # Total at top
            total = input_tokens[i] + output_tokens[i]
            plt.text(
                i,
                total + max(total * 0.02, 50),
                f"Total: {total:,}",
                ha="center",
                va="bottom",
                fontweight="bold",
            )

        plt.title(title)
        plt.xlabel("Search Method")
        plt.ylabel("Token Count")
        plt.xticks(x, labels, rotation=45, ha="right")
        plt.legend()
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

    def create_efficiency_scatter(
        self, data, title="Performance vs Token Efficiency", output_path=None
    ):
        """Create scatter plot comparing performance and token efficiency."""
        plt.figure(figsize=self.figsize)

        # Extract data for plotting
        mcp_times = [d["mcp_time"] for d in data]
        mcp_tokens = [d["mcp_tokens"] for d in data]
        direct_times = [d["direct_time"] for d in data]
        direct_tokens = [d["direct_tokens"] for d in data]

        # Create scatter plot
        plt.scatter(
            mcp_times, mcp_tokens, s=100, c="#4ECDC4", label="MCP", alpha=0.7, edgecolors="black"
        )
        plt.scatter(
            direct_times,
            direct_tokens,
            s=100,
            c="#FF6B6B",
            label="Direct Search",
            alpha=0.7,
            edgecolors="black",
        )

        # Add labels for each point
        for i, d in enumerate(data):
            # MCP label
            plt.annotate(
                d["query"][:10] + "...",
                (mcp_times[i], mcp_tokens[i]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=8,
            )

        plt.title(title)
        plt.xlabel("Response Time (ms)")
        plt.ylabel("Total Tokens Used")
        plt.legend()

        # Set log scale if there's a large difference
        if max(direct_tokens) / max(mcp_tokens) > 10:
            plt.yscale("log")

        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()


# Example usage functions
def example_token_usage():
    """Example of token usage comparison chart."""
    charts = QuickCharts()

    data = {"GPT-4": 15000, "GPT-3.5": 8000, "Claude": 12000, "Local Model": 3000}

    charts.token_usage_comparison(
        data, title="Token Usage by Model", output_path="token_usage.png", show=False
    )


def example_latency_comparison():
    """Example of latency comparison chart."""
    charts = QuickCharts()

    data = {
        "Symbol Lookup": 45.2,
        "Semantic Search": 120.5,
        "Code Search": 85.3,
        "File Read": 15.7,
        "Index Update": 250.0,
    }

    charts.latency_comparison(
        data,
        title="Operation Latency Comparison",
        unit="ms",
        output_path="latency_comparison.png",
        show=False,
    )


def example_timeline():
    """Example of latency timeline chart."""
    charts = QuickCharts()

    # Simulate timestamps and latencies
    timestamps = list(range(0, 60, 5))  # Every 5 seconds for a minute
    latencies = [50 + 20 * np.sin(t / 10) + np.random.normal(0, 5) for t in timestamps]

    charts.latency_timeline(
        timestamps,
        latencies,
        title="API Latency Over Time",
        unit="ms",
        output_path="latency_timeline.png",
        show=False,
    )


def example_multi_metric():
    """Example of multi-metric comparison."""
    charts = QuickCharts()

    categories = ["Python", "JavaScript", "TypeScript", "Go", "Rust"]
    metrics = {
        "Index Time (s)": [2.5, 3.1, 3.5, 1.8, 2.2],
        "Memory (MB)": [150, 180, 200, 120, 130],
        "Accuracy (%)": [95, 92, 94, 90, 93],
    }

    charts.multi_metric_comparison(
        categories,
        metrics,
        title="Language Plugin Performance Metrics",
        output_path="multi_metric.png",
        show=False,
    )


if __name__ == "__main__":
    # Run examples
    print("Generating example charts...")
    example_token_usage()
    example_latency_comparison()
    example_timeline()
    example_multi_metric()
    print("Charts saved as PNG files.")
