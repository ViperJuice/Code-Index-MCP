#!/usr/bin/env python3
"""
Test script for verifying reranking functionality with both Cohere and local models.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from mcp_server.config.settings import RerankingSettings, Settings
from mcp_server.indexer.reranker import (
    CohereReranker,
    HybridReranker,
    LocalCrossEncoderReranker,
    RerankerFactory,
    TFIDFReranker,
)
from mcp_server.interfaces.plugin_interfaces import SearchResult

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_test_results() -> List[SearchResult]:
    """Create sample search results for testing."""
    return [
        SearchResult(
            file_path="/app/src/auth/login.py",
            line=42,
            column=0,
            snippet="def authenticate_user(username: str, password: str) -> User:",
            match_type="exact",
            score=0.85,
            context="Authenticates a user with username and password",
        ),
        SearchResult(
            file_path="/app/docs/auth_guide.md",
            line=15,
            column=0,
            snippet="## User Authentication\n\nThe authentication system uses JWT tokens...",
            match_type="semantic",
            score=0.75,
            context="Documentation about user authentication",
        ),
        SearchResult(
            file_path="/app/src/models/user.py",
            line=10,
            column=0,
            snippet="class User(BaseModel):\n    username: str\n    email: str",
            match_type="exact",
            score=0.65,
            context="User model class",
        ),
        SearchResult(
            file_path="/app/tests/test_auth.py",
            line=25,
            column=0,
            snippet="def test_user_login():\n    # Test user authentication",
            match_type="fuzzy",
            score=0.60,
            context="Test function for user login",
        ),
        SearchResult(
            file_path="/app/src/utils/password.py",
            line=5,
            column=0,
            snippet="def hash_password(password: str) -> str:",
            match_type="exact",
            score=0.55,
            context="Hashes a password using bcrypt",
        ),
    ]


async def test_cohere_reranker():
    """Test Cohere reranker functionality."""
    logger.info("Testing Cohere Reranker...")

    # Check if API key is available
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        logger.warning("COHERE_API_KEY not set, skipping Cohere tests")
        return

    config = {"cohere_api_key": api_key, "model": "rerank-english-v2.0"}

    reranker = CohereReranker(config)

    # Initialize
    init_result = await reranker.initialize(config)
    if not init_result.is_success:
        logger.error(f"Failed to initialize Cohere reranker: {init_result.error}")
        return

    # Test reranking
    query = "user authentication login"
    results = create_test_results()

    rerank_result = await reranker.rerank(query, results, top_k=3)

    if rerank_result.is_success:
        logger.info("Cohere reranking successful!")
        for i, rr in enumerate(rerank_result.data):
            logger.info(
                f"  {i+1}. {rr.original_result.file_path} "
                f"(score: {rr.rerank_score:.3f}, original rank: {rr.original_rank+1})"
            )
    else:
        logger.error(f"Cohere reranking failed: {rerank_result.error}")

    await reranker.shutdown()


async def test_cross_encoder_reranker():
    """Test local cross-encoder reranker functionality."""
    logger.info("\nTesting Cross-Encoder Reranker...")

    config = {"model": "cross-encoder/ms-marco-MiniLM-L-6-v2", "device": "cpu"}

    reranker = LocalCrossEncoderReranker(config)

    # Initialize
    init_result = await reranker.initialize(config)
    if not init_result.is_success:
        logger.error(f"Failed to initialize cross-encoder: {init_result.error}")
        logger.info("You may need to install: pip install sentence-transformers")
        return

    # Test reranking
    query = "user authentication login"
    results = create_test_results()

    rerank_result = await reranker.rerank(query, results, top_k=3)

    if rerank_result.is_success:
        logger.info("Cross-encoder reranking successful!")
        for i, rr in enumerate(rerank_result.data):
            logger.info(
                f"  {i+1}. {rr.original_result.file_path} "
                f"(score: {rr.rerank_score:.3f}, original rank: {rr.original_rank+1})"
            )
    else:
        logger.error(f"Cross-encoder reranking failed: {rerank_result.error}")

    await reranker.shutdown()


async def test_tfidf_reranker():
    """Test TF-IDF reranker functionality."""
    logger.info("\nTesting TF-IDF Reranker...")

    config = {"max_features": 5000}

    reranker = TFIDFReranker(config)

    # Initialize
    init_result = await reranker.initialize(config)
    if not init_result.is_success:
        logger.error(f"Failed to initialize TF-IDF reranker: {init_result.error}")
        logger.info("You may need to install: pip install scikit-learn")
        return

    # Test reranking
    query = "user authentication login"
    results = create_test_results()

    rerank_result = await reranker.rerank(query, results, top_k=3)

    if rerank_result.is_success:
        logger.info("TF-IDF reranking successful!")
        for i, rr in enumerate(rerank_result.data):
            logger.info(
                f"  {i+1}. {rr.original_result.file_path} "
                f"(score: {rr.rerank_score:.3f}, original rank: {rr.original_rank+1})"
            )
    else:
        logger.error(f"TF-IDF reranking failed: {rerank_result.error}")

    await reranker.shutdown()


async def test_hybrid_reranker():
    """Test hybrid reranker functionality."""
    logger.info("\nTesting Hybrid Reranker...")

    config = {
        "primary_type": "tfidf",  # Use TF-IDF as primary since it doesn't need API key
        "fallback_type": "tfidf",
        "weight_primary": 0.7,
        "weight_fallback": 0.3,
    }

    reranker = HybridReranker(config)

    # Create and set sub-rerankers
    primary = TFIDFReranker(config)
    fallback = TFIDFReranker(config)
    reranker.set_rerankers(primary, fallback)

    # Initialize
    init_result = await reranker.initialize(config)
    if not init_result.is_success:
        logger.error(f"Failed to initialize hybrid reranker: {init_result.error}")
        return

    # Test reranking
    query = "user authentication login"
    results = create_test_results()

    rerank_result = await reranker.rerank(query, results, top_k=3)

    if rerank_result.is_success:
        logger.info("Hybrid reranking successful!")
        for i, rr in enumerate(rerank_result.data):
            logger.info(
                f"  {i+1}. {rr.original_result.file_path} "
                f"(score: {rr.rerank_score:.3f}, original rank: {rr.original_rank+1})"
            )
    else:
        logger.error(f"Hybrid reranking failed: {rerank_result.error}")

    await reranker.shutdown()


async def test_reranker_factory():
    """Test reranker factory functionality."""
    logger.info("\nTesting Reranker Factory...")

    factory = RerankerFactory()

    # Test available rerankers
    available = factory.get_available_rerankers()
    logger.info(f"Available rerankers: {', '.join(available)}")

    # Test creating each type
    for reranker_type in ["tfidf", "cross-encoder"]:
        try:
            reranker = factory.create_reranker(reranker_type, {})
            logger.info(f"Created {reranker_type} reranker: {reranker.__class__.__name__}")
            capabilities = reranker.get_capabilities()
            logger.info(f"  Capabilities: {capabilities['name']}")
        except Exception as e:
            logger.error(f"Failed to create {reranker_type} reranker: {e}")


async def test_caching():
    """Test reranking result caching."""
    logger.info("\nTesting Reranking Cache...")

    config = {"cache_ttl": 3600}

    reranker = TFIDFReranker(config)

    # Initialize
    await reranker.initialize(config)

    # First query (cache miss)
    query = "user authentication"
    results = create_test_results()

    import time

    start = time.time()
    result1 = await reranker.rerank(query, results, top_k=3)
    time1 = time.time() - start

    # Second query (should be cached)
    start = time.time()
    result2 = await reranker.rerank(query, results, top_k=3)
    time2 = time.time() - start

    logger.info(f"First query time: {time1:.3f}s")
    logger.info(f"Cached query time: {time2:.3f}s")

    if time2 < time1:
        logger.info("Cache is working! Cached query was faster.")

    await reranker.shutdown()


async def main():
    """Run all reranking tests."""
    logger.info("Starting Reranking Tests...")

    # Test each reranker type
    await test_tfidf_reranker()
    await test_cross_encoder_reranker()
    await test_cohere_reranker()
    await test_hybrid_reranker()

    # Test factory
    await test_reranker_factory()

    # Test caching
    await test_caching()

    logger.info("\nReranking tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
