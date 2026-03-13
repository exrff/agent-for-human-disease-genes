#!/usr/bin/env python3
"""
从real_ssgsea_validation_report.json中提取GSE28914数据
生成完整的GSE28914数据集文件
"""

import json
import pandas as pd
import numpy as np
import os
import gzip
from datetime import datetime

def extract_gse28914_data():
    """提取GSE28914的完整数据集"""
    
    json_file = 'results/full_classification/real_ssgsea_validation/real_ssgsea_validation_report.json'
    
    if not os.path.exists(json_file):
        print(f"❌ 文件不存在: {json_file}")
        return
    
    print(f"📁 读取文件: {json_file}")
    
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # 提取GSE28914数据
        gse28914_data = data['dataset_results']['GSE28914']
        
        print(f"✅ 成功加载GSE28914数据")
        print(f"   - 数据集: {gse28914_data['dataset_info']['name']}")
        print(f"   - 描述: {gse28914_data['dataset_info']['description']}")
        
        # A. 生成 gse28914_ssgsea_scores.csv
        print(f"\n📊 A. 生成ssGSEA得分文件...")
        scores_df = create_ssgsea_scores_file(gse28914_data)
        
        # B. 生成 gse28914_sample_info.csv  
        print(f"\n👥 B. 生成样本信息文件...")
        sample_info_df = create_sample_info_file(gse28914_data)
        
        # C. 生成 gse28914_system_scores.csv
        print(f"\n🏗️ C. 生成系统级得分文件...")
        system_scores_df = create_system_scores_file(gse28914_data)
        
        # D. 生成 gene_sets_14_subcategories.gmt
        print(f"\n🧬 D. 生成基因集定义文件...")
        create_gene_sets_gmt_file(data)
        
        # E. 生成 gse28914_expression_matrix.csv (可选)
        print(f"\n📈 E. 尝试生成表达矩阵文件...")
        expr_matrix_df = create_expression_matrix_file()
        
        # 验证所有文件
        print(f"\n🔍 验证生成的文件...")
        validate_gse28914_files()
        
        return scores_df, sample_info_df, system_scores_df
        
    except Exception as e:
        print(f"❌ 处理过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def create_ssgsea_scores_file(gse28914_data):
    """A. 创建ssGSEA得分文件"""
    
    subcategory_scores = gse28914_data['subcategory_scores']
    sample_info = gse28914_data['sample_info']
    
    # 获取样本ID
    sample_accessions = sample_info['accessions']
    
    print(f"   - 样本数量: {len(sample_accessions)}")
    print(f"   - 子分类数量: {len(subcategory_scores)}")
    
    # 创建ssGSEA得分DataFrame
    scores_data = {'sample_id': sample_accessions}
    
    # 添加所有14个子分类的得分
    subcategory_order = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1', 'D2', 'E1', 'E2']
    
    for subcat in subcategory_order:
        if subcat in subcategory_scores:
            scores = subcategory_scores[subcat]['scores']
            scores_data[subcat] = scores
            
            # 检查得分范围
            min_score = min(scores)
            max_score = max(scores)
            mean_score = np.mean(scores)
            
            print(f"   - {subcat}: {len(scores)} scores, 范围: [{min_score:.4f}, {max_score:.4f}], 均值: {mean_score:.4f}")
    
    # 创建DataFrame并保存
    scores_df = pd.DataFrame(scores_data)
    
    output_file = 'gse28914_ssgsea_scores.csv'
    scores_df.to_csv(output_file, index=False)
    
    print(f"✅ 保存: {output_file} ({scores_df.shape[0]}×{scores_df.shape[1]-1})")
    
    return scores_df

def create_sample_info_file(gse28914_data):
    """B. 创建样本信息文件"""
    
    sample_info = gse28914_data['sample_info']
    
    sample_accessions = sample_info['accessions']
    sample_titles = sample_info['titles']
    
    # 解析样本信息以提取时间点和分组
    sample_data = []
    
    for i, (sample_id, title) in enumerate(zip(sample_accessions, sample_titles)):
        # 解析标题以提取信息
        # 例如: "Patient 1, intact skin sample" -> Patient 1, intact skin
        # 例如: "Patient 1, 3rd post-operative day sample" -> Patient 1, day 3
        
        patient_num = None
        timepoint = None
        group = None
        condition = None
        
        title_lower = title.lower()
        
        # 提取患者编号
        if 'patient' in title_lower:
            try:
                patient_part = title_lower.split('patient')[1].split(',')[0].strip()
                patient_num = int(patient_part)
            except:
                patient_num = i // 3 + 1  # 估算患者编号
        
        # 提取时间点和条件
        if 'intact skin' in title_lower:
            timepoint = 'Day_0'
            condition = 'Intact_Skin'
            group = 'Baseline'
        elif 'acute wound' in title_lower:
            timepoint = 'Day_0'
            condition = 'Acute_Wound'
            group = 'Acute'
        elif '3rd post-operative day' in title_lower:
            timepoint = 'Day_3'
            condition = 'Post_Op'
            group = 'Day_3'
        elif '7th post-operative day' in title_lower:
            timepoint = 'Day_7'
            condition = 'Post_Op'
            group = 'Day_7'
        else:
            timepoint = 'Unknown'
            condition = 'Unknown'
            group = 'Unknown'
        
        sample_data.append({
            'sample_id': sample_id,
            'sample_title': title,
            'patient_id': f'Patient_{patient_num}' if patient_num else f'Patient_{i//3+1}',
            'timepoint': timepoint,
            'condition': condition,
            'group': group,
            'day_numeric': 0 if timepoint == 'Day_0' else (3 if timepoint == 'Day_3' else (7 if timepoint == 'Day_7' else -1))
        })
    
    # 创建DataFrame
    sample_info_df = pd.DataFrame(sample_data)
    
    # 统计分组
    group_counts = sample_info_df['group'].value_counts()
    print(f"   - 分组统计:")
    for group, count in group_counts.items():
        print(f"     * {group}: {count} samples")
    
    timepoint_counts = sample_info_df['timepoint'].value_counts()
    print(f"   - 时间点统计:")
    for timepoint, count in timepoint_counts.items():
        print(f"     * {timepoint}: {count} samples")
    
    # 保存文件
    output_file = 'gse28914_sample_info.csv'
    sample_info_df.to_csv(output_file, index=False)
    
    print(f"✅ 保存: {output_file} ({sample_info_df.shape[0]}×{sample_info_df.shape[1]})")
    
    return sample_info_df

def create_system_scores_file(gse28914_data):
    """C. 创建系统级得分文件"""
    
    system_scores = gse28914_data['system_scores']
    sample_info = gse28914_data['sample_info']
    
    sample_accessions = sample_info['accessions']
    
    # 创建系统级得分DataFrame
    system_data = {'sample_id': sample_accessions}
    
    # 系统定义
    systems = {
        'System_A': 'Homeostasis and Repair',
        'System_B': 'Immune Defense', 
        'System_C': 'Metabolic Regulation',
        'System_D': 'Regulatory Coordination',
        'System_E': 'Reproduction and Development'
    }
    
    system_order = ['System_A', 'System_B', 'System_C', 'System_D', 'System_E']
    
    for system_name in system_order:
        if system_name.replace('_', ' ') in system_scores:
            scores = system_scores[system_name.replace('_', ' ')]['scores']
            system_data[system_name] = scores
            
            # 统计信息
            mean_score = np.mean(scores)
            std_score = np.std(scores)
            subcats = system_scores[system_name.replace('_', ' ')]['subcategories']
            
            print(f"   - {system_name}: {mean_score:.4f} ± {std_score:.4f} (子分类: {subcats})")
    
    # 创建DataFrame并保存
    system_scores_df = pd.DataFrame(system_data)
    
    output_file = 'gse28914_system_scores.csv'
    system_scores_df.to_csv(output_file, index=False)
    
    print(f"✅ 保存: {output_file} ({system_scores_df.shape[0]}×{system_scores_df.shape[1]-1})")
    
    return system_scores_df

def create_gene_sets_gmt_file(data):
    """D. 创建基因集定义文件 (GMT格式)"""
    
    # 加载基因映射
    go_mapping_file = "data/go_annotations/go_to_genes.json"
    kegg_mapping_file = "data/kegg_mappings/kegg_to_genes.json"
    
    go_to_genes = {}
    kegg_to_genes = {}
    
    if os.path.exists(go_mapping_file):
        with open(go_mapping_file, 'r') as f:
            go_to_genes = json.load(f)
        print(f"   - 加载GO映射: {len(go_to_genes)} GO条目")
    
    if os.path.exists(kegg_mapping_file):
        with open(kegg_mapping_file, 'r') as f:
            kegg_data = json.load(f)
        kegg_to_genes = {pathway_id: info['genes'] for pathway_id, info in kegg_data.items()}
        print(f"   - 加载KEGG映射: {len(kegg_to_genes)} KEGG通路")
    
    # 加载分类结果
    classification_file = "results/full_classification/full_classification_results.csv"
    
    if not os.path.exists(classification_file):
        print(f"   ⚠️  分类文件不存在: {classification_file}")
        return
    
    df = pd.read_csv(classification_file)
    
    # 创建GMT文件
    output_file = 'gene_sets_14_subcategories.gmt'
    
    subcategories = {
        'A1': 'Genomic_Stability_and_Repair',
        'A2': 'Somatic_Maintenance_and_Identity_Preservation', 
        'A3': 'Cellular_Homeostasis_and_Structural_Maintenance',
        'A4': 'Inflammation_Resolution_and_Damage_Containment',
        'B1': 'Innate_Immunity',
        'B2': 'Adaptive_Immunity',
        'B3': 'Immune_Regulation_and_Tolerance',
        'C1': 'Energy_Metabolism_and_Catabolism',
        'C2': 'Biosynthesis_and_Anabolism', 
        'C3': 'Detoxification_and_Metabolic_Stress_Handling',
        'D1': 'Neural_Regulation_and_Signal_Transmission',
        'D2': 'Endocrine_and_Autonomic_Regulation',
        'E1': 'Reproduction',
        'E2': 'Development_and_Reproductive_Maturation'
    }
    
    with open(output_file, 'w') as f:
        for subcat_code, subcat_name in subcategories.items():
            # 获取该子分类的过程
            subcat_processes = df[df['Subcategory_Code'] == subcat_code]
            
            # 收集基因
            all_genes = set()
            
            for _, process in subcat_processes.iterrows():
                process_id = process['ID']
                
                if process_id.startswith('GO:') and process_id in go_to_genes:
                    all_genes.update(go_to_genes[process_id])
                elif process_id.startswith('KEGG:') and process_id in kegg_to_genes:
                    all_genes.update(kegg_to_genes[process_id])
            
            # 写入GMT格式
            # 格式: gene_set_name\tdescription\tgene1\tgene2\t...
            gene_list = sorted(list(all_genes))
            
            if gene_list:
                f.write(f"{subcat_code}_{subcat_name}\t{subcat_name.replace('_', ' ')}\t")
                f.write('\t'.join(gene_list))
                f.write('\n')
                
                print(f"   - {subcat_code}: {len(gene_list)} genes")
    
    print(f"✅ 保存: {output_file}")

def create_expression_matrix_file():
    """E. 创建表达矩阵文件 (可选)"""
    
    # 尝试从原始数据文件加载表达矩阵
    data_path = "data/validation_datasets/GSE28914/GSE28914_series_matrix.txt.gz"
    
    if not os.path.exists(data_path):
        print(f"   ⚠️  原始数据文件不存在: {data_path}")
        return None
    
    try:
        print(f"   - 读取原始表达数据...")
        
        # 读取压缩文件
        with gzip.open(data_path, 'rt', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # 找到数据表开始位置
        data_start = None
        for i, line in enumerate(lines):
            if line.startswith('!series_matrix_table_begin'):
                data_start = i + 1
                break
        
        if data_start is None:
            print(f"   ⚠️  无法找到数据表开始位置")
            return None
        
        # 读取数据表
        data_lines = []
        for line in lines[data_start:]:
            if line.startswith('!series_matrix_table_end'):
                break
            data_lines.append(line.strip().split('\t'))
        
        if len(data_lines) < 2:
            print(f"   ⚠️  数据不足")
            return None
        
        # 创建DataFrame
        header = [col.strip('"') for col in data_lines[0]]
        data_rows = [[cell.strip('"') for cell in row] for row in data_lines[1:]]
        
        expr_df = pd.DataFrame(data_rows, columns=header)
        
        # 设置探针ID为索引
        if 'ID_REF' in expr_df.columns:
            expr_df = expr_df.set_index('ID_REF')
        
        # 转换为数值
        for col in expr_df.columns:
            expr_df[col] = pd.to_numeric(expr_df[col], errors='coerce')
        
        # 移除缺失值过多的行
        expr_df = expr_df.dropna(thresh=len(expr_df.columns) * 0.5)
        
        print(f"   - 表达矩阵形状: {expr_df.shape[0]} probes × {expr_df.shape[1]} samples")
        
        # 保存 (由于文件可能很大，只保存前1000个探针作为示例)
        output_file = 'gse28914_expression_matrix_sample.csv'
        expr_sample = expr_df.head(1000)  # 前1000个探针
        expr_sample.to_csv(output_file)
        
        print(f"✅ 保存: {output_file} (前1000个探针示例)")
        
        return expr_sample
        
    except Exception as e:
        print(f"   ⚠️  读取表达矩阵失败: {e}")
        return None

def validate_gse28914_files():
    """验证生成的GSE28914文件"""
    
    files_to_check = [
        'gse28914_ssgsea_scores.csv',
        'gse28914_sample_info.csv', 
        'gse28914_system_scores.csv',
        'gene_sets_14_subcategories.gmt',
        'gse28914_expression_matrix_sample.csv'
    ]
    
    for filename in files_to_check:
        if os.path.exists(filename):
            if filename.endswith('.csv'):
                df = pd.read_csv(filename)
                print(f"✅ {filename}: {df.shape[0]} rows × {df.shape[1]} columns")
                print(f"   列名: {list(df.columns)}")
            elif filename.endswith('.gmt'):
                with open(filename, 'r') as f:
                    lines = f.readlines()
                print(f"✅ {filename}: {len(lines)} gene sets")
            print()
        else:
            print(f"❌ 文件不存在: {filename}")

def create_summary_report():
    """创建数据摘要报告"""
    
    print(f"\n📋 GSE28914数据集摘要报告")
    print(f"{'='*60}")
    
    # 读取生成的文件并创建摘要
    files_info = {}
    
    if os.path.exists('gse28914_ssgsea_scores.csv'):
        df = pd.read_csv('gse28914_ssgsea_scores.csv')
        files_info['ssGSEA Scores'] = {
            'file': 'gse28914_ssgsea_scores.csv',
            'shape': df.shape,
            'description': '14个子分类的ssGSEA富集得分',
            'score_range': f"[{df.select_dtypes(include=[np.number]).min().min():.4f}, {df.select_dtypes(include=[np.number]).max().max():.4f}]"
        }
    
    if os.path.exists('gse28914_sample_info.csv'):
        df = pd.read_csv('gse28914_sample_info.csv')
        files_info['Sample Info'] = {
            'file': 'gse28914_sample_info.csv',
            'shape': df.shape,
            'description': '样本时间点和分组信息',
            'groups': df['group'].value_counts().to_dict()
        }
    
    if os.path.exists('gse28914_system_scores.csv'):
        df = pd.read_csv('gse28914_system_scores.csv')
        files_info['System Scores'] = {
            'file': 'gse28914_system_scores.csv', 
            'shape': df.shape,
            'description': '5大系统的聚合得分'
        }
    
    # 保存摘要报告
    summary = {
        'dataset': 'GSE28914 - Human Skin Wound Healing',
        'description': 'Time course study of wound healing process',
        'timestamp': datetime.now().isoformat(),
        'files_generated': files_info
    }
    
    with open('gse28914_data_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"✅ 保存数据摘要: gse28914_data_summary.json")
    
    # 打印摘要
    for name, info in files_info.items():
        print(f"\n📁 {name}:")
        print(f"   文件: {info['file']}")
        print(f"   形状: {info['shape'][0]} × {info['shape'][1]}")
        print(f"   描述: {info['description']}")
        if 'score_range' in info:
            print(f"   得分范围: {info['score_range']}")
        if 'groups' in info:
            print(f"   分组: {info['groups']}")

if __name__ == "__main__":
    print("="*80)
    print("GSE28914 完整数据提取工具")
    print("="*80)
    
    # 提取数据
    scores_df, sample_info_df, system_scores_df = extract_gse28914_data()
    
    if scores_df is not None:
        # 创建摘要报告
        create_summary_report()
        
        print(f"\n✅ GSE28914数据提取完成!")
        print(f"📊 生成了完整的伤口愈合时间序列数据集")
    else:
        print(f"\n❌ 数据提取失败")