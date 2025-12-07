"""Token counting utility for estimating tokens and costs across different models."""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass
class TokenCounter:
    """Simple token counter with cost estimation for various models."""

    # Rough estimation: 4 characters ≈ 1 token (industry standard approximation)
    CHARS_PER_TOKEN = 4

    # Model pricing per 1M tokens (as of 2024)
    # Format: (input_price, output_price) in USD per 1M tokens
    MODEL_PRICING = {
        # OpenAI models
        "gpt-4": (30.0, 60.0),
        "gpt-4-turbo": (10.0, 30.0),
        "gpt-3.5-turbo": (0.5, 1.5),
        # Anthropic models
        "claude-3-opus": (15.0, 75.0),
        "claude-3-sonnet": (3.0, 15.0),
        "claude-3-haiku": (0.25, 1.25),
        "claude-2.1": (8.0, 24.0),
        "claude-2": (8.0, 24.0),
        # Voyage AI embedding models
        "voyage-large-2": (0.12, 0.0),  # Embeddings have no output cost
        "voyage-code-2": (0.12, 0.0),
        "voyage-2": (0.10, 0.0),
        "voyage-lite-02-instruct": (0.08, 0.0),
    }

    # Token tracking
    input_tokens: int = field(default=0)
    output_tokens: int = field(default=0)
    token_history: list = field(default_factory=list)

    def count_tokens(self, text: str, model: str = "gpt-4") -> int:
        """
        Count tokens in text using character-based estimation.

        Args:
            text: Text to count tokens for
            model: Model name (used for tracking, estimation is the same)

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Basic character-based estimation
        token_count = len(text) // self.CHARS_PER_TOKEN

        # Account for whitespace and special characters (slight adjustment)
        whitespace_count = text.count(" ") + text.count("\n") + text.count("\t")
        token_count += whitespace_count // 10  # Minor adjustment for formatting

        # Ensure at least 1 token for non-empty text
        return max(1, token_count)

    def add_input_tokens(self, text: str, model: str = "gpt-4") -> int:
        """Add tokens from input text and return count."""
        tokens = self.count_tokens(text, model)
        self.input_tokens += tokens
        self.token_history.append(
            {
                "type": "input",
                "model": model,
                "tokens": tokens,
                "text_preview": text[:100] + "..." if len(text) > 100 else text,
            }
        )
        return tokens

    def add_output_tokens(self, text: str, model: str = "gpt-4") -> int:
        """Add tokens from output text and return count."""
        tokens = self.count_tokens(text, model)
        self.output_tokens += tokens
        self.token_history.append(
            {
                "type": "output",
                "model": model,
                "tokens": tokens,
                "text_preview": text[:100] + "..." if len(text) > 100 else text,
            }
        )
        return tokens

    def estimate_cost(
        self,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        model: str = "gpt-4",
    ) -> float:
        """
        Estimate cost based on token counts and model pricing.

        Args:
            input_tokens: Number of input tokens (uses tracked total if None)
            output_tokens: Number of output tokens (uses tracked total if None)
            model: Model to calculate pricing for

        Returns:
            Estimated cost in USD
        """
        # Use tracked totals if not specified
        input_tokens = input_tokens if input_tokens is not None else self.input_tokens
        output_tokens = output_tokens if output_tokens is not None else self.output_tokens

        # Get model pricing
        if model not in self.MODEL_PRICING:
            # Default to GPT-4 pricing if model unknown
            input_price, output_price = self.MODEL_PRICING["gpt-4"]
        else:
            input_price, output_price = self.MODEL_PRICING[model]

        # Calculate cost (pricing is per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * input_price
        output_cost = (output_tokens / 1_000_000) * output_price

        return input_cost + output_cost

    def get_token_summary(self) -> Dict:
        """
        Get comprehensive summary of token usage and costs.

        Returns:
            Dictionary with token counts and cost estimates for all models
        """
        summary = {
            "total_tokens": self.input_tokens + self.output_tokens,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_costs": {},
            "cost_breakdown": {},
        }

        # Calculate costs for each model
        for model in self.MODEL_PRICING:
            cost = self.estimate_cost(model=model)
            summary["estimated_costs"][model] = f"${cost:.4f}"

            # Detailed breakdown
            input_price, output_price = self.MODEL_PRICING[model]
            input_cost = (self.input_tokens / 1_000_000) * input_price
            output_cost = (self.output_tokens / 1_000_000) * output_price

            summary["cost_breakdown"][model] = {
                "input_cost": f"${input_cost:.4f}",
                "output_cost": f"${output_cost:.4f}",
                "total_cost": f"${cost:.4f}",
            }

        # Add token history summary
        summary["history_count"] = len(self.token_history)

        return summary

    def reset(self):
        """Reset all token counts and history."""
        self.input_tokens = 0
        self.output_tokens = 0
        self.token_history.clear()

    def get_model_comparison(self) -> str:
        """
        Get a formatted string comparing costs across models.

        Returns:
            Formatted string with cost comparison
        """
        if self.input_tokens == 0 and self.output_tokens == 0:
            return "No tokens counted yet."

        lines = [
            "Token Usage Summary:",
            f"  Input tokens: {self.input_tokens:,}",
            f"  Output tokens: {self.output_tokens:,}",
            f"  Total tokens: {self.input_tokens + self.output_tokens:,}",
            "",
            "Estimated Costs by Model:",
        ]

        # Sort models by cost
        costs = []
        for model in self.MODEL_PRICING:
            cost = self.estimate_cost(model=model)
            costs.append((model, cost))

        costs.sort(key=lambda x: x[1])

        for model, cost in costs:
            lines.append(f"  {model:<25} ${cost:.4f}")

        return "\n".join(lines)


# Convenience functions
def quick_estimate(text: str, model: str = "gpt-4") -> Tuple[int, float]:
    """
    Quick token and cost estimation for a single text.

    Args:
        text: Text to estimate
        model: Model to use for pricing

    Returns:
        Tuple of (token_count, estimated_cost)
    """
    counter = TokenCounter()
    tokens = counter.count_tokens(text, model)
    cost = counter.estimate_cost(input_tokens=tokens, output_tokens=0, model=model)
    return tokens, cost


def compare_model_costs(text: str, is_output: bool = False) -> Dict[str, float]:
    """
    Compare costs across all models for given text.

    Args:
        text: Text to estimate
        is_output: Whether this is output text (affects pricing)

    Returns:
        Dictionary mapping model names to costs
    """
    counter = TokenCounter()
    tokens = counter.count_tokens(text)

    costs = {}
    for model in TokenCounter.MODEL_PRICING:
        if is_output:
            cost = counter.estimate_cost(input_tokens=0, output_tokens=tokens, model=model)
        else:
            cost = counter.estimate_cost(input_tokens=tokens, output_tokens=0, model=model)
        costs[model] = cost

    return costs
