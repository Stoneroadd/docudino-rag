"""Small HTTP adapters for local Ollama and hosted LLM APIs."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlsplit


class ProviderError(RuntimeError):
    pass


def is_local(provider: str) -> bool:
    if provider == "ollama":
        url = os.environ.get("DOCUDINO_OLLAMA_URL", "http://localhost:11434/api/chat")
    elif provider == "openai-compatible":
        url = os.environ.get("DOCUDINO_LLM_BASE_URL", "")
    else:
        return False
    try:
        return urlsplit(url).hostname in {"localhost", "127.0.0.1", "::1"}
    except ValueError:
        return False


def post_json(url: str, body: dict, headers: dict[str, str]) -> dict:
    request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json", **headers}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=150) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:1200]
        raise ProviderError(f"API respondió HTTP {error.code}: {detail}") from error
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise ProviderError(f"No se pudo conectar con {url}: {error}") from error


def generate(provider: str, system: str, user: str, model: str | None = None) -> str:
    if provider == "ollama":
        url = os.environ.get("DOCUDINO_OLLAMA_URL", "http://localhost:11434/api/chat")
        model = model or os.environ.get("DOCUDINO_OLLAMA_MODEL")
        if not model:
            raise ProviderError("Indica --model o configura DOCUDINO_OLLAMA_MODEL.")
        data = post_json(url, {"model": model, "stream": False,
                               "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}, {})
        return str(data.get("message", {}).get("content", ""))
    if provider == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        model = model or os.environ.get("DOCUDINO_ANTHROPIC_MODEL")
        if not api_key or not model:
            raise ProviderError("Configura ANTHROPIC_API_KEY y DOCUDINO_ANTHROPIC_MODEL o indica --model.")
        data = post_json("https://api.anthropic.com/v1/messages",
                         {"model": model, "max_tokens": 1200, "system": system,
                          "messages": [{"role": "user", "content": user}]},
                         {"x-api-key": api_key, "anthropic-version": "2023-06-01"})
        return "\n".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        model = model or os.environ.get("DOCUDINO_OPENAI_MODEL")
        if not api_key or not model:
            raise ProviderError("Configura OPENAI_API_KEY y DOCUDINO_OPENAI_MODEL o indica --model.")
        data = post_json("https://api.openai.com/v1/responses",
                         {"model": model, "instructions": system, "input": user},
                         {"Authorization": f"Bearer {api_key}"})
        parts = []
        for item in data.get("output", []):
            if item.get("type") == "message":
                parts.extend(block.get("text", "") for block in item.get("content", []) if block.get("type") == "output_text")
        return "\n".join(parts)
    if provider == "openai-compatible":
        url = os.environ.get("DOCUDINO_LLM_BASE_URL")
        model = model or os.environ.get("DOCUDINO_LLM_MODEL")
        if not url or not model:
            raise ProviderError("Configura DOCUDINO_LLM_BASE_URL y DOCUDINO_LLM_MODEL.")
        api_key = os.environ.get("DOCUDINO_LLM_API_KEY", "")
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        data = post_json(url, {"model": model, "messages": [{"role": "system", "content": system},
                                                               {"role": "user", "content": user}],
                               "temperature": 0.2}, headers)
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as error:
            raise ProviderError("Respuesta compatible sin choices[0].message.content.") from error
    raise ProviderError(f"Proveedor desconocido: {provider}")
