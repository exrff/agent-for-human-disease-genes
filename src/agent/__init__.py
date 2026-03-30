"""Public exports for the active disease analysis agent package."""

from typing import Any

_IMPORT_ERROR: Exception | None = None

try:
    from .disease_analysis_agent import AnalysisState, create_disease_analysis_graph, run_disease_analysis
except Exception as exc:  # pragma: no cover - import guard
    AnalysisState = Any  # type: ignore[assignment]
    _IMPORT_ERROR = exc

    def _raise_import_error() -> None:
        raise RuntimeError(
            "Failed to import disease_analysis_agent. "
            "Please install missing runtime dependencies (e.g., langgraph). "
            f"Original error: {exc}"
        ) from exc

    def create_disease_analysis_graph():  # type: ignore[override]
        _raise_import_error()

    def run_disease_analysis(*args, **kwargs):  # type: ignore[override]
        _raise_import_error()

__all__ = ["AnalysisState", "create_disease_analysis_graph", "run_disease_analysis"]
