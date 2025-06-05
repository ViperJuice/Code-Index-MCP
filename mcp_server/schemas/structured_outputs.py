"""
Structured output schemas for enhanced MCP code retrieval.

This module defines JSON schemas and data structures for structured
agent-MCP interactions, improving context, reducing ambiguity, and
enabling sophisticated multi-step workflows.
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import json

# =============================================================================
# Enums for Structured Types
# =============================================================================

class SearchIntent(str, Enum):
    """Intent types for code search operations."""
    CODE_REVIEW = "code_review"
    REFACTORING = "refactoring"
    DEBUGGING = "debugging"
    OPTIMIZATION = "optimization"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    SECURITY_AUDIT = "security_audit"
    API_DESIGN = "api_design"


class AgentType(str, Enum):
    """Types of agents that may interact with MCP."""
    CODING_ASSISTANT = "coding_assistant"
    REFACTORING_AGENT = "refactoring_agent"
    TESTING_AGENT = "testing_agent"
    SECURITY_AGENT = "security_agent"
    DOCUMENTATION_AGENT = "documentation_agent"
    CODE_REVIEWER = "code_reviewer"
    ARCHITECTURE_ADVISOR = "architecture_advisor"


class EditType(str, Enum):
    """Types of code edits."""
    MODIFICATION = "modification"
    ADDITION = "addition"
    REFACTORING = "refactoring"
    DELETION = "deletion"
    OPTIMIZATION = "optimization"
    BUG_FIX = "bug_fix"


class ComplexityLevel(str, Enum):
    """Complexity levels for code changes."""
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"


class RiskLevel(str, Enum):
    """Risk levels for code changes."""
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SymbolType(str, Enum):
    """Types of code symbols."""
    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    VARIABLE = "variable"
    CONSTANT = "constant"
    INTERFACE = "interface"
    ENUM = "enum"
    NAMESPACE = "namespace"
    MODULE = "module"


# =============================================================================
# Core Data Structures
# =============================================================================

@dataclass
class SearchContext:
    """Context information for search operations."""
    intent: SearchIntent
    agent_type: AgentType
    workflow_step: str
    desired_output_format: str = "detailed_context"
    session_id: Optional[str] = None
    previous_context: Optional[Dict[str, Any]] = None


@dataclass
class RetrievalOptions:
    """Options for how to retrieve and format results."""
    include_related_symbols: bool = True
    include_dependencies: bool = True
    include_usage_examples: bool = False
    include_tests: bool = False
    include_documentation: bool = True
    context_window_lines: int = 5
    max_results: int = 10
    include_edit_guidance: bool = True
    include_quality_metrics: bool = True
    language_filter: Optional[List[str]] = None
    file_pattern_filter: Optional[str] = None


@dataclass
class LineRange:
    """Represents a range of lines in a file."""
    start: int
    end: int
    
    def __post_init__(self):
        if self.start > self.end:
            raise ValueError("Start line must be <= end line")


@dataclass
class SymbolInfo:
    """Structured information about a code symbol."""
    name: str
    type: SymbolType
    signature: Optional[str] = None
    docstring: Optional[str] = None
    line_range: Optional[LineRange] = None
    scope: Optional[str] = None
    visibility: str = "public"  # public, private, protected, internal
    is_async: bool = False
    is_static: bool = False
    return_type: Optional[str] = None
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    annotations: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RelatedSymbol:
    """Information about a symbol related to the main result."""
    name: str
    type: SymbolType
    relationship: str  # calls, called_by, inherits, implements, uses, etc.
    file_path: str
    line: int
    confidence: float = 1.0


@dataclass
class DependencyInfo:
    """Information about code dependencies."""
    name: str
    type: str  # import, inheritance, composition, etc.
    source: Optional[str] = None
    is_external: bool = False
    version: Optional[str] = None


@dataclass
class FileMetrics:
    """Metrics about a file."""
    lines_of_code: int
    complexity_score: int
    test_coverage: float
    last_modified: Optional[str] = None
    commit_frequency: Optional[int] = None
    maintainability_index: Optional[float] = None


@dataclass
class ContextInfo:
    """Context information for a code location."""
    file_path: str
    language: str
    full_content: str
    imports: List[str] = field(default_factory=list)
    related_symbols: List[RelatedSymbol] = field(default_factory=list)
    dependencies: List[DependencyInfo] = field(default_factory=list)
    file_metrics: Optional[FileMetrics] = None
    surrounding_context: Optional[str] = None
    usage_examples: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class EditGuidance:
    """Guidance for agents on how to edit the code."""
    edit_type: EditType
    complexity_level: ComplexityLevel
    dependencies: List[str] = field(default_factory=list)
    test_requirements: bool = True
    breaking_change_risk: RiskLevel = RiskLevel.LOW
    recommended_approach: str = ""
    prerequisites: List[str] = field(default_factory=list)
    estimated_effort: Optional[str] = None  # hours, days, etc.
    required_expertise: Optional[str] = None


@dataclass
class QualityMetrics:
    """Quality and relevance metrics for search results."""
    relevance_score: float  # 0.0 to 1.0
    confidence_score: float  # 0.0 to 1.0
    complexity_score: int  # 1 to 10
    maintainability_score: float  # 0.0 to 1.0
    test_coverage_score: float = 0.0  # 0.0 to 1.0
    documentation_score: float = 0.0  # 0.0 to 1.0
    
    def __post_init__(self):
        """Validate metric ranges."""
        for score_name in ['relevance_score', 'confidence_score', 'maintainability_score', 
                          'test_coverage_score', 'documentation_score']:
            score = getattr(self, score_name)
            if not 0.0 <= score <= 1.0:
                raise ValueError(f"{score_name} must be between 0.0 and 1.0")
        
        if not 1 <= self.complexity_score <= 10:
            raise ValueError("complexity_score must be between 1 and 10")


@dataclass
class WorkflowSuggestion:
    """Suggested next step in a workflow."""
    step_type: str
    tool_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    priority: int = 5  # 1-10, 10 being highest
    estimated_duration: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not 1 <= self.priority <= 10:
            raise ValueError("Priority must be between 1 and 10")


@dataclass
class StructuredSearchResult:
    """Complete structured search result."""
    symbol_info: SymbolInfo
    context_info: ContextInfo
    edit_guidance: EditGuidance
    quality_metrics: QualityMetrics
    result_id: Optional[str] = None
    timestamp: Optional[str] = None


@dataclass
class SearchMetadata:
    """Metadata about the search operation."""
    query: str
    search_time_ms: int
    total_results: int
    result_confidence: float
    search_strategy: str
    filters_applied: Dict[str, Any] = field(default_factory=dict)
    cache_hit: bool = False


@dataclass
class StructuredSearchResponse:
    """Complete response for a structured search."""
    results: List[StructuredSearchResult]
    metadata: SearchMetadata
    workflow_suggestions: List[WorkflowSuggestion]
    search_context: SearchContext
    next_page_token: Optional[str] = None


# =============================================================================
# Prompt-Related Structures
# =============================================================================

@dataclass
class PromptSection:
    """A section within a structured prompt."""
    name: str
    content: str
    type: str  # instructions, context, requirements, examples, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OutputValidationSchema:
    """Schema for validating prompt outputs."""
    schema_type: str  # json_schema, regex, custom
    schema_definition: Dict[str, Any]
    validation_rules: List[str] = field(default_factory=list)
    error_messages: Dict[str, str] = field(default_factory=dict)


@dataclass
class FollowUpPrompt:
    """Information about a potential follow-up prompt."""
    name: str
    condition: str  # When this follow-up should be triggered
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    priority: int = 5


@dataclass
class PromptMetadata:
    """Metadata about a generated prompt."""
    generated_at: str
    template_version: str
    estimated_tokens: int
    complexity_level: ComplexityLevel
    review_scope: Optional[str] = None
    agent_optimizations: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StructuredPromptResponse:
    """Complete structured prompt response."""
    prompt_content: str
    metadata: PromptMetadata
    structured_sections: List[PromptSection]
    validation_schema: Optional[OutputValidationSchema] = None
    follow_up_prompts: List[FollowUpPrompt] = field(default_factory=list)
    context_variables: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# JSON Schema Definitions
# =============================================================================

def get_structured_search_request_schema() -> Dict[str, Any]:
    """Get JSON schema for structured search requests."""
    return {
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 1},
            "search_context": {
                "type": "object",
                "properties": {
                    "intent": {"enum": [e.value for e in SearchIntent]},
                    "agent_type": {"enum": [e.value for e in AgentType]},
                    "workflow_step": {"type": "string"},
                    "desired_output_format": {"type": "string", "default": "detailed_context"},
                    "session_id": {"type": "string"},
                    "previous_context": {"type": "object"}
                },
                "required": ["intent", "agent_type", "workflow_step"]
            },
            "retrieval_options": {
                "type": "object",
                "properties": {
                    "include_related_symbols": {"type": "boolean", "default": True},
                    "include_dependencies": {"type": "boolean", "default": True},
                    "include_usage_examples": {"type": "boolean", "default": False},
                    "include_tests": {"type": "boolean", "default": False},
                    "context_window_lines": {"type": "integer", "minimum": 0, "maximum": 50, "default": 5},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
                    "language_filter": {"type": "array", "items": {"type": "string"}},
                    "file_pattern_filter": {"type": "string"}
                }
            },
            "response_schema_version": {"type": "string", "default": "v1"}
        },
        "required": ["query", "search_context"]
    }


def get_structured_search_response_schema() -> Dict[str, Any]:
    """Get JSON schema for structured search responses."""
    return {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "symbol_info": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"enum": [e.value for e in SymbolType]},
                                "signature": {"type": "string"},
                                "docstring": {"type": "string"},
                                "line_range": {
                                    "type": "object",
                                    "properties": {
                                        "start": {"type": "integer", "minimum": 1},
                                        "end": {"type": "integer", "minimum": 1}
                                    },
                                    "required": ["start", "end"]
                                },
                                "visibility": {"enum": ["public", "private", "protected", "internal"]}
                            },
                            "required": ["name", "type"]
                        },
                        "context_info": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string"},
                                "language": {"type": "string"},
                                "full_content": {"type": "string"},
                                "imports": {"type": "array", "items": {"type": "string"}},
                                "related_symbols": {"type": "array"}
                            },
                            "required": ["file_path", "language", "full_content"]
                        },
                        "edit_guidance": {
                            "type": "object",
                            "properties": {
                                "edit_type": {"enum": [e.value for e in EditType]},
                                "complexity_level": {"enum": [e.value for e in ComplexityLevel]},
                                "breaking_change_risk": {"enum": [e.value for e in RiskLevel]},
                                "recommended_approach": {"type": "string"}
                            },
                            "required": ["edit_type", "complexity_level", "breaking_change_risk"]
                        },
                        "quality_metrics": {
                            "type": "object",
                            "properties": {
                                "relevance_score": {"type": "number", "minimum": 0, "maximum": 1},
                                "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
                                "complexity_score": {"type": "integer", "minimum": 1, "maximum": 10}
                            },
                            "required": ["relevance_score", "confidence_score", "complexity_score"]
                        }
                    },
                    "required": ["symbol_info", "context_info", "edit_guidance", "quality_metrics"]
                }
            },
            "metadata": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "search_time_ms": {"type": "integer", "minimum": 0},
                    "total_results": {"type": "integer", "minimum": 0},
                    "result_confidence": {"type": "number", "minimum": 0, "maximum": 1}
                },
                "required": ["query", "search_time_ms", "total_results", "result_confidence"]
            },
            "workflow_suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "step_type": {"type": "string"},
                        "tool_name": {"type": "string"},
                        "parameters": {"type": "object"},
                        "description": {"type": "string"},
                        "priority": {"type": "integer", "minimum": 1, "maximum": 10}
                    },
                    "required": ["step_type", "tool_name", "description"]
                }
            }
        },
        "required": ["results", "metadata", "workflow_suggestions"]
    }


def get_structured_prompt_request_schema() -> Dict[str, Any]:
    """Get JSON schema for structured prompt requests."""
    return {
        "type": "object",
        "properties": {
            "template_name": {"type": "string"},
            "context_data": {"type": "object"},
            "output_requirements": {
                "type": "object",
                "properties": {
                    "format": {"enum": ["markdown", "json", "structured_text", "code"]},
                    "max_length": {"type": "integer", "minimum": 100},
                    "include_examples": {"type": "boolean", "default": True},
                    "validation_schema": {"type": "object"}
                }
            },
            "agent_context": {
                "type": "object",
                "properties": {
                    "agent_type": {"enum": [e.value for e in AgentType]},
                    "expertise_level": {"enum": ["beginner", "intermediate", "expert"]},
                    "time_constraint": {"enum": ["urgent", "normal", "flexible"]}
                },
                "required": ["agent_type"]
            }
        },
        "required": ["template_name", "context_data", "agent_context"]
    }


# =============================================================================
# Utility Functions
# =============================================================================

def validate_structured_response(response_data: Dict[str, Any], schema_version: str = "v1") -> bool:
    """Validate a structured response against its schema."""
    # This would implement actual JSON schema validation
    # For now, return True as placeholder
    return True


def serialize_structured_response(response: StructuredSearchResponse) -> str:
    """Serialize a structured response to JSON."""
    def default_serializer(obj):
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)
    
    return json.dumps(response, default=default_serializer, indent=2)


def deserialize_structured_response(json_str: str) -> StructuredSearchResponse:
    """Deserialize a structured response from JSON."""
    # This would implement proper deserialization
    # For now, just parse the JSON
    data = json.loads(json_str)
    # Would need to reconstruct the proper dataclass instances
    return data


# =============================================================================
# Schema Registry
# =============================================================================

SCHEMA_REGISTRY = {
    "structured_search_request_v1": get_structured_search_request_schema(),
    "structured_search_response_v1": get_structured_search_response_schema(),
    "structured_prompt_request_v1": get_structured_prompt_request_schema()
}


def get_schema(schema_name: str) -> Dict[str, Any]:
    """Get a schema by name."""
    if schema_name not in SCHEMA_REGISTRY:
        raise ValueError(f"Unknown schema: {schema_name}")
    return SCHEMA_REGISTRY[schema_name]


def list_available_schemas() -> List[str]:
    """List all available schemas."""
    return list(SCHEMA_REGISTRY.keys())