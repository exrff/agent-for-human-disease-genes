#!/usr/bin/env python3
"""
从GSE21899原始数据中提取详细的临床元数据
挖掘戈谢病与五大系统分类的潜在契合规律
"""

import pandas as pd
import numpy as np
import gzip
import re

def extract_gse21899_metadata():
    """提取GSE21899的详细元数据"""
    print("="*80)
    print("GSE21899 GAUCHER DISEASE METADATA EXTRACTION")
    print("="*80)
    
    # 读取原始GEO数据
    data_path = 'data/validation_datasets/GSE21899-戈谢病/GSE21899_series_matrix.txt.gz'
    
    print(f"\n📂 Reading GEO series matrix file...")
    
    try:
        with gzip.open(data_path, 'rt', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        print(f"   • Total lines in file: {len(lines)}")
        
        # 解析元数据
        metadata = parse_geo_metadata(lines)
        
        # 显示找到的信息
        print(f"\n🔍 Metadata found:")
        for key, value in metadata.items():
            if isinstance(value, list):
                print(f"   • {key}: {len(value)} entries")
                if len(value) > 0 and len(str(value[0])) < 200:
                    print(f"     - Example: {value[0]}")
            else:
                print(f"   • {key}: {str(value)[:100]}...")
        
        # 解析样本特征
        if 'sample_characteristics' in metadata:
            clinical_features = parse_sample_characteristics(metadata)
            
            if clinical_features:
                print(f"\n🧬 Clinical features extracted:")
                for feature, values in clinical_features.items():
                    unique_values = list(set(values))
                    print(f"   • {feature}: {len(unique_values)} unique values")
                    print(f"     - Values: {unique_values}")
                
                # 保存临床特征
                save_clinical_features(clinical_features, metadata.get('sample_ids', []))
                
                # 分析戈谢病特异性信息
                analyze_gaucher_specific_info(clinical_features, metadata)
                
                return clinical_features
            else:
                print(f"   ⚠️ No structured clinical features found")
        
        # 如果没有找到特征，尝试从标题和描述中提取
        if 'sample_titles' in metadata or 'sample_descriptions' in metadata:
            print(f"\n🔍 Attempting to extract info from titles/descriptions...")
            extracted_info = extract_from_titles_descriptions(metadata)
            
            if extracted_info:
                save_clinical_features(extracted_info, metadata.get('sample_ids', []))
                return extracted_info
        
    except Exception as e:
        print(f"❌ Error reading GEO file: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def parse_geo_metadata(lines):
    """解析GEO元数据"""
    metadata = {}
    
    # 查找关键信息
    sample_ids = []
    sample_titles = []
    sample_characteristics = []
    sample_descriptions = []
    sample_sources = []
    
    for line in lines:
        line = line.strip()
        
        if line.startswith('!Sample_geo_accession'):
            parts = line.split('\t')
            sample_ids = [p.strip('"') for p in parts[1:] if p.strip()]
            
        elif line.startswith('!Sample_title'):
            parts = line.split('\t')
            sample_titles = [p.strip('"') for p in parts[1:] if p.strip()]
            
        elif line.startswith('!Sample_description'):
            parts = line.split('\t')
            sample_descriptions = [p.strip('"') for p in parts[1:] if p.strip()]
            
        elif line.startswith('!Sample_source_name'):
            parts = line.split('\t')
            sample_sources = [p.strip('"') for p in parts[1:] if p.strip()]
            
        elif line.startswith('!Sample_characteristics_ch1'):
            parts = line.split('\t')
            characteristics = [p.strip('"') for p in parts[1:] if p.strip()]
            sample_characteristics.append(characteristics)
            
        elif line.startswith('!series_matrix_table_begin'):
            break
    
    metadata['sample_ids'] = sample_ids
    metadata['sample_titles'] = sample_titles
    metadata['sample_descriptions'] = sample_descriptions
    metadata['sample_sources'] = sample_sources
    metadata['sample_characteristics'] = sample_characteristics
    
    return metadata

def parse_sample_characteristics(metadata):
    """解析样本特征信息"""
    characteristics_lines = metadata.get('sample_characteristics', [])
    sample_ids = metadata.get('sample_ids', [])
    
    if not characteristics_lines or not sample_ids:
        return None
    
    print(f"\n   Parsing {len(characteristics_lines)} characteristic lines...")
    
    # 显示原始特征信息
    for i, char_line in enumerate(characteristics_lines):
        print(f"   Line {i+1}: {len(char_line)} samples")
        if char_line and len(char_line) > 0:
            print(f"     Example: {char_line[0]}")
    
    # 尝试识别特征类型
    clinical_features = {}
    
    for i, char_line in enumerate(characteristics_lines):
        if len(char_line) != len(sample_ids):
            print(f"   ⚠️ Line {i+1}: Length mismatch ({len(char_line)} vs {len(sample_ids)})")
            continue
        
        # 分析第一个样本的特征来确定类型
        if char_line and len(char_line) > 0:
            sample_char = char_line[0].lower()
            
            # 检查是否包含戈谢病相关关键词
            if any(keyword in sample_char for keyword in ['cell type', 'cell_type', 'tissue']):
                clinical_features['cell_type'] = char_line
                print(f"   ✅ Found cell type information")
                
            elif any(keyword in sample_char for keyword in ['treatment', 'condition', 'disease']):
                clinical_features['condition'] = char_line
                print(f"   ✅ Found condition information")
                
            elif any(keyword in sample_char for keyword in ['genotype', 'mutation', 'variant']):
                clinical_features['genotype'] = char_line
                print(f"   ✅ Found genotype information")
                
            elif any(keyword in sample_char for keyword in ['age', 'time']):
                clinical_features['age_time'] = char_line
                print(f"   ✅ Found age/time information")
                
            elif any(keyword in sample_char for keyword in ['sex', 'gender']):
                clinical_features['gender'] = char_line
                print(f"   ✅ Found gender information")
                
            elif any(keyword in sample_char for keyword in ['severity', 'stage', 'grade']):
                clinical_features['severity'] = char_line
                print(f"   ✅ Found severity information")
                
            else:
                # 通用特征
                feature_name = f"characteristic_{i+1}"
                clinical_features[feature_name] = char_line
                print(f"   • Generic feature {i+1}: {sample_char[:50]}...")
    
    return clinical_features if clinical_features else None

def extract_from_titles_descriptions(metadata):
    """从标题和描述中提取信息"""
    
    sample_ids = metadata.get('sample_ids', [])
    sample_titles = metadata.get('sample_titles', [])
    sample_descriptions = metadata.get('sample_descriptions', [])
    sample_sources = metadata.get('sample_sources', [])
    
    extracted_info = {}
    
    # 从标题中提取信息
    if sample_titles and len(sample_titles) == len(sample_ids):
        print(f"   Analyzing sample titles...")
        
        # 尝试识别模式
        groups = []
        cell_types = []
        
        for title in sample_titles:
            title_lower = title.lower()
            
            # 识别对照组vs疾病组
            if any(keyword in title_lower for keyword in ['control', 'normal', 'healthy']):
                groups.append('Control')
            elif any(keyword in title_lower for keyword in ['gaucher', 'patient', 'disease']):
                groups.append('Gaucher')
            else:
                groups.append('Unknown')
            
            # 识别细胞类型
            if 'macrophage' in title_lower:
                cell_types.append('Macrophage')
            elif 'monocyte' in title_lower:
                cell_types.append('Monocyte')
            elif 'cell' in title_lower:
                cell_types.append('Cell')
            else:
                cell_types.append('Unknown')
        
        if len(set(groups)) > 1:
            extracted_info['group'] = groups
            print(f"     - Groups identified: {set(groups)}")
        
        if len(set(cell_types)) > 1:
            extracted_info['cell_type'] = cell_types
            print(f"     - Cell types identified: {set(cell_types)}")
    
    # 从来源信息中提取
    if sample_sources and len(sample_sources) == len(sample_ids):
        print(f"   Analyzing sample sources...")
        
        source_types = []
        for source in sample_sources:
            source_lower = source.lower()
            
            if 'gaucher' in source_lower:
                source_types.append('Gaucher_Cell')
            elif 'control' in source_lower or 'normal' in source_lower:
                source_types.append('Control_Cell')
            else:
                source_types.append('Unknown_Cell')
        
        if len(set(source_types)) > 1:
            extracted_info['source_type'] = source_types
            print(f"     - Source types identified: {set(source_types)}")
    
    return extracted_info if extracted_info else None

def analyze_gaucher_specific_info(clinical_features, metadata):
    """分析戈谢病特异性信息"""
    
    print(f"\n🧬 Gaucher Disease Specific Analysis:")
    
    sample_ids = metadata.get('sample_ids', [])
    
    # 分析细胞类型分布
    if 'cell_type' in clinical_features:
        cell_types = clinical_features['cell_type']
        cell_type_counts = {}
        for cell_type in cell_types:
            cell_type_counts[cell_type] = cell_type_counts.get(cell_type, 0) + 1
        
        print(f"   • Cell type distribution:")
        for cell_type, count in cell_type_counts.items():
            print(f"     - {cell_type}: {count} samples")
    
    # 分析疾病vs对照分布
    if 'group' in clinical_features:
        groups = clinical_features['group']
        group_counts = {}
        for group in groups:
            group_counts[group] = group_counts.get(group, 0) + 1
        
        print(f"   • Disease vs Control distribution:")
        for group, count in group_counts.items():
            print(f"     - {group}: {count} samples")
    
    # 戈谢病相关的生物学背景
    print(f"\n📚 Gaucher Disease Background:")
    print(f"   • Lysosomal storage disorder")
    print(f"   • Deficiency in glucocerebrosidase enzyme")
    print(f"   • Accumulation of glucocerebroside")
    print(f"   • Affects macrophages (Gaucher cells)")
    print(f"   • Expected system activation: System C (Metabolism)")

def save_clinical_features(clinical_features, sample_ids):
    """保存临床特征到CSV文件"""
    
    if not clinical_features or not sample_ids:
        return
    
    # 创建DataFrame
    clinical_df = pd.DataFrame({'sample_id': sample_ids})
    
    for feature_name, feature_values in clinical_features.items():
        if len(feature_values) == len(sample_ids):
            clinical_df[feature_name] = feature_values
    
    # 保存到文件
    output_path = 'results/disease_analysis/GSE21899-戈谢病/analysis_results/GSE21899_clinical_metadata.csv'
    
    # 确保目录存在
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    clinical_df.to_csv(output_path, index=False)
    
    print(f"\n💾 Clinical metadata saved to: {output_path}")
    print(f"   • Samples: {len(clinical_df)}")
    print(f"   • Features: {len(clinical_df.columns) - 1}")

def suggest_additional_labels():
    """建议补充的戈谢病相关标签"""
    
    print(f"\n💡 SUGGESTED ADDITIONAL LABELS FOR GAUCHER DISEASE:")
    
    print(f"\n🏷️ Clinical Labels to Consider:")
    print(f"   1. **Gaucher Disease Type**:")
    print(f"      - Type 1 (Non-neuronopathic)")
    print(f"      - Type 2 (Acute neuronopathic)")
    print(f"      - Type 3 (Chronic neuronopathic)")
    
    print(f"\n   2. **Disease Severity**:")
    print(f"      - Mild")
    print(f"      - Moderate") 
    print(f"      - Severe")
    
    print(f"\n   3. **Organ Involvement**:")
    print(f"      - Hepatomegaly (liver enlargement)")
    print(f"      - Splenomegaly (spleen enlargement)")
    print(f"      - Bone involvement")
    print(f"      - Neurological involvement")
    
    print(f"\n   4. **Treatment Status**:")
    print(f"      - Treatment-naive")
    print(f"      - Enzyme replacement therapy (ERT)")
    print(f"      - Substrate reduction therapy (SRT)")
    
    print(f"\n   5. **Biomarkers**:")
    print(f"      - Chitotriosidase levels")
    print(f"      - CCL18/PARC levels")
    print(f"      - Glucosylsphingosine levels")
    
    print(f"\n🧬 Molecular Labels:")
    print(f"   6. **GBA Gene Mutations**:")
    print(f"      - L444P (common severe mutation)")
    print(f"      - N370S (common mild mutation)")
    print(f"      - 84GG (frameshift mutation)")
    print(f"      - IVS2+1G>A (splicing mutation)")
    
    print(f"\n   7. **Functional Impact**:")
    print(f"      - Residual enzyme activity level")
    print(f"      - Protein stability")
    print(f"      - Cellular localization")
    
    print(f"\n🔬 Cellular Labels:")
    print(f"   8. **Cell Type Specificity**:")
    print(f"      - Gaucher cells (lipid-laden macrophages)")
    print(f"      - Normal macrophages")
    print(f"      - Monocytes")
    print(f"      - Other immune cells")
    
    print(f"\n   9. **Metabolic State**:")
    print(f"      - Glucocerebroside accumulation level")
    print(f"      - Lysosomal dysfunction degree")
    print(f"      - Inflammatory activation state")

def create_enhanced_sample_info():
    """创建增强的样本信息，基于已知的戈谢病生物学"""
    
    print(f"\n🔧 Creating Enhanced Sample Information...")
    
    # 读取当前样本信息
    current_sample_info = pd.read_csv('results/disease_analysis/GSE21899-戈谢病/clean_data/GSE21899_sample_info.csv')
    
    print(f"   Current samples: {len(current_sample_info)}")
    
    # 基于样本ID和已知信息推断标签
    enhanced_info = current_sample_info.copy()
    
    # 根据文献和数据集描述添加推断的标签
    # GSE21899研究的是Gaucher细胞的巨噬细胞表型
    
    # 添加细胞类型标签
    enhanced_info['cell_type'] = 'Macrophage'
    
    # 添加疾病状态（基于已有的group信息）
    enhanced_info['disease_state'] = enhanced_info['group'].map({
        'Gaucher': 'Gaucher_Disease',
        'Control': 'Normal'
    })
    
    # 添加预期的系统激活模式
    enhanced_info['expected_primary_system'] = enhanced_info['group'].map({
        'Gaucher': 'System_C_Metabolism',
        'Control': 'Baseline'
    })
    
    # 添加生物学相关性标签
    enhanced_info['biological_relevance'] = enhanced_info['group'].map({
        'Gaucher': 'Lysosomal_storage_disorder',
        'Control': 'Normal_metabolism'
    })
    
    # 添加预期的分子通路
    enhanced_info['expected_pathways'] = enhanced_info['group'].map({
        'Gaucher': 'Glucocerebroside_metabolism,Lysosomal_function,Macrophage_activation',
        'Control': 'Normal_cellular_metabolism'
    })
    
    # 保存增强的样本信息
    output_path = 'results/disease_analysis/GSE21899-戈谢病/analysis_results/GSE21899_enhanced_sample_info.csv'
    enhanced_info.to_csv(output_path, index=False)
    
    print(f"   ✅ Enhanced sample info saved: {output_path}")
    print(f"   Added labels: cell_type, disease_state, expected_primary_system, biological_relevance, expected_pathways")
    
    return enhanced_info

def main():
    """主函数"""
    try:
        print("Starting GSE21899 Gaucher Disease metadata extraction...")
        
        # 提取元数据
        clinical_features = extract_gse21899_metadata()
        
        # 建议额外标签
        suggest_additional_labels()
        
        # 创建增强的样本信息
        enhanced_info = create_enhanced_sample_info()
        
        print(f"\n{'='*80}")
        print("GSE21899 METADATA EXTRACTION COMPLETED")
        print(f"{'='*80}")
        
        print(f"\n🎯 Summary:")
        if clinical_features:
            print(f"   • Extracted {len(clinical_features)} clinical features")
        print(f"   • Created enhanced sample information with biological labels")
        print(f"   • Suggested additional labels for deeper analysis")
        
        print(f"\n📁 Generated Files:")
        print(f"   • GSE21899_clinical_metadata.csv (if metadata found)")
        print(f"   • GSE21899_enhanced_sample_info.csv")
        
        print(f"\n💡 Next Steps:")
        print(f"   • Use enhanced labels for deeper system-disease correlation analysis")
        print(f"   • Consider adding mutation/severity information if available")
        print(f"   • Validate system activation patterns against biological expectations")
        
    except Exception as e:
        print(f"❌ Error in metadata extraction: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()