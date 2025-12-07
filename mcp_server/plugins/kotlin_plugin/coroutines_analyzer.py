"""Coroutines and concurrency analysis for Kotlin code."""

import logging
import re
from typing import Any, Dict, List

import tree_sitter

logger = logging.getLogger(__name__)


class CoroutinesAnalyzer:
    """Analyzes Kotlin coroutines, suspend functions, and concurrency patterns."""

    def __init__(self):
        # Coroutines-related queries
        self.coroutine_queries = {
            "suspend_functions": """
                (function_declaration
                    (modifiers
                        (modifier) @suspend
                        (#eq? @suspend "suspend")
                    )
                    name: (simple_identifier) @suspend.function.name
                    parameters: (function_value_parameters)? @suspend.function.parameters
                    type: (_)? @suspend.function.return.type
                ) @suspend.function
            """,
            "coroutine_builders": """
                (call_expression
                    function: (simple_identifier) @builder.function
                    (#match? @builder.function "(launch|async|runBlocking|withContext)")
                    arguments: (value_arguments) @builder.arguments
                ) @coroutine.builder
            """,
            "flow_operations": """
                (call_expression
                    function: (navigation_expression
                        expression: (_) @flow.receiver
                        (simple_identifier) @flow.operation
                        (#match? @flow.operation "(collect|map|filter|transform|flatMap|zip|combine|merge)")
                    )
                    arguments: (value_arguments)? @flow.arguments
                ) @flow.operation.call
            """,
            "flow_builders": """
                (call_expression
                    function: (simple_identifier) @flow.builder
                    (#match? @flow.builder "(flowOf|flow|asFlow|channelFlow|callbackFlow)")
                    arguments: (value_arguments)? @flow.builder.arguments
                ) @flow.builder.call
            """,
            "coroutine_scope_functions": """
                (call_expression
                    function: (simple_identifier) @scope.function
                    (#match? @scope.function "(coroutineScope|supervisorScope|withTimeout|withTimeoutOrNull)")
                    arguments: (value_arguments) @scope.arguments
                ) @coroutine.scope
            """,
            "dispatchers": """
                (navigation_expression
                    expression: (simple_identifier) @dispatcher.class
                    (#eq? @dispatcher.class "Dispatchers")
                    (simple_identifier) @dispatcher.type
                    (#match? @dispatcher.type "(Main|IO|Default|Unconfined)")
                ) @dispatcher.usage
            """,
            "channel_operations": """
                (call_expression
                    function: (navigation_expression
                        expression: (_) @channel.receiver
                        (simple_identifier) @channel.operation
                        (#match? @channel.operation "(send|receive|trySend|tryReceive|close)")
                    )
                ) @channel.operation.call
            """,
            "channel_builders": """
                (call_expression
                    function: (simple_identifier) @channel.builder
                    (#match? @channel.builder "(Channel|produce|actor)")
                    arguments: (value_arguments)? @channel.arguments
                ) @channel.builder.call
            """,
            "delay_calls": """
                (call_expression
                    function: (simple_identifier) @delay.function
                    (#eq? @delay.function "delay")
                    arguments: (value_arguments
                        (value_argument
                            expression: (_) @delay.time
                        )
                    )
                ) @delay.call
            """,
            "yield_calls": """
                (call_expression
                    function: (simple_identifier) @yield.function
                    (#eq? @yield.function "yield")
                ) @yield.call
            """,
            "cancellation_checks": """
                (call_expression
                    function: (navigation_expression
                        expression: (simple_identifier) @cancellation.context
                        (simple_identifier) @cancellation.method
                        (#match? @cancellation.method "(ensureActive|isActive)")
                    )
                ) @cancellation.check
            """,
            "exception_handling": """
                (try_expression
                    body: (control_structure_body
                        (_) @try.body
                    )
                    (catch_block
                        parameter: (simple_identifier) @catch.parameter
                        type: (user_type
                            (type_identifier) @exception.type
                            (#match? @exception.type "(CancellationException|TimeoutCancellationException)")
                        )?
                        body: (_) @catch.body
                    )
                ) @coroutine.exception.handling
            """,
            "state_flow_usage": """
                (property_declaration
                    (variable_declaration
                        (simple_identifier) @stateflow.property
                    )
                    type: (user_type
                        (type_identifier) @stateflow.type
                        (#match? @stateflow.type "(StateFlow|MutableStateFlow|SharedFlow|MutableSharedFlow)")
                    )
                ) @state.flow.property
            """,
            "hot_flows": """
                (call_expression
                    function: (navigation_expression
                        expression: (_) @hotflow.receiver
                        (simple_identifier) @hotflow.method
                        (#match? @hotflow.method "(shareIn|stateIn)")
                    )
                    arguments: (value_arguments) @hotflow.arguments
                ) @hot.flow.conversion
            """,
            "coroutine_context": """
                (navigation_expression
                    expression: (simple_identifier) @context.receiver
                    (#eq? @context.receiver "coroutineContext")
                    (simple_identifier) @context.property
                ) @coroutine.context.access
            """,
            "job_operations": """
                (call_expression
                    function: (navigation_expression
                        expression: (_) @job.receiver
                        (simple_identifier) @job.operation
                        (#match? @job.operation "(cancel|join|cancelAndJoin|invokeOnCompletion)")
                    )
                ) @job.operation.call
            """,
            "mutex_operations": """
                (call_expression
                    function: (navigation_expression
                        expression: (_) @mutex.receiver
                        (simple_identifier) @mutex.operation
                        (#match? @mutex.operation "(withLock|lock|unlock|tryLock)")
                    )
                ) @mutex.operation.call
            """,
            "semaphore_operations": """
                (call_expression
                    function: (navigation_expression
                        expression: (_) @semaphore.receiver
                        (simple_identifier) @semaphore.operation
                        (#match? @semaphore.operation "(withPermit|acquire|release|tryAcquire)")
                    )
                ) @semaphore.operation.call
            """,
            "deferred_operations": """
                (call_expression
                    function: (navigation_expression
                        expression: (_) @deferred.receiver
                        (simple_identifier) @deferred.operation
                        (#match? @deferred.operation "(await|getCompleted|getCompletionExceptionOrNull)")
                    )
                ) @deferred.operation.call
            """,
            "coroutine_annotations": """
                (annotation
                    (user_type
                        (type_identifier) @coroutine.annotation
                        (#match? @coroutine.annotation "(DelicateCoroutinesApi|ExperimentalCoroutinesApi|InternalCoroutinesApi)")
                    )
                ) @coroutine.annotation.usage
            """,
            "flow_collection": """
                (call_expression
                    function: (navigation_expression
                        expression: (_) @flow.source
                        (simple_identifier) @collection.method
                        (#match? @collection.method "(collect|collectLatest|collectIndexed)")
                    )
                    arguments: (value_arguments
                        (value_argument
                            expression: (lambda_literal) @collection.lambda
                        )
                    )
                ) @flow.collection
            """,
        }

        # Patterns for coroutine-related issues
        self.anti_patterns = [
            r"runBlocking\s*\{",  # runBlocking in suspend functions
            r"GlobalScope\.launch",  # GlobalScope usage
            r"Dispatchers\.Main\.immediate",  # Immediate dispatcher misuse
            r"Job\(\)\.cancel\(\)",  # Job cancellation without proper scope
        ]

        # Coroutine best practices patterns
        self.best_practices = [
            r"viewModelScope\.launch",
            r"lifecycleScope\.launch",
            r"withContext\(",
            r"supervisorScope\s*\{",
            r"coroutineScope\s*\{",
            r"flow\s*\{",
            r"\.catch\s*\{",
            r"\.onEach\s*\{",
            r"\.flowOn\(",
        ]

    def analyze(self, tree: tree_sitter.Tree, content: str) -> Dict[str, Any]:
        """Perform comprehensive coroutines analysis."""
        try:
            analysis_result = {
                "suspend_functions": [],
                "coroutine_builders": [],
                "flow_operations": [],
                "channel_operations": [],
                "state_management": [],
                "concurrency_primitives": [],
                "exception_handling": [],
                "performance_patterns": [],
                "anti_patterns": [],
                "best_practices": [],
                "dispatcher_usage": [],
                "cancellation_handling": [],
                "statistics": {},
            }

            lines = content.split("\n")

            # Analyze each coroutine pattern
            for query_name, query_str in self.coroutine_queries.items():
                try:
                    # Use regex-based analysis as fallback
                    pattern_results = self._analyze_pattern_with_regex(query_name, content, lines)
                    self._categorize_coroutine_results(query_name, pattern_results, analysis_result)
                except Exception as e:
                    logger.debug(f"Query {query_name} failed: {e}")

            # Analyze anti-patterns
            analysis_result["anti_patterns"] = self._analyze_anti_patterns(content, lines)

            # Analyze best practices
            analysis_result["best_practices"] = self._analyze_best_practices(content, lines)

            # Analyze concurrency complexity
            analysis_result["concurrency_complexity"] = self._analyze_concurrency_complexity(
                analysis_result, content
            )

            # Calculate statistics
            analysis_result["statistics"] = self._calculate_coroutine_statistics(analysis_result)

            return analysis_result

        except Exception as e:
            logger.error(f"Error in coroutines analysis: {e}")
            return {"error": str(e)}

    def _analyze_pattern_with_regex(
        self, pattern_name: str, content: str, lines: List[str]
    ) -> List[Dict[str, Any]]:
        """Analyze coroutine patterns using regex."""
        results = []

        # Regex patterns for different coroutine constructs
        regex_patterns = {
            "suspend_functions": r"suspend\s+fun\s+(\w+)",
            "coroutine_builders": r"(launch|async|runBlocking|withContext)\s*\{",
            "flow_operations": r"\.(\w+)\s*\{\s*",  # Flow operations with lambda
            "flow_builders": r"(flowOf|flow|asFlow|channelFlow|callbackFlow)\s*\(",
            "coroutine_scope_functions": r"(coroutineScope|supervisorScope|withTimeout|withTimeoutOrNull)\s*\{",
            "dispatchers": r"Dispatchers\.(Main|IO|Default|Unconfined)",
            "channel_operations": r"\.(\w+)\s*\(",  # Channel operations
            "channel_builders": r"(Channel|produce|actor)\s*\(",
            "delay_calls": r"delay\s*\(\s*(\d+)",
            "yield_calls": r"yield\s*\(\s*\)",
            "cancellation_checks": r"(ensureActive|isActive)\s*\(\s*\)",
            "state_flow_usage": r"(StateFlow|MutableStateFlow|SharedFlow|MutableSharedFlow)<",
            "hot_flows": r"\.(shareIn|stateIn)\s*\(",
            "coroutine_context": r"coroutineContext\[",
            "job_operations": r"\.(cancel|join|cancelAndJoin|invokeOnCompletion)\s*\(",
            "mutex_operations": r"\.(withLock|lock|unlock|tryLock)\s*\(",
            "semaphore_operations": r"\.(withPermit|acquire|release|tryAcquire)\s*\(",
            "deferred_operations": r"\.(await|getCompleted|getCompletionExceptionOrNull)\s*\(",
            "coroutine_annotations": r"@(DelicateCoroutinesApi|ExperimentalCoroutinesApi|InternalCoroutinesApi)",
            "flow_collection": r"\.(collect|collectLatest|collectIndexed)\s*\{",
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
                result.update(self._get_pattern_metadata(pattern_name, match, content, line_num))

                results.append(result)

        return results

    def _get_pattern_metadata(
        self, pattern_name: str, match: re.Match, content: str, line_num: int
    ) -> Dict[str, Any]:
        """Get pattern-specific metadata."""
        metadata = {}

        if pattern_name == "suspend_functions":
            metadata["function_type"] = "suspend"
            metadata["performance_impact"] = "low"

        elif pattern_name == "coroutine_builders":
            builder_type = match.group(1) if match.groups() else "unknown"
            metadata["builder_type"] = builder_type
            metadata["concurrency_level"] = self._assess_concurrency_level(builder_type)

        elif pattern_name == "dispatchers":
            dispatcher_type = match.group(1) if match.groups() else "unknown"
            metadata["dispatcher_type"] = dispatcher_type
            metadata["performance_characteristics"] = self._get_dispatcher_characteristics(
                dispatcher_type
            )

        elif pattern_name == "flow_operations":
            metadata["flow_operation_type"] = (
                "transformation" if match.group(1) in ["map", "filter", "transform"] else "terminal"
            )

        elif pattern_name == "delay_calls":
            delay_time = match.group(1) if match.groups() else "0"
            metadata["delay_ms"] = int(delay_time) if delay_time.isdigit() else 0
            metadata["performance_impact"] = "high" if int(delay_time) > 1000 else "medium"

        elif pattern_name == "state_flow_usage":
            flow_type = match.group(1) if match.groups() else "unknown"
            metadata["flow_type"] = flow_type
            metadata["state_management"] = True

        return metadata

    def _assess_concurrency_level(self, builder_type: str) -> str:
        """Assess the concurrency level of coroutine builders."""
        concurrency_levels = {
            "launch": "fire_and_forget",
            "async": "concurrent_with_result",
            "runBlocking": "blocking",
            "withContext": "context_switching",
        }
        return concurrency_levels.get(builder_type, "unknown")

    def _get_dispatcher_characteristics(self, dispatcher_type: str) -> Dict[str, str]:
        """Get performance characteristics of dispatchers."""
        characteristics = {
            "Main": {
                "type": "ui_thread",
                "use_case": "ui_updates",
                "blocking": "avoid",
            },
            "IO": {
                "type": "thread_pool",
                "use_case": "io_operations",
                "blocking": "acceptable",
            },
            "Default": {
                "type": "cpu_intensive",
                "use_case": "computation",
                "blocking": "avoid",
            },
            "Unconfined": {
                "type": "immediate",
                "use_case": "testing",
                "blocking": "special_case",
            },
        }
        return characteristics.get(dispatcher_type, {"type": "unknown"})

    def _categorize_coroutine_results(
        self,
        pattern_name: str,
        results: List[Dict[str, Any]],
        analysis_result: Dict[str, Any],
    ) -> None:
        """Categorize coroutine pattern results into appropriate analysis categories."""
        category_mapping = {
            "suspend_functions": "suspend_functions",
            "coroutine_builders": "coroutine_builders",
            "flow_operations": "flow_operations",
            "flow_builders": "flow_operations",
            "coroutine_scope_functions": "coroutine_builders",
            "dispatchers": "dispatcher_usage",
            "channel_operations": "channel_operations",
            "channel_builders": "channel_operations",
            "delay_calls": "performance_patterns",
            "yield_calls": "performance_patterns",
            "cancellation_checks": "cancellation_handling",
            "exception_handling": "exception_handling",
            "state_flow_usage": "state_management",
            "hot_flows": "state_management",
            "coroutine_context": "concurrency_primitives",
            "job_operations": "concurrency_primitives",
            "mutex_operations": "concurrency_primitives",
            "semaphore_operations": "concurrency_primitives",
            "deferred_operations": "concurrency_primitives",
            "coroutine_annotations": "performance_patterns",
            "flow_collection": "flow_operations",
        }

        category = category_mapping.get(pattern_name, "performance_patterns")

        for result in results:
            result["type"] = pattern_name
            result["category"] = category
            analysis_result[category].append(result)

    def _analyze_anti_patterns(self, content: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Analyze coroutine anti-patterns."""
        anti_patterns = []

        for pattern in self.anti_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)

            for match in matches:
                line_num = content[: match.start()].count("\n") + 1

                context_start = max(0, line_num - 2)
                context_end = min(len(lines), line_num + 2)
                context = "\n".join(lines[context_start:context_end])

                anti_pattern = {
                    "type": "anti_pattern",
                    "pattern": pattern,
                    "line": line_num,
                    "match": match.group(),
                    "context": context,
                    "severity": self._get_anti_pattern_severity(pattern),
                    "description": self._get_anti_pattern_description(pattern),
                    "recommendation": self._get_anti_pattern_recommendation(pattern),
                }

                anti_patterns.append(anti_pattern)

        return anti_patterns

    def _analyze_best_practices(self, content: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Analyze coroutine best practices usage."""
        best_practices = []

        for pattern in self.best_practices:
            matches = re.finditer(pattern, content, re.MULTILINE)

            for match in matches:
                line_num = content[: match.start()].count("\n") + 1

                context_start = max(0, line_num - 2)
                context_end = min(len(lines), line_num + 2)
                context = "\n".join(lines[context_start:context_end])

                best_practice = {
                    "type": "best_practice",
                    "pattern": pattern,
                    "line": line_num,
                    "match": match.group(),
                    "context": context,
                    "benefit": self._get_best_practice_benefit(pattern),
                }

                best_practices.append(best_practice)

        return best_practices

    def _get_anti_pattern_severity(self, pattern: str) -> str:
        """Get severity level for anti-patterns."""
        severity_map = {
            r"runBlocking\s*\{": "high",
            r"GlobalScope\.launch": "high",
            r"Dispatchers\.Main\.immediate": "medium",
            r"Job\(\)\.cancel\(\)": "medium",
        }
        return severity_map.get(pattern, "medium")

    def _get_anti_pattern_description(self, pattern: str) -> str:
        """Get description for anti-patterns."""
        descriptions = {
            r"runBlocking\s*\{": "runBlocking blocks the current thread and should be avoided in suspend functions",
            r"GlobalScope\.launch": "GlobalScope creates unstructured concurrency and should be avoided",
            r"Dispatchers\.Main\.immediate": "Immediate dispatcher should be used carefully to avoid blocking",
            r"Job\(\)\.cancel\(\)": "Job cancellation without proper scope management",
        }
        return descriptions.get(pattern, "Potential coroutine anti-pattern")

    def _get_anti_pattern_recommendation(self, pattern: str) -> str:
        """Get recommendations for fixing anti-patterns."""
        recommendations = {
            r"runBlocking\s*\{": "Use coroutineScope or other suspending scope functions",
            r"GlobalScope\.launch": "Use structured concurrency with proper scope (viewModelScope, lifecycleScope)",
            r"Dispatchers\.Main\.immediate": "Consider using Dispatchers.Main without immediate",
            r"Job\(\)\.cancel\(\)": "Use structured cancellation with proper parent-child relationship",
        }
        return recommendations.get(pattern, "Review coroutine usage pattern")

    def _get_best_practice_benefit(self, pattern: str) -> str:
        """Get benefits of best practices."""
        benefits = {
            r"viewModelScope\.launch": "Automatic cancellation when ViewModel is cleared",
            r"lifecycleScope\.launch": "Automatic cancellation based on lifecycle",
            r"withContext\(": "Proper context switching for different types of work",
            r"supervisorScope\s*\{": "Independent failure handling for child coroutines",
            r"coroutineScope\s*\{": "Structured concurrency with proper cancellation",
            r"flow\s*\{": "Proper flow builder usage",
            r"\.catch\s*\{": "Exception handling in flow pipelines",
            r"\.onEach\s*\{": "Side-effect handling in flows",
            r"\.flowOn\(": "Proper dispatcher switching for flow operations",
        }
        return benefits.get(pattern, "Good coroutine practice")

    def _analyze_concurrency_complexity(
        self, analysis_result: Dict[str, Any], content: str
    ) -> Dict[str, Any]:
        """Analyze the complexity of concurrent operations."""
        complexity = {
            "concurrent_operations_count": len(analysis_result["coroutine_builders"]),
            "flow_operations_count": len(analysis_result["flow_operations"]),
            "state_management_complexity": len(analysis_result["state_management"]),
            "synchronization_primitives": len(analysis_result["concurrency_primitives"]),
            "overall_complexity": "low",
        }

        # Calculate overall complexity
        total_concurrent_elements = (
            complexity["concurrent_operations_count"]
            + complexity["flow_operations_count"]
            + complexity["state_management_complexity"]
            + complexity["synchronization_primitives"]
        )

        if total_concurrent_elements > 20:
            complexity["overall_complexity"] = "high"
        elif total_concurrent_elements > 10:
            complexity["overall_complexity"] = "medium"
        else:
            complexity["overall_complexity"] = "low"

        # Analyze nested coroutine patterns
        nested_patterns = re.findall(r"launch\s*\{[^}]*launch\s*\{", content)
        complexity["nested_coroutines"] = len(nested_patterns)

        if complexity["nested_coroutines"] > 0:
            complexity["nesting_warning"] = "Nested coroutines detected - consider refactoring"

        return complexity

    def _calculate_coroutine_statistics(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate coroutine usage statistics."""
        stats = {
            "suspend_function_count": len(analysis_result["suspend_functions"]),
            "coroutine_builder_count": len(analysis_result["coroutine_builders"]),
            "flow_operation_count": len(analysis_result["flow_operations"]),
            "channel_operation_count": len(analysis_result["channel_operations"]),
            "state_management_count": len(analysis_result["state_management"]),
            "concurrency_primitive_count": len(analysis_result["concurrency_primitives"]),
            "exception_handling_count": len(analysis_result["exception_handling"]),
            "anti_pattern_count": len(analysis_result["anti_patterns"]),
            "best_practice_count": len(analysis_result["best_practices"]),
            "dispatcher_usage_count": len(analysis_result["dispatcher_usage"]),
            "cancellation_handling_count": len(analysis_result["cancellation_handling"]),
        }

        # Calculate coroutine maturity score
        total_coroutine_usage = (
            stats["suspend_function_count"]
            + stats["coroutine_builder_count"]
            + stats["flow_operation_count"]
        )

        if total_coroutine_usage > 0:
            good_practices = stats["best_practice_count"] + stats["exception_handling_count"]
            bad_practices = stats["anti_pattern_count"]

            stats["maturity_score"] = min(
                100,
                max(
                    0,
                    int(((good_practices - bad_practices) / total_coroutine_usage) * 100),
                ),
            )
        else:
            stats["maturity_score"] = 0

        # Performance impact assessment
        performance_indicators = (
            stats["flow_operation_count"]
            + stats["state_management_count"]
            + stats["concurrency_primitive_count"]
        )

        if performance_indicators > 15:
            stats["performance_impact"] = "high"
        elif performance_indicators > 5:
            stats["performance_impact"] = "medium"
        else:
            stats["performance_impact"] = "low"

        return stats

    def get_coroutine_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        """Generate coroutine usage recommendations."""
        recommendations = []
        stats = analysis_result.get("statistics", {})

        if stats.get("anti_pattern_count", 0) > 0:
            recommendations.append(
                "Address coroutine anti-patterns to improve code quality and performance"
            )

        if (
            stats.get("exception_handling_count", 0) == 0
            and stats.get("coroutine_builder_count", 0) > 0
        ):
            recommendations.append(
                "Add exception handling for coroutines using try-catch or .catch operators"
            )

        if (
            stats.get("cancellation_handling_count", 0) == 0
            and stats.get("coroutine_builder_count", 0) > 3
        ):
            recommendations.append(
                "Implement proper cancellation handling for long-running coroutines"
            )

        if stats.get("maturity_score", 0) < 50:
            recommendations.append(
                "Consider adopting more coroutine best practices for better structured concurrency"
            )

        complexity = analysis_result.get("concurrency_complexity", {})
        if complexity.get("overall_complexity") == "high":
            recommendations.append(
                "Consider simplifying complex concurrent operations or breaking them into smaller functions"
            )

        if complexity.get("nested_coroutines", 0) > 0:
            recommendations.append(
                "Refactor nested coroutines to use structured concurrency patterns"
            )

        return recommendations
