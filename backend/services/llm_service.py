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
    """
    Strip markdown code fences, comments, repair truncated or malformed JSON,
    and extract the outermost JSON object/array.
    """
    if not text:
        return "{}"
    text = text.strip()
    # Remove markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    # Find the start of JSON object or array
    first_brace = text.find("{")
    first_bracket = text.find("[")
    if first_brace == -1 and first_bracket == -1:
        return "{}"

    start_idx = first_brace if (first_bracket == -1 or (first_brace != -1 and first_brace < first_bracket)) else first_bracket
    text = text[start_idx:]

    # Remove trailing commas before closing braces/brackets
    text = re.sub(r",\s*([\]}])", r"\1", text)

    # Fast path: try parsing directly
    try:
        json.loads(text)
        return text
    except Exception:
        pass

    # Repair truncated or malformed JSON
    stack = []
    in_string = False
    escape = False
    cleaned_chars = []

    for char in text:
        if escape:
            escape = False
            cleaned_chars.append(char)
            continue
        if char == '\\':
            escape = True
            cleaned_chars.append(char)
            continue
        if char == '"':
            in_string = not in_string
            cleaned_chars.append(char)
            continue
        if in_string:
            cleaned_chars.append(char)
            continue

        if char in '{[':
            stack.append('}' if char == '{' else ']')
            cleaned_chars.append(char)
        elif char in '}]':
            if stack and stack[-1] == char:
                stack.pop()
            cleaned_chars.append(char)
        else:
            cleaned_chars.append(char)

    repaired = "".join(cleaned_chars)

    # If truncated inside a string literal, close the quote
    if in_string:
        repaired += '"'

    # Remove trailing commas
    repaired = re.sub(r",\s*$", "", repaired.strip())

    # Close any unclosed brackets/braces in reverse order
    for closing in reversed(stack):
        repaired = re.sub(r",\s*$", "", repaired.strip())
        repaired += closing

    repaired = re.sub(r",\s*([\]}])", r"\1", repaired)

    try:
        json.loads(repaired)
        return repaired
    except Exception:
        # If repair needs line-by-line backtracking (e.g. truncated key/colon)
        lines = repaired.split("\n")
        for i in range(len(lines) - 1, 0, -1):
            candidate = "\n".join(lines[:i])
            candidate = re.sub(r",\s*$", "", candidate.strip())
            c_stack = []
            c_in_str = False
            c_esc = False
            for c in candidate:
                if c_esc:
                    c_esc = False
                    continue
                if c == '\\':
                    c_esc = True
                    continue
                if c == '"':
                    c_in_str = not c_in_str
                    continue
                if c_in_str:
                    continue
                if c in '{[':
                    c_stack.append('}' if c == '{' else ']')
                elif c in '}]' and c_stack and c_stack[-1] == c:
                    c_stack.pop()
            if c_in_str:
                candidate += '"'
            for cl in reversed(c_stack):
                candidate = re.sub(r",\s*$", "", candidate.strip())
                candidate += cl
            candidate = re.sub(r",\s*([\]}])", r"\1", candidate)
            try:
                json.loads(candidate)
                return candidate
            except Exception:
                continue

    return text


async def _execute_provider_json(
    provider: str,
    system_prompt: str,
    user_message: str,
    use_smart_model: bool = False,
    temperature: float = 0.1,
    max_tokens: int = 4000,
) -> str:
    if provider == "openai":
        raw_model = settings.openai_smart_model if use_smart_model else settings.openai_fast_model
    elif provider == "gemini":
        raw_model = settings.gemini_smart_model if use_smart_model else settings.gemini_fast_model
    elif provider == "groq":
        raw_model = settings.groq_smart_model if use_smart_model else settings.groq_fast_model
    else:
        raw_model = settings.smart_model if use_smart_model else settings.fast_model

    model = _resolve_model(provider, raw_model)
    logger.debug(f"LLM call | provider={provider} model={model}")

    json_instruction = "\n\nIMPORTANT: Return ONLY valid JSON. No explanation, no markdown, no code fences."
    full_system = system_prompt + json_instruction

    if provider in ("openai", "gemini"):
        client = _openai_client() if provider == "openai" else _gemini_client()
        candidate_models = [model]
        if provider == "gemini":
            for alt in [settings.gemini_fast_model, "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash", "gemini-flash-latest", "gemini-2.5-flash"]:
                if alt and alt not in candidate_models:
                    candidate_models.append(alt)
        elif provider == "openai":
            for alt in [settings.openai_fast_model, "gpt-4o-mini", "gpt-4o"]:
                if alt and alt not in candidate_models:
                    candidate_models.append(alt)
        
        last_err = None
        raw = None
        for cur_model in candidate_models:
            try:
                response = await client.chat.completions.create(
                    model=cur_model,
                    messages=[
                        {"role": "system", "content": full_system},
                        {"role": "user",   "content": user_message},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                )
                raw = response.choices[0].message.content
                if raw:
                    break
            except Exception as ex:
                last_err = ex
                logger.warning(f"Model {cur_model} failed ({ex}). Trying next candidate...")
                continue
        if raw is None and last_err:
            raise last_err
        return raw

    elif provider == "groq":
        client = _groq_client()
        groq_models = [model]
        for g_alt in [settings.groq_fast_model, "llama-3.1-8b-instant", "llama-3.3-70b-versatile", "llama-3.1-70b-versatile"]:
            if g_alt and g_alt not in groq_models:
                groq_models.append(g_alt)

        last_err = None
        raw = None
        for g_model in groq_models:
            try:
                try:
                    response = await client.chat.completions.create(
                        model=g_model,
                        messages=[
                            {"role": "system", "content": full_system},
                            {"role": "user",   "content": user_message},
                        ],
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format={"type": "json_object"},
                    )
                except Exception:
                    response = await client.chat.completions.create(
                        model=g_model,
                        messages=[
                            {"role": "system", "content": full_system},
                            {"role": "user",   "content": user_message},
                        ],
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                raw = response.choices[0].message.content
                if raw:
                    break
            except Exception as ex:
                last_err = ex
                logger.warning(f"Groq model {g_model} failed ({ex}). Trying next...")
                continue

        if raw is None and last_err:
            raise last_err
        return raw

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}")


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
    Call the LLM with automatic cross-provider fallback and return parsed JSON dict.
    """
    primary_provider = settings.llm_provider
    providers_to_try = [primary_provider]
    if "gemini" not in providers_to_try and settings.gemini_api_key:
        providers_to_try.append("gemini")
    if "groq" not in providers_to_try and settings.groq_api_key:
        providers_to_try.append("groq")
    if "openai" not in providers_to_try and settings.openai_api_key and settings.openai_api_key.strip() != "sk-..." and len(settings.openai_api_key.strip()) > 20:
        providers_to_try.append("openai")

    last_error = None
    for p in providers_to_try:
        try:
            raw = await _execute_provider_json(
                provider=p,
                system_prompt=system_prompt,
                user_message=user_message,
                use_smart_model=use_smart_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            cleaned = _clean_json(raw)
            return json.loads(cleaned)
        except Exception as e:
            last_error = e
            logger.warning(f"Provider '{p}' JSON completion failed: {e}. Attempting next available provider...")
            continue

    if last_error:
        raise last_error
    return {}


async def _execute_provider_text(
    provider: str,
    system_prompt: str,
    user_message: str,
    use_smart_model: bool = False,
    temperature: float = 0.7,
    max_tokens: int = 1000,
) -> str:
    if provider == "openai":
        raw_model = settings.openai_smart_model if use_smart_model else settings.openai_fast_model
    elif provider == "gemini":
        raw_model = settings.gemini_smart_model if use_smart_model else settings.gemini_fast_model
    elif provider == "groq":
        raw_model = settings.groq_smart_model if use_smart_model else settings.groq_fast_model
    else:
        raw_model = settings.smart_model if use_smart_model else settings.fast_model

    model = _resolve_model(provider, raw_model)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_message},
    ]

    if provider in ("openai", "gemini"):
        client = _openai_client() if provider == "openai" else _gemini_client()
        candidate_models = [model]
        if provider == "gemini":
            for alt in [settings.gemini_fast_model, "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash", "gemini-flash-latest", "gemini-2.5-flash"]:
                if alt and alt not in candidate_models:
                    candidate_models.append(alt)
        elif provider == "openai":
            for alt in [settings.openai_fast_model, "gpt-4o-mini", "gpt-4o"]:
                if alt and alt not in candidate_models:
                    candidate_models.append(alt)

        last_err = None
        for cur_model in candidate_models:
            try:
                response = await client.chat.completions.create(
                    model=cur_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                txt = response.choices[0].message.content
                if txt is not None:
                    return txt
            except Exception as ex:
                last_err = ex
                logger.warning(f"Text model {cur_model} failed ({ex}). Trying next candidate...")
                continue
        if last_err:
            raise last_err
        return ""

    elif provider == "groq":
        client = _groq_client()
        groq_models = [model]
        for g_alt in [settings.groq_fast_model, "llama-3.1-8b-instant", "llama-3.3-70b-versatile", "llama-3.1-70b-versatile"]:
            if g_alt and g_alt not in groq_models:
                groq_models.append(g_alt)

        last_err = None
        for g_model in groq_models:
            try:
                response = await client.chat.completions.create(
                    model=g_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                txt = response.choices[0].message.content
                if txt is not None:
                    return txt
            except Exception as ex:
                last_err = ex
                logger.warning(f"Groq text model {g_model} failed ({ex}). Trying next...")
                continue
        if last_err:
            raise last_err
        return ""

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}")


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
    """Return plain text (non-JSON) LLM response with automatic cross-provider fallback."""
    primary_provider = settings.llm_provider
    providers_to_try = [primary_provider]
    if "gemini" not in providers_to_try and settings.gemini_api_key:
        providers_to_try.append("gemini")
    if "groq" not in providers_to_try and settings.groq_api_key:
        providers_to_try.append("groq")
    if "openai" not in providers_to_try and settings.openai_api_key and settings.openai_api_key.strip() != "sk-..." and len(settings.openai_api_key.strip()) > 20:
        providers_to_try.append("openai")

    last_error = None
    for p in providers_to_try:
        try:
            return await _execute_provider_text(
                provider=p,
                system_prompt=system_prompt,
                user_message=user_message,
                use_smart_model=use_smart_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            last_error = e
            logger.warning(f"Provider '{p}' text completion failed: {e}. Attempting next available provider...")
            continue

    if last_error:
        raise last_error
    return ""
