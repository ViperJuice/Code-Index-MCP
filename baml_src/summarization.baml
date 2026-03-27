// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

class ChunkInput {
  chunk_id string
  symbol string
  node_type string
  line_start int
  line_end int
  content string
}

class ChunkSummary {
  chunk_id string
  summary string
}

class FileSummaryResult {
  summaries ChunkSummary[]
}

// ---------------------------------------------------------------------------
// Batch function — one API call per file
//
// Prompt layout (cache-friendly: static content first, dynamic last):
//   [system]  static task instructions
//   [user]    language + file path + full file content  ← cached prefix
//             chunk list                                ← dynamic suffix
// ---------------------------------------------------------------------------

function SummarizeFileChunks(
  language: string,
  file_path: string,
  file_content: string,
  chunks: ChunkInput[]
) -> FileSummaryResult {
  client Cerebras
  prompt #"
    {{ _.role("system") }}
    You are a concise code documentation assistant.
    For each code chunk listed below, write 1-2 sentences describing: what it does,
    and what it returns, produces, or causes (including side effects such as file writes,
    printed output, or state mutations). Mention key parameters only when they
    meaningfully affect behavior. Do not repeat or output code.

    {{ _.role("user") }}
    Language: {{ language }}
    File: {{ file_path }}

    Full source file:
    ```{{ language }}
    {{ file_content }}
    ```

    Summarize each of the following chunks from that file.
    Return one ChunkSummary per chunk using the exact chunk_id provided.

    Chunks to summarize:
    {% for chunk in chunks %}
    ---
    chunk_id: {{ chunk.chunk_id }}
    symbol: {{ chunk.symbol }}
    node_type: {{ chunk.node_type }}
    lines: {{ chunk.line_start }}-{{ chunk.line_end }}
    ```{{ language }}
    {{ chunk.content }}
    ```
    {% endfor %}

    {{ ctx.output_format }}
  "#
}

// ---------------------------------------------------------------------------
// Single-chunk function — fallback for per-chunk summarization
//
// Prompt layout (cache-friendly: static instructions first, dynamic chunk last):
//   [system]  static task instructions
//   [user]    language + file context  ← relatively static within a file
//             parent context           ← changes per chunk
//             chunk content            ← most dynamic, at the end
// ---------------------------------------------------------------------------

function SummarizeChunkAlone(
  language: string,
  symbol: string,
  line_start: int,
  line_end: int,
  content: string,
  parent_context: string,
  file_context: string
) -> ChunkSummary {
  client Cerebras
  prompt #"
    {{ _.role("system") }}
    You are a concise code documentation assistant.
    Write 1-2 sentences describing the code chunk: what it does, and what it
    returns, produces, or causes (including side effects such as file writes,
    printed output, or state mutations). Mention key parameters only when they
    meaningfully affect behavior. Do not repeat or output code.

    {{ _.role("user") }}
    Language: {{ language }}
    {{ file_context }}
    {{ parent_context }}
    Code chunk '{{ symbol }}' (lines {{ line_start }}-{{ line_end }}):
    ```{{ language }}
    {{ content }}
    ```

    Set chunk_id to "{{ symbol }}" in your response.

    {{ ctx.output_format }}
  "#
}
