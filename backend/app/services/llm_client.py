"""
LLM client — provider-agnostic on the outside, pluggable on the inside.

Set LLM_PROVIDER=ollama (default, fully local) or LLM_PROVIDER=groq
(hosted, needs GROQ_API_KEY) in the environment. Every other module in the
codebase only ever calls generate_text() / generate_json() / is_llm_available()
below, so adding a third provider means editing only this file.
"""
import json
import re
import logging
import requests

from app.config import settings

logger = logging.getLogger("llm_client")


# ---------------------------------------------------------------------------
# Ollama backend
# ---------------------------------------------------------------------------
def _ollama_post(prompt: str, system: str, temperature: float) -> str:
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": temperature},
    }
    try:
        resp = requests.post(url, json=payload, timeout=settings.OLLAMA_TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("response", "")
    except requests.exceptions.RequestException as exc:
        logger.warning("Ollama request failed: %s", exc)
        return ""


def _ollama_available() -> bool:
    try:
        resp = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)
        return resp.status_code == 200
    except requests.exceptions.RequestException:
        return False


# ---------------------------------------------------------------------------
# Groq backend (OpenAI-compatible chat completions API)
# ---------------------------------------------------------------------------
def _groq_post(prompt: str, system: str, temperature: float) -> str:
    if not settings.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY is not set; cannot call Groq.")
        return ""

    url = f"{settings.GROQ_BASE_URL}/chat/completions"
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=settings.GROQ_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as exc:
        logger.warning("Groq request failed: %s", exc)
        return ""
    except (KeyError, IndexError) as exc:
        logger.warning("Unexpected Groq response shape: %s", exc)
        return ""


def _groq_available() -> bool:
    if not settings.GROQ_API_KEY:
        return False
    try:
        resp = requests.get(
            f"{settings.GROQ_BASE_URL}/models",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            timeout=5,
        )
        return resp.status_code == 200
    except requests.exceptions.RequestException:
        return False


# ---------------------------------------------------------------------------
# Provider-agnostic public interface
# ---------------------------------------------------------------------------
def _dispatch(prompt: str, system: str, temperature: float) -> str:
    if settings.LLM_PROVIDER == "groq":
        return _groq_post(prompt, system, temperature)
    return _ollama_post(prompt, system, temperature)


def generate_text(prompt: str, system: str = "", temperature: float = 0.4) -> str:
    """Plain text generation. Returns '' on failure so callers can fall back."""
    return _dispatch(prompt, system, temperature).strip()


def _extract_json_block(text: str):
    # Grab the first {...} or [...] block in case the model adds preamble
    # or wraps it in markdown fences.
    text = re.sub(r"```(json)?", "", text)
    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def generate_json(prompt: str, system: str = "", temperature: float = 0.2):
    """
    Ask the model for JSON and parse it defensively.
    Returns None if the model is unreachable or output isn't parseable,
    so callers must have a deterministic fallback.
    """
    full_prompt = prompt + "\n\nRespond with ONLY the JSON object, no explanation, no markdown fences."
    raw = _dispatch(full_prompt, system, temperature)
    if not raw:
        return None
    return _extract_json_block(raw)


def is_llm_available() -> bool:
    if settings.LLM_PROVIDER == "groq":
        return _groq_available()
    return _ollama_available()


def active_model_name() -> str:
    return settings.GROQ_MODEL if settings.LLM_PROVIDER == "groq" else settings.OLLAMA_MODEL
