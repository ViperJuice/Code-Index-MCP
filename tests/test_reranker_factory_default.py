"""Pins RerankerFactory.create_default() against regression."""

import pytest

from mcp_server.indexer.reranker import RerankerFactory, TFIDFReranker


def test_create_default_returns_tfidf():
    reranker = RerankerFactory.create_default()
    assert isinstance(reranker, TFIDFReranker)


def test_create_default_is_classmethod():
    reranker = RerankerFactory.create_default()
    assert reranker is not None


def test_create_default_independent_instances():
    r1 = RerankerFactory.create_default()
    r2 = RerankerFactory.create_default()
    assert r1 is not r2
