"""LLM-as-Judge evaluation system for EnglishConnect teaching agent.

This module provides automated evaluation of agent responses using a local
Qwen 2.5-7B model as judge. It supports:
- 6 rubric dimensions (language, tool usage, cleanliness, etc.)
- Golden dataset regression testing
- A/B comparison with position bias mitigation
- CLI for running evaluations

Usage:
    # CLI
    python -m tests.evaluation.cli --dimension all

    # Python
    from tests.evaluation import EvaluationRunner, Dimension
    runner = EvaluationRunner()
    results = await runner.run_evaluation(dimension=Dimension.LANGUAGE_CHOICE)
"""

from tests.evaluation.rubrics import Dimension, RUBRICS, get_rubric
from tests.evaluation.judge import JudgeLLM, get_judge
from tests.evaluation.runner import EvaluationRunner, EvaluationResults, TestResult
from tests.evaluation.comparison import ABComparison, ComparisonResults, Winner

__all__ = [
    # Rubrics
    "Dimension",
    "RUBRICS",
    "get_rubric",
    # Judge
    "JudgeLLM",
    "get_judge",
    # Runner
    "EvaluationRunner",
    "EvaluationResults",
    "TestResult",
    # Comparison
    "ABComparison",
    "ComparisonResults",
    "Winner",
]
