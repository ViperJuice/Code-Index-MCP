"""Java interoperability analysis for Kotlin code."""

import logging
import re
from typing import Any, Dict, List

import tree_sitter

logger = logging.getLogger(__name__)


class JavaInteropAnalyzer:
    """Analyzes Java interoperability patterns and potential issues in Kotlin code."""

    def __init__(self):
        # Java interop related queries
        self.java_interop_queries = {
            "jvm_annotations": """
                (annotation
                    (user_type
                        (type_identifier) @jvm.annotation
                        (#match? @jvm.annotation "(JvmStatic|JvmOverloads|JvmField|JvmName|JvmSynthetic)")
                    )
                    arguments: (value_arguments)? @jvm.annotation.arguments
                ) @jvm.annotation.usage
            """,
            "platform_types": """
                (call_expression
                    function: (navigation_expression
                        expression: (_) @platform.receiver
                        (simple_identifier) @platform.method
                    )
                ) @platform.call
            """,
            "java_imports": """
                (import_header
                    (identifier) @java.import.path
                    (#match? @java.import.path "(java\\.|javax\\.|android\\.)")
                ) @java.import
            """,
            "java_class_usage": """
                (call_expression
                    function: (simple_identifier) @java.class.constructor
                    arguments: (value_arguments) @java.constructor.args
                ) @java.class.instantiation
            """,
            "throws_annotation": """
                (annotation
                    (user_type
                        (type_identifier) @throws.annotation
                        (#eq? @throws.annotation "Throws")
                    )
                    arguments: (value_arguments
                        (value_argument
                            expression: (_) @throws.exception
                        )
                    )
                ) @throws.declaration
            """,
            "jni_calls": """
                (call_expression
                    function: (simple_identifier) @external.function
                    (#match? @external.function "external")
                ) @jni.call
            """,
            "java_collections": """
                (user_type
                    (type_identifier) @java.collection.type
                    (#match? @java.collection.type "(ArrayList|HashMap|HashSet|LinkedList|TreeMap|TreeSet)")
                ) @java.collection.usage
            """,
            "kotlin_collections": """
                (user_type
                    (type_identifier) @kotlin.collection.type
                    (#match? @kotlin.collection.type "(List|Map|Set|MutableList|MutableMap|MutableSet)")
                ) @kotlin.collection.usage
            """,
            "nullable_platform_calls": """
                (call_expression
                    function: (navigation_expression
                        expression: (_) @nullable.platform.receiver
                        "?." @nullable.safe.call
                        (simple_identifier) @nullable.platform.method
                    )
                ) @nullable.platform.call
            """,
            "java_streams": """
                (call_expression
                    function: (navigation_expression
                        expression: (_) @stream.receiver
                        (simple_identifier) @stream.operation
                        (#match? @stream.operation "(stream|parallelStream|collect|filter|map|reduce)")
                    )
                ) @java.stream.usage
            """,
            "kotlin_sequences": """
                (call_expression
                    function: (navigation_expression
                        expression: (_) @sequence.receiver
                        (simple_identifier) @sequence.operation
                        (#match? @sequence.operation "(asSequence|sequenceOf|generateSequence)")
                    )
                ) @kotlin.sequence.usage
            """,
            "java_functional_interfaces": """
                (lambda_literal
                    parameters: (lambda_parameters)? @functional.params
                ) @functional.interface.usage
            """,
            "companion_object_java_access": """
                (companion_object
                    name: (type_identifier)? @companion.name
                    body: (class_body
                        (property_declaration
                            (modifiers
                                (annotation
                                    (user_type
                                        (type_identifier) @jvm.field
                                        (#eq? @jvm.field "JvmField")
                                    )
                                )
                            )
                        )? @companion.jvm.field
                    )
                ) @companion.java.accessible
            """,
            "data_class_java_interop": """
                (class_declaration
                    (modifiers
                        (modifier) @data.modifier
                        (#eq? @data.modifier "data")
                    )
                    name: (type_identifier) @data.class.name
                    primary_constructor: (primary_constructor
                        parameters: (class_parameters) @data.constructor.params
                    )
                ) @data.class.java.interop
            """,
            "object_java_singleton": """
                (object_declaration
                    name: (type_identifier) @object.singleton.name
                ) @object.java.singleton
            """,
            "sealed_class_java_compat": """
                (class_declaration
                    (modifiers
                        (modifier) @sealed.modifier
                        (#eq? @sealed.modifier "sealed")
                    )
                    name: (type_identifier) @sealed.class.name
                ) @sealed.class.java.compat
            """,
            "inline_class_java_interop": """
                (class_declaration
                    (modifiers
                        (modifier) @inline.modifier
                        (#match? @inline.modifier "(inline|value)")
                    )
                    name: (type_identifier) @inline.class.name
                ) @inline.class.java.interop
            """,
            "extension_functions_java": """
                (function_declaration
                    receiver: (function_value_parameters
                        (function_value_parameter
                            type: (_) @extension.receiver.type
                        )
                    )
                    name: (simple_identifier) @extension.function.name
                    (modifiers
                        (annotation
                            (user_type
                                (type_identifier) @jvm.extension.annotation
                                (#match? @jvm.extension.annotation "(JvmStatic|JvmName)")
                            )
                        )
                    )? @extension.jvm.annotations
                ) @extension.function.java.accessible
            """,
            "vararg_java_arrays": """
                (function_value_parameter
                    (modifiers
                        (modifier) @vararg.modifier
                        (#eq? @vararg.modifier "vararg")
                    )
                    name: (simple_identifier) @vararg.param.name
                    type: (_) @vararg.param.type
                ) @vararg.java.arrays
            """,
            "kotlin_properties_java_methods": """
                (property_declaration
                    (modifiers
                        (annotation
                            (user_type
                                (type_identifier) @property.jvm.annotation
                                (#match? @property.jvm.annotation "(JvmField|JvmName)")
                            )
                        )
                    )? @property.jvm.modifiers
                    (variable_declaration
                        (simple_identifier) @property.name
                    )
                    type: (_)? @property.type
                ) @property.java.accessible
            """,
            "default_parameters_java": """
                (function_declaration
                    (modifiers
                        (annotation
                            (user_type
                                (type_identifier) @overloads.annotation
                                (#eq? @overloads.annotation "JvmOverloads")
                            )
                        )
                    )? @function.jvm.overloads
                    name: (simple_identifier) @function.name
                    parameters: (function_value_parameters
                        (function_value_parameter
                            default_value: (_) @param.default.value
                        )* @default.parameters
                    )
                ) @function.default.params.java
            """,
        }

        # Java-specific patterns that might cause issues
        self.interop_issues = [
            r"System\.out\.println",  # Java-style printing
            r"\.equals\(",  # Java equals method usage
            r"\.hashCode\(",  # Java hashCode method usage
            r"\.getClass\(",  # Java getClass method
            r"instanceof\s+",  # Java instanceof instead of is
            r"new\s+\w+\(",  # Java-style constructor calls
            r"\.length\s*(?!\()",  # Java array.length vs Kotlin array.size
        ]

        # Platform type patterns (Java types without nullability info)
        self.platform_type_patterns = [
            r"String\s+\w+\s*=",  # Platform String
            r"List<\w+>\s+\w+\s*=",  # Platform List
            r"Map<\w+,\s*\w+>\s+\w+\s*=",  # Platform Map
            r"Integer\s+\w+\s*=",  # Platform Integer
        ]

        # Collections interop patterns
        self.collections_patterns = [
            r"ArrayList<",
            r"HashMap<",
            r"HashSet<",
            r"LinkedList<",
            r"TreeMap<",
            r"TreeSet<",
            r"Vector<",
            r"Stack<",
        ]

    def analyze(self, tree: tree_sitter.Tree, content: str) -> Dict[str, Any]:
        """Perform comprehensive Java interoperability analysis."""
        try:
            analysis_result = {
                "jvm_annotations": [],
                "java_imports": [],
                "platform_types": [],
                "collection_interop": [],
                "null_safety_issues": [],
                "performance_considerations": [],
                "compatibility_issues": [],
                "best_practices": [],
                "interop_patterns": [],
                "potential_issues": [],
                "statistics": {},
            }

            lines = content.split("\n")

            # Analyze each Java interop pattern
            for query_name, query_str in self.java_interop_queries.items():
                try:
                    # Use regex-based analysis as fallback
                    pattern_results = self._analyze_pattern_with_regex(query_name, content, lines)
                    self._categorize_interop_results(query_name, pattern_results, analysis_result)
                except Exception as e:
                    logger.debug(f"Query {query_name} failed: {e}")

            # Analyze potential interop issues
            analysis_result["potential_issues"] = self._analyze_interop_issues(content, lines)

            # Analyze platform types
            analysis_result["platform_types"].extend(self._analyze_platform_types(content, lines))

            # Analyze collections interop
            analysis_result["collection_interop"].extend(
                self._analyze_collections_interop(content, lines)
            )

            # Analyze null safety in Java interop
            analysis_result["null_safety_issues"] = self._analyze_null_safety_interop(
                content, lines
            )

            # Analyze performance considerations
            analysis_result["performance_considerations"] = self._analyze_performance_interop(
                analysis_result, content
            )

            # Calculate statistics
            analysis_result["statistics"] = self._calculate_interop_statistics(analysis_result)

            return analysis_result

        except Exception as e:
            logger.error(f"Error in Java interop analysis: {e}")
            return {"error": str(e)}

    def _analyze_pattern_with_regex(
        self, pattern_name: str, content: str, lines: List[str]
    ) -> List[Dict[str, Any]]:
        """Analyze Java interop patterns using regex."""
        results = []

        # Regex patterns for different Java interop constructs
        regex_patterns = {
            "jvm_annotations": r"@(JvmStatic|JvmOverloads|JvmField|JvmName|JvmSynthetic)",
            "java_imports": r"import\s+(java\.|javax\.|android\.)[^\s]+",
            "platform_types": r"(\w+)\s*\.\s*(\w+)\s*\(",  # Method calls that might be platform types
            "java_class_usage": r"(\w+)\s*\(",  # Constructor calls
            "throws_annotation": r"@Throws\s*\([^)]+\)",
            "java_collections": r"(ArrayList|HashMap|HashSet|LinkedList|TreeMap|TreeSet)<",
            "kotlin_collections": r"(listOf|mapOf|setOf|mutableListOf|mutableMapOf|mutableSetOf)\s*\(",
            "nullable_platform_calls": r"(\w+)\?\.\w+\(",
            "java_streams": r"\.(stream|parallelStream|collect|filter|map|reduce)\s*\(",
            "kotlin_sequences": r"\.(asSequence|sequenceOf|generateSequence)\s*\(",
            "companion_object_java_access": r"companion\s+object",
            "data_class_java_interop": r"data\s+class\s+(\w+)",
            "object_java_singleton": r"object\s+(\w+)",
            "sealed_class_java_compat": r"sealed\s+class\s+(\w+)",
            "inline_class_java_interop": r"(inline|value)\s+class\s+(\w+)",
            "extension_functions_java": r"fun\s+(\w+\.\w+)\s*\(",
            "vararg_java_arrays": r"vararg\s+(\w+)\s*:\s*(\w+)",
            "kotlin_properties_java_methods": r"(val|var)\s+(\w+)\s*:\s*(\w+)",
            "default_parameters_java": r"fun\s+(\w+)\s*\([^)]*=\s*[^)]+\)",
        }

        if pattern_name in regex_patterns:
            pattern = regex_patterns[pattern_name]
            matches = re.finditer(pattern, content, re.MULTILINE)

            for match in matches:
                line_num = content[: match.start()].count("\n") + 1

                # Get context around the match
                context_start = max(0, line_num - 3)
                context_end = min(len(lines), line_num + 3)
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

                # Add pattern-specific metadata
                result.update(self._get_interop_metadata(pattern_name, match, content, line_num))

                results.append(result)

        return results

    def _get_interop_metadata(
        self, pattern_name: str, match: re.Match, content: str, line_num: int
    ) -> Dict[str, Any]:
        """Get Java interop specific metadata."""
        metadata = {}

        if pattern_name == "jvm_annotations":
            annotation_type = match.group(1) if match.groups() else "unknown"
            metadata["annotation_type"] = annotation_type
            metadata["java_visibility"] = self._get_java_visibility_impact(annotation_type)

        elif pattern_name == "java_imports":
            import_path = match.group(1) if match.groups() else "unknown"
            metadata["import_package"] = import_path
            metadata["compatibility_level"] = self._assess_java_compatibility(import_path)

        elif pattern_name == "java_collections":
            collection_type = match.group(1) if match.groups() else "unknown"
            metadata["collection_type"] = collection_type
            metadata["kotlin_alternative"] = self._get_kotlin_collection_alternative(
                collection_type
            )

        elif pattern_name == "data_class_java_interop":
            _ = match.group(1) if match.groups() else "unknown"
            metadata["java_bean_compatible"] = True
            metadata["generates_methods"] = ["equals", "hashCode", "toString", "copy"]

        elif pattern_name == "object_java_singleton":
            _ = match.group(1) if match.groups() else "unknown"
            metadata["java_singleton_pattern"] = True
            metadata["thread_safe"] = True

        elif pattern_name == "extension_functions_java":
            _ = match.group(1) if match.groups() else "unknown"
            metadata["java_accessible"] = (
                False  # Extension functions not directly accessible from Java
            )
            metadata["utility_class_alternative"] = True

        return metadata

    def _get_java_visibility_impact(self, annotation_type: str) -> str:
        """Get the Java visibility impact of JVM annotations."""
        impacts = {
            "JvmStatic": "static_method_accessible",
            "JvmOverloads": "multiple_overloads_generated",
            "JvmField": "direct_field_access",
            "JvmName": "custom_java_name",
            "JvmSynthetic": "hidden_from_java",
        }
        return impacts.get(annotation_type, "unknown_impact")

    def _assess_java_compatibility(self, import_path: str) -> str:
        """Assess Java compatibility level based on import path."""
        if import_path.startswith("java."):
            return "high"  # Core Java APIs
        elif import_path.startswith("javax."):
            return "medium"  # Java extension APIs
        elif import_path.startswith("android."):
            return "platform_specific"  # Android-specific
        else:
            return "unknown"

    def _get_kotlin_collection_alternative(self, java_collection: str) -> str:
        """Get Kotlin alternative for Java collections."""
        alternatives = {
            "ArrayList": "mutableListOf() or arrayListOf()",
            "HashMap": "mutableMapOf() or hashMapOf()",
            "HashSet": "mutableSetOf() or hashSetOf()",
            "LinkedList": "mutableListOf() (consider ArrayDeque for performance)",
            "TreeMap": "sortedMapOf()",
            "TreeSet": "sortedSetOf()",
        }
        return alternatives.get(java_collection, "Consider Kotlin collections")

    def _categorize_interop_results(
        self,
        pattern_name: str,
        results: List[Dict[str, Any]],
        analysis_result: Dict[str, Any],
    ) -> None:
        """Categorize Java interop pattern results."""
        category_mapping = {
            "jvm_annotations": "jvm_annotations",
            "java_imports": "java_imports",
            "platform_types": "platform_types",
            "java_class_usage": "interop_patterns",
            "throws_annotation": "interop_patterns",
            "java_collections": "collection_interop",
            "kotlin_collections": "best_practices",
            "nullable_platform_calls": "null_safety_issues",
            "java_streams": "performance_considerations",
            "kotlin_sequences": "best_practices",
            "companion_object_java_access": "interop_patterns",
            "data_class_java_interop": "interop_patterns",
            "object_java_singleton": "interop_patterns",
            "sealed_class_java_compat": "compatibility_issues",
            "inline_class_java_interop": "compatibility_issues",
            "extension_functions_java": "compatibility_issues",
            "vararg_java_arrays": "interop_patterns",
            "kotlin_properties_java_methods": "interop_patterns",
            "default_parameters_java": "interop_patterns",
        }

        category = category_mapping.get(pattern_name, "interop_patterns")

        for result in results:
            result["type"] = pattern_name
            result["category"] = category
            analysis_result[category].append(result)

    def _analyze_interop_issues(self, content: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Analyze potential Java interop issues."""
        issues = []

        for pattern in self.interop_issues:
            matches = re.finditer(pattern, content, re.MULTILINE)

            for match in matches:
                line_num = content[: match.start()].count("\n") + 1

                context_start = max(0, line_num - 2)
                context_end = min(len(lines), line_num + 2)
                context = "\n".join(lines[context_start:context_end])

                issue = {
                    "type": "interop_issue",
                    "pattern": pattern,
                    "line": line_num,
                    "match": match.group(),
                    "context": context,
                    "severity": self._get_issue_severity(pattern),
                    "description": self._get_issue_description(pattern),
                    "kotlin_alternative": self._get_kotlin_alternative(pattern),
                }

                issues.append(issue)

        return issues

    def _analyze_platform_types(self, content: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Analyze platform type usage."""
        platform_types = []

        for pattern in self.platform_type_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)

            for match in matches:
                line_num = content[: match.start()].count("\n") + 1

                context_start = max(0, line_num - 2)
                context_end = min(len(lines), line_num + 2)
                context = "\n".join(lines[context_start:context_end])

                platform_type = {
                    "type": "platform_type",
                    "pattern": pattern,
                    "line": line_num,
                    "match": match.group(),
                    "context": context,
                    "risk_level": "medium",
                    "recommendation": "Add explicit nullability annotations or null checks",
                }

                platform_types.append(platform_type)

        return platform_types

    def _analyze_collections_interop(self, content: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Analyze collections interoperability."""
        collection_issues = []

        for pattern in self.collections_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)

            for match in matches:
                line_num = content[: match.start()].count("\n") + 1

                context_start = max(0, line_num - 2)
                context_end = min(len(lines), line_num + 2)
                context = "\n".join(lines[context_start:context_end])

                collection_type = pattern.replace("<", "").replace(">", "")
                kotlin_alternative = self._get_kotlin_collection_alternative(collection_type)

                collection_issue = {
                    "type": "java_collection_usage",
                    "collection_type": collection_type,
                    "line": line_num,
                    "match": match.group(),
                    "context": context,
                    "kotlin_alternative": kotlin_alternative,
                    "performance_impact": self._assess_collection_performance(collection_type),
                }

                collection_issues.append(collection_issue)

        return collection_issues

    def _assess_collection_performance(self, collection_type: str) -> str:
        """Assess performance impact of Java collections."""
        performance_map = {
            "ArrayList": "good",
            "LinkedList": "poor_for_random_access",
            "HashMap": "good",
            "TreeMap": "logarithmic_time",
            "HashSet": "good",
            "TreeSet": "logarithmic_time",
            "Vector": "synchronized_overhead",
            "Stack": "legacy_synchronized",
        }
        return performance_map.get(collection_type, "unknown")

    def _analyze_null_safety_interop(self, content: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Analyze null safety issues in Java interop."""
        null_safety_issues = []

        # Look for Java method calls without null checks
        java_call_pattern = r"(\w+)\.\w+\([^)]*\)(?!\s*\?)"
        matches = re.finditer(java_call_pattern, content, re.MULTILINE)

        for match in matches:
            line_num = content[: match.start()].count("\n") + 1
            line_content = lines[line_num - 1] if line_num <= len(lines) else ""

            # Check if this might be a Java object call
            if any(
                java_indicator in line_content
                for java_indicator in ["import java", "import javax", "import android"]
            ):
                context_start = max(0, line_num - 2)
                context_end = min(len(lines), line_num + 2)
                context = "\n".join(lines[context_start:context_end])

                issue = {
                    "type": "null_safety_risk",
                    "line": line_num,
                    "match": match.group(),
                    "context": context,
                    "risk_level": "medium",
                    "description": "Java method call without null safety check",
                    "recommendation": "Use safe call operator (?.) or add null check",
                }

                null_safety_issues.append(issue)

        return null_safety_issues

    def _analyze_performance_interop(
        self, analysis_result: Dict[str, Any], content: str
    ) -> List[Dict[str, Any]]:
        """Analyze performance considerations in Java interop."""
        performance_issues = []

        # Check for Java streams vs Kotlin sequences
        java_streams = len(
            [
                item
                for item in analysis_result.get("interop_patterns", [])
                if "stream" in item.get("match", "").lower()
            ]
        )
        kotlin_sequences = len(
            [
                item
                for item in analysis_result.get("best_practices", [])
                if "sequence" in item.get("match", "").lower()
            ]
        )

        if java_streams > kotlin_sequences and java_streams > 3:
            performance_issues.append(
                {
                    "type": "performance_consideration",
                    "category": "stream_vs_sequence",
                    "description": "Consider using Kotlin sequences instead of Java streams for better performance",
                    "impact": "medium",
                    "recommendation": "Replace Java streams with Kotlin sequences for lazy evaluation",
                }
            )

        # Check for excessive boxing/unboxing
        boxing_patterns = re.findall(r"(Integer|Double|Float|Long|Boolean)\s*\(", content)
        if len(boxing_patterns) > 5:
            performance_issues.append(
                {
                    "type": "performance_consideration",
                    "category": "boxing_unboxing",
                    "description": "Excessive boxing/unboxing detected",
                    "impact": "medium",
                    "recommendation": "Use Kotlin primitive types where possible",
                }
            )

        return performance_issues

    def _get_issue_severity(self, pattern: str) -> str:
        """Get severity level for interop issues."""
        severity_map = {
            r"System\.out\.println": "low",
            r"\.equals\(": "medium",
            r"\.hashCode\(": "medium",
            r"\.getClass\(": "low",
            r"instanceof\s+": "medium",
            r"new\s+\w+\(": "medium",
            r"\.length\s*(?!\()": "low",
        }
        return severity_map.get(pattern, "medium")

    def _get_issue_description(self, pattern: str) -> str:
        """Get description for interop issues."""
        descriptions = {
            r"System\.out\.println": "Using Java-style printing instead of Kotlin println",
            r"\.equals\(": "Using Java equals method instead of Kotlin == operator",
            r"\.hashCode\(": "Direct hashCode() call, consider Kotlin data classes",
            r"\.getClass\(": "Using Java getClass() instead of Kotlin ::class",
            r"instanceof\s+": "Using Java instanceof instead of Kotlin is operator",
            r"new\s+\w+\(": "Using Java-style constructor call",
            r"\.length\s*(?!\()": "Using Java array.length instead of Kotlin array.size",
        }
        return descriptions.get(pattern, "Java-style usage in Kotlin code")

    def _get_kotlin_alternative(self, pattern: str) -> str:
        """Get Kotlin alternative for Java patterns."""
        alternatives = {
            r"System\.out\.println": "println() or print()",
            r"\.equals\(": "== operator for structural equality",
            r"\.hashCode\(": "data class automatically generates hashCode",
            r"\.getClass\(": "::class.java for Java Class, ::class for KClass",
            r"instanceof\s+": "is operator for type checking",
            r"new\s+\w+\(": "Direct constructor call without new keyword",
            r"\.length\s*(?!\()": ".size property for arrays and collections",
        }
        return alternatives.get(pattern, "Use Kotlin idiomatic equivalent")

    def _calculate_interop_statistics(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate Java interop statistics."""
        stats = {
            "jvm_annotation_count": len(analysis_result["jvm_annotations"]),
            "java_import_count": len(analysis_result["java_imports"]),
            "platform_type_count": len(analysis_result["platform_types"]),
            "collection_interop_count": len(analysis_result["collection_interop"]),
            "null_safety_issue_count": len(analysis_result["null_safety_issues"]),
            "performance_consideration_count": len(analysis_result["performance_considerations"]),
            "compatibility_issue_count": len(analysis_result["compatibility_issues"]),
            "best_practice_count": len(analysis_result["best_practices"]),
            "interop_pattern_count": len(analysis_result["interop_patterns"]),
            "potential_issue_count": len(analysis_result["potential_issues"]),
        }

        # Calculate interop complexity score
        total_interop_usage = (
            stats["java_import_count"]
            + stats["jvm_annotation_count"]
            + stats["interop_pattern_count"]
        )

        if total_interop_usage > 0:
            issue_count = (
                stats["potential_issue_count"]
                + stats["null_safety_issue_count"]
                + stats["compatibility_issue_count"]
            )

            stats["interop_quality_score"] = min(
                100,
                max(
                    0,
                    int(((total_interop_usage - issue_count) / total_interop_usage) * 100),
                ),
            )
        else:
            stats["interop_quality_score"] = 100

        # Assess interop maturity
        if stats["interop_quality_score"] >= 80:
            stats["interop_maturity"] = "high"
        elif stats["interop_quality_score"] >= 60:
            stats["interop_maturity"] = "medium"
        else:
            stats["interop_maturity"] = "low"

        # Java dependency level
        if stats["java_import_count"] > 10:
            stats["java_dependency_level"] = "high"
        elif stats["java_import_count"] > 3:
            stats["java_dependency_level"] = "medium"
        else:
            stats["java_dependency_level"] = "low"

        return stats

    def get_interop_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        """Generate Java interop recommendations."""
        recommendations = []
        stats = analysis_result.get("statistics", {})

        if stats.get("potential_issue_count", 0) > 0:
            recommendations.append("Replace Java-style patterns with Kotlin idiomatic equivalents")

        if stats.get("null_safety_issue_count", 0) > 0:
            recommendations.append("Add null safety annotations or checks for Java interop code")

        if stats.get("platform_type_count", 0) > 0:
            recommendations.append("Explicitly declare nullability for platform types from Java")

        if stats.get("collection_interop_count", 0) > 3:
            recommendations.append("Consider using Kotlin collections instead of Java collections")

        if stats.get("interop_quality_score", 100) < 70:
            recommendations.append(
                "Improve Java interop code quality by addressing compatibility issues"
            )

        if stats.get("java_dependency_level") == "high":
            recommendations.append(
                "Consider reducing Java dependencies where possible to improve Kotlin-native patterns"
            )

        if (
            len(analysis_result.get("jvm_annotations", [])) == 0
            and stats.get("java_import_count", 0) > 0
        ):
            recommendations.append(
                "Consider adding JVM annotations for better Java interoperability"
            )

        return recommendations
