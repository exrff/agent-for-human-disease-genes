#!/usr/bin/env python3
"""LLM client with prompt rendering and trace capture."""

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from .prompts import (
    build_analysis_strategy_prompt,
    build_report_summary_prompt,
    build_result_interpretation_prompt,
    build_visualization_strategy_prompt,
)


class LLMClient:
    """Thin wrapper around the configured LLM provider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "qwen3.5-122b-a10b",
        provider: str = "dashscope",
    ) -> None:
        self.provider = provider.lower()
        self.model = model
        self._last_trace: Dict[str, Any] = {}

        if self.provider == "dashscope":
            self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "缺少 DashScope API key，请设置 DASHSCOPE_API_KEY 或显式传入 api_key。"
                )
            self.dashscope_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        elif self.provider == "google":
            self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "缺少 Google API key，请设置 GOOGLE_API_KEY 或显式传入 api_key。"
                )
            self._init_google()
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _init_google(self) -> None:
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise ImportError(
                "缺少 Google Generative AI SDK，请先执行: pip install google-generativeai"
            ) from exc

        genai.configure(api_key=self.api_key)
        self.model_instance = genai.GenerativeModel(self.model)

    def _set_trace(
        self,
        *,
        operation: str,
        prompt: str,
        response_text: Optional[str] = None,
        parsed_response: Optional[Any] = None,
        status: str = "success",
        error: Optional[str] = None,
        fallback_used: bool = False,
    ) -> None:
        self._last_trace = {
            "operation": operation,
            "provider": self.provider,
            "model": self.model,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "fallback_used": fallback_used,
            "prompt": prompt,
            "response_text": response_text,
            "parsed_response": parsed_response,
            "error": error,
        }

    def get_last_trace(self) -> Dict[str, Any]:
        return dict(self._last_trace)

    def _generate_content(self, prompt: str) -> str:
        if self.provider == "dashscope":
            return self._generate_dashscope(prompt)
        if self.provider == "google":
            return self._generate_google(prompt)
        raise ValueError(f"Unsupported provider: {self.provider}")

    def _generate_dashscope(self, prompt: str) -> str:
        import json as _json
        import urllib.error
        import urllib.request

        req = urllib.request.Request(
            f"{self.dashscope_base_url}/chat/completions",
            data=_json.dumps(
                {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                }
            ).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = _json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise Exception(f"DashScope HTTP {exc.code}: {body}") from exc

        return data["choices"][0]["message"]["content"]

    def _generate_google(self, prompt: str) -> str:
        return self.model_instance.generate_content(prompt).text

    @staticmethod
    def _parse_json_response(result_text: str) -> Dict[str, Any]:
        if "```json" in result_text:
            result_text = result_text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```", 1)[1].split("```", 1)[0].strip()
        return json.loads(result_text)

    def decide_analysis_strategy(self, dataset_info: Dict[str, Any]) -> Dict[str, Any]:
        prompt = build_analysis_strategy_prompt(dataset_info)
        try:
            response_text = self._generate_content(prompt)
            result = self._parse_json_response(response_text)
            result["llm_used"] = True
            result["timestamp"] = datetime.now().isoformat()
            self._set_trace(
                operation="decide_analysis_strategy",
                prompt=prompt,
                response_text=response_text,
                parsed_response=result,
            )
            return result
        except Exception as exc:
            print(f"Strategy decision failed: {exc}")
            fallback = self._fallback_strategy_decision(dataset_info)
            self._set_trace(
                operation="decide_analysis_strategy",
                prompt=prompt,
                parsed_response=fallback,
                status="fallback",
                error=str(exc),
                fallback_used=True,
            )
            return fallback

    def decide_visualization_strategy(
        self,
        analysis_strategy: str,
        data_characteristics: Dict[str, Any],
    ) -> Dict[str, Any]:
        prompt = build_visualization_strategy_prompt(
            analysis_strategy,
            data_characteristics,
        )
        try:
            response_text = self._generate_content(prompt)
            result = self._parse_json_response(response_text)
            result["llm_used"] = True
            self._set_trace(
                operation="decide_visualization_strategy",
                prompt=prompt,
                response_text=response_text,
                parsed_response=result,
            )
            return result
        except Exception as exc:
            print(f"Visualization decision failed: {exc}")
            fallback = self._fallback_visualization_decision(analysis_strategy)
            self._set_trace(
                operation="decide_visualization_strategy",
                prompt=prompt,
                parsed_response=fallback,
                status="fallback",
                error=str(exc),
                fallback_used=True,
            )
            return fallback

    def interpret_results(
        self,
        dataset_info: Dict[str, Any],
        ssgsea_scores: Dict[str, Any],
        statistical_results: Optional[Dict[str, Any]] = None,
    ) -> str:
        score_summary = self._prepare_score_summary(ssgsea_scores)
        prompt = build_result_interpretation_prompt(
            dataset_info,
            score_summary,
            statistical_results,
        )

        try:
            interpretation = self._generate_content(prompt)
            rendered = (
                "# 分析结果解读\n\n"
                f"**数据集**: {dataset_info.get('chinese_name', 'Unknown')} ({dataset_info.get('name', 'Unknown')})\n"
                f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"**模型**: {self.model} ({self.provider})\n\n"
                "---\n\n"
                f"{interpretation}\n\n"
                "---\n\n"
                "*以上内容由 AI 生成，建议结合原始结果进行复核。*\n"
            )
            self._set_trace(
                operation="interpret_results",
                prompt=prompt,
                response_text=interpretation,
                parsed_response={"interpretation_preview": interpretation[:300]},
            )
            return rendered
        except Exception as exc:
            print(f"Interpretation failed: {exc}")
            fallback = self._fallback_interpretation(dataset_info)
            self._set_trace(
                operation="interpret_results",
                prompt=prompt,
                response_text=fallback,
                parsed_response={"interpretation_preview": fallback[:300]},
                status="fallback",
                error=str(exc),
                fallback_used=True,
            )
            return fallback

    def select_next_dataset(self, prompt: str) -> Dict[str, Any]:
        try:
            response_text = self._generate_content(prompt)
            result = self._parse_json_response(response_text)
            result["llm_used"] = True
            result["timestamp"] = datetime.now().isoformat()
            self._set_trace(
                operation="select_next_dataset",
                prompt=prompt,
                response_text=response_text,
                parsed_response=result,
            )
            return result
        except Exception as exc:
            fallback = {
                "selected_dataset_id": None,
                "reasoning": f"LLM 选择失败: {exc}",
                "llm_used": False,
            }
            self._set_trace(
                operation="select_next_dataset",
                prompt=prompt,
                parsed_response=fallback,
                status="fallback",
                error=str(exc),
                fallback_used=True,
            )
            return fallback

    def generate_report_summary(
        self,
        dataset_info: Dict[str, Any],
        analysis_results: Dict[str, Any],
    ) -> str:
        prompt = build_report_summary_prompt(dataset_info, analysis_results)
        try:
            response_text = self._generate_content(prompt)
            self._set_trace(
                operation="generate_report_summary",
                prompt=prompt,
                response_text=response_text,
                parsed_response={"summary_preview": response_text[:300]},
            )
            return response_text
        except Exception as exc:
            print(f"Report summary failed: {exc}")
            fallback = (
                f"已完成 {dataset_info.get('chinese_name', 'Unknown')} 的五维分析，"
                "但自动摘要生成失败，请结合详细结果手动整理摘要。"
            )
            self._set_trace(
                operation="generate_report_summary",
                prompt=prompt,
                response_text=fallback,
                parsed_response={"summary_preview": fallback[:300]},
                status="fallback",
                error=str(exc),
                fallback_used=True,
            )
            return fallback

    @staticmethod
    def _prepare_score_summary(ssgsea_scores: Dict[str, Any]) -> str:
        if not ssgsea_scores:
            return "无 ssGSEA 得分。"

        systems = {
            "A": ["A1", "A2", "A3", "A4"],
            "B": ["B1", "B2", "B3"],
            "C": ["C1", "C2", "C3"],
            "D": ["D1", "D2"],
            "E": ["E1", "E2"],
        }

        summary_lines = []
        for system, subcats in systems.items():
            system_scores = []
            for subcat in subcats:
                if subcat in ssgsea_scores:
                    mean_score = ssgsea_scores[subcat].get("mean_score", 0)
                    system_scores.append(f"{subcat}: {mean_score:.3f}")
            if system_scores:
                summary_lines.append(f"System {system}: {', '.join(system_scores)}")

        return "\n".join(summary_lines) if summary_lines else "无 ssGSEA 得分。"

    @staticmethod
    def _fallback_strategy_decision(dataset_info: Dict[str, Any]) -> Dict[str, Any]:
        disease_type = dataset_info.get("disease_type", "unknown")
        strategy_map = {
            "neurodegenerative": "case_control",
            "cancer": "subtype_comparison",
            "metabolic": "case_control",
            "repair": "time_series",
            "infection": "case_control",
        }
        strategy = strategy_map.get(disease_type, "case_control")
        return {
            "strategy": strategy,
            "reasoning": f"根据疾病类型 {disease_type} 使用默认分析策略。",
            "confidence": 0.7,
            "secondary_analyses": ["correlation"],
            "key_focus": ["系统激活模式"],
            "llm_used": False,
        }

    @staticmethod
    def _fallback_visualization_decision(analysis_strategy: str) -> Dict[str, Any]:
        viz_map = {
            "case_control": ["heatmap", "boxplot", "volcano"],
            "subtype_comparison": ["clustering", "heatmap", "network"],
            "time_series": ["time_series", "heatmap", "trajectory"],
            "correlation": ["correlation_heatmap", "network"],
        }
        return {
            "primary_visualizations": viz_map.get(analysis_strategy, ["heatmap"]),
            "secondary_visualizations": [],
            "reasoning": "根据当前分析策略使用默认可视化方案。",
            "layout_suggestions": "单页纵向布局",
            "llm_used": False,
        }

    @staticmethod
    def _fallback_interpretation(dataset_info: Dict[str, Any]) -> str:
        return (
            "# 分析结果解读\n\n"
            f"**数据集**: {dataset_info.get('chinese_name', 'Unknown')}\n\n"
            "自动解读当前不可用，但 ssGSEA 得分和生成图表仍可用于人工复核。\n"
        )


def create_llm_integration(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> LLMClient:
    if provider is None or model is None:
        try:
            from .runtime_config import AgentConfig

            config = AgentConfig.LLM_CONFIG
            provider = provider or config.get("provider", "dashscope")
            model = model or config.get("model", "qwen3.5-122b-a10b")
        except Exception:
            provider = provider or "dashscope"
            model = model or "qwen3.5-122b-a10b"

    return LLMClient(api_key=api_key, model=model, provider=provider)
