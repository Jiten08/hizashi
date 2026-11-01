"""One Gemini call with a time limit and a per-process rate limit. Never raises: returns None
when there's no key, the limit is reached, the call is slow or fails, so every caller keeps
a non-LLM fallback. Used by the hub's sentence -> rules parser and the agents' haggle lines.
"""
import asyncio
import logging
import time
from collections import deque

from . import config

log = logging.getLogger("hizashi.llm")

_client = None
_calls: deque[float] = deque()
_quiet_until = 0.0              # after a 429, leave Gemini alone for a while
COOLDOWN = 30.0


def _gemini():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def _allowed(per_minute: int) -> bool:
    now = time.monotonic()
    if now < _quiet_until:
        return False
    while _calls and now - _calls[0] > 60:
        _calls.popleft()
    if len(_calls) >= per_minute:
        return False
    _calls.append(now)
    return True


async def generate(prompt: str, *, system: str | None = None, schema: type | None = None,
                   timeout: float = 8.0, per_minute: int = config.LLM_PER_MINUTE,
                   temperature: float = 0.4) -> str | None:
    """Text (or JSON text when `schema`, a pydantic model, is given), or None."""
    if not config.GEMINI_API_KEY or not _allowed(per_minute):
        return None
    from google.genai import types
    cfg = types.GenerateContentConfig(system_instruction=system, temperature=temperature)
    if schema is not None:
        cfg.response_mime_type = "application/json"
        cfg.response_schema = schema
    try:
        r = await asyncio.wait_for(
            _gemini().aio.models.generate_content(model=config.GEMINI_MODEL, contents=prompt, config=cfg), timeout)
        return (r.text or "").strip() or None
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            global _quiet_until
            _quiet_until = time.monotonic() + COOLDOWN
        log.info("gemini call skipped (%s: %s)", type(e).__name__, str(e)[:120])
        return None
