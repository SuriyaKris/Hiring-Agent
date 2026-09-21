"""
LLM Service — single abstraction for Groq (free POC) and OpenAI (production).

POC:  LLM_PROVIDER=groq   -> uses Groq API (llama-3.1-8b-instant / mixtral-8x7b)
Prod: LLM_PROVIDER=openai -> uses gpt-4o-mini / gpt-4o

To switch provider: change LLM_PROVIDER in .env — no code changes needed.
"""

import json
import re
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_not_exception_type
from loguru import logger
from config import get_settings

settings = get_settings()


def _groq_client():
    from groq import AsyncGroq
    if not settings.groq_api_key:
        raise ValueError(
            "GROQ_API_KEY is not set in environment.\n"
            "  Please set GROQ_API_KEY in your Render environment variables or .env file."
        )
    return AsyncGroq(api_key=settings.groq_api_key)


def _openai_client():
    from openai import AsyncOpenAI
    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY is not set in environment.\n"
            "  Please set OPENAI_API_KEY in your Render environment variables or .env file."
        )
    return AsyncOpenAI(api_key=settings.openai_api_key)


def _gemini_client():
    from openai import AsyncOpenAI
    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set in environment.\n"
            "  Get a free key at https://aistudio.google.com\n"
            "  Then set GEMINI_API_KEY in your Render environment variables or .env file."
        )
    return AsyncOpenAI(
        api_key=settings.gemini_api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )


def _resolve_model(provider: str, model: str) -> str:
    """Normalize model names and strip provider prefixes if present."""
    m = model.strip()
    if provider == "groq":
        if m.startswith("groq/"):
            m = m[5:]
        return m
    elif provider == "gemini":
        if m.startswith("gemini/"):
            m = m[7:]
        return m
    elif provider == "openai":
        if m.startswith("openai/"):
            m = m[7:]
        return m
    return m


def _clean_json(text: str) -> str:
    """Strip markdown code fences, trailing commas, and extract outermost JSON object."""
    if not text:
        return "{}"
    text = text.strip()
    # Remove markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    # If surrounded by commentary, extract outermost { ... }
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        text = match.group(1).strip()

    # Remove trailing commas before closing braces/brackets
    text = re.sub(r",\s*([\]}])", r"\1", text)
    return text


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_not_exception_type(ValueError)
)
async def complete_json(
    system_prompt: str,
    user_message: str,
    use_smart_model: bool = False,
    temperature: float = 0.1,
    max_tokens: int = 4000,
) -> dict:
    """
    Call the LLM and return parsed JSON dict.
    Handles markdown fence stripping for models that ignore json_object mode.
    """
    raw_model = settings.smart_model if use_smart_model else settings.fast_model
    provider  = settings.llm_provider
    model     = _resolve_model(provider, raw_model)
    logger.debug(f"LLM call | provider={provider} model={model}")

    # Tell the model explicitly to return only JSON
    json_instruction = "\n\nIMPORTANT: Return ONLY valid JSON. No explanation, no markdown, no code fences."
    full_system = system_prompt + json_instruction

    if provider in ("openai", "gemini"):
        client   = _openai_client() if provider == "openai" else _gemini_client()
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": full_system},
                {"role": "user",   "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},  # Enforce JSON
        )
        raw = response.choices[0].message.content

    elif provider == "groq":
        client = _groq_client()
        # Groq supports json_object on llama-3.1 and mixtral models
        # Use it when available, fall back on parse error
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": full_system},
                    {"role": "user",   "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        except Exception:
            # Some Groq models don't support response_format — retry without it
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": full_system},
                    {"role": "user",   "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        raw = response.choices[0].message.content

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}. Set to 'groq', 'openai', or 'gemini' in .env")

    cleaned = _clean_json(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed.\nRaw:\n{raw}\nCleaned:\n{cleaned}")
        raise ValueError(f"LLM returned invalid JSON: {e}") from e


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_not_exception_type(ValueError)
)
async def complete_text(
    system_prompt: str,
    user_message: str,
    use_smart_model: bool = False,
    temperature: float = 0.7,
    max_tokens: int = 1000,
) -> str:
    """Return plain text (non-JSON) LLM response."""
    raw_model = settings.smart_model if use_smart_model else settings.fast_model
    provider  = settings.llm_provider
    model     = _resolve_model(provider, raw_model)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_message},
    ]
    kwargs = dict(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)

    if provider == "openai":
        response = await _openai_client().chat.completions.create(**kwargs)
    elif provider == "gemini":
        response = await _gemini_client().chat.completions.create(**kwargs)
    elif provider == "groq":
        response = await _groq_client().chat.completions.create(**kwargs)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}")

    return response.choices[0].message.content
