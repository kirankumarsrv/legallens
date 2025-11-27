# modules/llm_manager.py

"""
LLM Manager (Official Groq SDK Version)
---------------------------------------

A unified interface for calling different LLM providers.
Currently supports:

- Groq (official SDK)
- OpenAI (optional)
- HuggingFace (optional)
- Ollama local endpoint (optional)
- Local HTTP server (optional)

Primary goal:
    Useful for legal NLP tasks, metadata extraction, and summarization.

This class abstracts away:
    → Prompt formatting
    → Model-specific calling code
    → Response parsing

So upper layers (MetadataBuilder, RAG engine) do not change
when you switch LLM providers.
"""

from __future__ import annotations
import os
import typing as t
from dataclasses import dataclass

import importlib
import requests

# -----------------------
# Optional imports (loaded dynamically to avoid static import errors)
# -----------------------
try:
    _groq_mod = importlib.import_module("groq")
    Groq = getattr(_groq_mod, "Groq", None)
except Exception:
    Groq = None

try:
    openai = importlib.import_module("openai")
except Exception:
    openai = None


# ------------------------------------------------------
# LLM Configuration
# ------------------------------------------------------
@dataclass
class LLMConfig:
    provider: str
    model_name: str
    api_key_env: t.Optional[str] = None
    base_url: t.Optional[str] = None
    timeout: int = 30


# ------------------------------------------------------
# LLM Manager Class
# ------------------------------------------------------
class LLMManager:
    """
    Unified LLM wrapper for multiple providers.

    Parameters
    ----------
    provider : str
        "groq", "openai", "huggingface", "ollama", "local"
    model_name : str
        Model identifier (e.g., "llama-3.3-70b-versatile")
    api_key_env : str or None
        Name of environment variable storing API key.
    base_url : str or None
        Used for local endpoints / Ollama / custom inference servers.
    """

    def __init__(self, provider: str, model_name: str,
                 api_key_env: str | None = None,
                 base_url: str | None = None,
                 timeout: int = 30):

        self.config = LLMConfig(
            provider=provider.lower(),
            model_name=model_name,
            api_key_env=api_key_env,
            base_url=base_url,
            timeout=timeout
        )
        self.client = None
        self._init_provider()

    # ------------------------------------------------------
    # Initialization Logic
    # ------------------------------------------------------
    def _init_provider(self):
        p = self.config.provider

        if p == "groq":
            self._init_groq()
        elif p == "openai":
            self._init_openai()
        elif p == "huggingface":
            self._init_huggingface()
        elif p == "ollama":
            self.client = {"base_url": self.config.base_url or "http://localhost:11434"}
        elif p == "local":
            self.client = {"base_url": self.config.base_url}
        else:
            raise ValueError(f"Unsupported provider: {p}")

    # -------------------- GROQ --------------------------
    def _init_groq(self):
        """
        Initialize official Groq SDK.

        Requires:
            pip install groq
            export GROQ_API_KEY=xxxx
        """
        if Groq is None:
            raise ImportError("Please install groq: pip install groq")

        key = os.getenv(self.config.api_key_env or "GROQ_API_KEY")
        if not key:
            raise EnvironmentError("Groq API key not found in env variable 'GROQ_API_KEY'.")

        self.client = Groq(api_key=key)

    # -------------------- OpenAI ------------------------
    def _init_openai(self):
        if openai is None:
            raise ImportError("Please install openai: pip install openai")

        key = os.getenv(self.config.api_key_env or "OPENAI_API_KEY")
        if not key:
            raise EnvironmentError("Missing OPENAI_API_KEY")

        openai.api_key = key
        self.client = openai

    # -------------------- HuggingFace --------------------
    def _init_huggingface(self):
        key = os.getenv(self.config.api_key_env or "HF_API_KEY")
        if not key:
            raise EnvironmentError("Missing HF_API_KEY")
        self.client = {
            "api_key": key,
            "model": self.config.model_name
        }

    # ------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------
    def summarize(self, text: str, max_chars: int = 5000) -> str:
        """
        Summarize long legal text in 4–5 lines.

        Strategy:
        - Trim input for cheaper calls.
        - Provide canonical legal summarization prompt.
        """
        trimmed = text[:max_chars]

        prompt = f"""
Summarize the following Indian Supreme Court judgment in 4–5 lines.
Be legally precise and include:
- Core facts
- Legal issue
- Final holding
Avoid speculation.

Text:
{trimmed}

Summary:
"""

        return self.generate(prompt, temperature=0.0, max_tokens=300)

    def generate(self, prompt: str, temperature: float = 0.0, max_tokens: int = 512) -> str:
        """
        Generate text from any provider.
        """
        p = self.config.provider

        if p == "groq":
            return self._call_groq(prompt, temperature, max_tokens)
        if p == "openai":
            return self._call_openai(prompt, temperature, max_tokens)
        if p == "huggingface":
            return self._call_huggingface(prompt, max_tokens)
        if p == "ollama":
            return self._call_ollama(prompt, max_tokens)
        if p == "local":
            return self._call_local(prompt, max_tokens)

        raise RuntimeError(f"No generation method implemented for provider '{p}'")

    # ------------------------------------------------------
    # Provider Implementations
    # ------------------------------------------------------

    # -------------------- GROQ (official) ----------------
    def _call_groq(self, prompt, temperature, max_tokens):
        """
        Official Groq SDK call for chat completions.

        Correct extraction:
            response.choices[0].message.content
        """

        try:
            completion = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            return completion.choices[0].message.content.strip()

        except Exception as e:
            raise RuntimeError(f"Groq call failed: {str(e)}")

    # -------------------- OPENAI --------------------------
    def _call_openai(self, prompt, temperature, max_tokens):
        try:
            r = self.client.ChatCompletion.create(
                model=self.config.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return r["choices"][0]["message"]["content"].strip()
        except Exception as e:
            raise RuntimeError("OpenAI call failed: " + str(e))

    # -------------------- HUGGINGFACE ---------------------
    def _call_huggingface(self, prompt, max_tokens):
        url = f"https://api-inference.huggingface.co/models/{self.client['model']}"
        headers = {"Authorization": f"Bearer {self.client['api_key']}"}

        payload = {
            "inputs": prompt,
            "parameters": {"max_new_tokens": max_tokens}
        }

        r = requests.post(url, headers=headers, json=payload, timeout=self.config.timeout)
        data = r.json()

        if isinstance(data, list) and len(data) and "generated_text" in data[0]:
            return data[0]["generated_text"]

        return str(data)

    # -------------------- OLLAMA --------------------------
    def _call_ollama(self, prompt, max_tokens):
        url = f"{self.client['base_url']}/api/chat?model={self.config.model_name}"
        body = {"messages": [{"role": "user", "content": prompt}]}

        r = requests.post(url, json=body, timeout=self.config.timeout)
        data = r.json()

        if "response" in data:
            return data["response"].strip()

        return str(data)

    # -------------------- LOCAL ENDPOINT ------------------
    def _call_local(self, prompt, max_tokens):
        url = self.client["base_url"]
        body = {"prompt": prompt, "max_tokens": max_tokens}

        r = requests.post(url, json=body, timeout=self.config.timeout)
        data = r.json()

        return data.get("text") or data.get("result") or str(data)
