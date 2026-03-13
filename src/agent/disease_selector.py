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


class DiseaseSelector:
    """疾病选择智能体"""
    
    def __init__(self, results_dir: str = "results/agent_analysis"):
        self.results_dir = Path(results_dir)
        self.logger = logging.getLogger(__name__)
    
    def scan_analyzed_datasets(self) -> Dict[str, Any]:
        """
        扫描已分析的数据集
        
        Returns:
            包含已分析数据集信息的字典
        """
        analyzed = {
            'datasets': [],
            'disease_types': set(),
            'system_coverage': {},
            'total_count': 0
        }
        
        if not self.results_dir.exists():
            self.logger.info("结果目录不存在，这是首次分析")
            return analyzed
        
        # 扫描结果目录
        for dataset_dir in self.results_dir.iterdir():
            if not dataset_dir.is_dir():
                continue
            
            # 查找 summary.json
            summary_file = dataset_dir / "summary.json"
            if summary_file.exists():
                try:
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        summary = json.load(f)
                    
                    analyzed['datasets'].append({
                        'dataset_id': dataset_dir.name,
                        'disease_type': summary.get('disease_type'),
                        'analysis_date': summary.get('analysis_date'),
                        'systems_activated': summary.get('top_systems', []),
                        'strategy_used': summary.get('analysis_strategy')
                    })
                    
                    # 统计疾病类型
                    disease_type = summary.get('disease_type')
                    if disease_type:
                        analyzed['disease_types'].add(disease_type)
                    
                    # 统计系统覆盖
                    for system in summary.get('top_systems', []):
                        analyzed['system_coverage'][system] = \
                            analyzed['system_coverage'].get(system, 0) + 1
                    
                    analyzed['total_count'] += 1
                    
                except Exception as e:
                    self.logger.warning(f"无法读取 {summary_file}: {e}")
        
        analyzed['disease_types'] = list(analyzed['disease_types'])
        
        return analyzed

    
    def get_available_datasets(self) -> List[Dict[str, Any]]:
        """
        获取所有可用的数据集
        
        Returns:
            可用数据集列表
        """
        from .config import AgentConfig
        
        available = []
        for dataset_id, info in AgentConfig.DATASETS.items():
            available.append({
                'dataset_id': dataset_id,
                'name': info['name'],
                'chinese_name': info['chinese_name'],
                'disease_type': info['disease_type'],
                'expected_systems': info['expected_systems'],
                'description': info['description']
            })
        
        return available
    
    def select_next_dataset_with_llm(
        self, 
        analyzed: Dict[str, Any],
        available: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        使用 LLM 选择下一个最有价值的数据集
        
        Args:
            analyzed: 已分析数据集信息
            available: 可用数据集列表
        
        Returns:
            推荐的数据集信息，如果失败返回 None
        """
        try:
            from .llm_integration import create_llm_integration
            
            llm = create_llm_integration()
            
            # 过滤掉已分析的数据集
            analyzed_ids = {d['dataset_id'] for d in analyzed['datasets']}
            unanalyzed = [d for d in available if d['dataset_id'] not in analyzed_ids]
            
            if not unanalyzed:
                self.logger.info("所有数据集都已分析完成")
                return None
            
            # 构建 LLM 提示
            prompt = self._build_selection_prompt(analyzed, unanalyzed)
            
            # 调用 LLM
            response = llm.select_next_dataset(prompt)
            
            # 解析响应
            selected_id = response.get('selected_dataset_id')
            reasoning = response.get('reasoning', '')
            
            if selected_id:
                # 找到对应的数据集信息
                selected = next((d for d in unanalyzed if d['dataset_id'] == selected_id), None)
                if selected:
                    selected['selection_reasoning'] = reasoning
                    self.logger.info(f"LLM 推荐数据集: {selected_id}")
                    self.logger.info(f"推荐理由: {reasoning}")
                    return selected
            
            # 如果 LLM 没有返回有效结果，使用规则引擎
            self.logger.warning("LLM 未返回有效推荐，使用规则引擎")
            return self.select_next_dataset_with_rules(analyzed, unanalyzed)
            
        except Exception as e:
            self.logger.error(f"LLM 选择失败: {e}")
            # 回退到规则引擎
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
        """构建 LLM 选择提示"""
        
        prompt = f"""# 疾病数据集选择任务

你是一个生物医学研究助手，需要从未分析的数据集中选择下一个最有价值的进行分析。

## 已分析数据集 ({analyzed['total_count']} 个)

"""
        
        if analyzed['datasets']:
            for d in analyzed['datasets']:
                prompt += f"- **{d['dataset_id']}**: {d['disease_type']}, "
                prompt += f"激活系统: {', '.join(d.get('systems_activated', []))}\n"
        else:
            prompt += "（尚未分析任何数据集）\n"
        
        prompt += f"""
## 疾病类型覆盖

已覆盖: {', '.join(analyzed['disease_types']) if analyzed['disease_types'] else '无'}

## 系统激活统计

"""
        
        if analyzed['system_coverage']:
            for system, count in sorted(analyzed['system_coverage'].items()):
                prompt += f"- {system}: {count} 次\n"
        else:
            prompt += "（尚无统计数据）\n"
        
        prompt += f"""
## 可选数据集 ({len(unanalyzed)} 个)

"""
        
        for d in unanalyzed:
            prompt += f"""
### {d['dataset_id']}
- **名称**: {d['chinese_name']} ({d['name']})
- **疾病类型**: {d['disease_type']}
- **预期系统**: {', '.join(d['expected_systems'])}
- **描述**: {d['description']}
"""
        
        prompt += """
## 选择标准

请根据以下标准选择最有价值的数据集：

1. **疾病类型多样性**: 优先选择未覆盖的疾病类型
2. **系统覆盖完整性**: 优先选择能激活未充分研究系统的数据集
3. **科学价值**: 考虑疾病的重要性和研究意义
4. **互补性**: 选择能与已有结果形成对比或互补的数据集

## 输出格式

请以 JSON 格式返回你的选择：

```json
{
    "selected_dataset_id": "GSE数据集ID",
    "reasoning": "选择理由（2-3句话）",
    "expected_insights": "预期发现（1-2句话）"
}
```

请直接返回 JSON，不要添加其他文字。
"""
        
        return prompt
    
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
        self.logger.info(f"  已分析: {analyzed['total_count']} 个数据集")
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
