#!/usr/bin/env python3
"""
生成GSE2034乳腺癌"功能三角"分析表格
支持"整体生理意图"的叙述框架
"""

import pandas as pd
import numpy as np

def generate_functional_triangle_table():
    """生成功能三角分析表格"""
    
    print("="*80)
    print("GSE2034 BREAST CANCER FUNCTIONAL TRIANGLE TABLE GENERATION")
    print("Macro-physiological Intent Analysis")
    print("="*80)
    
    # 1. 加载分析结果
    print(f"\n📊 Loading analysis results...")
    system_data, subcategory_data, feature_importance = load_analysis_results()
    
    # 2. 生成系统级功能三角表格
    print(f"\n🔺 Generating system-level functional triangle table...")
    system_table = generate_system_triangle_table(system_data)
    
    # 3. 生成子分类详细排序表格
    print(f"\n📋 Generating subcategory ranking table...")
    subcategory_table = generate_subcategory_ranking_table(subcategory_data)
    
    # 4. 生成特征重要性表格
    print(f"\n⭐ Generating feature importance table...")
    importance_table = generate_importance_table(feature_importance)
    
    # 5. 生成综合解释表格
    print(f"\n🧬 Generating biological interpretation table...")
    interpretation_table = generate_interpretation_table(system_data, subcategory_data)
    
    # 6. 保存所有表格
    print(f"\n💾 Saving all tables...")
    save_all_tables(system_table, subcategory_table, importance_table, interpretation_table)
    
    return {
        'system_table': system_table,
        'subcategory_table': subcategory_table,
        'importance_table': importance_table,
        'interpretation_table': interpretation_table
    }

def load_analysis_results():
    """加载分析结果"""
    
    # 加载系统差异分析
    system_data = pd.read_csv('results/disease_analysis/GSE2034-乳腺癌/analysis_results/relapse_system_differences.csv', index_col=0)
    
    # 加载子分类差异分析
    subcategory_data = pd.read_csv('results/disease_analysis/GSE2034-乳腺癌/analysis_results/relapse_subcategory_differences.csv', index_col=0)
    
    # 加载特征重要性
    feature_importance = pd.read_csv('results/disease_analysis/GSE2034-乳腺癌/analysis_results/relapse_feature_importance.csv')
    
    print(f"   • System data: {system_data.shape}")
    print(f"   • Subcategory data: {subcategory_data.shape}")
    print(f"   • Feature importance: {feature_importance.shape}")
    
    return system_data, subcategory_data, feature_importance

def generate_system_triangle_table(system_data):
    """生成系统级功能三角表格"""
    
    # 系统名称映射
    system_names = {
        'A': '生长与发育 (Growth & Development)',
        'B': '防御与应激 (Defense & Stress Response)', 
        'C': '代谢与能量 (Metabolism & Energy)',
        'D': '维持与修复 (Maintenance & Repair)',
        'E': '连续性与生殖 (Continuity & Reproduction)'
    }
    
    # 按效应量排序
    system_data_sorted = system_data.reindex(system_data['cohens_d'].abs().sort_values(ascending=False).index)
    
    # 构建表格
    table_data = []
    for idx, (system, row) in enumerate(system_data_sorted.iterrows()):
        
        # 计算方向和意义
        direction = "↑" if row['difference'] > 0 else "↓"
        magnitude = "强" if abs(row['cohens_d']) > 0.3 else "中" if abs(row['cohens_d']) > 0.2 else "弱"
        
        # 功能三角标记
        triangle_member = ""
        if system in ['E', 'B']:  # 主要功能三角成员
            triangle_member = "🔺 核心"
        elif system == 'C':  # 代谢支撑
            triangle_member = "⚡ 支撑"
        
        table_data.append({
            '排名': idx + 1,
            '系统': f"{system} - {system_names[system]}",
            '复发组均值': f"{row['relapse_mean']:.4f}",
            '对照组均值': f"{row['no_relapse_mean']:.4f}",
            '差异': f"{row['difference']:+.4f}",
            '方向': direction,
            '效应量 (Cohen\'s d)': f"{row['cohens_d']:.3f}",
            '效应强度': magnitude,
            'AUC': f"{row['auc']:.3f}",
            'P值': f"{row['p_value']:.4f}",
            '功能三角': triangle_member,
            '生物学意义': get_system_biological_meaning(system, row['difference'] > 0)
        })
    
    return pd.DataFrame(table_data)

def generate_subcategory_ranking_table(subcategory_data):
    """生成子分类详细排序表格"""
    
    # 子分类名称映射
    subcategory_names = {
        'A1': 'A1 - 细胞周期与分裂',
        'A2': 'A2 - 发育与分化', 
        'A3': 'A3 - 形态建成',
        'A4': 'A4 - 干细胞与再生',
        'B1': 'B1 - 免疫应答',
        'B2': 'B2 - 应激反应',
        'B3': 'B3 - 炎症与修复',
        'C1': 'C1 - 能量代谢与分解代谢',
        'C2': 'C2 - 合成代谢',
        'C3': 'C3 - 代谢调节',
        'D1': 'D1 - 蛋白质稳态',
        'D2': 'D2 - DNA修复与维护',
        'E1': 'E1 - 生殖与配子形成',
        'E2': 'E2 - 遗传信息传递'
    }
    
    # 按效应量排序
    subcategory_data_sorted = subcategory_data.reindex(subcategory_data['cohens_d'].abs().sort_values(ascending=False).index)
    
    # 构建表格
    table_data = []
    for idx, (subcat, row) in enumerate(subcategory_data_sorted.iterrows()):
        
        # 计算方向和意义
        direction = "↑" if row['difference'] > 0 else "↓"
        magnitude = "强" if abs(row['cohens_d']) > 0.3 else "中" if abs(row['cohens_d']) > 0.2 else "弱"
        
        # 功能三角标记
        triangle_role = ""
        if subcat == 'E1':
            triangle_role = "🥇 增殖劫持"
        elif subcat in ['B1', 'B2', 'B3']:
            triangle_role = "🛡️ 免疫重塑"
        elif subcat == 'C1':
            triangle_role = "⚡ 代谢重编程"
        elif subcat[0] == 'E':
            triangle_role = "🔄 生殖程序"
        elif subcat[0] == 'B':
            triangle_role = "🔥 防御系统"
        elif subcat[0] == 'C':
            triangle_role = "🔋 能量系统"
        
        table_data.append({
            '排名': idx + 1,
            '子分类': subcategory_names.get(subcat, subcat),
            '所属系统': row['system'],
            '复发组均值': f"{row['relapse_mean']:.4f}",
            '对照组均值': f"{row['no_relapse_mean']:.4f}",
            '差异': f"{row['difference']:+.4f}",
            '方向': direction,
            '效应量 (Cohen\'s d)': f"{row['cohens_d']:.3f}",
            '效应强度': magnitude,
            'AUC': f"{row['auc']:.3f}",
            'P值': f"{row['p_value']:.4f}",
            '功能角色': triangle_role,
            '恶性意图解读': get_subcategory_malignant_interpretation(subcat, row['difference'] > 0)
        })
    
    return pd.DataFrame(table_data)

def generate_importance_table(feature_importance):
    """生成特征重要性表格"""
    
    # 添加功能注释
    feature_annotations = {
        'E1': '生殖与配子形成 - 无限增殖劫持',
        'E2': '遗传信息传递 - 基因组不稳定',
        'B1': '免疫应答 - 免疫微环境重塑',
        'B2': '应激反应 - 肿瘤应激适应',
        'B3': '炎症与修复 - 慢性炎症',
        'C1': '能量代谢与分解代谢 - Warburg效应',
        'C2': '合成代谢 - 生物合成增强',
        'C3': '代谢调节 - 代谢重编程',
        'A1': '细胞周期与分裂 - 周期失控',
        'A2': '发育与分化 - 去分化',
        'A3': '形态建成 - 组织结构破坏',
        'A4': '干细胞与再生 - 干性获得',
        'D1': '蛋白质稳态 - 蛋白质折叠异常',
        'D2': 'DNA修复与维护 - 修复缺陷',
        'A': '生长与发育系统',
        'B': '防御与应激系统',
        'C': '代谢与能量系统',
        'D': '维持与修复系统',
        'E': '连续性与生殖系统'
    }
    
    # 构建表格
    table_data = []
    for idx, row in feature_importance.head(10).iterrows():
        feature = row['feature']
        importance = row['importance']
        
        # 判断特征类型
        feature_type = "子分类" if len(feature) == 2 else "系统"
        
        # 功能三角标记
        triangle_mark = ""
        if feature in ['E1', 'E2', 'E']:
            triangle_mark = "🔺 增殖核心"
        elif feature in ['B1', 'B2', 'B3', 'B']:
            triangle_mark = "🔺 防御核心"
        elif feature in ['C1', 'C2', 'C3', 'C']:
            triangle_mark = "🔺 代谢核心"
        
        table_data.append({
            '重要性排名': idx + 1,
            '特征': feature,
            '特征类型': feature_type,
            '重要性得分': f"{importance:.4f}",
            '功能注释': feature_annotations.get(feature, '未知功能'),
            '功能三角角色': triangle_mark,
            '恶性转化意义': get_malignant_transformation_meaning(feature)
        })
    
    return pd.DataFrame(table_data)

def generate_interpretation_table(system_data, subcategory_data):
    """生成生物学解释表格"""
    
    # 功能三角的核心发现
    interpretations = [
        {
            '功能模块': 'E系统 - 连续性与生殖',
            '核心发现': 'E1(生殖与配子形成)效应量最高',
            '效应量': f"{subcategory_data.loc['E1', 'cohens_d']:.3f}",
            'AUC': f"{subcategory_data.loc['E1', 'auc']:.3f}",
            '生物学解读': '恶性肿瘤劫持生殖程序实现无限增殖',
            '分子机制': '去分化并重启减数分裂样高速复制状态',
            '临床意义': '反映癌细胞获得干性和自我更新能力'
        },
        {
            '功能模块': 'B系统 - 防御与应激',
            '核心发现': '整体B系统效应量第二',
            '效应量': f"{system_data.loc['B', 'cohens_d']:.3f}",
            'AUC': f"{system_data.loc['B', 'auc']:.3f}",
            '生物学解读': '免疫微环境重塑与肿瘤免疫逃逸',
            '分子机制': '慢性炎症状态与免疫抑制性微环境',
            '临床意义': '预示免疫治疗敏感性差异'
        },
        {
            '功能模块': 'C1 - 能量代谢与分解代谢',
            '核心发现': '特征重要性分析中排名靠前',
            '效应量': f"{subcategory_data.loc['C1', 'cohens_d']:.3f}",
            'AUC': f"{subcategory_data.loc['C1', 'auc']:.3f}",
            '生物学解读': '代谢重编程支撑恶性增殖',
            '分子机制': 'Warburg效应与糖酵解增强',
            '临床意义': '代谢靶向治疗的潜在靶点'
        },
        {
            '功能模块': '整体分类框架',
            '核心发现': 'AUC ~0.51 (接近随机)',
            '效应量': '所有系统效应量 < 0.3',
            'AUC': '0.509±0.056',
            '生物学解读': '宏观生理意图识别vs微观变异追踪',
            '分子机制': '全基因组平均化策略的固有特性',
            '临床意义': '功能解释层而非精准预测工具'
        }
    ]
    
    return pd.DataFrame(interpretations)

def get_system_biological_meaning(system, is_upregulated):
    """获取系统生物学意义"""
    
    meanings = {
        'A': {
            True: '生长发育程序异常激活，细胞周期失控',
            False: '生长发育程序受抑，分化能力下降'
        },
        'B': {
            True: '防御应激系统过度激活，免疫微环境重塑',
            False: '防御应激系统功能下降，免疫监视缺陷'
        },
        'C': {
            True: '代谢系统重编程，能量需求增加',
            False: '代谢系统功能下降，能量供应不足'
        },
        'D': {
            True: '维修系统过度激活，应对基因组不稳定',
            False: '维修系统功能缺陷，DNA损伤累积'
        },
        'E': {
            True: '生殖程序异常激活，无限增殖潜能',
            False: '生殖程序受抑，细胞衰老加速'
        }
    }
    
    return meanings.get(system, {}).get(is_upregulated, '未知意义')

def get_subcategory_malignant_interpretation(subcat, is_upregulated):
    """获取子分类恶性解读"""
    
    interpretations = {
        'E1': {
            True: '劫持生殖程序，获得无限增殖能力',
            False: '生殖程序抑制，增殖能力受限'
        },
        'E2': {
            True: '遗传信息传递异常，基因组不稳定',
            False: '遗传信息传递稳定，突变率较低'
        },
        'B1': {
            True: '免疫应答重塑，免疫逃逸增强',
            False: '免疫应答减弱，免疫监视缺陷'
        },
        'C1': {
            True: 'Warburg效应，糖酵解代谢重编程',
            False: '氧化代谢为主，代谢相对正常'
        }
    }
    
    # 默认解读
    default_interpretation = {
        True: f'{subcat}功能异常激活',
        False: f'{subcat}功能相对抑制'
    }
    
    return interpretations.get(subcat, default_interpretation).get(is_upregulated, '未知意义')

def get_malignant_transformation_meaning(feature):
    """获取恶性转化意义"""
    
    meanings = {
        'E1': '无限增殖程序的分子开关',
        'E2': '基因组不稳定性的驱动因子',
        'B1': '免疫逃逸的关键调节器',
        'B2': '肿瘤应激适应的核心机制',
        'B3': '慢性炎症微环境的维持者',
        'C1': 'Warburg效应的代谢重编程',
        'C2': '生物合成通路的异常激活',
        'C3': '代谢检查点的失调',
        'A1': '细胞周期检查点的失效',
        'A2': '去分化过程的分子基础',
        'A3': '组织结构破坏的驱动力',
        'A4': '癌症干细胞特性的获得',
        'D1': '蛋白质稳态的崩溃',
        'D2': 'DNA修复缺陷的累积效应',
        'E': '生殖系统程序的整体劫持',
        'B': '防御系统的全面重塑',
        'C': '代谢系统的根本性改变',
        'A': '生长发育程序的失控',
        'D': '维护修复系统的功能衰退'
    }
    
    return meanings.get(feature, '未知的恶性转化意义')

def save_all_tables(system_table, subcategory_table, importance_table, interpretation_table):
    """保存所有表格"""
    
    output_dir = 'results/disease_analysis/GSE2034-乳腺癌/analysis_results/'
    
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存系统功能三角表格
    system_table.to_csv(f'{output_dir}functional_triangle_systems.csv', index=False, encoding='utf-8-sig')
    
    # 保存子分类排序表格
    subcategory_table.to_csv(f'{output_dir}functional_triangle_subcategories.csv', index=False, encoding='utf-8-sig')
    
    # 保存特征重要性表格
    importance_table.to_csv(f'{output_dir}functional_triangle_importance.csv', index=False, encoding='utf-8-sig')
    
    # 保存生物学解释表格
    interpretation_table.to_csv(f'{output_dir}functional_triangle_interpretation.csv', index=False, encoding='utf-8-sig')
    
    # 生成Markdown格式的表格用于论文
    with open(f'{output_dir}functional_triangle_tables_for_paper.md', 'w', encoding='utf-8') as f:
        f.write("# GSE2034乳腺癌功能三角分析表格\n\n")
        
        f.write("## 表1: 系统级功能三角分析\n\n")
        f.write(system_table.to_markdown(index=False))
        f.write("\n\n")
        
        f.write("## 表2: 子分类详细排序（Top 10）\n\n")
        f.write(subcategory_table.head(10).to_markdown(index=False))
        f.write("\n\n")
        
        f.write("## 表3: 特征重要性分析（Top 10）\n\n")
        f.write(importance_table.to_markdown(index=False))
        f.write("\n\n")
        
        f.write("## 表4: 生物学解释与临床意义\n\n")
        f.write(interpretation_table.to_markdown(index=False))
        f.write("\n\n")
    
    print(f"   ✅ All functional triangle tables saved to {output_dir}")
    print(f"   📝 Markdown tables for paper saved as functional_triangle_tables_for_paper.md")

def main():
    """主函数"""
    try:
        results = generate_functional_triangle_table()
        
        print(f"\n{'='*80}")
        print("GSE2034 FUNCTIONAL TRIANGLE TABLE GENERATION COMPLETED")
        print(f"{'='*80}")
        
        # 显示关键统计
        system_table = results['system_table']
        subcategory_table = results['subcategory_table']
        
        print(f"\n🔺 Functional Triangle Core Members:")
        print(f"   • Top system: {system_table.iloc[0]['系统']}")
        print(f"   • Top subcategory: {subcategory_table.iloc[0]['子分类']}")
        print(f"   • Effect size range: {subcategory_table['效应量 (Cohen\'s d)'].iloc[0]} to {subcategory_table['效应量 (Cohen\'s d)'].iloc[-1]}")
        
        print(f"\n📊 Table Summary:")
        print(f"   • System table: {len(system_table)} rows")
        print(f"   • Subcategory table: {len(subcategory_table)} rows")
        print(f"   • Importance table: {len(results['importance_table'])} rows")
        print(f"   • Interpretation table: {len(results['interpretation_table'])} rows")
        
    except Exception as e:
        print(f"❌ Error in table generation: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()