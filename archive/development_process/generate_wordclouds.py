"""
Figure 1B: 五大系统功能词云图生成器
展示每个系统的核心生物学词汇组成，证明分类的合理性
"""

import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import re
from pathlib import Path

# 设置中文字体支持（如果需要）
plt.rcParams['font.sans-serif'] = ['Arial']
plt.rcParams['axes.unicode_minus'] = False

# 1. 读取数据
print("正在读取分类数据...")
df = pd.read_csv('数据/classified_systems_data_driven_v6.csv')
print(f"✓ 读取 {len(df)} 条记录")

# 2. 定义系统配置
systems_config = {
    "System A: Self-healing": {
        "color": "Reds", 
        "title": "System A: Self-healing\n(Repair & Development)"
    },
    "System B: Immune": {
        "color": "Blues", 
        "title": "System B: Immune\n(Defense & Response)"
    },
    "System C: Energy/Metabolism": {
        "color": "Greens", 
        "title": "System C: Metabolism\n(Energy & Transport)"
    },
    "System D: Regulation (Neuro)": {
        "color": "Purples", 
        "title": "System D: Regulation\n(Neuro & Endocrine)"
    },
    "System E: Reproductive": {
        "color": "Oranges", 
        "title": "System E: Reproductive\n(Propagation & Mating)"
    }
}

# 3. 停用词列表（生物学常见但无意义的词）
stopwords = {
    'process', 'involved', 'regulation', 'positive', 'negative',
    'activity', 'pathway', 'system', 'cellular', 'biological',
    'via', 'related', 'associated', 'mediated', 'dependent',
    'induced', 'specific', 'general', 'other', 'various'
}

# 4. 分词清洗函数
def get_text_corpus(system_name):
    """提取系统下所有条目名称并清洗"""
    # 筛选该系统下的所有条目
    texts = df[df['Primary_System'] == system_name]['Name'].tolist()
    
    # 合并成大字符串
    text_combined = " ".join(texts).lower()
    
    # 清洗：去除非字母字符，保留空格
    text_cleaned = re.sub(r'[^a-z\s]', ' ', text_combined)
    
    # 去除停用词
    words = text_cleaned.split()
    words_filtered = [w for w in words if w not in stopwords and len(w) > 3]
    
    return " ".join(words_filtered)

# 5. 生成词云图
print("\n正在生成词云图...")
output_dir = Path('结果/可视化')
output_dir.mkdir(parents=True, exist_ok=True)

fig = plt.figure(figsize=(20, 12))

for i, (sys_name, config) in enumerate(systems_config.items()):
    print(f"  生成 {config['title'].split()[0]} 词云...")
    
    plt.subplot(2, 3, i+1)
    
    # 获取文本语料
    text = get_text_corpus(sys_name)
    
    if not text.strip():
        print(f"    ⚠️ {sys_name} 无有效文本")
        continue
    
    # 生成词云
    wc = WordCloud(
        width=800, 
        height=400,
        background_color='white',
        colormap=config['color'],
        max_words=80,
        collocations=False,
        relative_scaling=0.5,
        min_font_size=10
    ).generate(text)
    
    # 显示词云
    plt.imshow(wc, interpolation='bilinear')
    plt.axis('off')
    plt.title(config['title'], fontsize=16, fontweight='bold', pad=10)

plt.tight_layout()

# 保存图片
output_file = output_dir / 'Figure_1B_WordClouds.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"\n✓ 已保存: {output_file}")

# 同时保存高分辨率版本
output_file_hires = output_dir / 'Figure_1B_WordClouds_HighRes.png'
plt.savefig(output_file_hires, dpi=600, bbox_inches='tight')
print(f"✓ 已保存高分辨率版本: {output_file_hires}")

plt.show()

print("\n" + "="*80)
print("Figure 1B 生成完成！")
print("="*80)
