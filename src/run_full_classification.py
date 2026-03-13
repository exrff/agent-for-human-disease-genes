#!/usr/bin/env python3
"""
完整的大规模五大功能系统分类

处理所有GO和KEGG数据，生成以子类为主的分类结果，用于论文发表。
使用完整的技术架构，不是简化版本。
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import logging

# 设置Python路径以支持相对导入
current_dir = Path(__file__).parent.parent  # 回到项目根目录
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / 'src'))

# 导入完整的技术模块 - 这是严谨版本，不是简化版本
import src.preprocessing.go_parser as go_parser_module
import src.preprocessing.kegg_parser as kegg_parser_module
import src.classification.five_system_classifier as classifier_module
import src.models.biological_entry as entry_module
import src.config.settings as settings_module

GOParser = go_parser_module.GOParser
KEGGParser = kegg_parser_module.KEGGParser
FiveSystemClassifier = classifier_module.FiveSystemClassifier
BiologicalEntry = entry_module.BiologicalEntry
get_settings = settings_module.get_settings

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_biological_entry_from_go(go_term) -> BiologicalEntry:
    """从GO条目创建BiologicalEntry"""
    return BiologicalEntry(
        id=go_term.id,
        name=go_term.name,
        definition=go_term.definition,
        source="GO",
        namespace=go_term.namespace
    )


def create_biological_entry_from_kegg(kegg_pathway) -> BiologicalEntry:
    """从KEGG通路创建BiologicalEntry"""
    return BiologicalEntry(
        id=f"KEGG:{kegg_pathway.id}",  # 添加KEGG前缀
        name=kegg_pathway.name,
        definition=kegg_pathway.description or "",
        source="KEGG",
        namespace="pathway"
    )


def get_subcategory_details() -> Dict[str, Dict[str, str]]:
    """获取子类详细信息"""
    return {
        # System A: Self-Healing & Structural Reconstruction
        "A1": {
            "name": "Genomic Stability and Repair",
            "description": "DNA damage sensing/repair, chromatin maintenance, telomere maintenance"
        },
        "A2": {
            "name": "Somatic Maintenance and Identity Preservation", 
            "description": "Stem/progenitor maintenance, differentiation, senescence programs"
        },
        "A3": {
            "name": "Cellular Homeostasis and Structural Maintenance",
            "description": "Proteostasis, autophagy, organelle biogenesis and repair"
        },
        "A4": {
            "name": "Inflammation Resolution and Damage Containment",
            "description": "Efferocytosis, pro-resolving mediators, tissue homeostasis restoration"
        },
        
        # System B: Immune Defense
        "B1": {
            "name": "Innate Immunity",
            "description": "Pattern recognition, inflammatory signaling, phagocytosis"
        },
        "B2": {
            "name": "Adaptive Immunity", 
            "description": "Antigen-specific responses, immune memory, targeted effectors"
        },
        "B3": {
            "name": "Immune Regulation and Tolerance",
            "description": "Negative feedback control, checkpoint regulation, tolerance mechanisms"
        },
        
        # System C: Energy & Metabolic Homeostasis
        "C1": {
            "name": "Energy Metabolism and Catabolism",
            "description": "Nutrient breakdown, ATP generation, redox balancing"
        },
        "C2": {
            "name": "Biosynthesis and Anabolism",
            "description": "Macromolecular building blocks synthesis, growth demands"
        },
        "C3": {
            "name": "Detoxification and Metabolic Stress Handling",
            "description": "Xenobiotic transformation, harmful metabolite elimination"
        },
        
        # System D: Cognitive-Regulatory (Neuro-Endocrine Control)
        "D1": {
            "name": "Neural Regulation and Signal Transmission",
            "description": "Neural signaling, synaptic communication, sensor-motor integration"
        },
        "D2": {
            "name": "Endocrine and Autonomic Regulation",
            "description": "Hormonal signaling, autonomic control, physiological set-points"
        },
        
        # System E: Reproduction & Continuity
        "E1": {
            "name": "Reproduction",
            "description": "Gametogenesis, reproductive endocrine, fertilization, gestation"
        },
        "E2": {
            "name": "Development and Reproductive Maturation",
            "description": "Embryonic development, sex differentiation, reproductive competence"
        }
    }


def run_full_classification():
    """运行完整的大规模分类"""
    
    logger.info("开始完整的五大功能系统分类...")
    
    # 获取设置
    settings = get_settings()
    
    # 初始化解析器
    logger.info("初始化数据解析器...")
    go_file = Path("data/ontology/go-basic.txt")
    kegg_file = Path("data/ontology/br_br08901.txt")
    
    if not go_file.exists():
        logger.error(f"GO文件不存在: {go_file}")
        return
    
    if not kegg_file.exists():
        logger.error(f"KEGG文件不存在: {kegg_file}")
        return
    
    go_parser = GOParser(str(go_file))
    kegg_parser = KEGGParser(str(kegg_file))
    
    # 解析数据
    logger.info("解析GO本体数据...")
    go_terms = go_parser.parse_go_terms()
    logger.info(f"解析得到 {len(go_terms)} 个GO条目")
    
    logger.info("解析KEGG通路数据...")
    kegg_pathways = kegg_parser.parse_pathways()
    logger.info(f"解析得到 {len(kegg_pathways)} 个KEGG通路")
    
    # 过滤生物过程
    biological_processes = {
        term_id: term for term_id, term in go_terms.items()
        if term.is_biological_process() and not term.is_obsolete
    }
    logger.info(f"过滤得到 {len(biological_processes)} 个生物过程GO条目")
    
    # 初始化分类器
    logger.info("初始化分类器...")
    classifier = FiveSystemClassifier()
    
    # 执行分类
    logger.info("开始分类处理...")
    results = []
    subcategory_details = get_subcategory_details()
    
    total_entries = len(biological_processes) + len(kegg_pathways)
    processed = 0
    
    # 处理GO条目
    for term_id, term in biological_processes.items():
        try:
            entry = create_biological_entry_from_go(term)
            result = classifier.classify_entry(entry)
            
            # 获取子类详细信息
            subcategory_info = subcategory_details.get(result.subsystem, {})
            
            results.append({
                'ID': term_id,
                'Name': term.name,
                'Definition': term.definition,
                'Source': 'GO',
                'Namespace': term.namespace,
                'Primary_System': result.primary_system,
                'Subcategory_Code': result.subsystem,
                'Subcategory_Name': subcategory_info.get('name', ''),
                'Subcategory_Description': subcategory_info.get('description', ''),
                'All_Systems': str(result.all_systems),
                'Inflammation_Polarity': result.inflammation_polarity or '',
                'Confidence_Score': result.confidence_score,
                'Decision_Path': result.decision_path or '',
                'Classification_Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'Version': 'v8.0'
            })
            
            processed += 1
            if processed % 1000 == 0:
                logger.info(f"已处理 {processed}/{total_entries} 个条目 ({processed/total_entries*100:.1f}%)")
                
        except Exception as e:
            logger.error(f"处理GO条目 {term_id} 时出错: {e}")
            continue
    
    # 处理KEGG通路
    for pathway in kegg_pathways:  # kegg_pathways是列表，不是字典
        try:
            entry = create_biological_entry_from_kegg(pathway)
            result = classifier.classify_entry(entry)
            
            # 获取子类详细信息
            subcategory_info = subcategory_details.get(result.subsystem, {})
            
            results.append({
                'ID': pathway.id,
                'Name': pathway.name,
                'Definition': pathway.description or '',
                'Source': 'KEGG',
                'Namespace': 'pathway',
                'Primary_System': result.primary_system,
                'Subcategory_Code': result.subsystem,
                'Subcategory_Name': subcategory_info.get('name', ''),
                'Subcategory_Description': subcategory_info.get('description', ''),
                'All_Systems': str(result.all_systems),
                'Inflammation_Polarity': result.inflammation_polarity or '',
                'Confidence_Score': result.confidence_score,
                'Decision_Path': result.decision_path or '',
                'Classification_Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'Version': 'v8.0'
            })
            
            processed += 1
            if processed % 100 == 0:
                logger.info(f"已处理 {processed}/{total_entries} 个条目 ({processed/total_entries*100:.1f}%)")
                
        except Exception as e:
            logger.error(f"处理KEGG通路 {pathway.id} 时出错: {e}")
            continue
    
    logger.info(f"分类完成！共处理 {len(results)} 个条目")
    
    # 创建结果DataFrame
    df = pd.DataFrame(results)
    
    # 确保输出目录存在
    output_dir = Path("results/full_classification")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存完整结果（以子类为主要排序）
    full_results_file = output_dir / "full_classification_results.csv"
    df_sorted = df.sort_values(['Subcategory_Code', 'Confidence_Score'], ascending=[True, False])
    df_sorted.to_csv(full_results_file, index=False, encoding='utf-8')
    logger.info(f"完整分类结果已保存到: {full_results_file}")
    
    # 按子类分组保存
    for subcategory in df['Subcategory_Code'].unique():
        if pd.notna(subcategory) and subcategory:
            subcategory_df = df[df['Subcategory_Code'] == subcategory]
            subcategory_file = output_dir / f"subcategory_{subcategory}.csv"
            subcategory_df.to_csv(subcategory_file, index=False, encoding='utf-8')
            logger.info(f"子类 {subcategory} 结果已保存到: {subcategory_file}")
    
    # 生成统计报告
    generate_statistics_report(df, output_dir)
    
    # 生成论文级别的分析
    generate_paper_analysis(df, output_dir)
    
    logger.info("完整分类任务完成！")


def generate_statistics_report(df: pd.DataFrame, output_dir: Path):
    """生成统计报告"""
    
    logger.info("生成统计报告...")
    
    # 子类分布统计
    subcategory_stats = df.groupby(['Subcategory_Code', 'Subcategory_Name']).agg({
        'ID': 'count',
        'Confidence_Score': ['mean', 'std'],
        'Source': lambda x: x.value_counts().to_dict()
    }).round(3)
    
    subcategory_stats.columns = ['Count', 'Mean_Confidence', 'Std_Confidence', 'Source_Distribution']
    subcategory_stats = subcategory_stats.reset_index()
    subcategory_stats['Percentage'] = (subcategory_stats['Count'] / len(df) * 100).round(2)
    
    # 保存子类统计
    subcategory_stats_file = output_dir / "subcategory_statistics.csv"
    subcategory_stats.to_csv(subcategory_stats_file, index=False, encoding='utf-8')
    
    # 主系统统计
    system_stats = df.groupby('Primary_System').agg({
        'ID': 'count',
        'Confidence_Score': ['mean', 'std']
    }).round(3)
    
    system_stats.columns = ['Count', 'Mean_Confidence', 'Std_Confidence']
    system_stats = system_stats.reset_index()
    system_stats['Percentage'] = (system_stats['Count'] / len(df) * 100).round(2)
    
    # 保存主系统统计
    system_stats_file = output_dir / "system_statistics.csv"
    system_stats.to_csv(system_stats_file, index=False, encoding='utf-8')
    
    # 炎症极性统计
    inflammation_stats = df[df['Inflammation_Polarity'] != '']['Inflammation_Polarity'].value_counts()
    inflammation_stats_file = output_dir / "inflammation_statistics.csv"
    inflammation_stats.to_csv(inflammation_stats_file, header=['Count'])
    
    # 生成总体统计JSON
    overall_stats = {
        'total_entries': len(df),
        'go_entries': len(df[df['Source'] == 'GO']),
        'kegg_entries': len(df[df['Source'] == 'KEGG']),
        'average_confidence': df['Confidence_Score'].mean(),
        'subcategories_covered': df['Subcategory_Code'].nunique(),
        'inflammation_annotated': len(df[df['Inflammation_Polarity'] != '']),
        'classification_date': datetime.now().isoformat(),
        'version': 'v8.0'
    }
    
    stats_json_file = output_dir / "overall_statistics.json"
    with open(stats_json_file, 'w', encoding='utf-8') as f:
        json.dump(overall_stats, f, indent=2, ensure_ascii=False)
    
    logger.info(f"统计报告已保存到: {output_dir}")


def generate_paper_analysis(df: pd.DataFrame, output_dir: Path):
    """生成论文级别的分析"""
    
    logger.info("生成论文级别分析...")
    
    # 创建论文分析目录
    paper_dir = output_dir / "paper_analysis"
    paper_dir.mkdir(exist_ok=True)
    
    # 1. 子类分布分析表
    subcategory_analysis = df.groupby(['Primary_System', 'Subcategory_Code', 'Subcategory_Name']).agg({
        'ID': 'count',
        'Confidence_Score': 'mean'
    }).round(3)
    
    subcategory_analysis.columns = ['Entry_Count', 'Mean_Confidence']
    subcategory_analysis = subcategory_analysis.reset_index()
    subcategory_analysis['Percentage_of_Total'] = (subcategory_analysis['Entry_Count'] / len(df) * 100).round(2)
    
    # 计算每个主系统内的子类占比
    system_totals = df.groupby('Primary_System')['ID'].count()
    subcategory_analysis['Percentage_within_System'] = subcategory_analysis.apply(
        lambda row: (row['Entry_Count'] / system_totals[row['Primary_System']] * 100), axis=1
    ).round(2)
    
    subcategory_table_file = paper_dir / "table_subcategory_distribution.csv"
    subcategory_analysis.to_csv(subcategory_table_file, index=False, encoding='utf-8')
    
    # 2. 高置信度分类示例
    high_confidence_examples = df[df['Confidence_Score'] >= 0.9].groupby('Subcategory_Code').head(3)
    examples_file = paper_dir / "high_confidence_examples.csv"
    high_confidence_examples[['ID', 'Name', 'Subcategory_Code', 'Subcategory_Name', 'Confidence_Score']].to_csv(
        examples_file, index=False, encoding='utf-8'
    )
    
    # 3. 子类功能验证表
    validation_table = []
    subcategory_details = get_subcategory_details()
    
    for subcategory_code in sorted(subcategory_details.keys()):
        subcategory_data = df[df['Subcategory_Code'] == subcategory_code]
        if len(subcategory_data) > 0:
            validation_table.append({
                'Subcategory_Code': subcategory_code,
                'Subcategory_Name': subcategory_details[subcategory_code]['name'],
                'Functional_Description': subcategory_details[subcategory_code]['description'],
                'Entry_Count': len(subcategory_data),
                'Mean_Confidence': subcategory_data['Confidence_Score'].mean().round(3),
                'Example_Entries': '; '.join(subcategory_data.head(3)['Name'].tolist()),
                'GO_Count': len(subcategory_data[subcategory_data['Source'] == 'GO']),
                'KEGG_Count': len(subcategory_data[subcategory_data['Source'] == 'KEGG'])
            })
    
    validation_df = pd.DataFrame(validation_table)
    validation_file = paper_dir / "table_subcategory_validation.csv"
    validation_df.to_csv(validation_file, index=False, encoding='utf-8')
    
    # 4. 生成论文摘要统计
    paper_summary = {
        'study_title': 'Functional Classification of Biological Processes: A Five-System Framework with 14 Subcategories',
        'total_biological_processes': len(df),
        'go_terms_classified': len(df[df['Source'] == 'GO']),
        'kegg_pathways_classified': len(df[df['Source'] == 'KEGG']),
        'subcategories_identified': len(validation_df),
        'average_classification_confidence': df['Confidence_Score'].mean().round(3),
        'high_confidence_classifications': len(df[df['Confidence_Score'] >= 0.8]),
        'inflammation_processes_identified': len(df[df['Inflammation_Polarity'] != '']),
        'key_findings': {
            'most_populated_subcategory': validation_df.loc[validation_df['Entry_Count'].idxmax(), 'Subcategory_Name'],
            'highest_confidence_subcategory': validation_df.loc[validation_df['Mean_Confidence'].idxmax(), 'Subcategory_Name'],
            'system_distribution': df.groupby('Primary_System')['ID'].count().to_dict()
        }
    }
    
    summary_file = paper_dir / "paper_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(paper_summary, f, indent=2, ensure_ascii=False)
    
    logger.info(f"论文级别分析已保存到: {paper_dir}")


if __name__ == "__main__":
    run_full_classification()