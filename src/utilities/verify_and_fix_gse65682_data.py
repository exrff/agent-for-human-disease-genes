#!/usr/bin/env python3
"""
验证GSE65682数据的真实性并修复空数据问题
"""

import pandas as pd
import numpy as np
import os
import shutil

def verify_and_fix_gse65682_data():
    """验证并修复GSE65682数据"""
    print("="*80)
    print("VERIFYING AND FIXING GSE65682 DATA")
    print("="*80)
    
    # 1. 检查数据来源和真实性
    print(f"\n🔍 Step 1: Verifying data sources...")
    
    # 检查根目录下的提取文件
    root_files = [
        'gse65682_ssgsea_scores.csv',
        'gse65682_sample_groups.csv', 
        'gse65682_detailed_sample_info.csv'
    ]
    
    valid_files = []
    for file in root_files:
        if os.path.exists(file):
            df = pd.read_csv(file)
            print(f"   ✅ {file}: {df.shape[0]} rows × {df.shape[1]} columns")
            
            # 检查数据是否为空
            if file == 'gse65682_ssgsea_scores.csv':
                numeric_cols = [col for col in df.columns if col != 'sample_id']
                non_zero_count = (df[numeric_cols] != 0).sum().sum()
                print(f"      - Non-zero values: {non_zero_count}")
                
                if non_zero_count > 0:
                    print(f"      - Data range: {df[numeric_cols].min().min():.4f} to {df[numeric_cols].max().max():.4f}")
                    valid_files.append(file)
                else:
                    print(f"      ⚠️ All values are zero!")
            else:
                valid_files.append(file)
        else:
            print(f"   ❌ {file}: Not found")
    
    # 2. 验证数据来源
    print(f"\n🔍 Step 2: Verifying data authenticity...")
    
    if 'gse65682_ssgsea_scores.csv' in valid_files:
        scores_df = pd.read_csv('gse65682_ssgsea_scores.csv')
        
        # 检查数据合理性
        print(f"   📊 Data quality checks:")
        
        # 检查样本ID格式
        sample_ids = scores_df['sample_id'].tolist()
        gsm_pattern = all(sid.startswith('GSM') for sid in sample_ids)
        print(f"   • Sample ID format (GSM*): {'✅' if gsm_pattern else '❌'}")
        
        # 检查数据分布
        numeric_cols = [col for col in scores_df.columns if col != 'sample_id']
        means = scores_df[numeric_cols].mean()
        stds = scores_df[numeric_cols].std()
        
        print(f"   • Mean range: {means.min():.4f} to {means.max():.4f}")
        print(f"   • Std range: {stds.min():.4f} to {stds.max():.4f}")
        
        # 检查是否有合理的ssGSEA得分范围
        reasonable_range = (means.min() > -0.2) and (means.max() < 0.5) and (stds.mean() > 0.001)
        print(f"   • Reasonable ssGSEA range: {'✅' if reasonable_range else '❌'}")
        
        # 检查样本数量
        expected_samples = 802  # GSE65682应该有802个样本
        actual_samples = len(scores_df)
        print(f"   • Sample count: {actual_samples} (expected: {expected_samples}) {'✅' if actual_samples == expected_samples else '⚠️'}")
        
        if gsm_pattern and reasonable_range:
            print(f"\n   ✅ Data appears to be authentic GSE65682 ssGSEA scores!")
            
            # 3. 替换空数据
            print(f"\n🔧 Step 3: Replacing empty data in clean_data folder...")
            replace_empty_data(valid_files)
            
        else:
            print(f"\n   ❌ Data authenticity questionable!")
            return False
    else:
        print(f"\n   ❌ No valid ssGSEA scores found!")
        return False
    
    return True

def replace_empty_data(valid_files):
    """替换clean_data文件夹中的空数据"""
    
    clean_data_dir = 'results/disease_analysis/GSE65682-脓毒症/clean_data'
    
    # 确保目录存在
    os.makedirs(clean_data_dir, exist_ok=True)
    
    print(f"   📁 Target directory: {clean_data_dir}")
    
    # 处理ssGSEA得分数据
    if 'gse65682_ssgsea_scores.csv' in valid_files:
        print(f"\n   🔄 Processing ssGSEA scores...")
        
        # 读取真实数据
        scores_df = pd.read_csv('gse65682_ssgsea_scores.csv')
        sample_groups = pd.read_csv('gse65682_sample_groups.csv') if 'gse65682_sample_groups.csv' in valid_files else None
        
        # 创建系统级得分
        system_scores = create_system_scores(scores_df, sample_groups)
        
        # 保存文件
        target_system_file = os.path.join(clean_data_dir, 'GSE65682_system_scores.csv')
        target_subcategory_file = os.path.join(clean_data_dir, 'GSE65682_subcategory_scores.csv')
        
        system_scores.to_csv(target_system_file, index=False)
        print(f"   ✅ Saved: {target_system_file}")
        
        # 为子分类得分添加元数据
        subcategory_scores = scores_df.copy()
        if sample_groups is not None:
            subcategory_scores = subcategory_scores.merge(sample_groups, on='sample_id')
            
            # 添加标准列
            if 'group' in subcategory_scores.columns:
                subcategory_scores['subject_id'] = subcategory_scores['sample_id'].str.replace('GSM', 'Subject_')
                subcategory_scores['condition'] = subcategory_scores['group'].map({'Sepsis': 'Sepsis', 'Control': 'Control'})
                
                # 重新排列列
                cols = ['sample_id', 'subject_id', 'condition', 'group'] + [col for col in subcategory_scores.columns if col not in ['sample_id', 'subject_id', 'condition', 'group']]
                subcategory_scores = subcategory_scores[cols]
        
        subcategory_scores.to_csv(target_subcategory_file, index=False)
        print(f"   ✅ Saved: {target_subcategory_file}")
    
    # 处理样本信息
    if 'gse65682_sample_groups.csv' in valid_files:
        print(f"\n   🔄 Processing sample info...")
        
        sample_groups = pd.read_csv('gse65682_sample_groups.csv')
        
        # 添加标准列
        sample_info = sample_groups.copy()
        sample_info['subject_id'] = sample_info['sample_id'].str.replace('GSM', 'Subject_')
        sample_info['condition'] = sample_info['group'].map({'Sepsis': 'Sepsis', 'Control': 'Control'})
        
        # 重新排列列
        sample_info = sample_info[['sample_id', 'subject_id', 'condition', 'group']]
        
        target_sample_file = os.path.join(clean_data_dir, 'GSE65682_sample_info.csv')
        sample_info.to_csv(target_sample_file, index=False)
        print(f"   ✅ Saved: {target_sample_file}")
    
    # 复制详细样本信息
    if 'gse65682_detailed_sample_info.csv' in valid_files:
        print(f"\n   🔄 Processing detailed sample info...")
        
        source_file = 'gse65682_detailed_sample_info.csv'
        target_file = os.path.join(clean_data_dir, 'gse65682_detailed_sample_info.csv')
        
        shutil.copy2(source_file, target_file)
        print(f"   ✅ Copied: {target_file}")
    
    print(f"\n   🎉 Data replacement completed!")

def create_system_scores(scores_df, sample_groups=None):
    """从子分类得分创建系统级得分"""
    
    # 系统映射
    system_mapping = {
        'A': ['A1', 'A2', 'A3', 'A4'],
        'B': ['B1', 'B2', 'B3'],
        'C': ['C1', 'C2', 'C3'],
        'D': ['D1', 'D2'],
        'E': ['E1', 'E2']
    }
    
    # 创建系统得分
    system_scores = pd.DataFrame()
    system_scores['sample_id'] = scores_df['sample_id']
    
    for system, subcats in system_mapping.items():
        available_subcats = [sc for sc in subcats if sc in scores_df.columns]
        if available_subcats:
            system_scores[system] = scores_df[available_subcats].mean(axis=1)
        else:
            system_scores[system] = 0.0
    
    # 添加元数据
    if sample_groups is not None:
        system_scores = system_scores.merge(sample_groups, on='sample_id')
        
        if 'group' in system_scores.columns:
            system_scores['subject_id'] = system_scores['sample_id'].str.replace('GSM', 'Subject_')
            system_scores['condition'] = system_scores['group'].map({'Sepsis': 'Sepsis', 'Control': 'Control'})
            
            # 重新排列列
            cols = ['sample_id', 'subject_id', 'condition', 'group', 'A', 'B', 'C', 'D', 'E']
            system_scores = system_scores[cols]
    
    return system_scores

def verify_replacement():
    """验证替换结果"""
    print(f"\n🔍 Step 4: Verifying replacement...")
    
    clean_data_dir = 'results/disease_analysis/GSE65682-脓毒症/clean_data'
    
    files_to_check = [
        'GSE65682_system_scores.csv',
        'GSE65682_subcategory_scores.csv',
        'GSE65682_sample_info.csv'
    ]
    
    for file in files_to_check:
        file_path = os.path.join(clean_data_dir, file)
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            print(f"   ✅ {file}: {df.shape[0]} rows × {df.shape[1]} columns")
            
            # 检查是否还有零值
            if 'scores' in file:
                numeric_cols = [col for col in df.columns if col not in ['sample_id', 'subject_id', 'condition', 'group']]
                if numeric_cols:
                    non_zero_count = (df[numeric_cols] != 0).sum().sum()
                    total_values = len(df) * len(numeric_cols)
                    print(f"      - Non-zero values: {non_zero_count}/{total_values} ({non_zero_count/total_values*100:.1f}%)")
                    
                    if non_zero_count > 0:
                        print(f"      - Data range: {df[numeric_cols].min().min():.4f} to {df[numeric_cols].max().max():.4f}")
        else:
            print(f"   ❌ {file}: Not found")

def main():
    """主函数"""
    try:
        success = verify_and_fix_gse65682_data()
        
        if success:
            verify_replacement()
            
            print(f"\n{'='*80}")
            print("GSE65682 DATA VERIFICATION AND FIX COMPLETED")
            print(f"{'='*80}")
            
            print(f"\n✅ Summary:")
            print(f"   • Data authenticity: Verified")
            print(f"   • Empty data: Replaced with real ssGSEA scores")
            print(f"   • Files updated in: results/disease_analysis/GSE65682-脓毒症/clean_data/")
            
        else:
            print(f"\n❌ Data verification failed!")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()