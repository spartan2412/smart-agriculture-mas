"""Local MLX-LM JSON client for the optional E3 deployment experiment.

This adapter is intentionally separate from the legacy multi-provider client.
It is used only when ``LLM_BACKEND=mlx-lm`` and ``MLX_MODEL_PATH`` names an
explicit, locally bound artifact.  It exposes the same ``generate_json``
surface accepted by :class:`BenchmarkLLMClientV5`; selection validation remains
in the bounded client and no agricultural fact or action is generated here.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional

import config


class MLXLMClientError(RuntimeError):
    """Raised when the optional local MLX-LM backend is unavailable or invalid."""


class MLXLMJSONClient:
    """Lazy, deterministic JSON-mode wrapper around one explicit MLX artifact."""

    def __init__(self, model_path: Optional[str | Path] = None) -> None:
        configured_path = str(model_path if model_path is not None else config.MLX_MODEL_PATH).strip()
        if not configured_path:
            raise MLXLMClientError(
                "MLX_MODEL_PATH is required for LLM_BACKEND=mlx-lm; do not select an MLX model implicitly."
            )
        self.model_path = Path(configured_path).expanduser().resolve()
        if not self.model_path.is_dir():
            raise MLXLMClientError(f"MLX_MODEL_PATH is not a local model directory: {self.model_path}")
        self._model: Any = None
        self._tokenizer: Any = None
        self._generate: Any = None
        self._make_sampler: Any = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            from mlx_lm import generate, load
            from mlx_lm.sample_utils import make_sampler
        except ImportError as exc:  # pragma: no cover - platform/dependency dependent
            raise MLXLMClientError(
                "mlx-lm is required for E3. Install the macOS Apple-Silicon optional dependencies first."
            ) from exc
        try:
            self._model, self._tokenizer = load(str(self.model_path))
        except Exception as exc:  # pragma: no cover - depends on external model artifact
            raise MLXLMClientError(f"Unable to load the bound MLX artifact at {self.model_path}: {exc}") from exc
        self._generate = generate
        self._make_sampler = make_sampler

    def _chat_prompt(self, system_prompt: str, user_prompt: str) -> str:
        messages = (
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        )
        if hasattr(self._tokenizer, "apply_chat_template"):
            return str(
                self._tokenizer.apply_chat_template(
                    list(messages), tokenize=False, add_generation_prompt=True
                )
            )
        # The documented Qwen chat template is normally present.  This fallback
        # is intentionally explicit rather than pretending a generic prompt is
        # artifact-equivalent.
        raise MLXLMClientError("The bound MLX tokenizer lacks apply_chat_template.")

    @staticmethod
    def _parse_json(raw: str) -> Mapping[str, Any]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()
        try:
            value = json.loads(cleaned)
        except json.JSONDecodeError:
            start, end = cleaned.find("{"), cleaned.rfind("}")
            if start == -1 or end <= start:
                return {"error": "json_parse_failed", "raw": raw}
            try:
                value = json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                return {"error": "json_parse_failed", "raw": raw}
        return value if isinstance(value, Mapping) else {"error": "json_response_not_object", "raw": raw}

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 200,
    ) -> Mapping[str, Any]:
        """Generate one JSON object with the configured local MLX artifact."""
        self._load()
        prompt = self._chat_prompt(
            system_prompt
            + "\n\nIMPORTANT: Respond with ONLY a valid JSON object. No prose or markdown fences.",
            user_prompt,
        )
        try:
            raw = self._generate(
                self._model,
                self._tokenizer,
                prompt=prompt,
                max_tokens=max_tokens,
                sampler=self._make_sampler(temp=temperature),
                verbose=False,
            )
        except Exception as exc:  # pragma: no cover - depends on MLX runtime
            raise MLXLMClientError(f"MLX-LM generation failed: {exc}") from exc
        return self._parse_json(str(raw))
