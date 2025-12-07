"""Null safety analysis for Kotlin code."""

import logging
import re
from typing import Any, Dict, List

import tree_sitter

logger = logging.getLogger(__name__)


class NullSafetyAnalyzer:
    """Analyzes Kotlin code for null safety patterns and potential issues."""

    def __init__(self):
        # Null safety related queries
        self.null_safety_queries = {
            "nullable_types": """
                (nullable_type
                    type: (_) @nullable.type
                ) @nullable
            """,
            "safe_calls": """
                (navigation_expression
                    "?." @safe.call.operator
                    expression: (_) @safe.call.target
                ) @safe.call
            """,
            "not_null_assertions": """
                (postfix_expression
                    expression: (_) @not.null.target
                    "!!" @not.null.operator
                ) @not.null.assertion
            """,
            "elvis_operators": """
                (elvis_expression
                    left: (_) @elvis.left
                    "?:" @elvis.operator
                    right: (_) @elvis.right
                ) @elvis
            """,
            "null_checks": """
                (binary_expression
                    left: (_) @null.check.target
                    operator: "!=" @null.check.operator
                    right: (null_literal) @null.literal
                ) @null.check.not.equal
                
                (binary_expression
                    left: (_) @null.check.target
                    operator: "==" @null.check.operator
                    right: (null_literal) @null.literal
                ) @null.check.equal
            """,
            "platform_types": """
                (call_expression
                    function: (navigation_expression
                        expression: (_) @platform.expression
                        (simple_identifier) @platform.method
                    )
                ) @platform.call
            """,
            "lateinit_properties": """
                (property_declaration
                    (modifiers
                        (modifier) @lateinit
                        (#eq? @lateinit "lateinit")
                    )
                    (variable_declaration
                        (simple_identifier) @lateinit.property.name
                    )
                    type: (_)? @lateinit.property.type
                ) @lateinit.property
            """,
            "lazy_properties": """
                (property_declaration
                    (variable_declaration
                        (simple_identifier) @lazy.property.name
                    )
                    (property_delegate
                        "by" @lazy.delegate.keyword
                        expression: (call_expression
                            function: (simple_identifier) @lazy.function
                            (#eq? @lazy.function "lazy")
                        ) @lazy.expression
                    )
                ) @lazy.property
            """,
            "let_scope_functions": """
                (call_expression
                    expression: (navigation_expression
                        expression: (_) @let.receiver
                        "?." @let.safe.call
                        (simple_identifier) @let.function
                        (#eq? @let.function "let")
                    )
                ) @let.safe.call.chain
            """,
            "also_scope_functions": """
                (call_expression
                    expression: (navigation_expression
                        expression: (_) @also.receiver
                        "?." @also.safe.call
                        (simple_identifier) @also.function
                        (#eq? @also.function "also")
                    )
                ) @also.safe.call.chain
            """,
            "run_scope_functions": """
                (call_expression
                    expression: (navigation_expression
                        expression: (_) @run.receiver
                        "?." @run.safe.call
                        (simple_identifier) @run.function
                        (#eq? @run.function "run")
                    )
                ) @run.safe.call.chain
            """,
            "apply_scope_functions": """
                (call_expression
                    expression: (navigation_expression
                        expression: (_) @apply.receiver
                        "?." @apply.safe.call
                        (simple_identifier) @apply.function
                        (#eq? @apply.function "apply")
                    )
                ) @apply.safe.call.chain
            """,
            "null_safety_annotations": """
                (annotation
                    (user_type
                        (type_identifier) @annotation.name
                        (#match? @annotation.name "(Nullable|NonNull|NotNull)")
                    )
                ) @null.safety.annotation
            """,
            "smart_casts": """
                (is_expression
                    expression: (_) @smart.cast.expression
                    type: (_) @smart.cast.type
                ) @smart.cast
            """,
            "safe_cast": """
                (as_expression
                    expression: (_) @safe.cast.expression
                    "as?" @safe.cast.operator
                    type: (_) @safe.cast.type
                ) @safe.cast
            """,
            "unsafe_cast": """
                (as_expression
                    expression: (_) @unsafe.cast.expression
                    "as" @unsafe.cast.operator
                    type: (_) @unsafe.cast.type
                ) @unsafe.cast
            """,
            "null_coalescing_assignment": """
                (assignment
                    left: (_) @assignment.target
                    right: (elvis_expression
                        left: (_) @elvis.check
                        right: (_) @elvis.fallback
                    )
                ) @null.coalescing.assignment
            """,
            "nullable_function_parameters": """
                (function_value_parameter
                    name: (simple_identifier) @param.name
                    type: (nullable_type
                        type: (_) @param.base.type
                    ) @param.nullable.type
                ) @nullable.parameter
            """,
            "nullable_return_types": """
                (function_declaration
                    name: (simple_identifier) @function.name
                    type: (nullable_type
                        type: (_) @return.base.type
                    ) @return.nullable.type
                ) @nullable.return.function
            """,
            "requireNotNull_calls": """
                (call_expression
                    function: (simple_identifier) @require.function
                    (#eq? @require.function "requireNotNull")
                    arguments: (value_arguments
                        (value_argument
                            expression: (_) @require.argument
                        )
                    )
                ) @require.not.null
            """,
            "checkNotNull_calls": """
                (call_expression
                    function: (simple_identifier) @check.function
                    (#eq? @check.function "checkNotNull")
                    arguments: (value_arguments
                        (value_argument
                            expression: (_) @check.argument
                        )
                    )
                ) @check.not.null
            """,
        }

        # Patterns that suggest potential null safety issues
        self.risk_patterns = [
            r"!!\s*\.",  # Multiple not-null assertions chained
            r"as\s+\w+",  # Unsafe casts
            r"\.toInt\(\)",  # Direct conversions without null checks
            r"\.toString\(\)",  # toString() calls on potentially null objects
        ]

        # Java interop patterns that might introduce null safety issues
        self.java_interop_patterns = [
            r"@JvmStatic",
            r"@JvmOverloads",
            r"@JvmField",
            r"@Throws",
            r"java\.",
            r"javax\.",
            r"android\.",
        ]

    def analyze(self, tree: tree_sitter.Tree, content: str) -> Dict[str, Any]:
        """Perform comprehensive null safety analysis."""
        try:
            analysis_result = {
                "nullable_usages": [],
                "safe_call_chains": [],
                "not_null_assertions": [],
                "elvis_operations": [],
                "null_checks": [],
                "potential_risks": [],
                "null_safety_annotations": [],
                "smart_casts": [],
                "lateinit_usage": [],
                "lazy_properties": [],
                "scope_function_chains": [],
                "java_interop_risks": [],
                "statistics": {},
            }

            lines = content.split("\n")

            # Analyze each null safety pattern
            for query_name, query_str in self.null_safety_queries.items():
                try:
                    # Note: This would need access to tree-sitter Kotlin parser
                    # For now, we'll use regex-based analysis as fallback
                    pattern_results = self._analyze_pattern_with_regex(query_name, content, lines)
                    self._categorize_pattern_results(query_name, pattern_results, analysis_result)
                except Exception as e:
                    logger.debug(f"Query {query_name} failed: {e}")

            # Analyze potential risks
            analysis_result["potential_risks"] = self._analyze_null_safety_risks(content, lines)

            # Analyze Java interop risks
            analysis_result["java_interop_risks"] = self._analyze_java_interop_risks(content, lines)

            # Calculate statistics
            analysis_result["statistics"] = self._calculate_null_safety_statistics(analysis_result)

            return analysis_result

        except Exception as e:
            logger.error(f"Error in null safety analysis: {e}")
            return {"error": str(e)}

    def _analyze_pattern_with_regex(
        self, pattern_name: str, content: str, lines: List[str]
    ) -> List[Dict[str, Any]]:
        """Analyze patterns using regex as fallback when tree-sitter is not available."""
        results = []

        # Regex patterns for different null safety constructs
        regex_patterns = {
            "nullable_types": r"(\w+)\?(?:\s*=|\s*,|\s*\))",
            "safe_calls": r"(\w+)\?\.",
            "not_null_assertions": r"(\w+)!!",
            "elvis_operators": r"(\w+)\s*\?\:\s*(\w+)",
            "null_checks": r"(\w+)\s*(!?==?)\s*null",
            "lateinit_properties": r"lateinit\s+var\s+(\w+)",
            "lazy_properties": r"val\s+(\w+)\s+by\s+lazy",
            "let_scope_functions": r"(\w+)\?\.let",
            "also_scope_functions": r"(\w+)\?\.also",
            "run_scope_functions": r"(\w+)\?\.run",
            "apply_scope_functions": r"(\w+)\?\.apply",
            "null_safety_annotations": r"@(Nullable|NonNull|NotNull)",
            "smart_casts": r"(\w+)\s+is\s+(\w+)",
            "safe_cast": r"(\w+)\s+as\?\s+(\w+)",
            "unsafe_cast": r"(\w+)\s+as\s+(\w+)",
            "requireNotNull_calls": r"requireNotNull\(([^)]+)\)",
            "checkNotNull_calls": r"checkNotNull\(([^)]+)\)",
        }

        if pattern_name in regex_patterns:
            pattern = regex_patterns[pattern_name]
            matches = re.finditer(pattern, content, re.MULTILINE)

            for match in matches:
                line_num = content[: match.start()].count("\n") + 1

                # Get context around the match
                context_start = max(0, line_num - 3)
                context_end = min(len(lines), line_num + 2)
                context = "\n".join(lines[context_start:context_end])

                result = {
                    "name": match.group(1) if match.groups() else match.group(),
                    "line": line_num,
                    "column": match.start() - content.rfind("\n", 0, match.start()),
                    "match": match.group(),
                    "context": context,
                    "pattern": pattern_name,
                    "groups": match.groups() if match.groups() else [],
                }

                results.append(result)

        return results

    def _categorize_pattern_results(
        self,
        pattern_name: str,
        results: List[Dict[str, Any]],
        analysis_result: Dict[str, Any],
    ) -> None:
        """Categorize pattern results into appropriate analysis categories."""
        category_mapping = {
            "nullable_types": "nullable_usages",
            "safe_calls": "safe_call_chains",
            "not_null_assertions": "not_null_assertions",
            "elvis_operators": "elvis_operations",
            "null_checks": "null_checks",
            "lateinit_properties": "lateinit_usage",
            "lazy_properties": "lazy_properties",
            "let_scope_functions": "scope_function_chains",
            "also_scope_functions": "scope_function_chains",
            "run_scope_functions": "scope_function_chains",
            "apply_scope_functions": "scope_function_chains",
            "null_safety_annotations": "null_safety_annotations",
            "smart_casts": "smart_casts",
            "safe_cast": "smart_casts",
            "unsafe_cast": "potential_risks",
            "requireNotNull_calls": "null_checks",
            "checkNotNull_calls": "null_checks",
        }

        category = category_mapping.get(pattern_name, "nullable_usages")

        for result in results:
            # Add pattern-specific metadata
            result["type"] = pattern_name
            result["category"] = category

            # Add risk assessment for certain patterns
            if pattern_name in ["not_null_assertions", "unsafe_cast"]:
                result["risk_level"] = "high"
            elif pattern_name in ["nullable_types", "safe_calls"]:
                result["risk_level"] = "low"
            else:
                result["risk_level"] = "medium"

            analysis_result[category].append(result)

    def _analyze_null_safety_risks(self, content: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Analyze potential null safety risks in the code."""
        risks = []

        for pattern in self.risk_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)

            for match in matches:
                line_num = content[: match.start()].count("\n") + 1

                # Get context
                context_start = max(0, line_num - 2)
                context_end = min(len(lines), line_num + 2)
                context = "\n".join(lines[context_start:context_end])

                risk = {
                    "type": "potential_null_safety_risk",
                    "pattern": pattern,
                    "line": line_num,
                    "match": match.group(),
                    "context": context,
                    "risk_level": "medium",
                    "description": self._get_risk_description(pattern),
                }

                risks.append(risk)

        # Check for complex chained operations that might be risky
        complex_chains = re.finditer(r"(\w+)\?\.\w+\?\.\w+", content)
        for match in complex_chains:
            line_num = content[: match.start()].count("\n") + 1

            risk = {
                "type": "complex_null_safe_chain",
                "pattern": "complex_chain",
                "line": line_num,
                "match": match.group(),
                "context": lines[line_num - 1] if line_num <= len(lines) else "",
                "risk_level": "low",
                "description": "Complex null-safe call chain that might be hard to debug",
            }

            risks.append(risk)

        return risks

    def _analyze_java_interop_risks(self, content: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Analyze Java interoperability that might introduce null safety issues."""
        risks = []

        for pattern in self.java_interop_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)

            for match in matches:
                line_num = content[: match.start()].count("\n") + 1

                # Get context
                context_start = max(0, line_num - 2)
                context_end = min(len(lines), line_num + 2)
                context = "\n".join(lines[context_start:context_end])

                risk = {
                    "type": "java_interop_risk",
                    "pattern": pattern,
                    "line": line_num,
                    "match": match.group(),
                    "context": context,
                    "risk_level": "medium",
                    "description": f"Java interop pattern {pattern} may introduce null safety issues",
                }

                risks.append(risk)

        return risks

    def _get_risk_description(self, pattern: str) -> str:
        """Get a description for a risk pattern."""
        descriptions = {
            r"!!\s*\.": "Chained not-null assertions can cause NPE if any link is null",
            r"as\s+\w+": "Unsafe cast can throw ClassCastException",
            r"\.toInt\(\)": "Direct conversion without null check on potentially null string",
            r"\.toString\(\)": "toString() call on potentially null object",
        }

        return descriptions.get(pattern, "Potential null safety issue")

    def _calculate_null_safety_statistics(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate null safety statistics from the analysis."""
        stats = {
            "total_nullable_usages": len(analysis_result["nullable_usages"]),
            "safe_call_count": len(analysis_result["safe_call_chains"]),
            "not_null_assertion_count": len(analysis_result["not_null_assertions"]),
            "elvis_operation_count": len(analysis_result["elvis_operations"]),
            "null_check_count": len(analysis_result["null_checks"]),
            "potential_risk_count": len(analysis_result["potential_risks"]),
            "smart_cast_count": len(analysis_result["smart_casts"]),
            "lateinit_usage_count": len(analysis_result["lateinit_usage"]),
            "lazy_property_count": len(analysis_result["lazy_properties"]),
            "scope_function_count": len(analysis_result["scope_function_chains"]),
            "java_interop_risk_count": len(analysis_result["java_interop_risks"]),
        }

        # Calculate safety score (0-100)
        total_operations = (
            stats["total_nullable_usages"]
            + stats["not_null_assertion_count"]
            + stats["potential_risk_count"]
        )

        if total_operations > 0:
            safe_operations = (
                stats["safe_call_count"]
                + stats["elvis_operation_count"]
                + stats["null_check_count"]
                + stats["smart_cast_count"]
            )

            stats["safety_score"] = min(100, int((safe_operations / total_operations) * 100))
        else:
            stats["safety_score"] = 100

        # Risk level assessment
        if stats["safety_score"] >= 80:
            stats["overall_risk"] = "low"
        elif stats["safety_score"] >= 60:
            stats["overall_risk"] = "medium"
        else:
            stats["overall_risk"] = "high"

        return stats

    def get_null_safety_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        """Generate null safety recommendations based on analysis."""
        recommendations = []
        stats = analysis_result.get("statistics", {})

        if stats.get("not_null_assertion_count", 0) > 5:
            recommendations.append(
                "Consider reducing not-null assertions (!!) and use safe calls (?.) instead"
            )

        if stats.get("potential_risk_count", 0) > 0:
            recommendations.append(
                "Review potential null safety risks and add appropriate null checks"
            )

        if stats.get("java_interop_risk_count", 0) > 0:
            recommendations.append("Add null safety annotations for Java interop code")

        if stats.get("safety_score", 100) < 70:
            recommendations.append(
                "Consider adopting more null-safe patterns like scope functions and safe calls"
            )

        if len(analysis_result.get("scope_function_chains", [])) == 0:
            recommendations.append(
                "Consider using scope functions (let, also, run, apply) for null-safe operations"
            )

        return recommendations
