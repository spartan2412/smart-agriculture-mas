"""
Pluggable LLM client.

Supports:
  - ollama    : free, fully local, no API key (default)
  - groq      : free tier, cloud, very fast
  - openai    : paid, optional
  - anthropic : paid, optional

All backends are called through a single `LLMClient.generate()` interface so
agents never need to know which backend is active.
"""
from __future__ import annotations
import json
import logging
import time
from typing import Optional

import config

logger = logging.getLogger(__name__)

# Retry settings for transient network failures (timeouts, connection errors, rate limits) —
# matters a lot for long evaluation runs (e.g. evaluation/run_accuracy_eval.py makes ~160 calls
# in a row) where hitting ONE flaky request shouldn't kill hours of prior progress.
MAX_RETRIES = 4
INITIAL_BACKOFF_SECONDS = 2.0
BACKOFF_MULTIPLIER = 2.0


def _with_retries(fn, backend_name: str):
    """Calls fn() with exponential-backoff retries on transient errors (timeouts, connection
    errors, HTTP 429/5xx). Re-raises immediately on non-transient errors (e.g. bad API key)."""
    last_exc = None
    delay = INITIAL_BACKOFF_SECONDS
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if not _is_transient(e):
                raise
            if attempt == MAX_RETRIES:
                break
            logger.warning("%s call failed (attempt %d/%d): %s — retrying in %.1fs",
                            backend_name, attempt, MAX_RETRIES, e, delay)
            print(f"  [retry] {backend_name} request failed ({type(e).__name__}: {e}); "
                  f"retrying in {delay:.0f}s (attempt {attempt}/{MAX_RETRIES})...")
            time.sleep(delay)
            delay *= BACKOFF_MULTIPLIER
    raise RuntimeError(
        f"{backend_name} request failed after {MAX_RETRIES} attempts. Last error: {last_exc}"
    ) from last_exc


def _is_transient(exc: Exception) -> bool:
    """Heuristic: treat timeouts, connection errors, and rate-limit/server errors as transient
    (worth retrying); treat auth/bad-request errors as permanent (fail fast instead of retrying
    a request that will never succeed)."""
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    transient_markers = ("timeout", "connection", "connecterror", "rate limit", "ratelimit",
                          "429", "500", "502", "503", "504", "temporarily unavailable",
                          "json_validate_failed", "failed to validate json")
    return any(marker in name or marker in msg for marker in transient_markers)


class LLMClient:
    def __init__(self, backend: Optional[str] = None):
        self.backend = (backend or config.LLM_BACKEND).lower()

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.2,
                 max_tokens: int = 1000, json_mode: bool = False) -> str:
        """Returns the raw text response from the configured LLM backend."""
        if self.backend == "ollama":
            return self._generate_ollama(system_prompt, user_prompt, temperature, max_tokens, json_mode)
        elif self.backend == "groq":
            return self._generate_groq(system_prompt, user_prompt, temperature, max_tokens, json_mode)
        elif self.backend == "openai":
            return self._generate_openai(system_prompt, user_prompt, temperature, max_tokens, json_mode)
        elif self.backend == "anthropic":
            return self._generate_anthropic(system_prompt, user_prompt, temperature, max_tokens, json_mode)
        else:
            raise ValueError(f"Unknown LLM_BACKEND: {self.backend}")

    def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.1,
                       max_tokens: int = 1000) -> dict:
        """Convenience wrapper that asks the model for strict JSON and parses it,
        with a repair fallback if the model wraps output in markdown fences."""
        instructed_system = (
            system_prompt
            + "\n\nIMPORTANT: Respond with ONLY a valid JSON object. No prose, no markdown "
              "fences, no explanation outside the JSON."
        )
        raw = self.generate(instructed_system, user_prompt, temperature, max_tokens, json_mode=True)
        return self._parse_json(raw)

    @staticmethod
    def _parse_json(raw: str) -> dict:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # last-resort: find the first { ... } block
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(cleaned[start:end + 1])
                except json.JSONDecodeError:
                    pass
            logger.warning("Failed to parse JSON from LLM output: %s", raw[:300])
            return {"error": "json_parse_failed", "raw": raw}

    # ---------------- backends ----------------

    def _generate_ollama(self, system_prompt, user_prompt, temperature, max_tokens, json_mode) -> str:
        try:
            import ollama
        except ImportError as e:
            raise RuntimeError(
                "The 'ollama' package is not installed. Run: pip install ollama, "
                "and make sure `ollama serve` is running locally."
            ) from e
        client = ollama.Client(host=config.OLLAMA_HOST)
        options = {"temperature": temperature, "num_predict": max_tokens}

        def _call():
            response = client.chat(
                model=config.OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                options=options,
                format="json" if json_mode else "",
            )
            return response["message"]["content"]

        return _with_retries(_call, "ollama")

    def _generate_groq(self, system_prompt, user_prompt, temperature, max_tokens, json_mode) -> str:
        try:
            from groq import Groq
        except ImportError as e:
            raise RuntimeError("Run: pip install groq") from e
        # Explicit timeout (seconds) — the default client timeout can be long enough that a
        # single hung request stalls a whole evaluation run; fail faster so retries kick in sooner.
        client = Groq(api_key=config.GROQ_API_KEY, timeout=30.0)
        kwargs = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        def _call():
            resp = client.chat.completions.create(
                model=config.GROQ_MODEL,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                **kwargs,
            )
            return resp.choices[0].message.content

        return _with_retries(_call, "groq")

    def _generate_openai(self, system_prompt, user_prompt, temperature, max_tokens, json_mode) -> str:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError("Run: pip install openai") from e
        client = OpenAI(api_key=config.OPENAI_API_KEY, timeout=30.0)
        kwargs = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        def _call():
            resp = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                **kwargs,
            )
            return resp.choices[0].message.content

        return _with_retries(_call, "openai")

    def _generate_anthropic(self, system_prompt, user_prompt, temperature, max_tokens, json_mode) -> str:
        try:
            import anthropic
        except ImportError as e:
            raise RuntimeError("Run: pip install anthropic") from e
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, timeout=30.0)

        def _call():
            resp = client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return "".join(block.text for block in resp.content if block.type == "text")

        return _with_retries(_call, "anthropic")


class MockLLMClient(LLMClient):
    """Deterministic mock backend used in unit tests — no network, no model required."""

    def __init__(self, fixed_response: str = '{"mock": true}'):
        super().__init__(backend="mock")
        self.fixed_response = fixed_response

    def generate(self, system_prompt, user_prompt, temperature=0.2, max_tokens=1000, json_mode=False):
        return self.fixed_response