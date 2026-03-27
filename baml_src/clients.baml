// Cerebras inference via OpenAI-compatible API.
// For cache-friendly prompts, static content (system instructions, file context)
// is placed at the front of each prompt so the provider can cache the prefix.
client<llm> Cerebras {
  provider openai-generic
  options {
    base_url "https://api.cerebras.ai/v1"
    model "gpt-oss-120b"
    api_key env.CEREBRAS_API_KEY
    max_tokens 4096
  }
}
