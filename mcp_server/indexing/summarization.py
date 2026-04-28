import asyncio
import hashlib
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import mcp.types as types

from ..setup.semantic_preflight import EnrichmentModelResolution, resolve_enrichment_model
from ..storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a concise code documentation assistant. "
    "Respond with exactly 2 sentences summarizing the code chunk: "
    "what it does, its key inputs/parameters, and what it returns or produces."
)

_USER_PROMPT_TEMPLATE = (
    "Describe this {language} code chunk in 2 concise sentences. "
    "Cover: what it does, its inputs/parameters, and what it returns or produces. "
    "Do not repeat the code. Do not output code.\n\n"
    "{parent_context}"
    "{file_context}"
    "Code chunk '{symbol}' (lines {start}-{end}):\n```{language}\n{content}\n```"
)

# Max characters of the surrounding file to include as context (~100k tokens ≈ 400k chars,
# but we keep it conservative to leave room for the chunk itself and the response.
_MAX_FILE_CONTEXT_CHARS = 60_000

# Files larger than this (in characters) skip the single-batch API call and fall back
# to the topological per-chunk path.
_BATCH_FILE_SIZE_THRESHOLD = 400_000


class FileTooLargeError(Exception):
    """Raised when a file exceeds the batch summarization size limit."""


@dataclass(frozen=True)
class SummaryGenerationResult:
    """Structured result for authoritative summary generation."""

    chunks_attempted: int = 0
    summaries_written: int = 0
    authoritative_chunks: int = 0
    missing_chunk_ids: List[str] = field(default_factory=list)
    files_attempted: int = 0
    files_summarized: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunks_attempted": self.chunks_attempted,
            "summaries_written": self.summaries_written,
            "authoritative_chunks": self.authoritative_chunks,
            "missing_chunk_ids": list(self.missing_chunk_ids),
            "files_attempted": self.files_attempted,
            "files_summarized": self.files_summarized,
        }


def _topological_order(chunks: List[Dict]) -> List[str]:
    """Return chunk_ids in topological order — leaves (innermost scopes) first.

    Kahn's algorithm over the parent→child relationship.  Any cycles (rare in
    practice) are appended at the end in their original order.
    """
    chunk_map = {c["chunk_id"]: c for c in chunks}
    children: Dict[str, List[str]] = {cid: [] for cid in chunk_map}
    parent_of: Dict[str, Optional[str]] = {}
    for c in chunks:
        cid = c["chunk_id"]
        pid = c.get("parent_chunk_id")
        parent_of[cid] = pid
        if pid and pid in children:
            children[pid].append(cid)

    in_degree = {
        cid: (1 if parent_of.get(cid) and parent_of[cid] in chunk_map else 0) for cid in chunk_map
    }
    queue: List[str] = [cid for cid, deg in in_degree.items() if deg == 0]
    order: List[str] = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for child in children.get(node, []):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    seen = set(order)
    order.extend(cid for cid in chunk_map if cid not in seen)
    return order


class ChunkWriter:
    """Base interface for semantic chunk summarization.

    Summarization is attempted via three paths in order:
    1. MCP ``sampling/createMessage`` — if the connected client declares
       sampling capability (e.g. Cursor).
    2. BAML ``SummarizeChunkAlone`` — if ``CEREBRAS_API_KEY`` is set.
    3. Direct LLM API — if ``ANTHROPIC_API_KEY`` or ``OPENAI_API_KEY`` is
       set in the environment (works in Claude Code which lacks sampling).
    """

    def __init__(
        self,
        db_path: str,
        qdrant_client: Any,
        session: Any = None,
        client_name: Optional[str] = None,
        summarization_config: Optional[Dict[str, Any]] = None,
    ):
        self.db_path = db_path
        self.qdrant_client = qdrant_client
        self.session = session
        self.client_name = client_name
        self.summarization_config = summarization_config or {}
        self._sqlite_store: Optional[SQLiteStore] = None
        self._profile_model_resolution: Optional[EnrichmentModelResolution] = None

    def _get_sqlite_store(self) -> SQLiteStore:
        if self._sqlite_store is None:
            self._sqlite_store = SQLiteStore(self.db_path)
        return self._sqlite_store

    def _prompt_fingerprint(self) -> str:
        payload = "\n".join(
            [
                _SYSTEM_PROMPT,
                _USER_PROMPT_TEMPLATE,
                str(self.summarization_config.get("base_url", "")),
                str(self.summarization_config.get("model_name", "")),
                str(self.summarization_config.get("profile_id", "")),
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def _resolve_effective_profile_model(self) -> Optional[EnrichmentModelResolution]:
        if not self.summarization_config.get("base_url"):
            return None
        if self._profile_model_resolution is None:
            cfg = self.summarization_config
            self._profile_model_resolution = resolve_enrichment_model(
                base_url=str(cfg["base_url"]),
                configured_model=str(cfg.get("model_name", "gpt-4o-mini")),
                api_key_env=str(cfg.get("api_key_env", "OPENAI_API_KEY")),
                timeout_s=float(cfg.get("timeout_s", 10.0)),
            )
        return self._profile_model_resolution

    def _build_summary_audit_metadata(self, *, model_name: str) -> Dict[str, Any]:
        base_url = self.summarization_config.get("base_url")
        if base_url:
            provider_name = "openai_compatible"
        elif os.environ.get("CEREBRAS_API_KEY"):
            provider_name = "cerebras"
        elif os.environ.get("ANTHROPIC_API_KEY"):
            provider_name = "anthropic"
        elif os.environ.get("OPENAI_API_KEY"):
            provider_name = "openai"
        else:
            provider_name = "mcp_sampling"

        audit_metadata = {
            "provider_name": provider_name,
            "llm_model": model_name,
            "profile_id": self.summarization_config.get("profile_id"),
            "base_url": base_url,
            "prompt_fingerprint": self._prompt_fingerprint(),
        }
        resolution = self._resolve_effective_profile_model()
        if resolution is not None:
            audit_metadata["configured_model_name"] = resolution.configured_model
            audit_metadata["effective_model_name"] = resolution.effective_model
            audit_metadata["model_resolution_strategy"] = resolution.resolution_strategy
            audit_metadata["considered_model_ids"] = list(resolution.available_models)
        return audit_metadata

    def _persist_summary(
        self,
        *,
        chunk_hash: str,
        file_id: int,
        chunk_start: int,
        chunk_end: int,
        symbol: Optional[str],
        summary_text: str,
        model_name: str,
        is_authoritative: bool,
    ) -> bool:
        audit_metadata = self._build_summary_audit_metadata(model_name=model_name)
        return self._get_sqlite_store().store_chunk_summary(
            chunk_hash=chunk_hash,
            file_id=file_id,
            chunk_start=chunk_start,
            chunk_end=chunk_end,
            summary_text=summary_text,
            llm_model=model_name,
            symbol=symbol,
            is_authoritative=is_authoritative,
            provider_name=str(audit_metadata["provider_name"]),
            profile_id=(
                str(audit_metadata["profile_id"]) if audit_metadata.get("profile_id") else None
            ),
            prompt_fingerprint=str(audit_metadata["prompt_fingerprint"]),
            audit_metadata=audit_metadata,
        )

    def _has_sampling_capability(self) -> bool:
        """Return True if the connected MCP client supports sampling/createMessage."""
        if self.session is None:
            return False
        try:
            params = getattr(self.session, "client_params", None)
            caps = params.capabilities if params else None
            return caps is not None and caps.sampling is not None
        except Exception:
            return False

    def _has_direct_api(self) -> bool:
        """Return True if any direct LLM API key or profile endpoint is configured."""
        if self.summarization_config.get("base_url"):
            return True
        return bool(
            os.environ.get("CEREBRAS_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
        )

    def can_summarize(self) -> bool:
        """Return True if any summarization path is available."""
        return self._has_sampling_capability() or self._has_direct_api()

    async def _call_cerebras_api(self, system: str, prompt: str) -> str:
        """Call Cerebras inference API via the openai SDK (OpenAI-compatible)."""
        from openai import AsyncOpenAI

        model = self.summarization_config.get("cerebras_model", "llama3.1-8b")
        client = AsyncOpenAI(
            api_key=os.environ["CEREBRAS_API_KEY"],
            base_url="https://api.cerebras.ai/v1",
        )
        response = await client.chat.completions.create(
            model=model,
            max_tokens=150,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content

    async def _call_anthropic_api(self, system: str, prompt: str) -> str:
        """Call Anthropic API directly via httpx (no SDK required)."""
        import httpx

        api_key = os.environ["ANTHROPIC_API_KEY"]
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.summarization_config.get(
                        "anthropic_model", "claude-haiku-4-5-20251001"
                    ),
                    "max_tokens": 150,
                    "system": system,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]

    async def _call_openai_api(self, system: str, prompt: str) -> str:
        """Call OpenAI API via the openai SDK."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = await client.chat.completions.create(
            model=self.summarization_config.get("openai_model", "gpt-5.4-nano"),
            max_tokens=150,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content

    async def _call_profile_api(self, system: str, prompt: str) -> tuple[str, str]:
        """Call the profile-configured OpenAI-compatible endpoint."""
        from openai import AsyncOpenAI

        cfg = self.summarization_config
        base_url = cfg["base_url"]
        resolution = self._resolve_effective_profile_model()
        model = (
            resolution.effective_model
            if resolution is not None
            else cfg.get("model_name", "gpt-4o-mini")
        )
        api_key_env = cfg.get("api_key_env", "OPENAI_API_KEY")
        api_key = os.environ.get(api_key_env) or "vllm-local"
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        response = await client.chat.completions.create(
            model=model,
            max_tokens=150,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content, model

    async def _call_direct_api(self, system: str, prompt: str) -> tuple[Optional[str], Optional[str]]:
        """Try profile endpoint first, then Cerebras, Anthropic, OpenAI."""
        if self.summarization_config.get("base_url"):
            try:
                return await self._call_profile_api(system, prompt)
            except Exception as exc:
                logger.warning(
                    "Profile summarization endpoint %s failed, falling back to env API: %s",
                    self.summarization_config["base_url"],
                    exc,
                )
        if os.environ.get("CEREBRAS_API_KEY"):
            return await self._call_cerebras_api(system, prompt), None
        elif os.environ.get("ANTHROPIC_API_KEY"):
            return await self._call_anthropic_api(system, prompt), None
        elif os.environ.get("OPENAI_API_KEY"):
            return await self._call_openai_api(system, prompt), None
        return None, None

    def _get_model_name(self) -> str:
        if self.summarization_config.get("model_name"):
            resolution = self._resolve_effective_profile_model()
            if resolution is not None:
                return resolution.effective_model
            return self.summarization_config["model_name"]
        if os.environ.get("CEREBRAS_API_KEY"):
            return self.summarization_config.get("cerebras_model", "llama3.1-8b")
        if os.environ.get("ANTHROPIC_API_KEY"):
            return self.summarization_config.get("anthropic_model", "claude-haiku-4-5-20251001")
        return self.summarization_config.get("openai_model", "gpt-5.4-nano")

    async def summarize_chunk(
        self,
        chunk_hash: str,
        file_id: int,
        chunk_start: int,
        chunk_end: int,
        symbol: str,
        content: str,
        language: str = "unknown",
        parent_context: str = "",
        file_content: str = "",
    ) -> Optional[str]:
        """Generate a summary for a code chunk and persist it to SQLite.

        Tries MCP sampling first; then BAML ``SummarizeChunkAlone`` (Cerebras);
        then falls back to a direct LLM API call (Cerebras → Anthropic → OpenAI).

        *parent_context*: pre-computed summary of the enclosing scope, from
        the topological traversal — improves accuracy for nested symbols.

        *file_content*: the full source file text.  When provided, this is
        injected into the prompt so the model understands the chunk in its
        broader file context — especially valuable for cross-reference and
        import analysis.

        Returns the summary text on success, ``None`` otherwise.
        """
        if not self.can_summarize():
            logger.debug(
                "Skipping summary for '%s': no sampling capability and no API key",
                symbol,
            )
            return None

        # Skip if an authoritative summary already exists.
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT is_authoritative, summary_text FROM chunk_summaries WHERE chunk_hash = ?",
                (chunk_hash,),
            )
            row = cursor.fetchone()
            if row and row[0]:
                return row[1]

        # Prompt without file context — used by MCP sampling (tight token budget).
        sampling_prompt = _USER_PROMPT_TEMPLATE.format(
            language=language,
            parent_context=parent_context,
            file_context="",
            symbol=symbol,
            start=chunk_start,
            end=chunk_end,
            content=content,
        )

        # File context injected for direct API calls (large context window).
        api_file_context = ""
        if file_content:
            trimmed = file_content[:_MAX_FILE_CONTEXT_CHARS]
            if len(file_content) > _MAX_FILE_CONTEXT_CHARS:
                trimmed += "\n... [file truncated for context window]"
            api_file_context = (
                f"Full source file ({language}):\n```{language}\n{trimmed}\n```\n\n"
                f"Now summarize only the following chunk from that file:\n\n"
            )

        # Fallback manual prompt for non-BAML direct API paths.
        api_prompt = _USER_PROMPT_TEMPLATE.format(
            language=language,
            parent_context=parent_context,
            file_context=api_file_context,
            symbol=symbol,
            start=chunk_start,
            end=chunk_end,
            content=content,
        )

        summary_text: Optional[str] = None
        model_name: Optional[str] = None

        # Path 1: MCP sampling (client performs the inference, no file context)
        if self._has_sampling_capability():
            try:
                result = await self.session.create_message(
                    messages=[
                        types.SamplingMessage(
                            role="user",
                            content=types.TextContent(type="text", text=sampling_prompt),
                        )
                    ],
                    system_prompt=_SYSTEM_PROMPT,
                    max_tokens=150,
                )
                content_block = result.content
                if hasattr(content_block, "text"):
                    summary_text = content_block.text
                elif isinstance(content_block, list) and content_block:
                    first = content_block[0]
                    summary_text = getattr(first, "text", str(first))
                else:
                    summary_text = str(content_block)
                model_name = result.model or "mcp-sampling"
            except Exception as exc:
                logger.warning("MCP sampling failed for chunk '%s': %s", symbol, exc)

        # Path 2: BAML SummarizeChunkAlone (Cerebras, cache-friendly prompt structure)
        if summary_text is None and os.environ.get("CEREBRAS_API_KEY"):
            try:
                from mcp_server.indexing.baml_client.baml_client.async_client import b

                result = await b.SummarizeChunkAlone(
                    language=language,
                    symbol=symbol or "unknown",
                    line_start=chunk_start,
                    line_end=chunk_end,
                    content=content or "",
                    parent_context=parent_context or "",
                    file_context=api_file_context,
                )
                summary_text = result.summary
                model_name = self._get_model_name()
            except Exception as exc:
                logger.warning(
                    "BAML SummarizeChunkAlone failed for '%s': %s, falling back to direct API",
                    symbol,
                    exc,
                )

        # Path 3: Direct API fallback (Anthropic / OpenAI raw call, or Cerebras raw)
        if summary_text is None and self._has_direct_api():
            try:
                summary_text, resolved_model_name = await self._call_direct_api(
                    _SYSTEM_PROMPT, api_prompt
                )
                model_name = resolved_model_name or self._get_model_name()
            except Exception as exc:
                logger.warning("Direct API summarization failed for '%s': %s", symbol, exc)

        if summary_text is None:
            return None

        self._persist_summary(
            chunk_hash=chunk_hash,
            file_id=file_id,
            chunk_start=chunk_start,
            chunk_end=chunk_end,
            symbol=symbol,
            summary_text=summary_text,
            model_name=model_name,
            is_authoritative=False,
        )
        logger.info("Stored summary for chunk '%s' via %s", symbol, model_name)
        return summary_text


class FileBatchSummarizer(ChunkWriter):
    """Summarizes all chunks of a file in a single BAML API call.

    For files that exceed ``_BATCH_FILE_SIZE_THRESHOLD`` characters the batch
    call is skipped and a topological per-chunk fallback is used instead
    (same Kahn's-sort logic as ``ComprehensiveChunkWriter``, but operating on
    ``Dict`` rows rather than raw SQL tuples).
    """

    async def _call_batch_api(
        self,
        file_id: int,
        file_path: str,
        file_content: str,
        chunks: List[Dict],
        symbol_map: Dict[int, str],
    ) -> SummaryGenerationResult:
        """Call BAML SummarizeFileChunks for all chunks in a single request.

        Raises ``FileTooLargeError`` when *file_content* exceeds the threshold
        so callers can switch to the per-chunk fallback.
        """
        if len(file_content) > _BATCH_FILE_SIZE_THRESHOLD:
            raise FileTooLargeError(
                f"{file_path} ({len(file_content):,} chars) exceeds batch threshold "
                f"({_BATCH_FILE_SIZE_THRESHOLD:,} chars)"
            )

        from mcp_server.indexing.baml_client.baml_client.async_client import b
        from mcp_server.indexing.baml_client.baml_client.types import ChunkInput

        language = (chunks[0].get("language") or "unknown") if chunks else "unknown"
        chunk_inputs = [
            ChunkInput(
                chunk_id=c["chunk_id"],
                symbol=symbol_map.get(c.get("symbol_id")) or c.get("node_type") or "unknown",
                node_type=c.get("node_type") or "unknown",
                line_start=c.get("line_start") or 1,
                line_end=c.get("line_end") or 1,
                content=c.get("content") or "",
            )
            for c in chunks
        ]

        result = await b.SummarizeFileChunks(
            language=language,
            file_path=file_path,
            file_content=file_content,
            chunks=chunk_inputs,
        )
        return result.summaries

    async def _summarize_topological(
        self,
        file_id: int,
        file_path: str,
        file_content: str,
        chunks: List[Dict],
        symbol_map: Dict[int, str],
    ) -> List[Any]:
        """Per-chunk fallback: summarize in topological order (leaves first)."""
        from mcp_server.indexing.baml_client.baml_client.types import ChunkSummary

        order = _topological_order(chunks)
        chunk_map = {c["chunk_id"]: c for c in chunks}
        stored_summaries: Dict[str, str] = {}
        results: List[Any] = []
        missing_chunk_ids: List[str] = []

        for chunk_id in order:
            c = chunk_map[chunk_id]
            symbol = symbol_map.get(c.get("symbol_id")) or c.get("node_type") or "unknown"

            parent_context = ""
            pid = c.get("parent_chunk_id")
            if pid and pid in stored_summaries:
                parent_chunk = chunk_map.get(pid)
                parent_sym = (
                    (
                        symbol_map.get(parent_chunk.get("symbol_id"))
                        or parent_chunk.get("node_type")
                        or "parent"
                    )
                    if parent_chunk
                    else "parent"
                )
                parent_context = (
                    f"Context from enclosing scope ({parent_sym}): " f"{stored_summaries[pid]}\n\n"
                )

            try:
                summary_text = await self.summarize_chunk(
                    chunk_hash=chunk_id,
                    file_id=file_id,
                    chunk_start=c.get("line_start") or 1,
                    chunk_end=c.get("line_end") or 1,
                    symbol=symbol,
                    content=c.get("content") or "",
                    language=c.get("language") or "unknown",
                    parent_context=parent_context,
                    file_content=file_content,
                )
                if summary_text:
                    stored_summaries[chunk_id] = summary_text
                    results.append(ChunkSummary(chunk_id=chunk_id, summary=summary_text))
                else:
                    missing_chunk_ids.append(chunk_id)
            except Exception as exc:
                logger.error("Failed to summarize chunk %s: %s", chunk_id, exc)
                missing_chunk_ids.append(chunk_id)

        return SummaryGenerationResult(
            chunks_attempted=len(chunks),
            summaries_written=len(results),
            authoritative_chunks=len(results),
            missing_chunk_ids=missing_chunk_ids,
            files_attempted=1,
            files_summarized=1 if results else 0,
        )

    async def summarize_file_chunks(
        self,
        file_id: int,
        file_path: str,
        file_content: str,
        chunks: List[Dict],
        symbol_map: Optional[Dict[int, str]] = None,
        persist: bool = True,
    ) -> SummaryGenerationResult:
        """Summarize all chunks of a file, preferring the batch API path.

        Filters already-authoritative chunks, calls ``_call_batch_api``, and
        handles ``FileTooLargeError`` by delegating to the topological
        per-chunk path.  Persists to ``chunk_summaries`` with
        ``is_authoritative=1`` when *persist* is ``True``.

        Returns a list of ``ChunkSummary`` objects.
        """
        if symbol_map is None:
            symbol_map = {}

        # Filter already-authoritative chunks.
        with sqlite3.connect(self.db_path) as conn:
            auth_hashes = {
                row[0]
                for row in conn.execute(
                    "SELECT chunk_hash FROM chunk_summaries WHERE is_authoritative=1"
                ).fetchall()
            }

        to_summarize = [c for c in chunks if c["chunk_id"] not in auth_hashes]
        if not to_summarize:
            return SummaryGenerationResult(
                chunks_attempted=len(chunks),
                summaries_written=0,
                authoritative_chunks=len(chunks),
                missing_chunk_ids=[],
                files_attempted=1,
                files_summarized=0,
            )

        try:
            summaries = await self._call_batch_api(
                file_id, file_path, file_content, to_summarize, symbol_map
            )
            missing_chunk_ids: List[str] = []
        except FileTooLargeError as exc:
            logger.info("Large-file fallback for %s: %s", file_path, exc)
            result = await self._summarize_topological(
                file_id, file_path, file_content, to_summarize, symbol_map
            )
            return result
        except Exception as exc:
            logger.warning(
                "Batch API failed for %s (%s), falling back to per-chunk path",
                file_path,
                exc,
            )
            result = await self._summarize_topological(
                file_id, file_path, file_content, to_summarize, symbol_map
            )
            return result

        if persist and summaries:
            model_name = self._get_model_name()
            chunk_lookup = {c["chunk_id"]: c for c in to_summarize}
            for s in summaries:
                c = chunk_lookup.get(s.chunk_id)
                if c is None:
                    continue
                sym = symbol_map.get(c.get("symbol_id")) or c.get("node_type") or "unknown"
                self._persist_summary(
                    chunk_hash=s.chunk_id,
                    file_id=file_id,
                    chunk_start=c.get("line_start") or 1,
                    chunk_end=c.get("line_end") or 1,
                    symbol=sym,
                    summary_text=s.summary,
                    model_name=model_name,
                    is_authoritative=True,
                )
            logger.info(
                "FileBatchSummarizer: persisted %d summaries for %s",
                len(summaries),
                file_path,
            )

        summarized_chunk_ids = {s.chunk_id for s in summaries}
        missing_chunk_ids = [
            c["chunk_id"] for c in to_summarize if c["chunk_id"] not in summarized_chunk_ids
        ]
        return SummaryGenerationResult(
            chunks_attempted=len(to_summarize),
            summaries_written=len(summaries),
            authoritative_chunks=len(summaries) + len(chunks) - len(to_summarize),
            missing_chunk_ids=missing_chunk_ids,
            files_attempted=1,
            files_summarized=1 if summaries else 0,
        )


class ComprehensiveChunkWriter(FileBatchSummarizer):
    """Summarizes all un-summarized chunks in the index.

    Chunks are grouped by file so each file's content is read from disk only
    once.  Each file's chunks are handed off to ``FileBatchSummarizer``, which
    sends a single API call per file (or falls back to the topological
    per-chunk path for very large files).

    Requires either an active MCP session with sampling capability **or** an
    ``ANTHROPIC_API_KEY`` / ``OPENAI_API_KEY`` / ``CEREBRAS_API_KEY``
    environment variable.
    """

    def _fetch_unsummarized_rows(
        self, *, limit: int, target_paths: Optional[Sequence[Path]] = None
    ) -> List[Any]:
        normalized_paths = {
            Path(path).resolve(strict=False).as_posix() for path in (target_paths or []) if path
        }
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT c.chunk_id, c.file_id, c.line_start, c.line_end,
                          c.content, c.node_type, c.parent_chunk_id,
                          c.language, s.name AS symbol, f.path AS file_path,
                          c.symbol_id
                   FROM code_chunks c
                   JOIN files f ON c.file_id = f.id
                   LEFT JOIN symbols s ON c.symbol_id = s.id
                   LEFT JOIN chunk_summaries cs ON c.chunk_id = cs.chunk_hash
                   WHERE cs.chunk_hash IS NULL
                   LIMIT ?""",
                (limit,),
            )
            rows = cursor.fetchall()

        if not normalized_paths:
            return rows
        return [
            row for row in rows if Path(row[9]).resolve(strict=False).as_posix() in normalized_paths
        ]

    async def process_scope(
        self, *, limit: int = 500, target_paths: Optional[Sequence[Path]] = None
    ) -> SummaryGenerationResult:
        """Generate summaries for unsummarized chunks within an optional file scope."""
        if not self.can_summarize():
            logger.warning(
                "Cannot run summarization: no MCP sampling and no API key set "
                "(set CEREBRAS_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY)"
            )
            return SummaryGenerationResult()

        rows = self._fetch_unsummarized_rows(limit=limit, target_paths=target_paths)

        if not rows:
            logger.info("ComprehensiveChunkWriter: no unsummarized chunks found")
            return SummaryGenerationResult()

        # Group chunks and symbol names by file_id.
        file_meta: Dict[int, tuple] = {}  # file_id -> (file_path, language)
        file_chunks: Dict[int, List[Dict]] = {}
        file_symbol_maps: Dict[int, Dict[int, str]] = {}

        for row in rows:
            (
                chunk_id,
                file_id,
                line_start,
                line_end,
                chunk_content,
                node_type,
                parent_chunk_id,
                language,
                symbol,
                file_path,
                symbol_id,
            ) = row

            if file_id not in file_meta:
                file_meta[file_id] = (file_path, language or "unknown")
                file_chunks[file_id] = []
                file_symbol_maps[file_id] = {}

            file_chunks[file_id].append(
                {
                    "chunk_id": chunk_id,
                    "file_id": file_id,
                    "line_start": line_start,
                    "line_end": line_end,
                    "content": chunk_content,
                    "node_type": node_type,
                    "parent_chunk_id": parent_chunk_id,
                    "language": language,
                    "symbol_id": symbol_id,
                }
            )
            if symbol_id and symbol:
                file_symbol_maps[file_id][symbol_id] = symbol

        result = SummaryGenerationResult(
            chunks_attempted=len(rows),
            files_attempted=len(file_meta),
        )
        for file_id, (file_path, _) in file_meta.items():
            try:
                with open(file_path, encoding="utf-8", errors="replace") as fh:
                    file_content = fh.read()
            except Exception:
                file_content = ""

            try:
                file_result = await self.summarize_file_chunks(
                    file_id=file_id,
                    file_path=file_path,
                    file_content=file_content,
                    chunks=file_chunks[file_id],
                    symbol_map=file_symbol_maps[file_id],
                    persist=True,
                )
                result = SummaryGenerationResult(
                    chunks_attempted=result.chunks_attempted,
                    summaries_written=result.summaries_written + file_result.summaries_written,
                    authoritative_chunks=(
                        result.authoritative_chunks + file_result.authoritative_chunks
                    ),
                    missing_chunk_ids=result.missing_chunk_ids + file_result.missing_chunk_ids,
                    files_attempted=result.files_attempted,
                    files_summarized=result.files_summarized + file_result.files_summarized,
                )
            except Exception as exc:
                logger.error("Failed to summarize file %s: %s", file_path, exc)
                result.missing_chunk_ids.extend(
                    [chunk["chunk_id"] for chunk in file_chunks.get(file_id, [])]
                )

        logger.info(
            "ComprehensiveChunkWriter: stored %d/%d summaries",
            result.summaries_written,
            len(rows),
        )
        return result

    async def process_all(self, limit: int = 500) -> int:
        """Generate summaries for every unsummarized chunk, grouped by file."""
        result = await self.process_scope(limit=limit)
        return result.summaries_written


class LazyChunkWriter(ChunkWriter):
    """Enqueues chunks seen during search and summarizes them in the background.

    Usage::

        writer = LazyChunkWriter(db_path=..., qdrant_client=None)
        writer.start()                      # launch background worker
        writer.update_session(session)      # call on every tool invocation
        writer.enqueue(chunk_data_dict)     # fire-and-forget after each search
    """

    def __init__(
        self,
        db_path: str,
        qdrant_client: Any,
        session: Any = None,
        client_name: Optional[str] = None,
        summarization_config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(db_path, qdrant_client, session, client_name, summarization_config)
        self.queue: asyncio.Queue = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        """Start the background worker task (idempotent)."""
        if self._task is None:
            self._task = asyncio.create_task(self._worker())

    def update_session(self, session: Any) -> None:
        """Refresh the MCP session reference used for sampling.

        Call this on every tool invocation so the writer always holds a live
        session even if the client reconnects.
        """
        self.session = session

    async def _worker(self) -> None:
        while True:
            chunk = await self.queue.get()
            try:
                await self.summarize_chunk(**chunk)
            except Exception as exc:
                logger.error("Error summarizing chunk: %s", exc)
            finally:
                self.queue.task_done()

    def enqueue(self, chunk_data: Dict[str, Any]) -> None:
        """Add a chunk to the background summarization queue (non-blocking)."""
        self.queue.put_nowait(chunk_data)
