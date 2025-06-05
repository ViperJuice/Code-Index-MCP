# Structured Outputs for MCP Code Retrieval and Prompt Generation

## Executive Summary

This analysis examines how structured outputs (JSON Schema, function calling, and tool use schemas) can significantly improve the MCP code retrieval and prompt generation workflow. By implementing structured inputs and outputs, we can reduce ambiguity, improve consistency, and enable more sophisticated multi-step workflows for coding agents.

## Current State Analysis

### Existing Structure in MCP Implementation

The current MCP implementation has foundational structured elements:

1. **Tool Schemas** (`mcp_server/tools/schemas.py`):
   - Well-defined JSON schemas for search operations
   - Parameter validation and type checking
   - Clear documentation for each tool parameter

2. **Prompt Templates** (`mcp_server/prompts/registry.py`):
   - Structured prompt arguments with types and validation
   - Template-based prompt generation
   - Categorization and metadata management

3. **Method Handlers** (`mcp_server/protocol/methods.py`):
   - Structured MCP method routing
   - Parameter schema validation (partial)
   - Standardized response formats

### Current Limitations

1. **Inconsistent Response Formats**: Tool responses lack standardized structure
2. **Limited Metadata**: Search results don't include rich contextual information
3. **No Workflow Chaining**: No structured way to chain operations
4. **Agent Integration**: Current outputs not optimized for agent consumption

## Proposed Structured Output Improvements

### 1. Agent Request Structuring

#### Current Approach
```json
{
  "method": "tools/call",
  "params": {
    "name": "search_code",
    "arguments": {
      "query": "authentication function",
      "file_pattern": "*.py"
    }
  }
}
```

#### Enhanced Structured Request
```json
{
  "method": "tools/call",
  "params": {
    "name": "search_code",
    "arguments": {
      "query": "authentication function",
      "file_pattern": "*.py",
      "search_context": {
        "intent": "code_review",
        "agent_type": "refactoring_agent",
        "workflow_step": "initial_discovery",
        "desired_output_format": "detailed_context"
      },
      "retrieval_options": {
        "include_related_symbols": true,
        "include_dependencies": true,
        "include_usage_examples": true,
        "context_window_lines": 10
      },
      "response_schema": "detailed_search_result_v1"
    }
  }
}
```

### 2. Structured MCP Response Format

#### Enhanced Search Result Schema
```json
{
  "type": "object",
  "properties": {
    "results": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/StructuredSearchResult"
      }
    },
    "metadata": {
      "$ref": "#/definitions/SearchMetadata"
    },
    "workflow_context": {
      "$ref": "#/definitions/WorkflowContext"
    }
  },
  "definitions": {
    "StructuredSearchResult": {
      "type": "object",
      "properties": {
        "symbol_info": {
          "type": "object",
          "properties": {
            "name": {"type": "string"},
            "type": {"enum": ["function", "class", "method", "variable"]},
            "signature": {"type": "string"},
            "docstring": {"type": "string", "nullable": true},
            "line_range": {
              "type": "object",
              "properties": {
                "start": {"type": "integer"},
                "end": {"type": "integer"}
              }
            }
          }
        },
        "context_info": {
          "type": "object",
          "properties": {
            "file_path": {"type": "string"},
            "language": {"type": "string"},
            "full_content": {"type": "string"},
            "imports": {"type": "array", "items": {"type": "string"}},
            "related_symbols": {
              "type": "array",
              "items": {"$ref": "#/definitions/RelatedSymbol"}
            }
          }
        },
        "edit_guidance": {
          "type": "object",
          "properties": {
            "edit_type": {"enum": ["modification", "addition", "refactoring"]},
            "complexity_level": {"enum": ["simple", "moderate", "complex"]},
            "dependencies": {"type": "array", "items": {"type": "string"}},
            "test_requirements": {"type": "boolean"},
            "breaking_change_risk": {"enum": ["low", "medium", "high"]}
          }
        },
        "quality_metrics": {
          "type": "object",
          "properties": {
            "relevance_score": {"type": "number", "minimum": 0, "maximum": 1},
            "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
            "complexity_score": {"type": "integer", "minimum": 1, "maximum": 10}
          }
        }
      }
    },
    "WorkflowContext": {
      "type": "object",
      "properties": {
        "suggested_next_steps": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "step_type": {"type": "string"},
              "tool_name": {"type": "string"},
              "parameters": {"type": "object"},
              "description": {"type": "string"}
            }
          }
        },
        "workflow_state": {"type": "object"},
        "agent_recommendations": {"type": "array", "items": {"type": "string"}}
      }
    }
  }
}
```

### 3. Structured Prompt Generation

#### Enhanced Prompt Request Schema
```json
{
  "method": "prompts/get",
  "params": {
    "name": "code_review_with_context",
    "arguments": {
      "code_context": {
        "file_path": "/path/to/file.py",
        "symbol_name": "authenticate_user",
        "symbol_type": "function",
        "full_content": "...",
        "line_range": {"start": 10, "end": 25}
      },
      "review_focus": {
        "aspects": ["security", "performance", "maintainability"],
        "severity_threshold": "medium",
        "include_suggestions": true
      },
      "output_format": {
        "structure": "markdown",
        "include_code_blocks": true,
        "include_diff_suggestions": true,
        "max_length": 2000
      }
    }
  }
}
```

#### Structured Prompt Response
```json
{
  "result": {
    "prompt_content": "...",
    "metadata": {
      "generated_at": "2025-01-01T12:00:00Z",
      "template_version": "1.2.0",
      "estimated_tokens": 450,
      "complexity_level": "intermediate"
    },
    "structured_sections": {
      "instructions": "Review the following code...",
      "context": "This function handles user authentication...",
      "requirements": [
        "Check for SQL injection vulnerabilities",
        "Verify input validation",
        "Assess error handling"
      ],
      "expected_output_format": {
        "findings": "array of issues",
        "recommendations": "array of improvements",
        "code_suggestions": "diff format"
      }
    },
    "follow_up_prompts": [
      {
        "name": "security_deep_dive",
        "condition": "if security issues found",
        "parameters": {"focus": "security_vulnerabilities"}
      }
    ]
  }
}
```

## Implementation Strategy

### Phase 1: Schema Definitions

```python
# mcp_server/schemas/structured_outputs.py

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

class SearchIntent(str, Enum):
    CODE_REVIEW = "code_review"
    REFACTORING = "refactoring"
    DEBUGGING = "debugging"
    OPTIMIZATION = "optimization"
    TESTING = "testing"

class AgentType(str, Enum):
    CODING_ASSISTANT = "coding_assistant"
    REFACTORING_AGENT = "refactoring_agent"
    TESTING_AGENT = "testing_agent"
    DOCUMENTATION_AGENT = "documentation_agent"

@dataclass
class SearchContext:
    intent: SearchIntent
    agent_type: AgentType
    workflow_step: str
    desired_output_format: str

@dataclass
class RetrievalOptions:
    include_related_symbols: bool = True
    include_dependencies: bool = True
    include_usage_examples: bool = False
    context_window_lines: int = 5
    max_results: int = 10

@dataclass
class SymbolInfo:
    name: str
    type: str
    signature: Optional[str]
    docstring: Optional[str]
    line_range: Dict[str, int]
    scope: Optional[str]

@dataclass
class ContextInfo:
    file_path: str
    language: str
    full_content: str
    imports: List[str]
    related_symbols: List['RelatedSymbol']
    
@dataclass
class EditGuidance:
    edit_type: str
    complexity_level: str
    dependencies: List[str]
    test_requirements: bool
    breaking_change_risk: str

@dataclass
class QualityMetrics:
    relevance_score: float
    confidence_score: float
    complexity_score: int

@dataclass
class StructuredSearchResult:
    symbol_info: SymbolInfo
    context_info: ContextInfo
    edit_guidance: EditGuidance
    quality_metrics: QualityMetrics
```

### Phase 2: Enhanced Tool Handlers

```python
# mcp_server/tools/handlers/structured_search.py

from typing import Dict, Any, List
from ..schemas.structured_outputs import StructuredSearchResult, SearchContext

class StructuredSearchHandler:
    async def search_with_context(
        self, 
        query: str,
        search_context: SearchContext,
        retrieval_options: RetrievalOptions
    ) -> List[StructuredSearchResult]:
        """Enhanced search with structured output."""
        
        # 1. Perform basic search
        basic_results = await self._basic_search(query)
        
        # 2. Enrich with context based on intent
        enriched_results = []
        for result in basic_results:
            structured_result = await self._enrich_result(
                result, search_context, retrieval_options
            )
            enriched_results.append(structured_result)
        
        # 3. Rank based on intent and agent type
        ranked_results = self._rank_for_intent(
            enriched_results, search_context
        )
        
        return ranked_results[:retrieval_options.max_results]
    
    async def _enrich_result(
        self, 
        result: Dict[str, Any], 
        context: SearchContext,
        options: RetrievalOptions
    ) -> StructuredSearchResult:
        """Enrich search result with structured context."""
        
        # Extract symbol information
        symbol_info = await self._extract_symbol_info(result)
        
        # Build context information
        context_info = await self._build_context_info(
            result, options
        )
        
        # Generate edit guidance based on intent
        edit_guidance = self._generate_edit_guidance(
            symbol_info, context.intent
        )
        
        # Calculate quality metrics
        quality_metrics = self._calculate_metrics(
            result, context, symbol_info
        )
        
        return StructuredSearchResult(
            symbol_info=symbol_info,
            context_info=context_info,
            edit_guidance=edit_guidance,
            quality_metrics=quality_metrics
        )
```

### Phase 3: Workflow-Aware Prompts

```python
# mcp_server/prompts/structured_templates.py

from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class StructuredPromptRequest:
    template_name: str
    context_data: Dict[str, Any]
    output_requirements: Dict[str, Any]
    workflow_state: Dict[str, Any]

@dataclass
class StructuredPromptResponse:
    content: str
    metadata: Dict[str, Any]
    structured_sections: Dict[str, Any]
    follow_up_prompts: List[Dict[str, Any]]
    validation_schema: Dict[str, Any]

class StructuredPromptGenerator:
    def __init__(self):
        self.templates = {}
        self.workflow_handlers = {}
    
    async def generate_structured_prompt(
        self, 
        request: StructuredPromptRequest
    ) -> StructuredPromptResponse:
        """Generate prompt with structured output expectations."""
        
        # 1. Get base template
        template = self.templates[request.template_name]
        
        # 2. Apply context-aware enhancements
        enhanced_content = await self._enhance_with_context(
            template, request.context_data
        )
        
        # 3. Add output structure requirements
        structured_content = self._add_output_structure(
            enhanced_content, request.output_requirements
        )
        
        # 4. Generate follow-up workflow steps
        follow_ups = self._generate_follow_up_prompts(
            request.workflow_state, request.template_name
        )
        
        # 5. Create validation schema for expected output
        validation_schema = self._create_output_schema(
            request.output_requirements
        )
        
        return StructuredPromptResponse(
            content=structured_content,
            metadata=self._generate_metadata(request),
            structured_sections=self._extract_sections(structured_content),
            follow_up_prompts=follow_ups,
            validation_schema=validation_schema
        )
```

## Benefits and Impact

### 1. Reduced Ambiguity

**Before**: Agent receives unstructured search results
```json
{
  "results": [
    {
      "file": "/path/file.py",
      "line": 42,
      "snippet": "def auth(user, pass):\n    return True"
    }
  ]
}
```

**After**: Agent receives structured, actionable context
```json
{
  "results": [{
    "symbol_info": {
      "name": "auth",
      "type": "function",
      "signature": "auth(user: str, pass: str) -> bool"
    },
    "edit_guidance": {
      "edit_type": "modification",
      "complexity_level": "moderate",
      "breaking_change_risk": "low"
    },
    "quality_metrics": {
      "relevance_score": 0.95,
      "confidence_score": 0.88
    }
  }]
}
```

### 2. Multi-Step Workflow Support

```python
# Workflow-aware search chain
workflow_steps = [
    {
        "step": "initial_search",
        "tool": "search_code",
        "params": {"query": "authentication", "intent": "security_review"}
    },
    {
        "step": "dependency_analysis", 
        "tool": "analyze_dependencies",
        "params": {"symbols": "${previous.results[*].symbol_info.name}"}
    },
    {
        "step": "generate_review_prompt",
        "tool": "prompts/get",
        "params": {
            "name": "security_review",
            "context": "${previous.structured_results}"
        }
    }
]
```

### 3. Agent-Optimized Responses

```python
# Agent-specific response formatting
agent_optimizations = {
    "refactoring_agent": {
        "include_complexity_metrics": True,
        "include_test_coverage": True,
        "include_dependency_graph": True
    },
    "documentation_agent": {
        "include_public_apis": True,
        "include_examples": True,
        "include_type_annotations": True
    }
}
```

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- Define core structured schemas
- Implement basic structured response format
- Update tool handlers for structured output

### Phase 2: Enhanced Search (Week 3-4)
- Implement context-aware search enrichment
- Add metadata and quality metrics
- Implement intent-based result ranking

### Phase 3: Workflow Integration (Week 5-6)
- Add workflow context to requests/responses
- Implement follow-up step suggestions
- Add workflow state management

### Phase 4: Agent Optimization (Week 7-8)
- Implement agent-specific response formatting
- Add prompt validation schemas
- Implement response caching with structured keys

## Conclusion

Implementing structured outputs will transform the MCP code retrieval and prompt generation workflow from a basic search-and-retrieve system into an intelligent, context-aware platform that can support sophisticated coding agents. The structured approach will reduce ambiguity, enable complex workflows, and provide the rich metadata needed for high-quality agent interactions.

The proposed implementation provides a clear path forward while maintaining backward compatibility with existing tools and methods. The structured schemas will serve as a foundation for future enhancements and integrations with various agent frameworks.