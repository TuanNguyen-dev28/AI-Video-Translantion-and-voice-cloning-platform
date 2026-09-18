"""Client for Ollama or another self-hosted local language-model server."""

from __future__ import annotations

from typing import Any, Dict

import httpx

from config import (
    LOCAL_LLM_API_KEY,
    LOCAL_LLM_BASE_URL,
    LOCAL_LLM_MODEL,
    LOCAL_LLM_PROTOCOL,
    LOCAL_LLM_THINKING,
    LOCAL_LLM_TIMEOUT_SECONDS,
)


class LocalLLMProvider:
    """Generate text from a model running on the user's own infrastructure."""

    def __init__(
        self,
        base_url: str = LOCAL_LLM_BASE_URL,
        model: str = LOCAL_LLM_MODEL,
        api_key: str = LOCAL_LLM_API_KEY,
        protocol: str = LOCAL_LLM_PROTOCOL,
        thinking: bool = LOCAL_LLM_THINKING,
        timeout_seconds: float = LOCAL_LLM_TIMEOUT_SECONDS,
    ):
        if not base_url:
            raise ValueError("LOCAL_LLM_BASE_URL is not configured")
        if not model:
            raise ValueError("LOCAL_LLM_MODEL is not configured")
        if protocol not in {"ollama", "openai"}:
            raise ValueError("LOCAL_LLM_PROTOCOL must be 'ollama' or 'openai'")

        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.protocol = protocol
        self.thinking = thinking
        self.timeout_seconds = timeout_seconds

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float,
        max_tokens: int,
        json_mode: bool = False,
    ) -> str:
        if self.protocol == "ollama":
            return self._generate_with_ollama(
                system_prompt,
                user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
            )
        return self._generate_with_openai(
            system_prompt,
            user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
        )

    def _generate_with_ollama(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> str:
        """Use native Ollama API, including the Qwen thinking switch."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "think": self.thinking,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if json_mode:
            payload["format"] = "json"
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(f"{self._ollama_base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RuntimeError(
                "Local Ollama request failed. Confirm Ollama is running and "
                f"LOCAL_LLM_BASE_URL is correct: {self.base_url}"
            ) from exc

        try:
            content = data["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise RuntimeError("Local Ollama returned an unexpected response") from exc
        return self._validate_content(content, "Local Ollama")

    def _generate_with_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> str:
        """Call a standard OpenAI-compatible endpoint, for example vLLM."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RuntimeError(
                "Local LLM request failed. Confirm the server is running and "
                f"LOCAL_LLM_BASE_URL is correct: {self.base_url}"
            ) from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Local LLM returned an unexpected response") from exc
        return self._validate_content(content, "Local LLM")

    @staticmethod
    def _validate_content(content: Any, provider_name: str) -> str:
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(f"{provider_name} returned an empty response")
        return content.strip()

    def ensure_ready(self) -> None:
        """Verify that the local server exposes the configured model."""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        endpoint = (
            f"{self._ollama_base_url}/api/tags"
            if self.protocol == "ollama"
            else f"{self.base_url}/models"
        )
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(endpoint, headers=headers)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RuntimeError(
                "Local LLM is unavailable. Start the configured server and confirm "
                f"LOCAL_LLM_BASE_URL: {self.base_url}"
            ) from exc

        model_rows = data.get("models", []) if self.protocol == "ollama" else data.get("data", [])
        model_ids = {
            str(model.get("name") or model.get("id") or "")
            for model in model_rows
            if isinstance(model, dict)
        }
        if self.model not in model_ids:
            available = ", ".join(sorted(model_ids)) or "none"
            raise RuntimeError(
                f"Configured local model '{self.model}' is not available. "
                f"Available models: {available}"
            )

    @property
    def _ollama_base_url(self) -> str:
        """Convert an Ollama OpenAI-style URL ending in /v1 to its root URL."""
        return self.base_url[:-3] if self.base_url.endswith("/v1") else self.base_url
