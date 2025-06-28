#!/usr/bin/env python3
"""
Edit Pattern Analyzer
Correlates retrieval method quality with Claude Code's editing behavior patterns.
"""

import json
import re
import os
import ast
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
import logging
from collections import defaultdict, Counter
import difflib
from mcp_server.core.path_utils import PathUtils

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.enhanced_mcp_analysis_framework import EditType, RetrievalMethod, RetrievalMethodMetrics, EditBehaviorMetrics

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class EditOperation:
    """Detailed analysis of a single edit operation"""
    operation_id: str
    timestamp: datetime
    edit_type: EditType
    file_path: str
    
    # Edit details
    lines_before: int
    lines_after: int
    lines_added: int
    lines_removed: int
    lines_modified: int
    
    # Context analysis
    function_context: Optional[str] = None
    class_context: Optional[str] = None
    context_lines_used: int = 0
    
    # Precision metrics
    edit_precision_ratio: float = 0.0  # changed_lines / total_lines
    context_efficiency: float = 0.0    # useful_context / total_context
    
    # Related retrieval
    related_retrieval_method: Optional[RetrievalMethod] = None
    retrieval_metadata_quality: float = 0.0
    time_since_search_ms: float = 0.0
    
    # Change analysis
    change_type: str = "unknown"  # "function_modification", "variable_addition", "import_addition", etc.
    complexity_score: float = 0.0
    
    def calculate_precision_ratio(self) -> float:
        """Calculate edit precision ratio"""
        total_changes = self.lines_added + self.lines_removed + self.lines_modified
        if self.lines_before > 0:
            self.edit_precision_ratio = total_changes / self.lines_before
        return self.edit_precision_ratio


@dataclass
class ContextUsagePattern:
    """Analysis of how context is used before editing"""
    context_reads: int = 0
    total_context_lines: int = 0
    relevant_context_lines: int = 0
    context_efficiency: float = 0.0
    
    # Reading patterns
    used_offset_limit: bool = False
    read_entire_files: int = 0
    targeted_reads: int = 0
    
    # Context types
    same_file_context: int = 0
    related_file_context: int = 0
    unrelated_file_context: int = 0
    
    def calculate_efficiency(self) -> float:
        """Calculate context usage efficiency"""
        if self.total_context_lines > 0:
            self.context_efficiency = self.relevant_context_lines / self.total_context_lines
        return self.context_efficiency


@dataclass
class RetrievalEditCorrelation:
    """Correlation between retrieval method and edit behavior"""
    retrieval_method: RetrievalMethod
    schema_used: Optional[str]
    collection_used: Optional[str]
    
    # Retrieval quality metrics
    metadata_quality_score: float = 0.0
    line_numbers_provided: bool = False
    snippets_provided: bool = False
    usage_hints_provided: bool = False
    
    # Resulting edit behavior
    edit_operations: List[EditOperation] = field(default_factory=list)
    context_patterns: ContextUsagePattern = field(default_factory=ContextUsagePattern)
    
    # Performance correlation
    search_to_edit_time_ms: float = 0.0
    edit_success_rate: float = 0.0
    token_efficiency: float = 0.0  # successful_edits / total_tokens


class EditPatternAnalyzer:
    """Analyze patterns in Claude Code's editing behavior"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.edit_operations: List[EditOperation] = []
        self.retrieval_correlations: List[RetrievalEditCorrelation] = []
        self.file_snapshots: Dict[str, List[str]] = {}  # file_path -> lines
        
        # Pattern detection
        self.edit_patterns = {
            "function_modification": [
                r"def\s+\w+",
                r"function\s+\w+",
                r"class\s+\w+.*:.*def",
            ],
            "variable_addition": [
                r"^\s*\w+\s*=",
                r"^\s*var\s+\w+",
                r"^\s*let\s+\w+",
                r"^\s*const\s+\w+"
            ],
            "import_addition": [
                r"^import\s+",
                r"^from\s+.*import",
                r"^#include\s+",
                r"^using\s+"
            ],
            "parameter_addition": [
                r"def\s+\w+\([^)]*\w+[^)]*\):",
                r"function\s+\w+\([^)]*\w+[^)]*\)"
            ],
            "docstring_addition": [
                r'""".*"""',
                r"'''.*'''",
                r"/\*\*.*\*/"
            ]
        }
        
        # File monitoring for real-time edit detection
        self.monitored_files: Set[str] = set()
        
    def capture_file_snapshot(self, file_path: str) -> List[str]:
        """Capture current state of a file"""
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
                self.file_snapshots[file_path] = lines
                return lines
        except Exception as e:
            logger.error(f"Error capturing snapshot of {file_path}: {e}")
            return []
    
    def detect_edit_from_transcript(self, transcript_content: str, file_path: str, 
                                  retrieval_method: RetrievalMethodMetrics) -> Optional[EditOperation]:
        """Detect edit operation from Claude Code transcript"""
        
        # Extract edit details from transcript
        edit_type = self._classify_edit_type(transcript_content)
        if edit_type == EditType.NO_EDIT:
            return None
        
        # Get before/after snapshots
        lines_before = self.file_snapshots.get(file_path, [])
        current_lines = self.capture_file_snapshot(file_path)
        
        # Analyze the changes
        edit_analysis = self._analyze_file_changes(lines_before, current_lines, file_path)
        
        # Create edit operation
        operation = EditOperation(
            operation_id=f"edit_{int(datetime.now().timestamp())}",
            timestamp=datetime.now(),
            edit_type=edit_type,
            file_path=file_path,
            lines_before=len(lines_before),
            lines_after=len(current_lines),
            lines_added=edit_analysis["lines_added"],
            lines_removed=edit_analysis["lines_removed"],
            lines_modified=edit_analysis["lines_modified"],
            function_context=edit_analysis.get("function_context"),
            class_context=edit_analysis.get("class_context"),
            change_type=edit_analysis["change_type"],
            complexity_score=edit_analysis["complexity_score"],
            related_retrieval_method=retrieval_method.method_type,
            retrieval_metadata_quality=retrieval_method.metadata_quality_score
        )
        
        operation.calculate_precision_ratio()
        
        return operation
    
    def _classify_edit_type(self, transcript_content: str) -> EditType:
        """Classify the type of edit from transcript"""
        if "MultiEdit(" in transcript_content:
            return EditType.MULTI_EDIT
        elif "Write(" in transcript_content:
            # Check if it's a full rewrite or append
            if "Read(" in transcript_content and "offset=" not in transcript_content:
                return EditType.FULL_REWRITE
            else:
                return EditType.APPEND_ONLY
        elif "Edit(" in transcript_content:
            return EditType.TARGETED_EDIT
        else:
            return EditType.NO_EDIT
    
    def _analyze_file_changes(self, before_lines: List[str], after_lines: List[str], 
                            file_path: str) -> Dict[str, Any]:
        """Analyze changes between file versions"""
        
        # Calculate line-level changes
        diff = list(difflib.unified_diff(before_lines, after_lines, lineterm=''))
        
        lines_added = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        lines_removed = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
        
        # Calculate modified lines (lines that appear in both add/remove)
        added_content = [line[1:] for line in diff if line.startswith('+') and not line.startswith('+++')]
        removed_content = [line[1:] for line in diff if line.startswith('-') and not line.startswith('---')]
        
        # Simple heuristic for modified lines (similar but not identical)
        lines_modified = 0
        for added_line in added_content:
            for removed_line in removed_content:
                similarity = difflib.SequenceMatcher(None, added_line.strip(), removed_line.strip()).ratio()
                if 0.5 < similarity < 0.95:  # Similar but not identical
                    lines_modified += 1
                    break
        
        # Detect change type
        change_type = self._detect_change_type(after_lines, before_lines)
        
        # Detect context
        function_context = self._extract_function_context(after_lines, diff)
        class_context = self._extract_class_context(after_lines, diff)
        
        # Calculate complexity score
        complexity_score = self._calculate_complexity_score(before_lines, after_lines, change_type)
        
        return {
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "lines_modified": lines_modified,
            "change_type": change_type,
            "function_context": function_context,
            "class_context": class_context,
            "complexity_score": complexity_score
        }
    
    def _detect_change_type(self, after_lines: List[str], before_lines: List[str]) -> str:
        """Detect the type of change made"""
        after_content = '\n'.join(after_lines)
        before_content = '\n'.join(before_lines)
        
        # Check each pattern type
        for change_type, patterns in self.edit_patterns.items():
            for pattern in patterns:
                if re.search(pattern, after_content) and not re.search(pattern, before_content):
                    return change_type
        
        # If no specific pattern detected, classify by lines changed
        total_lines = len(before_lines)
        changed_lines = abs(len(after_lines) - len(before_lines))
        
        if changed_lines == 0:
            return "content_modification"
        elif changed_lines < total_lines * 0.1:
            return "minor_addition"
        elif changed_lines < total_lines * 0.3:
            return "moderate_addition"
        else:
            return "major_rewrite"
    
    def _extract_function_context(self, lines: List[str], diff: List[str]) -> Optional[str]:
        """Extract function context for the edit"""
        # Find changed line numbers from diff
        changed_lines = []
        for line in diff:
            if line.startswith('@@'):
                # Parse line numbers from unified diff header
                match = re.search(r'\+(\d+)', line)
                if match:
                    changed_lines.append(int(match.group(1)))
        
        # Look for function definitions near changed lines
        for line_num in changed_lines:
            if line_num < len(lines):
                # Search backwards for function definition
                for i in range(line_num, max(0, line_num - 20), -1):
                    if i < len(lines):
                        line = lines[i].strip()
                        if re.match(r'def\s+(\w+)', line) or re.match(r'function\s+(\w+)', line):
                            match = re.search(r'(def|function)\s+(\w+)', line)
                            if match:
                                return match.group(2)
        
        return None
    
    def _extract_class_context(self, lines: List[str], diff: List[str]) -> Optional[str]:
        """Extract class context for the edit"""
        # Similar to function context but look for class definitions
        changed_lines = []
        for line in diff:
            if line.startswith('@@'):
                match = re.search(r'\+(\d+)', line)
                if match:
                    changed_lines.append(int(match.group(1)))
        
        for line_num in changed_lines:
            if line_num < len(lines):
                for i in range(line_num, max(0, line_num - 50), -1):
                    if i < len(lines):
                        line = lines[i].strip()
                        if re.match(r'class\s+(\w+)', line):
                            match = re.search(r'class\s+(\w+)', line)
                            if match:
                                return match.group(1)
        
        return None
    
    def _calculate_complexity_score(self, before_lines: List[str], after_lines: List[str], 
                                  change_type: str) -> float:
        """Calculate complexity score for the edit"""
        complexity = 0.0
        
        # Base complexity by change type
        complexity_weights = {
            "function_modification": 0.8,
            "variable_addition": 0.2,
            "import_addition": 0.1,
            "parameter_addition": 0.6,
            "docstring_addition": 0.1,
            "minor_addition": 0.3,
            "moderate_addition": 0.5,
            "major_rewrite": 1.0
        }
        
        complexity += complexity_weights.get(change_type, 0.5)
        
        # Additional complexity factors
        after_content = '\n'.join(after_lines)
        
        # Complex patterns increase score
        if re.search(r'for\s+.*in.*:', after_content):
            complexity += 0.2
        if re.search(r'if\s+.*:', after_content):
            complexity += 0.1
        if re.search(r'try\s*:', after_content):
            complexity += 0.3
        if re.search(r'class\s+\w+.*:', after_content):
            complexity += 0.4
        
        # Normalize to 0-1 range
        return min(complexity, 1.0)
    
    def analyze_context_usage(self, transcript_content: str, edit_operation: EditOperation) -> ContextUsagePattern:
        """Analyze how context was used before the edit"""
        pattern = ContextUsagePattern()
        
        # Extract Read operations from transcript
        read_operations = re.findall(r'Read\([^)]+\)', transcript_content)
        pattern.context_reads = len(read_operations)
        
        # Analyze read patterns
        for read_op in read_operations:
            if "offset=" in read_op and "limit=" in read_op:
                pattern.targeted_reads += 1
                pattern.used_offset_limit = True
                
                # Extract limit to estimate context lines
                limit_match = re.search(r'limit=(\d+)', read_op)
                if limit_match:
                    pattern.total_context_lines += int(limit_match.group(1))
            else:
                pattern.read_entire_files += 1
                # Estimate full file size (this would be more accurate with actual file analysis)
                pattern.total_context_lines += 100  # Average estimate
        
        # Analyze file relationships
        if edit_operation.file_path:
            for read_op in read_operations:
                file_match = re.search(r'file_path=["\']([^"\']+)', read_op)
                if file_match:
                    read_file = file_match.group(1)
                    if read_file == edit_operation.file_path:
                        pattern.same_file_context += 1
                    else:
                        # Simple heuristic for related files
                        if (Path(read_file).parent == Path(edit_operation.file_path).parent or
                            Path(read_file).stem in edit_operation.file_path):
                            pattern.related_file_context += 1
                        else:
                            pattern.unrelated_file_context += 1
        
        # Calculate efficiency (this would be more accurate with actual content analysis)
        # For now, use heuristics based on edit success and context size
        if pattern.total_context_lines > 0:
            # Assume targeted reads are more efficient
            efficiency_bonus = 0.3 if pattern.used_offset_limit else 0.0
            same_file_bonus = 0.2 * (pattern.same_file_context / max(pattern.context_reads, 1))
            pattern.relevant_context_lines = int(pattern.total_context_lines * (0.5 + efficiency_bonus + same_file_bonus))
        
        pattern.calculate_efficiency()
        
        return pattern
    
    def correlate_retrieval_with_edit(self, retrieval_method: RetrievalMethodMetrics,
                                    edit_operation: EditOperation,
                                    context_pattern: ContextUsagePattern,
                                    search_to_edit_time_ms: float) -> RetrievalEditCorrelation:
        """Create correlation between retrieval method and edit behavior"""
        
        correlation = RetrievalEditCorrelation(
            retrieval_method=retrieval_method.method_type,
            schema_used=retrieval_method.schema_used,
            collection_used=retrieval_method.collection_used,
            metadata_quality_score=retrieval_method.metadata_quality_score,
            line_numbers_provided=retrieval_method.line_numbers_available,
            snippets_provided=retrieval_method.snippets_provided,
            usage_hints_provided=retrieval_method.usage_hints_generated,
            search_to_edit_time_ms=search_to_edit_time_ms
        )
        
        correlation.edit_operations = [edit_operation]
        correlation.context_patterns = context_pattern
        
        # Calculate edit success rate (simplified - in real implementation would track errors)
        correlation.edit_success_rate = 1.0 if edit_operation.complexity_score < 0.8 else 0.8
        
        return correlation
    
    def analyze_edit_efficiency_by_method(self) -> Dict[str, Any]:
        """Analyze edit efficiency grouped by retrieval method"""
        method_stats = defaultdict(lambda: {
            "edit_count": 0,
            "avg_precision": 0.0,
            "avg_context_efficiency": 0.0,
            "avg_search_to_edit_time": 0.0,
            "edit_types": Counter(),
            "change_types": Counter(),
            "success_rate": 0.0
        })
        
        for correlation in self.retrieval_correlations:
            method = correlation.retrieval_method.value
            stats = method_stats[method]
            
            # Aggregate edit operations
            for edit_op in correlation.edit_operations:
                stats["edit_count"] += 1
                stats["avg_precision"] += edit_op.edit_precision_ratio
                stats["edit_types"][edit_op.edit_type.value] += 1
                stats["change_types"][edit_op.change_type] += 1
            
            stats["avg_context_efficiency"] += correlation.context_patterns.context_efficiency
            stats["avg_search_to_edit_time"] += correlation.search_to_edit_time_ms
            stats["success_rate"] += correlation.edit_success_rate
        
        # Calculate averages
        for method, stats in method_stats.items():
            if stats["edit_count"] > 0:
                stats["avg_precision"] /= stats["edit_count"]
                stats["avg_context_efficiency"] /= stats["edit_count"]
                stats["avg_search_to_edit_time"] /= stats["edit_count"]
                stats["success_rate"] /= stats["edit_count"]
        
        return dict(method_stats)
    
    def analyze_metadata_quality_impact(self) -> Dict[str, Any]:
        """Analyze how retrieval metadata quality affects edit behavior"""
        quality_buckets = {
            "low": [],     # 0.0 - 0.3
            "medium": [],  # 0.3 - 0.7
            "high": []     # 0.7 - 1.0
        }
        
        for correlation in self.retrieval_correlations:
            quality = correlation.metadata_quality_score
            
            if quality < 0.3:
                bucket = "low"
            elif quality < 0.7:
                bucket = "medium"
            else:
                bucket = "high"
            
            quality_buckets[bucket].append(correlation)
        
        # Analyze each quality bucket
        analysis = {}
        for bucket, correlations in quality_buckets.items():
            if not correlations:
                continue
            
            # Calculate metrics for this quality bucket
            total_edits = sum(len(c.edit_operations) for c in correlations)
            avg_precision = sum(
                sum(op.edit_precision_ratio for op in c.edit_operations) 
                for c in correlations
            ) / max(total_edits, 1)
            
            avg_context_efficiency = sum(c.context_patterns.context_efficiency for c in correlations) / len(correlations)
            avg_search_time = sum(c.search_to_edit_time_ms for c in correlations) / len(correlations)
            
            # Edit type distribution
            edit_types = Counter()
            for c in correlations:
                for op in c.edit_operations:
                    edit_types[op.edit_type.value] += 1
            
            analysis[bucket] = {
                "correlation_count": len(correlations),
                "total_edits": total_edits,
                "avg_edit_precision": avg_precision,
                "avg_context_efficiency": avg_context_efficiency,
                "avg_search_to_edit_time": avg_search_time,
                "edit_type_distribution": dict(edit_types),
                "targeted_edit_percentage": (edit_types["targeted_edit"] / max(total_edits, 1)) * 100
            }
        
        return analysis
    
    def generate_edit_recommendations(self) -> List[str]:
        """Generate recommendations for improving edit efficiency"""
        recommendations = []
        
        method_stats = self.analyze_edit_efficiency_by_method()
        metadata_impact = self.analyze_metadata_quality_impact()
        
        # Find most efficient method
        if method_stats:
            best_method = max(method_stats.items(), key=lambda x: x[1]["avg_precision"])
            recommendations.append(
                f"Use {best_method[0]} retrieval for highest edit precision "
                f"({best_method[1]['avg_precision']:.1%} average precision)"
            )
        
        # Metadata quality recommendations
        if "high" in metadata_impact and "low" in metadata_impact:
            high_quality = metadata_impact["high"]
            low_quality = metadata_impact["low"]
            
            precision_diff = high_quality["avg_edit_precision"] - low_quality["avg_edit_precision"]
            if precision_diff > 0.1:
                recommendations.append(
                    f"Improve retrieval metadata quality - high quality metadata leads to "
                    f"{precision_diff:.1%} better edit precision"
                )
        
        # Context usage recommendations
        avg_context_efficiency = sum(
            c.context_patterns.context_efficiency for c in self.retrieval_correlations
        ) / max(len(self.retrieval_correlations), 1)
        
        if avg_context_efficiency < 0.5:
            recommendations.append(
                "Improve context usage efficiency - currently using only "
                f"{avg_context_efficiency:.1%} of retrieved context effectively"
            )
        
        # Edit type recommendations
        edit_type_counts = Counter()
        for correlation in self.retrieval_correlations:
            for edit_op in correlation.edit_operations:
                edit_type_counts[edit_op.edit_type.value] += 1
        
        total_edits = sum(edit_type_counts.values())
        if total_edits > 0:
            targeted_percentage = (edit_type_counts["targeted_edit"] / total_edits) * 100
            if targeted_percentage < 60:
                recommendations.append(
                    f"Focus on targeted edits - currently only {targeted_percentage:.1f}% "
                    "of edits are targeted (recommended: >60%)"
                )
        
        return recommendations
    
    def save_analysis_results(self, output_path: Path, session_id: str):
        """Save comprehensive edit analysis results"""
        results = {
            "session_id": session_id,
            "analysis_date": datetime.now().isoformat(),
            "total_edit_operations": len(self.edit_operations),
            "total_correlations": len(self.retrieval_correlations),
            
            "method_efficiency": self.analyze_edit_efficiency_by_method(),
            "metadata_quality_impact": self.analyze_metadata_quality_impact(),
            "recommendations": self.generate_edit_recommendations(),
            
            "detailed_operations": [asdict(op) for op in self.edit_operations],
            "detailed_correlations": [asdict(corr) for corr in self.retrieval_correlations]
        }
        
        output_file = output_path / f"edit_pattern_analysis_{session_id}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Saved edit pattern analysis to {output_file}")


def main():
    """Example usage of edit pattern analyzer"""
    workspace = Path("PathUtils.get_workspace_root()")
    session_id = f"edit_analysis_{int(time.time())}"
    
    analyzer = EditPatternAnalyzer(workspace)
    
    logger.info(f"Edit Pattern Analyzer initialized for session {session_id}")
    
    # Example: analyze a hypothetical edit
    # In real usage, this would be integrated with the MCP testing framework
    
    output_dir = Path("edit_analysis_results")
    output_dir.mkdir(exist_ok=True)
    
    # analyzer.save_analysis_results(output_dir, session_id)
    
    return analyzer


if __name__ == "__main__":
    main()