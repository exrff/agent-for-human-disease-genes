#!/usr/bin/env python3
"""
检查real_ssgsea_validation_report.json文件的数据完整性
"""

import json
import os

def check_json_completeness():
    """检查JSON文件的数据完整性"""
    
    json_file = 'results/full_classification/real_ssgsea_validation/real_ssgsea_validation_report.json'
    
    if not os.path.exists(json_file):
        print(f"❌ 文件不存在: {json_file}")
        return
    
    print(f"📁 检查文件: {json_file}")
    
    # 获取文件大小
    file_size = os.path.getsize(json_file)
    print(f"📊 文件大小: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        print(f"\n✅ JSON文件加载成功")
        
        # 检查基本信息
        analysis_info = data.get('analysis_info', {})
        print(f"\n📋 分析信息:")
        print(f"   - 标题: {analysis_info.get('title', 'N/A')}")
        print(f"   - 分析数据集数: {analysis_info.get('datasets_analyzed', 'N/A')}")
        print(f"   - 总样本数: {analysis_info.get('total_samples', 'N/A')}")
        print(f"   - 子分类数: {analysis_info.get('subcategories_analyzed', 'N/A')}")
        
        # 检查数据集结果
        dataset_results = data.get('dataset_results', {})
        print(f"\n📊 数据集结果:")
        
        for dataset_id, result in dataset_results.items():
            print(f"\n🔬 {dataset_id}:")
            
            # 检查表达数据形状
            expr_shape = result.get('expression_shape', [0, 0])
            gene_expr_shape = result.get('gene_expression_shape', [0, 0])
            print(f"   - 原始表达数据: {expr_shape[0]:,} probes × {expr_shape[1]:,} samples")
            print(f"   - 基因表达矩阵: {gene_expr_shape[0]:,} genes × {gene_expr_shape[1]:,} samples")
            
            # 检查样本信息
            sample_info = result.get('sample_info', {})
            titles = sample_info.get('titles', [])
            accessions = sample_info.get('accessions', [])
            characteristics = sample_info.get('characteristics', [])
            
            print(f"   - 样本标题数: {len(titles)}")
            print(f"   - 样本编号数: {len(accessions)}")
            print(f"   - 特征信息数: {len(characteristics)}")
            
            # 检查子分类得分
            subcategory_scores = result.get('subcategory_scores', {})
            print(f"   - 子分类数: {len(subcategory_scores)}")
            
            # 检查每个子分类的得分数组长度
            for subcat_code, scores_info in subcategory_scores.items():
                scores = scores_info.get('scores', [])
                expected_samples = gene_expr_shape[1]
                
                print(f"     * {subcat_code}: {len(scores)} scores (期望: {expected_samples})")
                
                if len(scores) != expected_samples:
                    print(f"       ⚠️  得分数量不匹配! 实际: {len(scores)}, 期望: {expected_samples}")
                else:
                    print(f"       ✅ 得分数量正确")
                
                # 显示前几个得分作为示例
                if len(scores) > 0:
                    sample_scores = scores[:min(5, len(scores))]
                    print(f"       📊 前{len(sample_scores)}个得分: {[f'{s:.4f}' for s in sample_scores]}")
            
            # 检查系统级得分
            system_scores = result.get('system_scores', {})
            print(f"   - 系统级得分数: {len(system_scores)}")
            
            for system_name, system_info in system_scores.items():
                system_score_array = system_info.get('scores', [])
                print(f"     * {system_name}: {len(system_score_array)} scores")
        
        # 检查生物学解释
        bio_interp = data.get('biological_interpretation', {})
        print(f"\n🧬 生物学解释:")
        for dataset_id, interp in bio_interp.items():
            expected_subcats = interp.get('expected_subcategories', [])
            top_subcats = interp.get('top_scoring_subcategories', [])
            success_rate = interp.get('validation_success_rate', 0)
            
            print(f"   - {dataset_id}:")
            print(f"     * 预期子分类: {expected_subcats}")
            print(f"     * 实际前5子分类: {top_subcats}")
            print(f"     * 验证成功率: {success_rate:.1%}")
        
        # 检查统计摘要
        stats = data.get('statistical_summary', {})
        print(f"\n📈 统计摘要:")
        print(f"   - 总体平均得分: {stats.get('overall_mean_score', 'N/A'):.4f}")
        print(f"   - 平均基因重叠率: {stats.get('mean_gene_overlap_percent', 'N/A'):.1f}%")
        print(f"   - 有效子分类测试: {stats.get('subcategories_with_genes', 'N/A')}/{stats.get('total_subcategory_tests', 'N/A')}")
        
        print(f"\n✅ 数据完整性检查完成")
        
        return data
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {e}")
        return None
    except Exception as e:
        print(f"❌ 检查过程中出错: {e}")
        return None

if __name__ == "__main__":
    check_json_completeness()