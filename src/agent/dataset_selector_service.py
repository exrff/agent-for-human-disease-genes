#!/usr/bin/env python3
"""dataset selection service backed by external prompt templates."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .prompts import build_dataset_selection_prompt


class DiseaseSelector:
    """Choose the next dataset via rules or LLM."""

    def __init__(self, results_dir: str = "results/agent_analysis"):
        self.results_dir = Path(results_dir)
        self.logger = logging.getLogger(__name__)

    def scan_analyzed_datasets(self) -> Dict[str, Any]:
        analyzed = {
            "datasets": [],
            "disease_types": set(),
            "system_coverage": {},
            "total_count": 0,
        }
        seen_ids = set()

        if self.results_dir.exists():
            for dataset_dir in self.results_dir.iterdir():
                if not dataset_dir.is_dir():
                    continue

                summary_file = dataset_dir / "summary.json"
                if not summary_file.exists():
                    summary_file = dataset_dir / "analysis_summary.json"
                if not summary_file.exists():
                    continue

                try:
                    with open(summary_file, "r", encoding="utf-8") as fh:
                        summary = json.load(fh)
                except Exception as exc:
                    self.logger.warning(f"Failed reading {summary_file}: {exc}")
                    continue

                dataset_id = dataset_dir.name
                seen_ids.add(dataset_id)
                top_systems = summary.get("top_systems", [])
                disease_type = summary.get("disease_type")

                analyzed["datasets"].append(
                    {
                        "dataset_id": dataset_id,
                        "disease_type": disease_type,
                        "analysis_date": summary.get("analysis_time")
                        or summary.get("analysis_date"),
                        "systems_activated": top_systems,
                        "strategy_used": summary.get("analysis_strategy"),
                        "source": "agent",
                    }
                )

                if disease_type:
                    analyzed["disease_types"].add(disease_type)

                for system in top_systems:
                    analyzed["system_coverage"][system] = (
                        analyzed["system_coverage"].get(system, 0) + 1
                    )

                analyzed["total_count"] += 1

        validation_dir = Path("data/validation_datasets")
        if validation_dir.exists():
            for folder in validation_dir.iterdir():
                if not folder.is_dir():
                    continue

                parts = folder.name.split("-", 1)
                dataset_id = parts[0]
                chinese_name = parts[1] if len(parts) > 1 else ""
                if not dataset_id.startswith("GSE") or dataset_id in seen_ids:
                    continue

                seen_ids.add(dataset_id)
                disease_type = self._lookup_disease_type(dataset_id)
                analyzed["datasets"].append(
                    {
                        "dataset_id": dataset_id,
                        "disease_type": disease_type or chinese_name or "unknown",
                        "analysis_date": None,
                        "systems_activated": [],
                        "strategy_used": "manual",
                        "source": "manual",
                    }
                )
                if disease_type:
                    analyzed["disease_types"].add(disease_type)
                analyzed["total_count"] += 1

        analyzed["disease_types"] = list(analyzed["disease_types"])
        return analyzed

    @staticmethod
    def _lookup_disease_type(dataset_id: str) -> Optional[str]:
        try:
            from .config import AgentConfig

            info = AgentConfig.DATASETS.get(dataset_id)
            if info:
                return info.get("disease_type")
        except Exception:
            pass
        return None

    def get_available_datasets(self) -> List[Dict[str, Any]]:
        from .config import AgentConfig

        available = []
        for dataset_id, info in AgentConfig.get_all_datasets().items():
            available.append(
                {
                    "dataset_id": dataset_id,
                    "name": info["name"],
                    "chinese_name": info["chinese_name"],
                    "disease_type": info["disease_type"],
                    "expected_systems": info["expected_systems"],
                    "description": info["description"],
                    "n_samples": info.get("n_samples", 0),
                }
            )
        return available

    def select_next_dataset_with_llm(
        self,
        analyzed: Dict[str, Any],
        available: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        try:
            from .llm_client import create_llm_integration

            llm = create_llm_integration()
            analyzed_ids = {d["dataset_id"] for d in analyzed["datasets"]}
            unanalyzed = [d for d in available if d["dataset_id"] not in analyzed_ids]
            if not unanalyzed:
                return None

            response = llm.select_next_dataset(
                build_dataset_selection_prompt(analyzed, unanalyzed)
            )
            selected_id = response.get("selected_dataset_id")
            reasoning = response.get("reasoning", "")

            if selected_id:
                selected = next(
                    (dataset for dataset in unanalyzed if dataset["dataset_id"] == selected_id),
                    None,
                )
                if selected:
                    selected["selection_reasoning"] = reasoning
                    return selected

            return self.select_next_dataset_with_rules(analyzed, available)
        except Exception as exc:
            self.logger.error(f"LLM selection failed: {exc}", exc_info=True)
            return self.select_next_dataset_with_rules(analyzed, available)

    def select_next_dataset_with_rules(
        self,
        analyzed: Dict[str, Any],
        available: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        analyzed_ids = {d["dataset_id"] for d in analyzed["datasets"]}
        unanalyzed = [d for d in available if d["dataset_id"] not in analyzed_ids]
        if not unanalyzed:
            return None

        scores = []
        for dataset in unanalyzed:
            score = 0
            reasons = []

            if dataset["disease_type"] not in analyzed["disease_types"]:
                score += 3
                reasons.append(f"new disease type: {dataset['disease_type']}")

            for system in dataset["expected_systems"]:
                if system not in analyzed["system_coverage"]:
                    score += 2
                    reasons.append(f"new system: {system}")
                elif analyzed["system_coverage"][system] < 2:
                    score += 1
                    reasons.append(f"low coverage system: {system}")

            if any(
                keyword in dataset["disease_type"].lower()
                for keyword in ["cancer", "neurodegenerative", "metabolic"]
            ):
                score += 1
                reasons.append("high-priority disease type")

            scores.append({"dataset": dataset, "score": score, "reasons": reasons})

        scores.sort(key=lambda item: item["score"], reverse=True)
        best = scores[0]
        best["dataset"]["selection_reasoning"] = (
            f"Rule-based selection (score={best['score']}): " + "; ".join(best["reasons"])
        )
        return best["dataset"]

    def _build_selection_prompt(
        self,
        analyzed: Dict[str, Any],
        unanalyzed: List[Dict[str, Any]],
    ) -> str:
        return build_dataset_selection_prompt(analyzed, unanalyzed)

    def run(self, use_llm: bool = True) -> Optional[Dict[str, Any]]:
        analyzed = self.scan_analyzed_datasets()
        available = self.get_available_datasets()
        return (
            self.select_next_dataset_with_llm(analyzed, available)
            if use_llm
            else self.select_next_dataset_with_rules(analyzed, available)
        )
