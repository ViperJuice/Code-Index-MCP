# Dispatcher SIGALRM Timeout Failure Investigation

## Symptom

The dispatcher's symbol lookup fallback path could hang indefinitely when encountering unresponsive plugins. The system had no effective timeout mechanism to interrupt slow plugin operations in `dispatcher_enhanced.py:751-779`, causing worker threads to accumulate and exhaust resources.

## Root Cause

A SIGALRM-based timeout utility was implemented in `bootstrap.py:166-182` but was never wired into the dispatcher's symbol lookup fallback. The fallback loop at `dispatcher_enhanced.py:751-779` iterates over plugins calling `p.getDefinition(symbol)` with no timeout guard, allowing a misbehaving plugin to block indefinitely.

## Why SIGALRM Would Not Have Fixed It Even If Wired

CPython only delivers signals on the main thread. The dispatcher runs within an ASGI worker thread, so even if SIGALRM were properly configured at `bootstrap.py:166-182`, the signal handler would never be invoked from a worker thread context. This architectural constraint meant SIGALRM was fundamentally unsuitable for this use case and would have given false protection.

## Remediation

The timeout guard was replaced with `run_gated_fallback`, which enforces per-plugin timeout boundaries using thread-safe concurrent futures instead of signal-based interruption. This ensures slow plugins are abandoned within a configurable timeout window, allowing the dispatcher to either fall back to the next plugin or return early to the caller.

## Residual Risk

Thread cancellation via `future.cancel()` cannot interrupt a CPU-bound or I/O-blocked Python thread actively running C extension code. The timeout ensures the caller is released within the timeout window (returning `None` or partial results), but the underlying plugin thread may continue running in the background. This is acceptable because:

1. The caller proceeds with degraded results rather than hanging.
2. Background threads are eventually cleaned up when the worker process recycles.
3. The performance impact of orphaned threads is bounded by the timeout window and plugin count.

## Follow-up

The `search()` method at `dispatcher_enhanced.py:829-834` provides query expansion for documentation queries and is covered in SL-4.
