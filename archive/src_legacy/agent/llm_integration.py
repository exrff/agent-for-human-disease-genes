#!/usr/bin/env python3
"""
LLM 集成模块 - 支持多种 LLM 提供商

支持：
- 阿里云百炼 (DashScope)
- Google Gemini
- OpenAI (可选)
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from .prompts import (
    build_analysis_strategy_prompt,
    build_report_summary_prompt,
    build_result_interpretation_prompt,
    build_visualization_strategy_prompt,
)


class LLMIntegration:
    """LLM 集成类 - 支持多种提供商"""
    
    def __init__(self, 
                 api_key: Optional[str] = None, 
                 model: str = "qwen3.5-122b-a10b",
                 provider: str = "dashscope"):
        """
        初始化 LLM 集成
        
        Args:
            api_key: API Key，如果为 None 则从环境变量读取
            model: 模型名称
                - DashScope: qwen3.5-122b-a10b, qwen-plus, qwen-max
            provider: 提供商 ('dashscope', 'google', 'openai')
        """
        self.provider = provider.lower()
        self.model = model
        
        # 根据提供商设置 API Key
        if self.provider == "dashscope":
            self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "未找到 DashScope API Key。请设置环境变量 DASHSCOPE_API_KEY "
                    "或在初始化时传入 api_key 参数"
                )
            self._init_dashscope()
            
        elif self.provider == "google":
            self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "未找到 Google API Key。请设置环境变量 GOOGLE_API_KEY "
                    "或在初始化时传入 api_key 参数"
                )
            self._init_google()
            
        else:
            raise ValueError(f"不支持的提供商: {provider}")
    
    def _init_dashscope(self):
        """初始化阿里云百炼 DashScope（使用 OpenAI 兼容接口）"""
        # 不依赖 dashscope SDK，直接用 urllib 调用兼容接口
        self.dashscope_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        print(f"✅ 阿里云百炼 DashScope ({self.model}) 初始化成功")
    
    def _init_google(self):
        """初始化 Google Gemini"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.genai = genai
            self.model_instance = genai.GenerativeModel(self.model)
            print(f"✅ Google Gemini ({self.model}) 初始化成功")
        except ImportError:
            raise ImportError(
                "请安装 Google Generative AI SDK: "
                "pip install google-generativeai"
            )
    
    def _generate_content(self, prompt: str) -> str:
        """
        统一的内容生成接口
        
        Args:
            prompt: 提示词
            
        Returns:
            生成的文本
        """
        if self.provider == "dashscope":
            return self._generate_dashscope(prompt)
        elif self.provider == "google":
            return self._generate_google(prompt)
        else:
            raise ValueError(f"不支持的提供商: {self.provider}")
    
    def _generate_dashscope(self, prompt: str) -> str:
        """使用 DashScope OpenAI 兼容接口生成内容"""
        import urllib.request
        import urllib.error
        import json as _json

        url = f"{self.dashscope_base_url}/chat/completions"
        payload = _json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = _json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            raise Exception(f"DashScope HTTP {e.code}: {body}") from e

        return data["choices"][0]["message"]["content"]
    
    def _generate_google(self, prompt: str) -> str:
        """使用 Google Gemini 生成内容"""
        response = self.model_instance.generate_content(prompt)
        return response.text
    
    def decide_analysis_strategy(self, dataset_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 LLM 决策分析策略
        
        Args:
            dataset_info: 数据集信息
            
        Returns:
            决策结果，包含策略、理由等
        """
        prompt = f"""
你是一个生物信息学分析专家。请根据以下数据集信息，决定最合适的分析策略。

数据集信息：
- ID: {dataset_info.get('dataset_id', 'Unknown')}
- 名称: {dataset_info.get('name', 'Unknown')}
- 中文名: {dataset_info.get('chinese_name', 'Unknown')}
- 疾病类型: {dataset_info.get('disease_type', 'Unknown')}
- 描述: {dataset_info.get('description', 'Unknown')}

可选的分析策略：
1. case_control - 病例对照分析（适用于正常vs异常样本）
2. subtype_comparison - 亚型比较分析（适用于多个疾病亚型）
3. time_series - 时序分析（适用于时间序列数据）
4. correlation - 相关性分析（适用于探索系统间关系）

请以 JSON 格式返回你的决策：
{{
    "strategy": "选择的策略名称",
    "reasoning": "选择理由（中文，2-3句话）",
    "confidence": 0.0-1.0之间的置信度,
    "secondary_analyses": ["建议的补充分析"],
    "key_focus": ["分析重点"]
}}

只返回 JSON，不要其他内容。
"""
        
        try:
            result_text = self._generate_content(prompt)
            
            # 提取 JSON（可能被 markdown 代码块包裹）
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            result['llm_used'] = True
            result['timestamp'] = datetime.now().isoformat()
            
            return result
            
        except Exception as e:
            print(f"⚠️  LLM 决策失败，使用规则引擎: {e}")
            # 回退到规则引擎
            return self._fallback_strategy_decision(dataset_info)
    
    def decide_visualization_strategy(self, 
                                     analysis_strategy: str,
                                     data_characteristics: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 LLM 决策可视化策略
        
        Args:
            analysis_strategy: 分析策略
            data_characteristics: 数据特征（样本数、分组信息等）
            
        Returns:
            可视化决策结果
        """
        prompt = f"""
你是一个数据可视化专家。请根据分析策略和数据特征，推荐最合适的可视化方案。

分析策略: {analysis_strategy}

数据特征:
{json.dumps(data_characteristics, ensure_ascii=False, indent=2)}

可选的可视化类型：
- heatmap: 热图（展示系统激活模式）
- boxplot: 箱线图（比较组间差异）
- volcano: 火山图（差异表达分析）
- time_series: 时序图（展示时间变化）
- clustering: 聚类图（识别亚型）
- network: 网络图（展示系统间关系）
- correlation_heatmap: 相关性热图
- trajectory: 轨迹图（时序轨迹）

请以 JSON 格式返回你的推荐：
{{
    "primary_visualizations": ["主要可视化类型"],
    "secondary_visualizations": ["补充可视化类型"],
    "reasoning": "推荐理由（中文）",
    "layout_suggestions": "布局建议"
}}

只返回 JSON，不要其他内容。
"""
        
        try:
            result_text = self._generate_content(prompt)
            
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            result['llm_used'] = True
            
            return result
            
        except Exception as e:
            print(f"⚠️  LLM 可视化决策失败，使用默认方案: {e}")
            return self._fallback_visualization_decision(analysis_strategy)
    
    def interpret_results(self, 
                         dataset_info: Dict[str, Any],
                         ssgsea_scores: Dict[str, Any],
                         statistical_results: Optional[Dict[str, Any]] = None) -> str:
        """
        使用 LLM 解读分析结果
        
        Args:
            dataset_info: 数据集信息
            ssgsea_scores: ssGSEA 得分
            statistical_results: 统计分析结果
            
        Returns:
            结果解读文本
        """
        # 准备 ssGSEA 得分摘要
        score_summary = self._prepare_score_summary(ssgsea_scores)
        
        prompt = f"""
你是一个生物医学研究专家。请对以下疾病数据集的分析结果进行专业解读。

数据集信息：
- 名称: {dataset_info.get('name', 'Unknown')}
- 中文名: {dataset_info.get('chinese_name', 'Unknown')}
- 疾病类型: {dataset_info.get('disease_type', 'Unknown')}
- 描述: {dataset_info.get('description', 'Unknown')}

五大功能系统分类框架：
- System A (稳态与修复): A1-基因组稳定性, A2-体细胞维持, A3-细胞稳态, A4-炎症消解
- System B (免疫防御): B1-先天免疫, B2-适应性免疫, B3-免疫调节
- System C (代谢调节): C1-能量代谢, C2-生物合成, C3-解毒代谢
- System D (调节协调): D1-神经调节, D2-内分泌调节
- System E (生殖发育): E1-生殖, E2-发育

ssGSEA 分析结果（14个子类的激活得分）：
{score_summary}

统计分析结果：
{json.dumps(statistical_results, ensure_ascii=False, indent=2) if statistical_results else "暂无"}

请提供以下内容的专业解读（中文）：

1. 主要发现（2-3段）
   - 哪些系统被显著激活？
   - 激活模式与疾病病理机制的关联
   - 与预期的生物学过程是否一致

2. 生物学意义（2-3段）
   - 激活的系统在疾病中的作用
   - 系统间的协同或拮抗关系
   - 对疾病进展的影响

3. 临床意义（1-2段）
   - 潜在的治疗靶点
   - 对疾病分型或预后的提示
   - 可能的干预策略

4. 研究局限和未来方向（1段）

请用专业但易懂的语言撰写，适合发表在学术论文中。
"""
        
        try:
            interpretation = self._generate_content(prompt)
            
            # 添加元信息
            interpretation = f"""# 分析结果解读

**数据集**: {dataset_info.get('chinese_name', 'Unknown')} ({dataset_info.get('name', 'Unknown')})
**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**解读模型**: {self.model} ({self.provider})

---

{interpretation}

---

*本解读由 AI 辅助生成，建议结合专业知识进行验证。*
"""
            
            return interpretation
            
        except Exception as e:
            print(f"⚠️  LLM 结果解读失败: {e}")
            return self._fallback_interpretation(dataset_info, ssgsea_scores)
    
    def select_next_dataset(self, prompt: str) -> Dict[str, Any]:
        """
        使用 LLM 选择下一个要分析的数据集
        """
        try:
            result_text = self._generate_content(prompt)

            # 提取 JSON（可能被 markdown 代码块包裹）
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result = json.loads(result_text)
            result['llm_used'] = True
            result['timestamp'] = datetime.now().isoformat()

            return result

        except Exception as e:
            import traceback
            print(f"⚠️  LLM 数据集选择失败: {e}")
            print(traceback.format_exc())
            return {
                'selected_dataset_id': None,
                'reasoning': f'LLM 选择失败: {e}',
                'llm_used': False
            }

    def generate_report_summary(self,
                               dataset_info: Dict[str, Any],
                               analysis_results: Dict[str, Any]) -> str:
        """
        生成报告摘要
        
        Args:
            dataset_info: 数据集信息
            analysis_results: 完整的分析结果
            
        Returns:
            报告摘要文本
        """
        prompt = f"""
请为以下疾病数据集分析生成一个简洁的摘要（Abstract），适合放在报告开头。

数据集: {dataset_info.get('chinese_name', 'Unknown')}
分析策略: {analysis_results.get('analysis_strategy', 'Unknown')}
主要发现: {analysis_results.get('key_findings', [])}

要求：
- 150-200字
- 包含：研究目的、方法、主要发现、结论
- 中文撰写
- 学术风格

只返回摘要文本，不要标题。
"""
        
        try:
            return self._generate_content(prompt)
        except Exception as e:
            print(f"⚠️  LLM 摘要生成失败: {e}")
            return f"本研究对 {dataset_info.get('chinese_name', 'Unknown')} 数据集进行了五大功能系统分类分析。"

    def _prepare_score_summary(self, ssgsea_scores: Dict[str, Any]) -> str:
        """准备 ssGSEA 得分摘要"""
        if not ssgsea_scores:
            return "暂无得分数据"
        
        summary_lines = []
        
        # 按系统分组
        systems = {
            'A': ['A1', 'A2', 'A3', 'A4'],
            'B': ['B1', 'B2', 'B3'],
            'C': ['C1', 'C2', 'C3'],
            'D': ['D1', 'D2'],
            'E': ['E1', 'E2']
        }
        
        for system, subcats in systems.items():
            system_scores = []
            for subcat in subcats:
                if subcat in ssgsea_scores:
                    score_info = ssgsea_scores[subcat]
                    mean_score = score_info.get('mean_score', 0)
                    system_scores.append(f"{subcat}: {mean_score:.3f}")
            
            if system_scores:
                summary_lines.append(f"System {system}: {', '.join(system_scores)}")
        
        return "\n".join(summary_lines)
    
    def _fallback_strategy_decision(self, dataset_info: Dict[str, Any]) -> Dict[str, Any]:
        """规则引擎回退方案"""
        disease_type = dataset_info.get('disease_type', 'unknown')
        
        strategy_map = {
            'neurodegenerative': 'case_control',
            'cancer': 'subtype_comparison',
            'metabolic': 'case_control',
            'repair': 'time_series',
            'infection': 'case_control'
        }
        
        strategy = strategy_map.get(disease_type, 'case_control')
        
        return {
            'strategy': strategy,
            'reasoning': f'基于疾病类型 {disease_type} 的规则引擎决策',
            'confidence': 0.7,
            'secondary_analyses': ['correlation'],
            'key_focus': ['系统激活模式'],
            'llm_used': False
        }
    
    def _fallback_visualization_decision(self, analysis_strategy: str) -> Dict[str, Any]:
        """可视化决策回退方案"""
        viz_map = {
            'case_control': ['heatmap', 'boxplot', 'volcano'],
            'subtype_comparison': ['clustering', 'heatmap', 'network'],
            'time_series': ['time_series', 'heatmap', 'trajectory'],
            'correlation': ['correlation_heatmap', 'network']
        }
        
        return {
            'primary_visualizations': viz_map.get(analysis_strategy, ['heatmap']),
            'secondary_visualizations': [],
            'reasoning': '基于分析策略的默认可视化方案',
            'layout_suggestions': '标准布局',
            'llm_used': False
        }
    
    def _fallback_interpretation(self, 
                                dataset_info: Dict[str, Any],
                                ssgsea_scores: Dict[str, Any]) -> str:
        """结果解读回退方案"""
        return f"""# 分析结果解读

**数据集**: {dataset_info.get('chinese_name', 'Unknown')}

## 主要发现

本研究对 {dataset_info.get('chinese_name', 'Unknown')} 数据集进行了五大功能系统分类分析。
通过 ssGSEA 方法计算了14个功能子类的激活得分。

## 系统激活模式

分析结果显示了不同功能系统的激活模式，反映了疾病相关的生物学过程。

*注：由于 LLM 服务不可用，此为简化版解读。建议人工审核分析结果。*
"""


# 便捷函数
    def decide_analysis_strategy(self, dataset_info: Dict[str, Any]) -> Dict[str, Any]:
        """Use centralized prompt builder for strategy selection."""
        prompt = build_analysis_strategy_prompt(dataset_info)

        try:
            result_text = self._generate_content(prompt)

            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result = json.loads(result_text)
            result['llm_used'] = True
            result['timestamp'] = datetime.now().isoformat()
            return result

        except Exception as e:
            print(f"Strategy decision failed: {e}")
            return self._fallback_strategy_decision(dataset_info)

    def decide_visualization_strategy(
        self,
        analysis_strategy: str,
        data_characteristics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use centralized prompt builder for visualization recommendations."""
        prompt = build_visualization_strategy_prompt(
            analysis_strategy,
            data_characteristics,
        )

        try:
            result_text = self._generate_content(prompt)

            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result = json.loads(result_text)
            result['llm_used'] = True
            return result

        except Exception as e:
            print(f"Visualization decision failed: {e}")
            return self._fallback_visualization_decision(analysis_strategy)

    def interpret_results(
        self,
        dataset_info: Dict[str, Any],
        ssgsea_scores: Dict[str, Any],
        statistical_results: Optional[Dict[str, Any]] = None
    ) -> str:
        """Use centralized prompt builder for result interpretation."""
        score_summary = self._prepare_score_summary(ssgsea_scores)
        prompt = build_result_interpretation_prompt(
            dataset_info,
            score_summary,
            statistical_results,
        )

        try:
            interpretation = self._generate_content(prompt)
            interpretation = f"""# é’å—˜ç€½ç¼æ’´ç‰ç‘™ï½ˆî‡°

**éç‰ˆåµé—†?*: {dataset_info.get('chinese_name', 'Unknown')} ({dataset_info.get('name', 'Unknown')})
**é’å—˜ç€½éƒå •æ£¿**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**ç‘™ï½ˆî‡°å¦¯â€³ç€·**: {self.model} ({self.provider})

---

{interpretation}

---

*éˆî„ƒÐ’ç’‡è¤æ•± AI æˆå‘­å§ªé¢ç†¸åžšé”›å±½ç¼“ç’î†¾ç²¨éšå œç¬“æ¶“æ°±ç…¡ç’‡å—šç¹˜ç›å²„ç™ç’‡ä½µâ‚¬?
"""
            return interpretation

        except Exception as e:
            print(f"Interpretation failed: {e}")
            return self._fallback_interpretation(dataset_info, ssgsea_scores)

    def generate_report_summary(
        self,
        dataset_info: Dict[str, Any],
        analysis_results: Dict[str, Any]
    ) -> str:
        """Use centralized prompt builder for report summaries."""
        prompt = build_report_summary_prompt(dataset_info, analysis_results)

        try:
            return self._generate_content(prompt)
        except Exception as e:
            print(f"Report summary failed: {e}")
            return (
                f"éˆî„‚çˆºç»Œè·ºî‡® {dataset_info.get('chinese_name', 'Unknown')} "
                f"éç‰ˆåµé—†å—šç¹˜ç›å±¼ç°¡æµœæ–¿ã‡é”ç†»å…˜ç»¯è¤ç²ºé’å—™è¢«é’å—˜ç€½éŠ†?"
            )

def create_llm_integration(api_key: Optional[str] = None, 
                          model: Optional[str] = None,
                          provider: Optional[str] = None) -> LLMIntegration:
    """
    创建 LLM 集成实例
    
    Args:
        api_key: API Key（可选，默认从环境变量读取）
        model: 模型名称（可选，默认使用配置文件中的设置）
        provider: 提供商（可选，默认使用配置文件中的设置）
        
    Returns:
        LLMIntegration 实例
        
    Examples:
        # 使用默认配置（从 config.py 读取）
        llm = create_llm_integration()
        
        # 使用阿里云百炼
        llm = create_llm_integration(
            api_key="your_dashscope_key",
            model="qwen3.5-122b-a10b",
            provider="dashscope"
        )
        
        # 使用 Google Gemini
        llm = create_llm_integration(
            api_key="your_google_key",
            model="gemini-pro",
            provider="google"
        )
    """
    # 如果没有指定，从配置文件读取
    if provider is None or model is None:
        try:
            from .runtime_config import AgentConfig
            config = AgentConfig.LLM_CONFIG
            provider = provider or config.get('provider', 'dashscope')
            model = model or config.get('model', 'qwen3.5-122b-a10b')
        except:
            # 默认使用阿里云百炼
            provider = provider or 'dashscope'
            model = model or 'qwen3.5-122b-a10b'
    
    return LLMIntegration(api_key=api_key, model=model, provider=provider)
