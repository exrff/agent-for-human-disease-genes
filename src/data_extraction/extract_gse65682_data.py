#!/usr/bin/env python3
"""
从real_ssgsea_validation_report.json中提取GSE65682数据
生成gse65682_ssgsea_scores.csv和gse65682_sample_groups.csv
"""

import json
import pandas as pd
import numpy as np
import os

def extract_gse65682_data():
    """提取GSE65682的ssGSEA得分和样本分组信息"""
    
    json_file = 'results/full_classification/real_ssgsea_validation/real_ssgsea_validation_report.json'
    
    if not os.path.exists(json_file):
        print(f"❌ 文件不存在: {json_file}")
        return
    
    print(f"📁 读取文件: {json_file}")
    
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # 提取GSE65682数据
        gse65682_data = data['dataset_results']['GSE65682']
        
        print(f"✅ 成功加载GSE65682数据")
        
        # 1. 提取ssGSEA得分数据
        print(f"\n📊 提取ssGSEA得分数据...")
        
        subcategory_scores = gse65682_data['subcategory_scores']
        sample_info = gse65682_data['sample_info']
        
        # 获取样本ID
        sample_accessions = sample_info['accessions']  # GSM编号
        sample_titles = sample_info['titles']  # 样本描述
        
        print(f"   - 样本数量: {len(sample_accessions)}")
        print(f"   - 子分类数量: {len(subcategory_scores)}")
        
        # 创建ssGSEA得分DataFrame
        scores_data = {}
        scores_data['sample_id'] = sample_accessions
        
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
            else:
                print(f"   ⚠️  缺少子分类: {subcat}")
        
        # 创建DataFrame并保存
        scores_df = pd.DataFrame(scores_data)
        
        output_file1 = 'gse65682_ssgsea_scores.csv'
        scores_df.to_csv(output_file1, index=False)
        
        print(f"✅ 保存ssGSEA得分文件: {output_file1}")
        print(f"   - 形状: {scores_df.shape[0]} samples × {scores_df.shape[1]-1} subcategories")
        
        # 2. 提取样本分组信息
        print(f"\n👥 提取样本分组信息...")
        
        # 分析样本标题以确定分组
        groups = []
        
        for i, (sample_id, title) in enumerate(zip(sample_accessions, sample_titles)):
            title_lower = title.lower()
            
            if 'healthy' in title_lower or 'control' in title_lower or 'hv' in title_lower:
                group = 'Control'
            elif 'intensive-care' in title_lower or 'icu' in title_lower or 'patient' in title_lower:
                group = 'Sepsis'  # ICU患者通常是脓毒症或严重疾病
            else:
                group = 'Unknown'
            
            groups.append(group)
        
        # 统计分组
        group_counts = pd.Series(groups).value_counts()
        print(f"   - 分组统计:")
        for group, count in group_counts.items():
            print(f"     * {group}: {count} samples")
        
        # 创建分组DataFrame
        groups_data = {
            'sample_id': sample_accessions,
            'group': groups
        }
        
        groups_df = pd.DataFrame(groups_data)
        
        output_file2 = 'gse65682_sample_groups.csv'
        groups_df.to_csv(output_file2, index=False)
        
        print(f"✅ 保存样本分组文件: {output_file2}")
        print(f"   - 形状: {groups_df.shape[0]} samples × {groups_df.shape[1]} columns")
        
        # 3. 显示示例数据
        print(f"\n📋 数据预览:")
        
        print(f"\n🔢 ssGSEA得分示例 (前5行, 关键子分类):")
        key_subcats = ['sample_id', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3']
        available_subcats = [col for col in key_subcats if col in scores_df.columns]
        print(scores_df[available_subcats].head())
        
        print(f"\n👥 样本分组示例 (前10行):")
        print(groups_df.head(10))
        
        # 4. 验证数据质量
        print(f"\n🔍 数据质量验证:")
        
        # 检查ssGSEA得分范围
        numeric_cols = [col for col in scores_df.columns if col != 'sample_id']
        all_scores = []
        for col in numeric_cols:
            all_scores.extend(scores_df[col].tolist())
        
        min_all = min(all_scores)
        max_all = max(all_scores)
        mean_all = np.mean(all_scores)
        
        print(f"   - ssGSEA得分总体范围: [{min_all:.4f}, {max_all:.4f}]")
        print(f"   - ssGSEA得分总体均值: {mean_all:.4f}")
        
        if abs(min_all) > 10 or abs(max_all) > 10:
            print(f"   ⚠️  警告: 得分范围可能异常 (期望: ~[-1,1] 或 [0,1])")
        else:
            print(f"   ✅ 得分范围正常")
        
        # 检查缺失值
        missing_scores = scores_df.isnull().sum().sum()
        missing_groups = groups_df.isnull().sum().sum()
        
        print(f"   - ssGSEA得分缺失值: {missing_scores}")
        print(f"   - 分组信息缺失值: {missing_groups}")
        
        if missing_scores == 0 and missing_groups == 0:
            print(f"   ✅ 无缺失值")
        
        # 5. 生成详细的样本信息文件（可选）
        print(f"\n📄 生成详细样本信息...")
        
        detailed_info = {
            'sample_id': sample_accessions,
            'sample_title': sample_titles,
            'group': groups
        }
        
        # 添加特征信息（如果有的话）
        characteristics = sample_info.get('characteristics', [])
        if characteristics:
            print(f"   - 发现 {len(characteristics)} 组特征信息")
            
            # 处理特征信息
            for i, char_group in enumerate(characteristics):
                if len(char_group) == len(sample_accessions):
                    detailed_info[f'characteristic_{i+1}'] = char_group
        
        detailed_df = pd.DataFrame(detailed_info)
        
        output_file3 = 'gse65682_detailed_sample_info.csv'
        detailed_df.to_csv(output_file3, index=False)
        
        print(f"✅ 保存详细样本信息: {output_file3}")
        
        print(f"\n🎯 生成的文件:")
        print(f"   1. {output_file1} - ssGSEA得分矩阵 ({scores_df.shape[0]}×{scores_df.shape[1]-1})")
        print(f"   2. {output_file2} - 样本分组信息 ({groups_df.shape[0]}×{groups_df.shape[1]})")
        print(f"   3. {output_file3} - 详细样本信息 ({detailed_df.shape[0]}×{detailed_df.shape[1]})")
        
        return scores_df, groups_df, detailed_df
        
    except Exception as e:
        print(f"❌ 处理过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def validate_output_files():
    """验证生成的输出文件"""
    
    print(f"\n🔍 验证输出文件...")
    
    files_to_check = [
        'gse65682_ssgsea_scores.csv',
        'gse65682_sample_groups.csv',
        'gse65682_detailed_sample_info.csv'
    ]
    
    for filename in files_to_check:
        if os.path.exists(filename):
            df = pd.read_csv(filename)
            print(f"✅ {filename}: {df.shape[0]} rows × {df.shape[1]} columns")
            
            # 显示列名
            print(f"   列名: {list(df.columns)}")
            
            # 显示前几行
            print(f"   前3行:")
            print(df.head(3).to_string(index=False))
            print()
        else:
            print(f"❌ 文件不存在: {filename}")

if __name__ == "__main__":
    print("="*80)
    print("GSE65682 数据提取工具")
    print("="*80)
    
    # 提取数据
    scores_df, groups_df, detailed_df = extract_gse65682_data()
    
    if scores_df is not None:
        # 验证输出文件
        validate_output_files()
        
        print(f"\n✅ 数据提取完成!")
        print(f"📊 现在您有了GSE65682的完整ssGSEA得分和样本分组信息")
    else:
        print(f"\n❌ 数据提取失败")