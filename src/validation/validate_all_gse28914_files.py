#!/usr/bin/env python3
"""
验证所有GSE28914生成的文件
"""

import pandas as pd
import numpy as np
import os

def validate_all_files():
    """验证所有生成的GSE28914文件"""
    
    print("="*80)
    print("GSE28914 数据文件完整性验证")
    print("="*80)
    
    files_status = {}
    
    # A. 验证 gse28914_ssgsea_scores.csv
    print("\n📊 A. 验证 ssGSEA 得分文件...")
    file_a = 'gse28914_ssgsea_scores.csv'
    if os.path.exists(file_a):
        df_a = pd.read_csv(file_a)
        print(f"✅ {file_a}")
        print(f"   - 形状: {df_a.shape[0]} samples × {df_a.shape[1]-1} subcategories")
        print(f"   - 样本ID列: {df_a.columns[0]}")
        print(f"   - 子分类: {list(df_a.columns[1:])}")
        
        # 检查得分范围
        numeric_cols = df_a.select_dtypes(include=[np.number]).columns
        score_min = df_a[numeric_cols].min().min()
        score_max = df_a[numeric_cols].max().max()
        score_mean = df_a[numeric_cols].mean().mean()
        
        print(f"   - 得分范围: [{score_min:.4f}, {score_max:.4f}]")
        print(f"   - 得分均值: {score_mean:.4f}")
        
        files_status['ssgsea_scores'] = {
            'exists': True,
            'shape': df_a.shape,
            'score_range': [score_min, score_max],
            'subcategories': len(df_a.columns) - 1
        }
    else:
        print(f"❌ {file_a} 不存在")
        files_status['ssgsea_scores'] = {'exists': False}
    
    # B. 验证 gse28914_sample_info.csv
    print("\n👥 B. 验证样本信息文件...")
    file_b = 'gse28914_sample_info.csv'
    if os.path.exists(file_b):
        df_b = pd.read_csv(file_b)
        print(f"✅ {file_b}")
        print(f"   - 形状: {df_b.shape[0]} samples × {df_b.shape[1]} columns")
        print(f"   - 列名: {list(df_b.columns)}")
        
        # 分组统计
        if 'group' in df_b.columns:
            group_counts = df_b['group'].value_counts()
            print(f"   - 分组统计:")
            for group, count in group_counts.items():
                print(f"     * {group}: {count} samples")
        
        # 时间点统计
        if 'timepoint' in df_b.columns:
            timepoint_counts = df_b['timepoint'].value_counts()
            print(f"   - 时间点统计:")
            for timepoint, count in timepoint_counts.items():
                print(f"     * {timepoint}: {count} samples")
        
        files_status['sample_info'] = {
            'exists': True,
            'shape': df_b.shape,
            'groups': group_counts.to_dict() if 'group' in df_b.columns else {},
            'timepoints': timepoint_counts.to_dict() if 'timepoint' in df_b.columns else {}
        }
    else:
        print(f"❌ {file_b} 不存在")
        files_status['sample_info'] = {'exists': False}
    
    # C. 验证 gse28914_system_scores.csv
    print("\n🏗️ C. 验证系统级得分文件...")
    file_c = 'gse28914_system_scores.csv'
    if os.path.exists(file_c):
        df_c = pd.read_csv(file_c)
        print(f"✅ {file_c}")
        print(f"   - 形状: {df_c.shape[0]} samples × {df_c.shape[1]-1} systems")
        print(f"   - 系统: {list(df_c.columns[1:])}")
        
        # 系统得分统计
        system_cols = df_c.columns[1:]
        for system in system_cols:
            mean_score = df_c[system].mean()
            std_score = df_c[system].std()
            print(f"   - {system}: {mean_score:.4f} ± {std_score:.4f}")
        
        files_status['system_scores'] = {
            'exists': True,
            'shape': df_c.shape,
            'systems': len(df_c.columns) - 1
        }
    else:
        print(f"❌ {file_c} 不存在")
        files_status['system_scores'] = {'exists': False}
    
    # D. 验证 gene_sets_14_subcategories.gmt
    print("\n🧬 D. 验证基因集定义文件...")
    file_d = 'gene_sets_14_subcategories.gmt'
    if os.path.exists(file_d):
        with open(file_d, 'r') as f:
            lines = f.readlines()
        
        print(f"✅ {file_d}")
        print(f"   - 基因集数量: {len(lines)}")
        
        # 分析每个基因集
        gene_set_info = {}
        for line in lines:
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                gene_set_name = parts[0]
                gene_count = len(parts) - 2  # 减去名称和描述
                gene_set_info[gene_set_name] = gene_count
                print(f"   - {gene_set_name}: {gene_count} genes")
        
        files_status['gene_sets'] = {
            'exists': True,
            'gene_sets': len(lines),
            'gene_set_info': gene_set_info
        }
    else:
        print(f"❌ {file_d} 不存在")
        files_status['gene_sets'] = {'exists': False}
    
    # E. 验证 gse28914_expression_matrix_sample.csv
    print("\n📈 E. 验证表达矩阵文件...")
    file_e = 'gse28914_expression_matrix_sample.csv'
    if os.path.exists(file_e):
        df_e = pd.read_csv(file_e, index_col=0)
        print(f"✅ {file_e}")
        print(f"   - 形状: {df_e.shape[0]} probes × {df_e.shape[1]} samples")
        print(f"   - 表达范围: [{df_e.min().min():.2f}, {df_e.max().max():.2f}]")
        
        files_status['expression_matrix'] = {
            'exists': True,
            'shape': df_e.shape
        }
    else:
        print(f"❌ {file_e} 不存在")
        files_status['expression_matrix'] = {'exists': False}
    
    # 数据一致性检查
    print("\n🔍 数据一致性检查...")
    
    if files_status['ssgsea_scores']['exists'] and files_status['sample_info']['exists']:
        # 检查样本ID是否一致
        samples_a = set(df_a['sample_id'])
        samples_b = set(df_b['sample_id'])
        
        if samples_a == samples_b:
            print("✅ ssGSEA得分和样本信息的样本ID完全一致")
        else:
            print("⚠️  ssGSEA得分和样本信息的样本ID不一致")
            print(f"   - 仅在得分文件中: {samples_a - samples_b}")
            print(f"   - 仅在信息文件中: {samples_b - samples_a}")
    
    if files_status['ssgsea_scores']['exists'] and files_status['system_scores']['exists']:
        # 检查样本数量是否一致
        if df_a.shape[0] == df_c.shape[0]:
            print("✅ ssGSEA得分和系统得分的样本数量一致")
        else:
            print(f"⚠️  样本数量不一致: ssGSEA({df_a.shape[0]}) vs 系统({df_c.shape[0]})")
    
    # 生成最终摘要
    print("\n📋 最终摘要...")
    
    total_files = 5
    existing_files = sum(1 for status in files_status.values() if status['exists'])
    
    print(f"   - 生成文件: {existing_files}/{total_files}")
    print(f"   - 完成率: {existing_files/total_files*100:.1f}%")
    
    if existing_files == total_files:
        print("🎉 所有文件生成成功！GSE28914数据集完整可用")
    else:
        print("⚠️  部分文件缺失，请检查生成过程")
    
    # 使用建议
    print(f"\n💡 使用建议:")
    print(f"   1. 主要分析文件:")
    print(f"      - gse28914_ssgsea_scores.csv: 14个子分类的ssGSEA得分")
    print(f"      - gse28914_sample_info.csv: 样本时间点和分组信息")
    print(f"   2. 系统级分析:")
    print(f"      - gse28914_system_scores.csv: 5大系统的聚合得分")
    print(f"   3. 基因集定义:")
    print(f"      - gene_sets_14_subcategories.gmt: 标准GMT格式基因集")
    print(f"   4. 原始数据:")
    print(f"      - gse28914_expression_matrix_sample.csv: 表达矩阵示例")
    
    return files_status

if __name__ == "__main__":
    validate_all_files()