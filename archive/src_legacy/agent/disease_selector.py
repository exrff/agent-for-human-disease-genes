#!/usr/bin/env python3
"""
疾病选择智能体

功能：
1. 扫描已分析的疾病数据集
2. 分析已有结果的模式和特征
3. 使用 LLM 推荐下一个最有价值的疾病数据集
4. 考虑系统覆盖度、疾病类型多样性等因素
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from .prompts import build_dataset_selection_prompt


class DiseaseSelector:
    """疾病选择智能体"""
    
    def __init__(self, results_dir: str = "results/agent_analysis"):
        self.results_dir = Path(results_dir)
        self.logger = logging.getLogger(__name__)
    
    def scan_analyzed_datasets(self) -> Dict[str, Any]:
        """
        扫描已分析的数据集。
        
        来源1: results/agent_analysis/ 下的 summary.json（agent 自动分析的）
        来源2: data/validation_datasets/ 下的文件夹（手动分析的，文件夹名格式 GSExxxx-疾病名）
        
        Returns:
            包含已分析数据集信息的字典
        """
        analyzed = {
            'datasets': [],
            'disease_types': set(),
            'system_coverage': {},
            'total_count': 0
        }
        
        seen_ids = set()
        
        # --- 来源1: agent 自动分析结果（有 summary.json）---
        if self.results_dir.exists():
            for dataset_dir in self.results_dir.iterdir():
                if not dataset_dir.is_dir():
                    continue
                summary_file = dataset_dir / "summary.json"
                if not summary_file.exists():
                    summary_file = dataset_dir / "analysis_summary.json"
                if summary_file.exists():
                    try:
                        with open(summary_file, 'r', encoding='utf-8') as f:
                            summary = json.load(f)
                        
                        dataset_id = dataset_dir.name
                        seen_ids.add(dataset_id)
                        
                        analyzed['datasets'].append({
                            'dataset_id': dataset_id,
                            'disease_type': summary.get('disease_type'),
                            'analysis_date': summary.get('analysis_time') or summary.get('analysis_date'),
                            'systems_activated': summary.get('top_systems', []),
                            'strategy_used': summary.get('analysis_strategy'),
                            'source': 'agent'
                        })
                        
                        disease_type = summary.get('disease_type')
                        if disease_type:
                            analyzed['disease_types'].add(disease_type)
                        
                        for system in summary.get('top_systems', []):
                            analyzed['system_coverage'][system] = \
                                analyzed['system_coverage'].get(system, 0) + 1
                        
                        analyzed['total_count'] += 1
                        
                    except Exception as e:
                        self.logger.warning(f"无法读取 {summary_file}: {e}")
        
        # --- 来源2: data/validation_datasets/ 手动分析的数据集 ---
        # 文件夹名格式: GSE2034-乳腺癌, GSE122063-阿尔兹海默症 等
        validation_dir = Path("data/validation_datasets")
        if validation_dir.exists():
            for folder in validation_dir.iterdir():
                if not folder.is_dir():
                    continue
                
                folder_name = folder.name  # e.g. "GSE2034-乳腺癌"
                parts = folder_name.split('-', 1)
                dataset_id = parts[0]  # e.g. "GSE2034"
                chinese_name = parts[1] if len(parts) > 1 else ''
                
                if not dataset_id.startswith('GSE'):
                    continue
                if dataset_id in seen_ids:
                    continue
                
                seen_ids.add(dataset_id)
                
                # 从 AgentConfig 中查找疾病类型信息
                disease_type = self._lookup_disease_type(dataset_id, chinese_name)
                
                analyzed['datasets'].append({
                    'dataset_id': dataset_id,
                    'disease_type': disease_type or chinese_name or 'unknown',
                    'analysis_date': None,
                    'systems_activated': [],
                    'strategy_used': 'manual',
                    'source': 'manual'
                })
                
                if disease_type:
                    analyzed['disease_types'].add(disease_type)
                
                analyzed['total_count'] += 1
                self.logger.debug(f"  手动数据集: {dataset_id} ({chinese_name})")
        
        analyzed['disease_types'] = list(analyzed['disease_types'])
        
        return analyzed
    
    def _lookup_disease_type(self, dataset_id: str, chinese_name: str) -> Optional[str]:
        """从 AgentConfig 中查找数据集的疾病类型"""
        from .whitelist_repository import get_dataset_info
        info = get_dataset_info(dataset_id)
        if info:
            return info.get('disease_type')
        return None

    
    def get_available_datasets(self) -> List[Dict[str, Any]]:
        """
        获取所有可用的数据集（核心白名单 + geo_whitelist.csv）
        """
        from .whitelist_repository import load_whitelist_datasets

        available = []
        for dataset_id, info in load_whitelist_datasets().items():
            available.append({
                'dataset_id': dataset_id,
                'name': info['name'],
                'chinese_name': info['chinese_name'],
                'disease_type': info['disease_type'],
                'expected_systems': info['expected_systems'],
                'description': info['description'],
                'n_samples': info.get('n_samples', 0),
            })

        return available
    
    def select_next_dataset_with_llm(
        self, 
        analyzed: Dict[str, Any],
        available: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        使用 LLM 从白名单中选择下一个最有价值的数据集。
        LLM 只做"选哪个"的决策，不允许自由推荐白名单外的 GSE 编号。
        """
        try:
            from .llm_client import create_llm_integration
            llm = create_llm_integration()

            analyzed_ids = {d['dataset_id'] for d in analyzed['datasets']}
            unanalyzed = [d for d in available if d['dataset_id'] not in analyzed_ids]

            if not unanalyzed:
                self.logger.info("白名单中所有数据集均已分析完成")
                return None

            self.logger.info(f"从白名单中选择（剩余 {len(unanalyzed)} 个未分析）...")
            prompt = self._build_selection_prompt(analyzed, unanalyzed)
            response = llm.select_next_dataset(prompt)

            selected_id = response.get('selected_dataset_id')
            reasoning = response.get('reasoning', '')

            # 严格校验：必须在白名单内
            if selected_id:
                selected = next((d for d in unanalyzed if d['dataset_id'] == selected_id), None)
                if selected:
                    selected['selection_reasoning'] = reasoning
                    self.logger.info(f"LLM 推荐数据集: {selected_id}")
                    self.logger.info(f"推荐理由: {reasoning}")
                    return selected
                else:
                    self.logger.warning(
                        f"LLM 推荐了白名单外的 {selected_id}，回退到规则引擎"
                    )

            return self.select_next_dataset_with_rules(analyzed, available)

        except Exception as e:
            self.logger.error(f"LLM 选择失败: {e}", exc_info=True)
            return self.select_next_dataset_with_rules(analyzed, available)

    
    def select_next_dataset_with_rules(
        self,
        analyzed: Dict[str, Any],
        available: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        使用规则引擎选择下一个数据集
        
        优先级：
        1. 未覆盖的疾病类型
        2. 未充分激活的系统
        3. 不同的分析策略
        
        Args:
            analyzed: 已分析数据集信息
            available: 可用数据集列表
        
        Returns:
            推荐的数据集
        """
        # 过滤已分析的
        analyzed_ids = {d['dataset_id'] for d in analyzed['datasets']}
        unanalyzed = [d for d in available if d['dataset_id'] not in analyzed_ids]
        
        if not unanalyzed:
            return None
        
        # 评分系统
        scores = []
        
        for dataset in unanalyzed:
            score = 0
            reasons = []
            
            # 1. 疾病类型多样性（权重：3）
            if dataset['disease_type'] not in analyzed['disease_types']:
                score += 3
                reasons.append(f"新疾病类型: {dataset['disease_type']}")
            
            # 2. 系统覆盖度（权重：2）
            for system in dataset['expected_systems']:
                if system not in analyzed['system_coverage']:
                    score += 2
                    reasons.append(f"新系统: {system}")
                elif analyzed['system_coverage'][system] < 2:
                    score += 1
                    reasons.append(f"系统覆盖不足: {system}")
            
            # 3. 数据集重要性（基于描述关键词）
            important_keywords = ['cancer', 'neurodegenerative', 'metabolic']
            if any(kw in dataset['disease_type'].lower() for kw in important_keywords):
                score += 1
                reasons.append("重要疾病类型")
            
            scores.append({
                'dataset': dataset,
                'score': score,
                'reasons': reasons
            })
        
        # 按分数排序
        scores.sort(key=lambda x: x['score'], reverse=True)
        
        if scores:
            best = scores[0]
            best['dataset']['selection_reasoning'] = \
                f"规则引擎推荐 (得分: {best['score']}): " + "; ".join(best['reasons'])
            
            self.logger.info(f"规则引擎推荐: {best['dataset']['dataset_id']}")
            self.logger.info(f"推荐理由: {best['dataset']['selection_reasoning']}")
            
            return best['dataset']
        
        return None

    def _build_selection_prompt(
        self,
        analyzed: Dict[str, Any],
        unanalyzed: List[Dict[str, Any]]
    ) -> str:
        """构建 LLM 选择提示（只能从白名单中选）"""
        
        prompt = f"""# 疾病数据集选择任务

你是一个生物医学研究助手。请从下方**候选数据集列表**中选择下一个最有价值的进行分析。

⚠️ 重要约束：你**只能**从"候选数据集"列表中选择，必须返回列表中存在的 dataset_id，不得推荐任何列表外的数据集。

## 已分析数据集 ({analyzed['total_count']} 个)

"""
        if analyzed['datasets']:
            for d in analyzed['datasets']:
                prompt += f"- **{d['dataset_id']}**: {d['disease_type']}, "
                prompt += f"激活系统: {', '.join(d.get('systems_activated', []))}\n"
        else:
            prompt += "（尚未分析任何数据集）\n"

        prompt += f"\n## 已覆盖疾病类型\n{', '.join(analyzed['disease_types']) if analyzed['disease_types'] else '无'}\n"

        prompt += "\n## 系统激活统计\n"
        if analyzed['system_coverage']:
            for system, count in sorted(analyzed['system_coverage'].items()):
                prompt += f"- {system}: {count} 次\n"
        else:
            prompt += "（尚无统计数据）\n"

        prompt += f"\n## 候选数据集（共 {len(unanalyzed)} 个，只能从此列表选择）\n\n"
        for d in unanalyzed:
            prompt += (
                f"- **{d['dataset_id']}** | {d['chinese_name']} ({d['name']}) | "
                f"疾病类型: {d['disease_type']} | "
                f"预期系统: {', '.join(d['expected_systems'])} | "
                f"样本数: {d.get('n_samples', '?')} | "
                f"{d['description']}\n"
            )

        prompt += """
## 选择标准

1. 疾病类型多样性：优先选择未覆盖的疾病类型
2. 系统覆盖完整性：优先选择能激活未充分研究系统的数据集
3. 科学价值：考虑疾病的重要性和研究意义
4. 互补性：与已有结果形成对比或互补

## 输出格式

```json
{
    "selected_dataset_id": "候选列表中的某个 dataset_id",
    "reasoning": "选择理由（2-3句话）",
    "expected_insights": "预期发现（1-2句话）"
}
```

只返回 JSON，不要其他内容。
"""
        return prompt
    
    def _build_selection_prompt(
        self,
        analyzed: Dict[str, Any],
        unanalyzed: List[Dict[str, Any]]
    ) -> str:
        """Centralized dataset-selection prompt builder."""
        return build_dataset_selection_prompt(analyzed, unanalyzed)

    def run(self, use_llm: bool = True) -> Optional[Dict[str, Any]]:
        """
        运行疾病选择智能体
        
        Args:
            use_llm: 是否使用 LLM（如果为 False 或失败，使用规则引擎）
        
        Returns:
            推荐的数据集信息
        """
        self.logger.info("=" * 60)
        self.logger.info("疾病选择智能体启动")
        self.logger.info("=" * 60)
        
        # 1. 扫描已分析的数据集
        self.logger.info("步骤 1: 扫描已分析数据集...")
        analyzed = self.scan_analyzed_datasets()
        manual_count = sum(1 for d in analyzed['datasets'] if d.get('source') == 'manual')
        agent_count = sum(1 for d in analyzed['datasets'] if d.get('source') == 'agent')
        self.logger.info(f"  已分析: {analyzed['total_count']} 个数据集 (手动: {manual_count}, agent: {agent_count})")
        self.logger.info(f"  疾病类型: {', '.join(analyzed['disease_types']) if analyzed['disease_types'] else '无'}")
        
        # 2. 获取可用数据集
        self.logger.info("步骤 2: 获取可用数据集...")
        available = self.get_available_datasets()
        self.logger.info(f"  可用数据集: {len(available)} 个")
        
        # 3. 选择下一个数据集
        self.logger.info("步骤 3: 选择下一个数据集...")
        
        if use_llm:
            selected = self.select_next_dataset_with_llm(analyzed, available)
        else:
            selected = self.select_next_dataset_with_rules(analyzed, available)
        
        if selected:
            self.logger.info("=" * 60)
            self.logger.info(f"✅ 推荐数据集: {selected['dataset_id']}")
            self.logger.info(f"   名称: {selected['chinese_name']}")
            self.logger.info(f"   理由: {selected.get('selection_reasoning', '无')}")
            self.logger.info("=" * 60)
        else:
            self.logger.info("=" * 60)
            self.logger.info("⚠️  没有可分析的数据集")
            self.logger.info("=" * 60)
        
        return selected


# ============================================================================
# 便捷函数
# ============================================================================

def select_next_disease(use_llm: bool = True) -> Optional[str]:
    """
    选择下一个要分析的疾病数据集
    
    Args:
        use_llm: 是否使用 LLM
    
    Returns:
        数据集 ID，如果没有可分析的返回 None
    """
    selector = DiseaseSelector()
    selected = selector.run(use_llm=use_llm)
    
    if selected:
        return selected['dataset_id']
    
    return None
