"""
生成五大系统的统计信息和高频词汇
用于论文 Figure 1 的说明文字
"""

import pandas as pd
from collections import Counter
import re

# 读取数据
df = pd.read_csv('数据/classified_systems_data_driven_v6.csv')

# 停用词
stopwords = {
    'process', 'involved', 'regulation', 'positive', 'negative',
    'activity', 'pathway', 'system', 'cellular', 'biological',
    'via', 'related', 'associated', 'mediated', 'dependent',
    'induced', 'specific', 'general', 'other', 'various'
}

systems = [
    "System A: Self-healing",
    "System B: Immune", 
    "System C: Energy/Metabolism",
    "System D: Regulation (Neuro)",
    "System E: Reproductive"
]

print("="*80)
print("五大功能系统统计分析")
print("="*80)

for sys_name in systems:
    print(f"\n{sys_name}")
    print("-" * 80)
    
    # 筛选该系统的数据
    sys_df = df[df['Primary_System'] == sys_name]
    
    # 统计条目数
    total_entries = len(sys_df)
    go_count = len(sys_df[sys_df['Source'] == 'GO'])
    kegg_count = len(sys_df[sys_df['Source'] == 'KEGG'])
    
    print(f"总条目数: {total_entries:,}")
    print(f"  - GO 条目: {go_count:,} ({go_count/total_entries*100:.1f}%)")
    print(f"  - KEGG 条目: {kegg_count:,} ({kegg_count/total_entries*100:.1f}%)")
    
    # 提取高频词汇
    texts = sys_df['Name'].tolist()
    text_combined = " ".join(texts).lower()
    text_cleaned = re.sub(r'[^a-z\s]', ' ', text_combined)
    
    words = text_cleaned.split()
    words_filtered = [w for w in words if w not in stopwords and len(w) > 3]
    
    # 统计词频
    word_counts = Counter(words_filtered)
    top_words = word_counts.most_common(15)
    
    print(f"\n高频关键词 (Top 15):")
    for i, (word, count) in enumerate(top_words, 1):
        print(f"  {i:2d}. {word:20s} ({count:4d} 次)")

print("\n" + "="*80)
print("系统分布概览")
print("="*80)

# 整体分布
system_counts = df['Primary_System'].value_counts()
print("\n各系统条目数量:")
for sys_name in systems:
    count = system_counts.get(sys_name, 0)
    percentage = count / len(df) * 100
    print(f"  {sys_name:35s}: {count:6,} ({percentage:5.2f}%)")

print(f"\n总计: {len(df):,} 条目")
print("="*80)
