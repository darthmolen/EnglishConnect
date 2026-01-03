"""LLM-as-Judge client using local Qwen 2.5-7B via vLLM.

Uses the same OpenAI-compatible API as Memori, configurable via:
- JUDGE_LLM_URL (default: http://localhost:8004/v1)
- JUDGE_LLM_MODEL (default: auto-detect from server)

Example:
    judge = JudgeLLM()
    verdict = judge.judge(rubric_prompt)
    # Returns: "PASS: Agent correctly used English" or "FAIL: ..."
"""

import logging
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


class JudgeLLM:
    """Synchronous LLM client for evaluation judging.

    Uses local vLLM with OpenAI-compatible API for zero-cost evaluation.
    Temperature is set to 0.0 for deterministic scoring.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """Initialize the judge LLM client.

        Args:
            base_url: vLLM endpoint URL. Defaults to config setting.
            model: Model name. If None, auto-detects from server.
        """
        # Import here to avoid circular imports in tests
        import sys
        sys.path.insert(0, "src/backend")
        from app.config import get_settings

        settings = get_settings()

        self.base_url = base_url or settings.judge_llm_url
        self._model = model or settings.judge_llm_model

        self.client = OpenAI(
            base_url=self.base_url,
            api_key="local",  # vLLM doesn't require auth
        )

        logger.info(f"JudgeLLM initialized: {self.base_url}")

    @property
    def model(self) -> str:
        """Get the model name, auto-detecting if not set."""
        if self._model is None:
            self._model = self._detect_model()
        return self._model

    def _detect_model(self) -> str:
        """Auto-detect model name from vLLM server."""
        try:
            models = self.client.models.list()
            if models.data:
                model_id = models.data[0].id
                logger.info(f"Auto-detected model: {model_id}")
                return model_id
            else:
                raise ValueError("No models available on vLLM server")
        except Exception as e:
            logger.error(f"Failed to detect model: {e}")
            raise

    def judge(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 200,
    ) -> str:
        """Get judgment from the LLM.

        Args:
            prompt: The rubric evaluation prompt
            temperature: Sampling temperature (0.0 for deterministic)
            max_tokens: Maximum response length

        Returns:
            Judge response (e.g., "PASS: reason" or "FAIL: reason")
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Judge LLM error: {e}")
            raise

    def is_available(self) -> bool:
        """Check if the judge LLM is available."""
        try:
            self.client.models.list()
            return True
        except Exception:
            return False


def get_judge() -> JudgeLLM:
    """Get a JudgeLLM instance (convenience function)."""
    return JudgeLLM()
