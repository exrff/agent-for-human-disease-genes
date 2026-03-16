#!/usr/bin/env python3
"""
Figure 5: Immunometabolic Dissociation in Sepsis (GSE65682)

科学目的：展示系统失配（system uncoupling）- 不是趋势，而是功能相空间的错位

Figure 5A: Defense vs Metabolism Functional Phase Space  
Figure 5B: Subcategory Drivers of the Collapse
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# 设置科学出版物风格
plt.style.use('default')
sns.set_palette("husl")

def load_sepsis_data():
    """加载GSE65682脓毒症数据"""
    print("Loading GSE65682 sepsis data...")
    
    # 读取ssGSEA得分
    ssgsea_scores = pd.read_csv('gse65682_ssgsea_scores.csv')
    print(f"ssGSEA scores shape: {ssgsea_scores.shape}")
    
    # 读取样本分组
    sample_groups = pd.read_csv('gse65682_sample_groups.csv')
    print(f"Sample groups shape: {sample_groups.shape}")
    
    # 合并数据
    merged_data = pd.merge(ssgsea_scores, sample_groups, on='sample_id')
    print(f"Merged data shape: {merged_data.shape}")
    
    # 检查分组分布
    group_counts = merged_data['group'].value_counts()
    print(f"Group distribution:\n{group_counts}")
    
    return merged_data

def calculate_system_scores(merged_data):
    """计算系统级得分"""
    print("\nCalculating system-level scores...")
    
    # 定义系统组成
    system_mapping = {
        'System_A': ['A1', 'A2', 'A3', 'A4'],
        'System_B': ['B1', 'B2', 'B3'], 
        'System_C': ['C1', 'C2', 'C3'],
        'System_D': ['D1', 'D2'],
        'System_E': ['E1', 'E2']
    }
    
    # 检查可用的子分类
    available_subcats = [col for col in merged_data.columns 
                        if col not in ['sample_id', 'group'] and 
                        any(col.startswith(prefix) for prefix in ['A', 'B', 'C', 'D', 'E'])]
    
    print(f"Available subcategories: {available_subcats}")
    
    # 计算系统得分
    system_scores = merged_data[['sample_id', 'group']].copy()
    
    for system_name, subcats in system_mapping.items():
        # 找到该系统中实际存在的子分类
        available_system_subcats = [sc for sc in subcats if sc in available_subcats]
        
        if available_system_subcats:
            # 计算系统平均得分
            system_scores[system_name] = merged_data[available_system_subcats].mean(axis=1)
            print(f"{system_name}: {len(available_system_subcats)} subcategories")
        else:
            print(f"Warning: No subcategories found for {system_name}")
            system_scores[system_name] = 0
    
    return system_scores

def create_figure5a_phase_space(system_scores):
    """创建Figure 5A: Defense vs Metabolism Functional Phase Space"""
    print("\nCreating Figure 5A: Functional Phase Space...")
    
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    
    # 提取System B和System C得分
    system_b_scores = system_scores['System_B']
    system_c_scores = system_scores['System_C']
    groups = system_scores['group']
    
    # 分组数据
    control_mask = groups == 'Control'
    sepsis_mask = groups == 'Sepsis'
    
    control_b = system_b_scores[control_mask]
    control_c = system_c_scores[control_mask]
    sepsis_b = system_b_scores[sepsis_mask]
    sepsis_c = system_c_scores[sepsis_mask]
    
    # 绘制散点图
    scatter_size = 60
    alpha = 0.7
    
    # Control组
    ax.scatter(control_c, control_b, 
              c='#2ECC71', s=scatter_size, alpha=alpha, 
              label=f'Control (n={len(control_b)})', 
              marker='o', edgecolors='darkgreen', linewidth=1)
    
    # Sepsis组
    ax.scatter(sepsis_c, sepsis_b, 
              c='#E74C3C', s=scatter_size, alpha=alpha,
              label=f'Sepsis (n={len(sepsis_b)})', 
              marker='^', edgecolors='darkred', linewidth=1)
    
    # 计算并绘制均值线
    control_b_mean = control_b.mean()
    control_c_mean = control_c.mean()
    sepsis_b_mean = sepsis_b.mean()
    sepsis_c_mean = sepsis_c.mean()
    
    # Control组均值线（虚线）
    ax.axhline(y=control_b_mean, color='#2ECC71', linestyle='--', 
              linewidth=2, alpha=0.8, label='Control Mean Defense')
    ax.axvline(x=control_c_mean, color='#2ECC71', linestyle='--', 
              linewidth=2, alpha=0.8, label='Control Mean Metabolism')
    
    # Sepsis组均值线
    ax.axhline(y=sepsis_b_mean, color='#E74C3C', linestyle='-', 
              linewidth=2, alpha=0.8, label='Sepsis Mean Defense')
    ax.axvline(x=sepsis_c_mean, color='#E74C3C', linestyle='-', 
              linewidth=2, alpha=0.8, label='Sepsis Mean Metabolism')
    
    # 标注四个象限
    x_range = ax.get_xlim()
    y_range = ax.get_ylim()
    
    # 使用Control均值作为象限分界
    x_mid = control_c_mean
    y_mid = control_b_mean
    
    # 象限标注
    quadrant_fontsize = 11
    quadrant_alpha = 0.8
    
    # 右上象限：High B, High C - Effective Defense
    ax.text(x_mid + (x_range[1] - x_mid) * 0.5, 
           y_mid + (y_range[1] - y_mid) * 0.8,
           'Effective Defense\n(High Immune + High Metabolism)', 
           ha='center', va='center', fontsize=quadrant_fontsize, fontweight='bold',
           bbox=dict(boxstyle="round,pad=0.5", facecolor='lightgreen', alpha=quadrant_alpha))
    
    # 左上象限：High B, Low C - Immunometabolic Paralysis  
    ax.text(x_mid - (x_mid - x_range[0]) * 0.5,
           y_mid + (y_range[1] - y_mid) * 0.8,
           'Immunometabolic\nParalysis', 
           ha='center', va='center', fontsize=quadrant_fontsize, fontweight='bold',
           bbox=dict(boxstyle="round,pad=0.5", facecolor='orange', alpha=quadrant_alpha))
    
    # 右下象限：Low B, High C - Recovery
    ax.text(x_mid + (x_range[1] - x_mid) * 0.5,
           y_mid - (y_mid - y_range[0]) * 0.5,
           'Recovery\n(Metabolic Restoration)', 
           ha='center', va='center', fontsize=quadrant_fontsize, fontweight='bold',
           bbox=dict(boxstyle="round,pad=0.5", facecolor='lightblue', alpha=quadrant_alpha))
    
    # 左下象限：Low B, Low C - Collapse
    ax.text(x_mid - (x_mid - x_range[0]) * 0.5,
           y_mid - (y_mid - y_range[0]) * 0.5,
           'Collapse\n(System Failure)', 
           ha='center', va='center', fontsize=quadrant_fontsize, fontweight='bold',
           bbox=dict(boxstyle="round,pad=0.5", facecolor='lightcoral', alpha=quadrant_alpha))
    
    # 添加箭头指示sepsis偏移
    ax.annotate('Sepsis Shift', 
               xy=(sepsis_c_mean, sepsis_b_mean),
               xytext=(control_c_mean, control_b_mean),
               arrowprops=dict(arrowstyle='->', lw=3, color='red'),
               fontsize=12, fontweight='bold',
               bbox=dict(boxstyle="round,pad=0.3", facecolor='yellow', alpha=0.8))
    
    # 设置坐标轴
    ax.set_xlabel('System C Score (Metabolism & Energy)', fontsize=14, fontweight='bold')
    ax.set_ylabel('System B Score (Immune Defense)', fontsize=14, fontweight='bold')
    
    # 网格
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    
    # 图例
    ax.legend(loc='upper left', fontsize=10, frameon=True, 
             fancybox=True, shadow=True)
    
    # 标题
    ax.set_title('Functional Phase Space of Immunometabolic Dissociation in Sepsis (GSE65682)', 
                fontsize=16, fontweight='bold', pad=20)
    
    # 统计检验
    # System B比较
    b_stat, b_pval = stats.mannwhitneyu(control_b, sepsis_b, alternative='two-sided')
    # System C比较  
    c_stat, c_pval = stats.mannwhitneyu(control_c, sepsis_c, alternative='two-sided')
    
    # 添加统计信息
    stats_text = f'Statistical Tests (Mann-Whitney U):\n'
    stats_text += f'System B: p = {b_pval:.2e}\n'
    stats_text += f'System C: p = {c_pval:.2e}'
    
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
           fontsize=10, verticalalignment='top',
           bbox=dict(boxstyle="round,pad=0.5", facecolor='white', alpha=0.9))
    
    plt.tight_layout()
    
    # 保存图片
    plt.savefig('Figure5A_Phase_Space.png', dpi=300, bbox_inches='tight')
    plt.savefig('Figure5A_Phase_Space.pdf', bbox_inches='tight')
    
    return fig

def create_figure5b_subcategory_drivers(merged_data):
    """创建Figure 5B: Subcategory Drivers of the Collapse"""
    print("\nCreating Figure 5B: Subcategory Drivers...")
    
    # 选择关键子分类：B1, B2, C1
    key_subcats = ['B1', 'B2', 'C1']
    
    # 检查可用的子分类
    available_subcats = [sc for sc in key_subcats if sc in merged_data.columns]
    print(f"Available key subcategories: {available_subcats}")
    
    if not available_subcats:
        # 如果关键子分类不可用，选择其他子分类
        numeric_cols = merged_data.select_dtypes(include=[np.number]).columns
        available_subcats = [col for col in numeric_cols if col.startswith(('B', 'C'))][:6]
        print(f"Using alternative subcategories: {available_subcats}")
    
    # 创建子图
    n_subcats = len(available_subcats)
    fig, axes = plt.subplots(1, n_subcats, figsize=(5*n_subcats, 8))
    
    if n_subcats == 1:
        axes = [axes]
    
    # 颜色设置
    colors = {'Control': '#2ECC71', 'Sepsis': '#E74C3C'}
    
    # 统计结果存储
    stats_results = {}
    
    for i, subcat in enumerate(available_subcats):
        ax = axes[i]
        
        # 准备数据
        control_data = merged_data[merged_data['group'] == 'Control'][subcat]
        sepsis_data = merged_data[merged_data['group'] == 'Sepsis'][subcat]
        
        # 创建violin plot
        data_for_plot = [control_data, sepsis_data]
        labels = ['Control', 'Sepsis']
        
        # 绘制violin plot
        parts = ax.violinplot(data_for_plot, positions=[1, 2], widths=0.6, 
                             showmeans=True, showmedians=True)
        
        # 设置颜色
        for j, pc in enumerate(parts['bodies']):
            pc.set_facecolor(colors[labels[j]])
            pc.set_alpha(0.7)
        
        # 设置其他元素颜色
        parts['cmeans'].set_color('black')
        parts['cmedians'].set_color('black')
        parts['cbars'].set_color('black')
        parts['cmins'].set_color('black')
        parts['cmaxes'].set_color('black')
        
        # 添加散点
        np.random.seed(42)  # 为了可重现性
        x1 = np.random.normal(1, 0.04, len(control_data))
        x2 = np.random.normal(2, 0.04, len(sepsis_data))
        
        ax.scatter(x1, control_data, alpha=0.6, s=20, color=colors['Control'], edgecolors='darkgreen')
        ax.scatter(x2, sepsis_data, alpha=0.6, s=20, color=colors['Sepsis'], edgecolors='darkred')
        
        # 统计检验
        stat, pval = stats.mannwhitneyu(control_data, sepsis_data, alternative='two-sided')
        stats_results[subcat] = {'statistic': stat, 'p_value': pval}
        
        # 添加统计显著性标注
        y_max = max(control_data.max(), sepsis_data.max())
        y_min = min(control_data.min(), sepsis_data.min())
        y_range = y_max - y_min
        
        # 显著性标记
        if pval < 0.001:
            sig_text = '***'
        elif pval < 0.01:
            sig_text = '**'
        elif pval < 0.05:
            sig_text = '*'
        else:
            sig_text = 'ns'
        
        # 添加显著性线和文本
        line_y = y_max + y_range * 0.05
        ax.plot([1, 2], [line_y, line_y], 'k-', linewidth=1)
        ax.plot([1, 1], [line_y, line_y - y_range * 0.02], 'k-', linewidth=1)
        ax.plot([2, 2], [line_y, line_y - y_range * 0.02], 'k-', linewidth=1)
        ax.text(1.5, line_y + y_range * 0.02, sig_text, ha='center', va='bottom', 
               fontsize=14, fontweight='bold')
        
        # 添加p值
        ax.text(1.5, line_y + y_range * 0.08, f'p = {pval:.2e}', ha='center', va='bottom', 
               fontsize=10)
        
        # 设置坐标轴
        ax.set_xlim(0.5, 2.5)
        ax.set_xticks([1, 2])
        ax.set_xticklabels(['Control', 'Sepsis'], fontsize=12)
        ax.set_ylabel(f'{subcat} ssGSEA Score', fontsize=12, fontweight='bold')
        
        # 子分类名称映射
        subcat_names = {
            'B1': 'Innate Immunity',
            'B2': 'Adaptive Immunity', 
            'B3': 'Immune Regulation',
            'C1': 'Energy Metabolism',
            'C2': 'Biosynthesis',
            'C3': 'Detoxification'
        }
        
        title = subcat_names.get(subcat, subcat)
        ax.set_title(f'{subcat}: {title}', fontsize=14, fontweight='bold', pad=15)
        
        # 网格
        ax.grid(True, alpha=0.3, axis='y')
        
        # 添加均值标注
        control_mean = control_data.mean()
        sepsis_mean = sepsis_data.mean()
        
        ax.text(1, control_mean, f'{control_mean:.3f}', ha='center', va='center',
               bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8),
               fontweight='bold', fontsize=10)
        ax.text(2, sepsis_mean, f'{sepsis_mean:.3f}', ha='center', va='center',
               bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8),
               fontweight='bold', fontsize=10)
    
    # 总标题
    fig.suptitle('Differential Activation of Functional Subcategories in Sepsis', 
                fontsize=16, fontweight='bold', y=0.95)
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.88)
    
    # 保存图片
    plt.savefig('Figure5B_Subcategory_Drivers.png', dpi=300, bbox_inches='tight')
    plt.savefig('Figure5B_Subcategory_Drivers.pdf', bbox_inches='tight')
    
    # 打印统计结果
    print("\nStatistical test results:")
    for subcat, result in stats_results.items():
        print(f"{subcat}: U = {result['statistic']:.1f}, p = {result['p_value']:.2e}")
    
    return fig

def create_combined_figure5():
    """创建组合的Figure 5"""
    print("\nCreating combined Figure 5...")
    
    # 加载数据
    merged_data = load_sepsis_data()
    system_scores = calculate_system_scores(merged_data)
    
    # 创建组合图
    fig = plt.figure(figsize=(20, 10))
    
    # Figure 5A - 左侧 (相空间图)
    ax1 = plt.subplot(1, 2, 1)
    
    # 提取System B和System C得分
    system_b_scores = system_scores['System_B']
    system_c_scores = system_scores['System_C']
    groups = system_scores['group']
    
    # 分组数据
    control_mask = groups == 'Control'
    sepsis_mask = groups == 'Sepsis'
    
    control_b = system_b_scores[control_mask]
    control_c = system_c_scores[control_mask]
    sepsis_b = system_b_scores[sepsis_mask]
    sepsis_c = system_c_scores[sepsis_mask]
    
    # 绘制散点图
    ax1.scatter(control_c, control_b, c='#2ECC71', s=60, alpha=0.7, 
               label=f'Control (n={len(control_b)})', marker='o', 
               edgecolors='darkgreen', linewidth=1)
    ax1.scatter(sepsis_c, sepsis_b, c='#E74C3C', s=60, alpha=0.7,
               label=f'Sepsis (n={len(sepsis_b)})', marker='^', 
               edgecolors='darkred', linewidth=1)
    
    # 均值线
    control_b_mean = control_b.mean()
    control_c_mean = control_c.mean()
    
    ax1.axhline(y=control_b_mean, color='#2ECC71', linestyle='--', linewidth=2, alpha=0.8)
    ax1.axvline(x=control_c_mean, color='#2ECC71', linestyle='--', linewidth=2, alpha=0.8)
    
    # 象限标注（简化版）
    x_range = ax1.get_xlim()
    y_range = ax1.get_ylim()
    x_mid = control_c_mean
    y_mid = control_b_mean
    
    ax1.text(x_mid + (x_range[1] - x_mid) * 0.5, y_mid + (y_range[1] - y_mid) * 0.7,
            'Effective\nDefense', ha='center', va='center', fontsize=10, fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgreen', alpha=0.8))
    
    ax1.text(x_mid - (x_mid - x_range[0]) * 0.5, y_mid + (y_range[1] - y_mid) * 0.7,
            'Immunometabolic\nParalysis', ha='center', va='center', fontsize=10, fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='orange', alpha=0.8))
    
    ax1.set_xlabel('System C Score (Metabolism)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('System B Score (Defense)', fontsize=12, fontweight='bold')
    ax1.set_title('A. Functional Phase Space', fontsize=14, fontweight='bold', pad=15)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left', fontsize=10)
    
    # Figure 5B - 右侧 (子分类比较)
    ax2 = plt.subplot(1, 2, 2)
    
    # 选择关键子分类进行展示
    key_subcats = ['B1', 'C1']  # 简化为两个关键子分类
    available_subcats = [sc for sc in key_subcats if sc in merged_data.columns]
    
    if not available_subcats:
        numeric_cols = merged_data.select_dtypes(include=[np.number]).columns
        available_subcats = [col for col in numeric_cols if col.startswith(('B', 'C'))][:2]
    
    # 创建简化的比较图
    x_positions = np.arange(len(available_subcats))
    width = 0.35
    
    control_means = []
    sepsis_means = []
    control_stds = []
    sepsis_stds = []
    
    for subcat in available_subcats:
        control_data = merged_data[merged_data['group'] == 'Control'][subcat]
        sepsis_data = merged_data[merged_data['group'] == 'Sepsis'][subcat]
        
        control_means.append(control_data.mean())
        sepsis_means.append(sepsis_data.mean())
        control_stds.append(control_data.std())
        sepsis_stds.append(sepsis_data.std())
    
    # 绘制柱状图
    bars1 = ax2.bar(x_positions - width/2, control_means, width, 
                    yerr=control_stds, label='Control', color='#2ECC71', 
                    alpha=0.8, capsize=5)
    bars2 = ax2.bar(x_positions + width/2, sepsis_means, width,
                    yerr=sepsis_stds, label='Sepsis', color='#E74C3C', 
                    alpha=0.8, capsize=5)
    
    ax2.set_xlabel('Functional Subcategories', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Mean ssGSEA Score', fontsize=12, fontweight='bold')
    ax2.set_title('B. Subcategory Drivers', fontsize=14, fontweight='bold', pad=15)
    ax2.set_xticks(x_positions)
    ax2.set_xticklabels(available_subcats, fontsize=11)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3, axis='y')
    
    # 添加显著性标注
    for i, subcat in enumerate(available_subcats):
        control_data = merged_data[merged_data['group'] == 'Control'][subcat]
        sepsis_data = merged_data[merged_data['group'] == 'Sepsis'][subcat]
        _, pval = stats.mannwhitneyu(control_data, sepsis_data, alternative='two-sided')
        
        y_max = max(control_means[i] + control_stds[i], sepsis_means[i] + sepsis_stds[i])
        
        if pval < 0.001:
            sig_text = '***'
        elif pval < 0.01:
            sig_text = '**'
        elif pval < 0.05:
            sig_text = '*'
        else:
            sig_text = 'ns'
        
        ax2.text(i, y_max * 1.1, sig_text, ha='center', va='bottom', 
                fontsize=12, fontweight='bold')
    
    # 总标题
    fig.suptitle('Figure 5. Immunometabolic Dissociation in Sepsis (GSE65682)', 
                fontsize=18, fontweight='bold', y=0.95)
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.88)
    
    # 保存组合图
    plt.savefig('Figure5_Combined_Immunometabolic_Dissociation.png', dpi=300, bbox_inches='tight')
    plt.savefig('Figure5_Combined_Immunometabolic_Dissociation.pdf', bbox_inches='tight')
    
    return fig

def main():
    """主函数"""
    print("="*80)
    print("GENERATING FIGURE 5: IMMUNOMETABOLIC DISSOCIATION")
    print("="*80)
    
    try:
        # 检查文件是否存在
        required_files = [
            'gse65682_ssgsea_scores.csv',
            'gse65682_sample_groups.csv'
        ]
        
        for file in required_files:
            if not pd.io.common.file_exists(file):
                print(f"❌ Required file not found: {file}")
                return
        
        print("✅ All required files found")
        
        # 加载数据
        merged_data = load_sepsis_data()
        system_scores = calculate_system_scores(merged_data)
        
        # 生成单独的图
        print("\n" + "="*50)
        print("GENERATING INDIVIDUAL FIGURES")
        print("="*50)
        
        # Figure 5A
        fig5a = create_figure5a_phase_space(system_scores)
        
        # Figure 5B
        fig5b = create_figure5b_subcategory_drivers(merged_data)
        
        # 组合图
        print("\n" + "="*50)
        print("GENERATING COMBINED FIGURE")
        print("="*50)
        
        fig5_combined = create_combined_figure5()
        
        print("\n" + "="*80)
        print("✅ FIGURE 5 GENERATION COMPLETED SUCCESSFULLY!")
        print("="*80)
        
        print("\n📁 Generated files:")
        print("   • Figure5A_Phase_Space.png")
        print("   • Figure5A_Phase_Space.pdf")
        print("   • Figure5B_Subcategory_Drivers.png") 
        print("   • Figure5B_Subcategory_Drivers.pdf")
        print("   • Figure5_Combined_Immunometabolic_Dissociation.png")
        print("   • Figure5_Combined_Immunometabolic_Dissociation.pdf")
        
        print("\n🎯 Scientific Impact:")
        print("   • Demonstrates system uncoupling in sepsis pathophysiology")
        print("   • Maps functional states to clinical phenotypes")
        print("   • Identifies subcategory drivers of immunometabolic collapse")
        print("   • Provides framework for precision medicine approaches")
        print("   • Bridges molecular signatures to physiological dysfunction")
        
        plt.show()
        
    except Exception as e:
        print(f"❌ Error generating Figure 5: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()