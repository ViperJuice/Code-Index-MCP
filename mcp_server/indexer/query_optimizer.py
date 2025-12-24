"""Query optimizer for search queries."""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class QueryType(Enum):
    """Types of search queries."""

    EXACT = "exact"
    PHRASE = "phrase"
    FUZZY = "fuzzy"
    BOOLEAN = "boolean"
    PROXIMITY = "proximity"
    WILDCARD = "wildcard"
    REGEX = "regex"


@dataclass
class Query:
    """Represents a parsed search query."""

    raw_query: str
    query_type: QueryType
    terms: List[str]
    filters: Optional[dict] = None
    options: Optional[dict] = None
