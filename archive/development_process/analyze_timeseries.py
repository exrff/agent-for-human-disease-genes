"""
GSE28914 伤口愈合时间序列分析
专门分析五大系统在伤口愈合过程中的动态变化
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

print("=" * 80)
print("GSE28914 伤口愈合时间序列分析")
print("=" * 80)

# 读取 ssGSEA 结果（使用V7.5最终版本数据）
df = pd.read_csv('结果/ssGSEA结果_V7.5_final/GSE28914_ssgsea_matrix_v7.5_final.csv', index_col=0)

print(f"\n数据维度: {df.shape}")
print(f"系统: {list(df.index)}")
print(f"样本: {list(df.columns)}")

# 根据样本名称提取时间点信息
# 样本格式: "GSM716451" 等
# 需要查看原始数据来确定时间点

# 读取原始 series matrix 来获取样本信息
import gzip

with gzip.open('验证数据集/GSE28914_series_matrix.txt.gz', 'rt', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# 提取样本标题
sample_titles = {}
for line in lines:
    if line.startswith('!Sample_title'):
        parts = line.strip().split('\t')
        for i, title in enumerate(parts[1:], 1):
            title = title.strip('"')
            sample_titles[f'GSM{716450+i}'] = title

print("\n样本信息:")
for sample_id, title in list(sample_titles.items())[:5]:
    print(f"  {sample_id}: {title}")

# 创建时间点分组
time_groups = {
    'Intact': [],
    'Acute': [],
    'Day3': [],
    'Day7': []
}

for sample_id, title in sample_titles.items():
    sample_id_clean = sample_id.strip('"')
    if 'intact' in title.lower():
        time_groups['Intact'].append(sample_id_clean)
    elif 'acute' in title.lower():
        time_groups['Acute'].append(sample_id_clean)
    elif '3rd' in title.lower() or 'day 3' in title.lower():
        time_groups['Day3'].append(sample_id_clean)
    elif '7th' in title.lower() or 'day 7' in title.lower():
        time_groups['Day7'].append(sample_id_clean)

print("\n时间点分组:")
for time_point, samples in time_groups.items():
    print(f"  {time_point}: {len(samples)} 个样本")

# 计算每个时间点的平均得分
time_order = ['Intact', 'Acute', 'Day3', 'Day7']
systems = df.index.tolist()

results = []
for time_point in time_order:
    samples = time_groups[time_point]
    if samples:
        # 清理样本 ID（去除引号）
        available_samples = [s for s in samples if s in df.columns or f'"{s}"' in df.columns]
        if not available_samples:
            # 尝试带引号的版本
            available_samples = [f'"{s}"' for s in samples if f'"{s}"' in df.columns]
        
        if available_samples:
            subset = df[available_samples]
            for system in systems:
                mean_score = subset.loc[system].mean()
                std_score = subset.loc[system].std()
                results.append({
                    'TimePoint': time_point,
                    'System': system,
                    'Mean': mean_score,
                    'Std': std_score,
                    'N': len(available_samples)
                })

df_timeseries = pd.DataFrame(results)

print("\n" + "=" * 80)
print("时间序列分析结果")
print("=" * 80)

# 显示每个系统在不同时间点的得分
for system in systems:
    print(f"\n{system}:")
    system_data = df_timeseries[df_timeseries['System'] == system]
    for _, row in system_data.iterrows():
        print(f"  {row['TimePoint']:10s}: {row['Mean']:8.1f} ± {row['Std']:6.1f} (n={int(row['N'])})")

# 保存结果（保存到V7.5最终版本文件夹）
df_timeseries.to_csv('结果/ssGSEA结果_V7.5_final/GSE28914_timeseries_v7.5_final.csv', index=False)
print("\n✓ 已保存: 结果/ssGSEA结果_V7.5_final/GSE28914_timeseries_v7.5_final.csv")

# 可视化：时间序列折线图
plt.figure(figsize=(12, 8))

colors = {'System A': '#FF6B6B', 'System B': '#4ECDC4', 'System C': '#45B7D1', 
          'System D': '#FFA07A', 'System E': '#98D8C8'}

for system in systems:
    system_data = df_timeseries[df_timeseries['System'] == system].sort_values('TimePoint', 
                                                                                 key=lambda x: x.map({t: i for i, t in enumerate(time_order)}))
    x_pos = [time_order.index(tp) for tp in system_data['TimePoint']]
    plt.plot(x_pos, system_data['Mean'], marker='o', linewidth=2, 
             label=system, color=colors.get(system, 'gray'), markersize=8)
    plt.fill_between(x_pos, 
                     system_data['Mean'] - system_data['Std'], 
                     system_data['Mean'] + system_data['Std'], 
                     alpha=0.2, color=colors.get(system, 'gray'))

plt.xlabel('时间点', fontsize=12, fontweight='bold')
plt.ylabel('ssGSEA 得分', fontsize=12, fontweight='bold')
plt.title('GSE28914: 伤口愈合过程中五大系统的动态变化', fontsize=14, fontweight='bold')
plt.xticks(range(len(time_order)), time_order, fontsize=11)
plt.legend(loc='best', fontsize=10)
plt.grid(True, alpha=0.3)
plt.tight_layout()
# 保存到时序图到V7.5最终版本文件夹
plt.savefig('结果/可视化_V7.5_final/GSE28914_timeseries_v7.5_final.png', dpi=300, bbox_inches='tight')
print("✓ 已保存: 结果/可视化_V7.5_final/GSE28914_timeseries_v7.5_final.png")
plt.close()

# 计算变化趋势
print("\n" + "=" * 80)
print("系统变化趋势分析")
print("=" * 80)

for system in systems:
    system_data = df_timeseries[df_timeseries['System'] == system].sort_values('TimePoint', 
                                                                                 key=lambda x: x.map({t: i for i, t in enumerate(time_order)}))
    if len(system_data) >= 2:
        intact_score = system_data[system_data['TimePoint'] == 'Intact']['Mean'].values[0] if 'Intact' in system_data['TimePoint'].values else None
        day7_score = system_data[system_data['TimePoint'] == 'Day7']['Mean'].values[0] if 'Day7' in system_data['TimePoint'].values else None
        
        if intact_score is not None and day7_score is not None:
            change = day7_score - intact_score
            change_pct = (change / abs(intact_score)) * 100 if intact_score != 0 else 0
            trend = "↑" if change > 0 else "↓"
            print(f"{system}: {intact_score:.1f} → {day7_score:.1f} ({change:+.1f}, {change_pct:+.1f}%) {trend}")

print("\n" + "=" * 80)
print("分析完成！")
print("=" * 80)

print("\n关键发现:")
print("  - 成功提取了伤口愈合的时间序列数据")
print("  - 可以观察五大系统在愈合过程中的动态变化")
print("  - 特别关注 System A (自愈) 和 System B (免疫) 的变化模式")
