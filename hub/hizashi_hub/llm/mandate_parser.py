"""Sentence -> proposed Mandate. Gemini with the Mandate JSON schema as required output,
validated with pydantic; Groq fallback; on failure keep the current mandate."""
from hizashi_shared.models import Mandate


async def parse(text: str, current: Mandate) -> Mandate:
    raise NotImplementedError("TODO(N4, Jiten)")
