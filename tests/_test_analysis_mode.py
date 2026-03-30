#!/usr/bin/env python3
"""Quick local checks for first-phase analysis mode nodes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agent.analysis_nodes_mode import (
    compute_mode_specific_analysis,
    decide_analysis_mode,
    decide_plot_plan,
)


def _make_state(sample_titles, sample_chars, sample_count=12):
    return {
        "dataset_id": "GSE_TEST",
        "dataset_info": {"expected_systems": ["System A", "System D"]},
        "sample_metadata": {
            "sample_count": sample_count,
            "titles": sample_titles,
            "characteristics": sample_chars,
            "accessions": [f"GSM{i}" for i in range(sample_count)],
        },
        "expression_matrix": None,
        "classification_results": None,
        "ssgsea_scores": None,
        "system_scores": None,
        "statistical_results": None,
        "analysis_mode": None,
        "analysis_design": None,
        "grouping_info": None,
        "focus_subcategories": [],
        "focus_systems": [],
        "plot_plan": None,
        "mode_specific_results": None,
        "log_messages": [],
        "errors": [],
        "current_step": "init",
        "metadata": {},
    }


def main():
    # Case-control signal
    state = _make_state(
        sample_titles=["Control_1", "Control_2", "Disease_1", "Disease_2"] * 3,
        sample_chars=[["group: control", "group: control", "group: disease", "group: disease"] * 3],
    )
    state = decide_analysis_mode(state)
    assert state["analysis_mode"] == "case_control", state["analysis_mode"]

    # Time-series signal
    state = _make_state(
        sample_titles=["t0", "t1 day", "t7 day", "t14 day"] * 3,
        sample_chars=[["timepoint: 0 day", "timepoint: 1 day", "timepoint: 7 day", "timepoint: 14 day"] * 3],
    )
    state = decide_analysis_mode(state)
    assert state["analysis_mode"] == "time_series", state["analysis_mode"]

    # Plot plan without mode-specific stats should still work
    state = decide_plot_plan(state)
    assert state["plot_plan"] is not None
    assert len(state["plot_plan"]["plots"]) >= 2

    # Subtype signal
    state = _make_state(
        sample_titles=[f"s{i}" for i in range(12)],
        sample_chars=[
            [
                "subtype: alpha",
                "subtype: alpha",
                "subtype: beta",
                "subtype: beta",
                "subtype: gamma",
                "subtype: gamma",
                "subtype: alpha",
                "subtype: beta",
                "subtype: gamma",
                "subtype: alpha",
                "subtype: beta",
                "subtype: gamma",
            ]
        ],
    )
    state = decide_analysis_mode(state)
    assert state["analysis_mode"] == "subtype_comparison", state["analysis_mode"]

    # Continuous trait signal
    state = _make_state(
        sample_titles=[f"s{i}" for i in range(12)],
        sample_chars=[[f"age: {20 + i}" for i in range(12)]],
    )
    state = decide_analysis_mode(state)
    assert state["analysis_mode"] == "continuous_trait_association", state["analysis_mode"]

    # Fallback compute_mode_specific_analysis should not crash when expression matrix is missing
    state = compute_mode_specific_analysis(state)
    assert state["statistical_results"] is not None
    print("analysis mode checks passed")


if __name__ == "__main__":
    main()
