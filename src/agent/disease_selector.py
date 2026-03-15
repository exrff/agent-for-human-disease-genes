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
                if summary_file.exists():
                    try:
                        with open(summary_file, 'r', encoding='utf-8') as f:
                            summary = json.load(f)
                        
                        dataset_id = dataset_dir.name
                        seen_ids.add(dataset_id)
                        
                        analyzed['datasets'].append({
                            'dataset_id': dataset_id,
                            'disease_type': summary.get('disease_type'),
                            'analysis_date': summary.get('analysis_date'),
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
        try:
            from .config import AgentConfig
            info = AgentConfig.DATASETS.get(dataset_id)
            if info:
                return info.get('disease_type')
        except Exception:
            pass
        return None

    
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
        
        策略：
        1. 如果 available 中还有未分析的，优先从中选择
        2. 如果都已分析，让 LLM 推荐新的 GEO 数据集
        
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
            
            if unanalyzed:
                # 还有预定义的数据集未分析
                self.logger.info("从预定义数据集中选择...")
                prompt = self._build_selection_prompt(analyzed, unanalyzed)
                response = llm.select_next_dataset(prompt)
                
                selected_id = response.get('selected_dataset_id')
                reasoning = response.get('reasoning', '')
                
                if selected_id:
                    selected = next((d for d in unanalyzed if d['dataset_id'] == selected_id), None)
                    if selected:
                        selected['selection_reasoning'] = reasoning
                        self.logger.info(f"LLM 推荐数据集: {selected_id}")
                        self.logger.info(f"推荐理由: {reasoning}")
                        return selected
            
            else:
                # 所有预定义数据集都已分析，让 LLM 推荐新的
                self.logger.info("所有预定义数据集已分析完成")
                self.logger.info("请 LLM 推荐新的 GEO 数据集...")
                
                prompt = self._build_new_dataset_prompt(analyzed)
                response = llm.select_next_dataset(prompt)
                
                # 解析 LLM 推荐的新数据集
                new_dataset = self._parse_new_dataset_recommendation(response)
                
                if new_dataset:
                    self.logger.info(f"LLM 推荐新数据集: {new_dataset['dataset_id']}")
                    self.logger.info(f"推荐理由: {new_dataset.get('selection_reasoning', '无')}")
                    return new_dataset
            
            # 如果 LLM 没有返回有效结果，使用规则引擎
            self.logger.warning("LLM 未返回有效推荐，使用规则引擎")
            return self.select_next_dataset_with_rules(analyzed, available)
            
        except Exception as e:
            self.logger.error(f"LLM 选择失败: {e}")
            # 规则引擎回退：如果还有未分析的预定义数据集就选一个，否则无法推荐
            analyzed_ids = {d['dataset_id'] for d in analyzed['datasets']}
            unanalyzed = [d for d in available if d['dataset_id'] not in analyzed_ids]
            if unanalyzed:
                return self.select_next_dataset_with_rules(analyzed, available)
            self.logger.warning("LLM 不可用且无预定义数据集可选，无法推荐新数据集")
            return None

    
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
    
    def _build_new_dataset_prompt(self, analyzed: Dict[str, Any]) -> str:
        """构建推荐新数据集的 LLM 提示"""
        
        prompt = f"""# 推荐新的 GEO 疾病数据集

你是一个生物医学研究助手。我们已经完成了以下疾病数据集的分析，现在需要你推荐新的、更有价值的疾病数据集进行研究。

## 五大功能系统定义

- **System A (稳态与修复)**: 基因组稳定性、体细胞维持、细胞稳态、炎症消解
- **System B (免疫防御)**: 先天免疫、适应性免疫、免疫调节
- **System C (代谢调节)**: 能量代谢、生物合成、解毒代谢
- **System D (调节协调)**: 神经调节、内分泌调节
- **System E (生殖发育)**: 生殖、发育

## 14 个功能子类

- A1: 基因组稳定性与修复
- A2: 体细胞维持与身份保持
- A3: 细胞稳态与结构维持
- A4: 炎症消解与损伤控制
- B1: 先天免疫
- B2: 适应性免疫
- B3: 免疫调节与耐受
- C1: 能量代谢与分解代谢
- C2: 生物合成与合成代谢
- C3: 解毒与代谢应激处理
- D1: 神经调节与信号传递
- D2: 内分泌与自主调节
- E1: 生殖
- E2: 发育与生殖成熟

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
        
        prompt += """
## 任务

请基于五大系统和 14 个子类的定义，推荐一个新的 GEO 疾病数据集（GSE 编号）进行分析。

### 推荐标准

1. **系统覆盖互补性**: 优先推荐能激活未充分研究系统的疾病
2. **疾病类型多样性**: 选择与已有疾病类型不同的新疾病
3. **科学价值**: 疾病具有重要的临床意义和研究价值
4. **系统间关联**: 能展示多个系统之间的相互作用
5. **数据可用性**: 确保 GEO 数据库中有该数据集

### 推荐疾病类型示例

- **自身免疫性疾病**: 系统性红斑狼疮、类风湿关节炎（B + C + D）
- **心血管疾病**: 心肌梗死、动脉粥样硬化（A + C + D）
- **肾脏疾病**: 慢性肾病、肾小球肾炎（C + D）
- **肝脏疾病**: 肝硬化、非酒精性脂肪肝（C + A）
- **呼吸系统疾病**: 慢性阻塞性肺病、哮喘（B + C）
- **精神疾病**: 抑郁症、精神分裂症（D + B）
- **罕见病**: 线粒体病、溶酶体贮积病（C + A）

## 输出格式

请以 JSON 格式返回你的推荐：

```json
{
    "selected_dataset_id": "GSE数据集ID",
    "name": "疾病英文名",
    "chinese_name": "疾病中文名",
    "disease_type": "疾病类型（如 autoimmune, cardiovascular 等）",
    "expected_systems": ["预期激活的系统，如 System A, System B"],
    "expected_subcategories": ["预期激活的子类，如 A1, B2, C1"],
    "reasoning": "推荐理由（2-3句话，说明为什么这个疾病有价值）",
    "expected_insights": "预期发现（1-2句话）",
    "description": "疾病简要描述"
}
```

请直接返回 JSON，不要添加其他文字。
"""
        
        return prompt
    
    def _parse_new_dataset_recommendation(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """解析 LLM 推荐的新数据集"""
        
        try:
            dataset_id = response.get('selected_dataset_id')
            
            if not dataset_id or not dataset_id.startswith('GSE'):
                self.logger.warning("LLM 未返回有效的 GSE ID")
                return None
            
            # 构建数据集信息
            new_dataset = {
                'dataset_id': dataset_id,
                'name': response.get('name', 'Unknown'),
                'chinese_name': response.get('chinese_name', '未知疾病'),
                'disease_type': response.get('disease_type', 'unknown'),
                'expected_systems': response.get('expected_systems', []),
                'expected_subcategories': response.get('expected_subcategories', []),
                'description': response.get('description', ''),
                'selection_reasoning': response.get('reasoning', ''),
                'expected_insights': response.get('expected_insights', ''),
                'is_new_recommendation': True  # 标记为新推荐
            }
            
            return new_dataset
            
        except Exception as e:
            self.logger.error(f"解析新数据集推荐失败: {e}")
            return None
    
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
