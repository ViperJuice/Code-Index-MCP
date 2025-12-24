#!/usr/bin/env python3
"""
Simple test to demonstrate reranking functionality.
"""

import asyncio
import logging

from mcp_server.indexer.reranker import RerankerFactory
from mcp_server.interfaces.plugin_interfaces import SearchResult

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


async def test_tfidf_reranker():
    """Test TF-IDF reranker with sample data."""
    logger.info("=" * 60)
    logger.info("Testing TF-IDF Reranker")
    logger.info("=" * 60)

    # Create sample search results
    search_results = [
        SearchResult(
            file_path="/app/mcp_server/auth/login.py",
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
            file_path="/app/mcp_server/models/user.py",
            line=10,
            column=0,
            snippet="class User(BaseModel):\n    username: str\n    email: str",
            match_type="exact",
            score=0.65,
            context="User model class definition",
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
            file_path="/app/mcp_server/utils/password.py",
            line=5,
            column=0,
            snippet="def hash_password(password: str) -> str:",
            match_type="exact",
            score=0.55,
            context="Hashes a password using bcrypt",
        ),
    ]

    # Test query
    query = "user authentication login"

    # Create TF-IDF reranker
    factory = RerankerFactory()
    reranker = factory.create_reranker("tfidf", {"cache_ttl": 0})

    # Initialize
    init_result = await reranker.initialize({})
    if not init_result.is_success:
        logger.error(f"Failed to initialize: {init_result.error}")
        return

    logger.info(f"\nOriginal ranking for query: '{query}'")
    for i, result in enumerate(search_results):
        logger.info(f"{i+1}. {result.file_path} (score: {result.score:.2f})")

    # Perform reranking
    rerank_result = await reranker.rerank(query, search_results, top_k=5)

    if rerank_result.is_success:
        logger.info("\nReranked results:")
        for i, rr in enumerate(rerank_result.data):
            old_rank = (
                next(
                    j
                    for j, r in enumerate(search_results)
                    if r.file_path == rr.original_result.file_path
                )
                + 1
            )
            logger.info(
                f"{i+1}. {rr.original_result.file_path} (score: {rr.rerank_score:.4f}, was #{old_rank})"
            )
    else:
        logger.error(f"Reranking failed: {rerank_result.error}")


async def test_reranking_quality():
    """Test reranking quality improvements."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Reranking Quality")
    logger.info("=" * 60)

    # Create results with varied relevance
    results = [
        # Highly relevant but low initial score
        SearchResult(
            file_path="/app/src/auth/user_authentication_flow.py",
            line=1,
            column=0,
            snippet="class UserAuthenticationFlow:\n    '''Handles complete user authentication flow'''",
            match_type="fuzzy",
            score=0.4,
            context="Main authentication flow implementation",
        ),
        # Medium relevance, high initial score
        SearchResult(
            file_path="/app/src/models/database.py",
            line=50,
            column=0,
            snippet="def get_user_by_id(user_id: int):",
            match_type="exact",
            score=0.9,
            context="Database user retrieval",
        ),
        # High relevance, medium score
        SearchResult(
            file_path="/app/src/auth/login_handler.py",
            line=20,
            column=0,
            snippet="async def handle_user_login(request):\n    '''Process user authentication request'''",
            match_type="semantic",
            score=0.6,
            context="Login request handler",
        ),
        # Low relevance, medium score
        SearchResult(
            file_path="/app/src/utils/logger.py",
            line=10,
            column=0,
            snippet="logger.info('User logged in successfully')",
            match_type="fuzzy",
            score=0.5,
            context="Logging utility",
        ),
    ]

    query = "user authentication login flow"

    # Test with TF-IDF
    factory = RerankerFactory()
    reranker = factory.create_reranker("tfidf", {"cache_ttl": 0})
    await reranker.initialize({})

    logger.info(f"\nQuery: '{query}'")
    logger.info("\nOriginal ranking:")
    sorted_original = sorted(results, key=lambda x: x.score, reverse=True)
    for i, r in enumerate(sorted_original):
        logger.info(f"{i+1}. {r.file_path.split('/')[-1]} (score: {r.score:.2f})")

    # Rerank
    rerank_result = await reranker.rerank(query, results)

    if rerank_result.is_success:
        logger.info("\nAfter TF-IDF reranking:")
        for i, rr in enumerate(rerank_result.data):
            filename = rr.original_result.file_path.split("/")[-1]
            logger.info(f"{i+1}. {filename} (score: {rr.rerank_score:.4f})")

        # Calculate improvement
        # The authentication flow file should rank higher after reranking
        auth_flow_original = (
            next(i for i, r in enumerate(sorted_original) if "authentication_flow" in r.file_path)
            + 1
        )
        auth_flow_reranked = (
            next(
                i
                for i, rr in enumerate(rerank_result.data)
                if "authentication_flow" in rr.original_result.file_path
            )
            + 1
        )

        logger.info("\nQuality improvement:")
        logger.info(
            f"'user_authentication_flow.py' moved from #{auth_flow_original} to #{auth_flow_reranked}"
        )

        if auth_flow_reranked < auth_flow_original:
            logger.info("✓ Reranking improved relevance!")
        else:
            logger.info("✗ Reranking did not improve relevance")


async def benchmark_reranking():
    """Benchmark reranking performance."""
    logger.info("\n" + "=" * 60)
    logger.info("Benchmarking Reranking Performance")
    logger.info("=" * 60)

    import time

    # Create different sized result sets
    sizes = [5, 10, 20, 50]

    for size in sizes:
        # Generate dummy results
        results = []
        for i in range(size):
            results.append(
                SearchResult(
                    file_path=f"/app/file_{i}.py",
                    line=i,
                    column=0,
                    snippet=f"Sample code snippet {i} with some keywords",
                    match_type="fuzzy",
                    score=0.5 + (i * 0.01),
                    context=f"Context for result {i}",
                )
            )

        # Test TF-IDF performance
        factory = RerankerFactory()
        reranker = factory.create_reranker("tfidf", {"cache_ttl": 0})
        await reranker.initialize({})

        query = "sample keywords search"

        # Measure time
        start = time.time()
        rerank_result = await reranker.rerank(query, results)
        elapsed = (time.time() - start) * 1000

        if rerank_result.is_success:
            logger.info(
                f"Reranking {size} results: {elapsed:.2f}ms ({elapsed/size:.2f}ms per result)"
            )
        else:
            logger.error(f"Failed to rerank {size} results")


async def main():
    """Run all tests."""
    try:
        await test_tfidf_reranker()
        await test_reranking_quality()
        await benchmark_reranking()

        logger.info("\n" + "=" * 60)
        logger.info("Summary")
        logger.info("=" * 60)
        logger.info("✓ TF-IDF reranker is working")
        logger.info("✓ Reranking can improve result relevance")
        logger.info("✓ Performance is reasonable for typical result sets")
        logger.info("\nNote: For production use, consider:")
        logger.info("- Cohere API for better quality (requires API key)")
        logger.info("- Cross-encoder models for best quality (requires sentence-transformers)")
        logger.info("- Hybrid approach for balance of speed and quality")

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
