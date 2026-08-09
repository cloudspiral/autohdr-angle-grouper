"""Deterministic evaluation infrastructure for the AutoHDR grouping challenge."""

from autohdr_eval.config import EvaluationConfig, load_config
from autohdr_eval.scoring import ScoreResult, score_groups

__all__ = ["EvaluationConfig", "ScoreResult", "load_config", "score_groups"]
