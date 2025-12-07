"""Trait analysis for Rust code."""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class TraitInfo:
    """Information about a Rust trait."""

    name: str
    line_number: int
    generic_params: List[str]
    lifetime_params: List[str]
    associated_types: List[str]
    methods: List[str]
    supertraits: List[str]


@dataclass
class ImplInfo:
    """Information about a trait implementation."""

    trait_name: Optional[str]
    target_type: str
    line_number: int
    generic_params: List[str]
    lifetime_params: List[str]
    methods: List[str]


@dataclass
class LifetimeInfo:
    """Information about lifetime usage."""

    name: str
    line_number: int
    context: str  # 'function', 'struct', 'impl', 'trait'


class RustTraitAnalyzer:
    """Analyzes Rust traits, implementations, and lifetimes."""

    def __init__(self):
        self.trait_pattern = re.compile(
            r"(?:pub\s+)?trait\s+(\w+)(?:<([^>]+)>)?\s*(?::\s*([^\{]+))?\s*\{",
            re.MULTILINE | re.DOTALL,
        )
        self.impl_pattern = re.compile(
            r"impl(?:<([^>]+)>)?\s+(?:(\w+(?:::\w+)*)\s+for\s+)?([^\{]+)\s*\{",
            re.MULTILINE | re.DOTALL,
        )
        self.lifetime_pattern = re.compile(r"'(\w+)")
        self.associated_type_pattern = re.compile(r"type\s+(\w+)(?:\s*[:=]|;)")
        self.method_pattern = re.compile(r"fn\s+(\w+)\s*(?:<[^>]+>)?\s*\(")

    def analyze_file(self, content: str) -> Dict[str, any]:
        """
        Analyze a Rust file for traits, implementations, and lifetimes.

        Returns:
            Dictionary with analysis results
        """
        return {
            "traits": self.find_traits(content),
            "implementations": self.find_implementations(content),
            "lifetimes": self.find_lifetimes(content),
            "trait_bounds": self.find_trait_bounds(content),
        }

    def find_traits(self, content: str) -> List[TraitInfo]:
        """Find all trait definitions in the content."""
        traits = []

        for match in self.trait_pattern.finditer(content):
            trait_name = match.group(1)
            generics = match.group(2) or ""
            supertraits_str = match.group(3) or ""

            # Find the trait body
            start_pos = match.end()
            brace_count = 1
            pos = start_pos

            while brace_count > 0 and pos < len(content):
                if content[pos] == "{":
                    brace_count += 1
                elif content[pos] == "}":
                    brace_count -= 1
                pos += 1

            trait_body = content[start_pos : pos - 1] if pos > start_pos else ""

            # Parse generic and lifetime parameters
            generic_params, lifetime_params = self._parse_generics(generics)

            # Parse supertraits
            supertraits = [s.strip() for s in supertraits_str.split("+") if s.strip()]

            # Find associated types
            associated_types = self.associated_type_pattern.findall(trait_body)

            # Find methods
            methods = self.method_pattern.findall(trait_body)

            # Calculate line number
            line_number = content[: match.start()].count("\n") + 1

            traits.append(
                TraitInfo(
                    name=trait_name,
                    line_number=line_number,
                    generic_params=generic_params,
                    lifetime_params=lifetime_params,
                    associated_types=associated_types,
                    methods=methods,
                    supertraits=supertraits,
                )
            )

        return traits

    def find_implementations(self, content: str) -> List[ImplInfo]:
        """Find all impl blocks in the content."""
        implementations = []

        for match in self.impl_pattern.finditer(content):
            generics = match.group(1) or ""
            trait_name = match.group(2)
            target_type = match.group(3).strip()

            # Find the impl body
            start_pos = match.end()
            brace_count = 1
            pos = start_pos

            while brace_count > 0 and pos < len(content):
                if content[pos] == "{":
                    brace_count += 1
                elif content[pos] == "}":
                    brace_count -= 1
                pos += 1

            impl_body = content[start_pos : pos - 1] if pos > start_pos else ""

            # Parse generic and lifetime parameters
            generic_params, lifetime_params = self._parse_generics(generics)

            # Find methods
            methods = self.method_pattern.findall(impl_body)

            # Calculate line number
            line_number = content[: match.start()].count("\n") + 1

            implementations.append(
                ImplInfo(
                    trait_name=trait_name,
                    target_type=target_type,
                    line_number=line_number,
                    generic_params=generic_params,
                    lifetime_params=lifetime_params,
                    methods=methods,
                )
            )

        return implementations

    def find_lifetimes(self, content: str) -> List[LifetimeInfo]:
        """Find all lifetime annotations in the content."""
        lifetimes = []
        lines = content.split("\n")

        # Patterns for different contexts
        contexts = [
            (re.compile(r"fn\s+\w+.*?'(\w+)"), "function"),
            (re.compile(r"struct\s+\w+.*?'(\w+)"), "struct"),
            (re.compile(r"impl.*?'(\w+)"), "impl"),
            (re.compile(r"trait\s+\w+.*?'(\w+)"), "trait"),
        ]

        for i, line in enumerate(lines):
            for pattern, context in contexts:
                for match in pattern.finditer(line):
                    lifetime_name = match.group(1)
                    if lifetime_name not in ["static", "a", "b"]:  # Filter common ones
                        lifetimes.append(
                            LifetimeInfo(name=lifetime_name, line_number=i + 1, context=context)
                        )

        return lifetimes

    def find_trait_bounds(self, content: str) -> List[Dict[str, any]]:
        """Find trait bounds in where clauses and generic parameters."""
        bounds = []

        # Pattern for where clauses
        where_pattern = re.compile(r"where\s+((?:[^{;]+(?:\n\s*)?)+)", re.MULTILINE)

        for match in where_pattern.finditer(content):
            where_clause = match.group(1)
            line_number = content[: match.start()].count("\n") + 1

            # Parse individual bounds
            bound_parts = re.split(r",\s*(?![^<>]*>)", where_clause)
            for bound in bound_parts:
                bound = bound.strip()
                if ":" in bound:
                    type_param, traits = bound.split(":", 1)
                    bounds.append(
                        {
                            "type": type_param.strip(),
                            "bounds": [t.strip() for t in traits.split("+")],
                            "line_number": line_number,
                        }
                    )

        return bounds

    def _parse_generics(self, generics_str: str) -> Tuple[List[str], List[str]]:
        """Parse generic and lifetime parameters from a generics string."""
        if not generics_str:
            return [], []

        generic_params = []
        lifetime_params = []

        # Split by comma, but not within angle brackets
        parts = re.split(r",\s*(?![^<>]*>)", generics_str)

        for part in parts:
            part = part.strip()
            if part.startswith("'"):
                # Lifetime parameter
                lifetime_name = part.split()[0]
                lifetime_params.append(lifetime_name)
            else:
                # Generic type parameter
                generic_name = part.split(":")[0].split("=")[0].strip()
                if generic_name and not generic_name.startswith("'"):
                    generic_params.append(generic_name)

        return generic_params, lifetime_params

    def get_trait_hierarchy(self, traits: List[TraitInfo]) -> Dict[str, Set[str]]:
        """Build a trait hierarchy from trait definitions."""
        hierarchy = {}

        for trait in traits:
            hierarchy[trait.name] = set(trait.supertraits)

        # Compute transitive closure
        changed = True
        while changed:
            changed = False
            for trait_name, supertraits in hierarchy.items():
                new_supertraits = set(supertraits)
                for supertrait in list(supertraits):
                    if supertrait in hierarchy:
                        new_supertraits.update(hierarchy[supertrait])
                if new_supertraits != supertraits:
                    hierarchy[trait_name] = new_supertraits
                    changed = True

        return hierarchy

    def find_associated_type_projections(self, content: str) -> List[Dict[str, any]]:
        """Find associated type projections (e.g., T::Item)."""
        projections = []

        # Pattern for associated type projections
        projection_pattern = re.compile(r"(\w+)::(\w+)")

        lines = content.split("\n")
        for i, line in enumerate(lines):
            for match in projection_pattern.finditer(line):
                type_name = match.group(1)
                assoc_type = match.group(2)

                # Filter out module paths
                if type_name[0].isupper():  # Likely a type, not a module
                    projections.append(
                        {
                            "type": type_name,
                            "associated_type": assoc_type,
                            "line_number": i + 1,
                        }
                    )

        return projections
