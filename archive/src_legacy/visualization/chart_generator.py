"""
可视化图表生成模块

生成五大功能系统分类的各种可视化图表，包括词云图、热图、箱线图、
时间序列图等，用于论文发表和结果展示。

Requirements: 8.3, 8.4, 8.5
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from wordcloud import WordCloud
import re
from collections import Counter
import logging

from ..models.classification_result import ClassificationResult, FunctionalSystem
from ..models.biological_entry import BiologicalEntry


class ChartGenerator:
    """
    图表生成器
    
    提供全面的可视化功能，包括系统分布图、词云图、热图、
    箱线图和时间序列可视化。
    """
    
    def __init__(self, output_dir: str = "results/figures", style: str = "seaborn-v0_8"):
        """
        初始化图表生成器
        
        Args:
            output_dir: 输出目录路径
            style: matplotlib样式
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 设置matplotlib样式
        try:
            plt.style.use(style)
        except:
            plt.style.use('default')
            self.logger.warning(f"Style '{style}' not available, using default")
        
        # 设置中文字体支持
        plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 系统颜色配置
        self.system_colors = {
            'System A': '#FF6B6B',  # 红色系 - 修复重建
            'System B': '#4ECDC4',  # 青色系 - 免疫防御
            'System C': '#45B7D1',  # 蓝色系 - 能量代谢
            'System D': '#96CEB4',  # 绿色系 - 认知调节
            'System E': '#FFEAA7',  # 黄色系 - 生殖延续
            'System 0': '#DDA0DD',  # 紫色系 - 通用机制
            'Unclassified': '#95A5A6'  # 灰色系 - 未分类
        }
        
        # 停用词列表
        self.stopwords = {
            'process', 'involved', 'regulation', 'positive', 'negative',
            'activity', 'pathway', 'system', 'cellular', 'biological',
            'via', 'related', 'associated', 'mediated', 'dependent',
            'induced', 'specific', 'general', 'other', 'various',
            'response', 'signaling', 'protein', 'gene', 'cell'
        }
    
    def generate_system_distribution_pie(self,
                                       results: List[ClassificationResult],
                                       title: str = "五大功能系统分布",
                                       filename: str = "system_distribution_pie.png") -> Path:
        """
        生成系统分布饼图
        
        Args:
            results: 分类结果列表
            title: 图表标题
            filename: 输出文件名
            
        Returns:
            输出文件路径
        """
        # 统计系统分布
        system_counts = Counter()
        for result in results:
            system_letter = result.get_system_letter()
            system_name = f"System {system_letter}"
            system_counts[system_name] += 1
        
        # 准备数据
        labels = list(system_counts.keys())
        sizes = list(system_counts.values())
        colors = [self.system_colors.get(label, '#95A5A6') for label in labels]
        
        # 创建饼图
        fig, ax = plt.subplots(figsize=(10, 8))
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors,
                                         autopct='%1.1f%%', startangle=90,
                                         textprops={'fontsize': 12})
        
        # 设置标题
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        
        # 添加图例
        ax.legend(wedges, [f"{label}\n({count:,} entries)" for label, count in zip(labels, sizes)],
                 title="Systems", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
        
        plt.tight_layout()
        
        # 保存图片
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info(f"Generated pie chart: {output_path}")
        return output_path
    
    def generate_system_bar_chart(self,
                                results: List[ClassificationResult],
                                entries: List[BiologicalEntry],
                                title: str = "系统分布条形图",
                                filename: str = "system_distribution_bar.png") -> Path:
        """
        生成系统分布条形图（按数据源分组）
        
        Args:
            results: 分类结果列表
            entries: 生物学条目列表
            title: 图表标题
            filename: 输出文件名
            
        Returns:
            输出文件路径
        """
        # 创建条目映射
        entry_map = {entry.id: entry for entry in entries}
        
        # 统计数据
        data = []
        for result in results:
            entry = entry_map.get(result.entry_id)
            if entry:
                system_letter = result.get_system_letter()
                data.append({
                    'System': f"System {system_letter}",
                    'Source': entry.source,
                    'Count': 1
                })
        
        # 创建DataFrame
        df = pd.DataFrame(data)
        df_grouped = df.groupby(['System', 'Source']).size().reset_index(name='Count')
        
        # 创建条形图
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # 使用seaborn绘制分组条形图
        sns.barplot(data=df_grouped, x='System', y='Count', hue='Source', ax=ax)
        
        # 设置标题和标签
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Functional Systems', fontsize=14)
        ax.set_ylabel('Number of Entries', fontsize=14)
        
        # 旋转x轴标签
        plt.xticks(rotation=45, ha='right')
        
        # 添加数值标签
        for container in ax.containers:
            ax.bar_label(container, fmt='%d')
        
        plt.tight_layout()
        
        # 保存图片
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info(f"Generated bar chart: {output_path}")
        return output_path
    
    def generate_wordclouds(self,
                          results: List[ClassificationResult],
                          entries: List[BiologicalEntry],
                          title: str = "五大系统功能词云图",
                          filename: str = "system_wordclouds.png") -> Path:
        """
        生成系统词云图
        
        Args:
            results: 分类结果列表
            entries: 生物学条目列表
            title: 图表标题
            filename: 输出文件名
            
        Returns:
            输出文件路径
        """
        # 创建条目映射
        entry_map = {entry.id: entry for entry in entries}
        
        # 按系统分组文本
        system_texts = {}
        for result in results:
            entry = entry_map.get(result.entry_id)
            if entry and not result.is_unclassified():
                system_letter = result.get_system_letter()
                system_name = f"System {system_letter}"
                
                if system_name not in system_texts:
                    system_texts[system_name] = []
                
                # 收集文本
                text = f"{entry.name} {entry.definition}"
                system_texts[system_name].append(text)
        
        # 创建子图
        n_systems = len(system_texts)
        if n_systems == 0:
            self.logger.warning("No classified entries found for wordcloud generation")
            return None
        
        # 计算子图布局
        cols = 3
        rows = (n_systems + cols - 1) // cols
        
        fig, axes = plt.subplots(rows, cols, figsize=(15, 5 * rows))
        if rows == 1:
            axes = [axes] if n_systems == 1 else axes
        else:
            axes = axes.flatten()
        
        # 为每个系统生成词云
        for i, (system_name, texts) in enumerate(system_texts.items()):
            if i >= len(axes):
                break
            
            # 合并文本并清洗
            combined_text = ' '.join(texts).lower()
            cleaned_text = self._clean_text_for_wordcloud(combined_text)
            
            if not cleaned_text.strip():
                axes[i].text(0.5, 0.5, f"No valid text\nfor {system_name}", 
                           ha='center', va='center', transform=axes[i].transAxes)
                axes[i].set_title(system_name, fontsize=14, fontweight='bold')
                axes[i].axis('off')
                continue
            
            # 生成词云
            color_map = self._get_colormap_for_system(system_name)
            wordcloud = WordCloud(
                width=400, height=300,
                background_color='white',
                colormap=color_map,
                max_words=50,
                collocations=False,
                relative_scaling=0.5,
                min_font_size=8
            ).generate(cleaned_text)
            
            # 显示词云
            axes[i].imshow(wordcloud, interpolation='bilinear')
            axes[i].set_title(system_name, fontsize=14, fontweight='bold')
            axes[i].axis('off')
        
        # 隐藏多余的子图
        for i in range(len(system_texts), len(axes)):
            axes[i].axis('off')
        
        plt.suptitle(title, fontsize=18, fontweight='bold', y=0.98)
        plt.tight_layout()
        
        # 保存图片
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info(f"Generated wordclouds: {output_path}")
        return output_path
    
    def generate_confidence_distribution(self,
                                       results: List[ClassificationResult],
                                       title: str = "分类置信度分布",
                                       filename: str = "confidence_distribution.png") -> Path:
        """
        生成置信度分布图
        
        Args:
            results: 分类结果列表
            title: 图表标题
            filename: 输出文件名
            
        Returns:
            输出文件路径
        """
        # 准备数据
        data = []
        for result in results:
            system_letter = result.get_system_letter()
            data.append({
                'System': f"System {system_letter}",
                'Confidence': result.confidence_score
            })
        
        df = pd.DataFrame(data)
        
        # 创建箱线图
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 箱线图
        sns.boxplot(data=df, x='System', y='Confidence', ax=ax1)
        ax1.set_title('置信度箱线图', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Functional Systems', fontsize=12)
        ax1.set_ylabel('Confidence Score', fontsize=12)
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # 直方图
        ax2.hist(df['Confidence'], bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        ax2.set_title('整体置信度分布', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Confidence Score', fontsize=12)
        ax2.set_ylabel('Frequency', fontsize=12)
        ax2.axvline(df['Confidence'].mean(), color='red', linestyle='--', 
                   label=f'Mean: {df["Confidence"].mean():.3f}')
        ax2.legend()
        
        plt.suptitle(title, fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        # 保存图片
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info(f"Generated confidence distribution: {output_path}")
        return output_path
    
    def generate_heatmap(self,
                        data: pd.DataFrame,
                        title: str = "系统活性热图",
                        filename: str = "system_heatmap.png",
                        figsize: Tuple[int, int] = (12, 8)) -> Path:
        """
        生成热图
        
        Args:
            data: 数据矩阵 (行为系统，列为样本)
            title: 图表标题
            filename: 输出文件名
            figsize: 图片大小
            
        Returns:
            输出文件路径
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        # 生成热图
        sns.heatmap(data, annot=False, cmap='RdBu_r', center=0,
                   linewidths=0.5, cbar_kws={'label': 'Z-Score'}, ax=ax)
        
        # 设置标题和标签
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Samples', fontsize=14)
        ax.set_ylabel('Functional Systems', fontsize=14)
        
        plt.tight_layout()
        
        # 保存图片
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info(f"Generated heatmap: {output_path}")
        return output_path
    
    def generate_time_series_plot(self,
                                data: pd.DataFrame,
                                time_column: str = 'Time',
                                value_column: str = 'Score',
                                group_column: str = 'System',
                                title: str = "系统得分时间序列",
                                filename: str = "time_series.png") -> Path:
        """
        生成时间序列图
        
        Args:
            data: 时间序列数据
            time_column: 时间列名
            value_column: 数值列名
            group_column: 分组列名
            title: 图表标题
            filename: 输出文件名
            
        Returns:
            输出文件路径
        """
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # 为每个系统绘制时间序列
        systems = data[group_column].unique()
        for system in systems:
            system_data = data[data[group_column] == system]
            color = self.system_colors.get(system, '#95A5A6')
            
            ax.plot(system_data[time_column], system_data[value_column],
                   marker='o', linewidth=2, label=system, color=color)
        
        # 设置标题和标签
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Time Points', fontsize=14)
        ax.set_ylabel('System Score', fontsize=14)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 保存图片
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info(f"Generated time series plot: {output_path}")
        return output_path
    
    def generate_comparison_boxplot(self,
                                  data: pd.DataFrame,
                                  x_column: str,
                                  y_column: str,
                                  hue_column: Optional[str] = None,
                                  title: str = "系统得分对比",
                                  filename: str = "comparison_boxplot.png") -> Path:
        """
        生成对比箱线图
        
        Args:
            data: 对比数据
            x_column: x轴列名
            y_column: y轴列名
            hue_column: 分组列名
            title: 图表标题
            filename: 输出文件名
            
        Returns:
            输出文件路径
        """
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # 生成箱线图
        sns.boxplot(data=data, x=x_column, y=y_column, hue=hue_column, ax=ax)
        
        # 设置标题和标签
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel(x_column, fontsize=14)
        ax.set_ylabel(y_column, fontsize=14)
        
        # 旋转x轴标签
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        
        # 保存图片
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info(f"Generated comparison boxplot: {output_path}")
        return output_path
    
    def generate_comprehensive_dashboard(self,
                                       results: List[ClassificationResult],
                                       entries: List[BiologicalEntry],
                                       title: str = "五大功能系统分类仪表板",
                                       filename: str = "classification_dashboard.png") -> Path:
        """
        生成综合仪表板
        
        Args:
            results: 分类结果列表
            entries: 生物学条目列表
            title: 图表标题
            filename: 输出文件名
            
        Returns:
            输出文件路径
        """
        # 创建大图
        fig = plt.figure(figsize=(20, 12))
        
        # 子图1: 系统分布饼图
        ax1 = plt.subplot(2, 3, 1)
        system_counts = Counter(result.get_system_letter() for result in results)
        labels = [f"System {k}" for k in system_counts.keys()]
        sizes = list(system_counts.values())
        colors = [self.system_colors.get(label, '#95A5A6') for label in labels]
        ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        ax1.set_title('系统分布', fontsize=14, fontweight='bold')
        
        # 子图2: 数据源分布
        ax2 = plt.subplot(2, 3, 2)
        entry_map = {entry.id: entry for entry in entries}
        source_data = []
        for result in results:
            entry = entry_map.get(result.entry_id)
            if entry:
                source_data.append({
                    'System': f"System {result.get_system_letter()}",
                    'Source': entry.source
                })
        
        df_source = pd.DataFrame(source_data)
        df_source_grouped = df_source.groupby(['System', 'Source']).size().reset_index(name='Count')
        sns.barplot(data=df_source_grouped, x='System', y='Count', hue='Source', ax=ax2)
        ax2.set_title('数据源分布', fontsize=14, fontweight='bold')
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # 子图3: 置信度分布
        ax3 = plt.subplot(2, 3, 3)
        confidence_scores = [result.confidence_score for result in results]
        ax3.hist(confidence_scores, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        ax3.axvline(np.mean(confidence_scores), color='red', linestyle='--', 
                   label=f'Mean: {np.mean(confidence_scores):.3f}')
        ax3.set_title('置信度分布', fontsize=14, fontweight='bold')
        ax3.set_xlabel('Confidence Score')
        ax3.set_ylabel('Frequency')
        ax3.legend()
        
        # 子图4: 子系统分布
        ax4 = plt.subplot(2, 3, 4)
        subsystem_counts = Counter()
        for result in results:
            if result.subsystem:
                subsystem_counts[result.subsystem] += 1
        
        if subsystem_counts:
            subsystems = list(subsystem_counts.keys())[:10]  # 显示前10个
            counts = [subsystem_counts[s] for s in subsystems]
            ax4.barh(subsystems, counts)
            ax4.set_title('子系统分布 (Top 10)', fontsize=14, fontweight='bold')
            ax4.set_xlabel('Count')
        else:
            ax4.text(0.5, 0.5, 'No subsystem data', ha='center', va='center', 
                    transform=ax4.transAxes)
            ax4.set_title('子系统分布', fontsize=14, fontweight='bold')
        
        # 子图5: 炎症极性分布
        ax5 = plt.subplot(2, 3, 5)
        inflammation_counts = Counter()
        for result in results:
            if result.inflammation_polarity:
                inflammation_counts[result.inflammation_polarity] += 1
        
        if inflammation_counts:
            polarities = list(inflammation_counts.keys())
            counts = list(inflammation_counts.values())
            ax5.pie(counts, labels=polarities, autopct='%1.1f%%', startangle=90)
            ax5.set_title('炎症极性分布', fontsize=14, fontweight='bold')
        else:
            ax5.text(0.5, 0.5, 'No inflammation data', ha='center', va='center',
                    transform=ax5.transAxes)
            ax5.set_title('炎症极性分布', fontsize=14, fontweight='bold')
        
        # 子图6: 分类质量指标
        ax6 = plt.subplot(2, 3, 6)
        classified_count = len([r for r in results if not r.is_unclassified()])
        classification_rate = (classified_count / len(results)) * 100
        avg_confidence = np.mean(confidence_scores)
        
        metrics = ['Classification\nRate (%)', 'Average\nConfidence', 'Total\nEntries (k)']
        values = [classification_rate, avg_confidence * 100, len(results) / 1000]
        
        bars = ax6.bar(metrics, values, color=['#FF6B6B', '#4ECDC4', '#45B7D1'])
        ax6.set_title('分类质量指标', fontsize=14, fontweight='bold')
        
        # 添加数值标签
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax6.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                    f'{value:.1f}', ha='center', va='bottom')
        
        plt.suptitle(title, fontsize=18, fontweight='bold', y=0.98)
        plt.tight_layout()
        
        # 保存图片
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info(f"Generated comprehensive dashboard: {output_path}")
        return output_path
    
    def _clean_text_for_wordcloud(self, text: str) -> str:
        """清洗文本用于词云生成"""
        # 转换为小写
        text = text.lower()
        
        # 去除非字母字符，保留空格
        text = re.sub(r'[^a-z\s]', ' ', text)
        
        # 分词并过滤
        words = text.split()
        filtered_words = [w for w in words if w not in self.stopwords and len(w) > 3]
        
        return ' '.join(filtered_words)
    
    def _get_colormap_for_system(self, system_name: str) -> str:
        """为系统获取对应的颜色映射"""
        color_maps = {
            'System A': 'Reds',
            'System B': 'Blues', 
            'System C': 'Greens',
            'System D': 'Purples',
            'System E': 'Oranges',
            'System 0': 'Greys'
        }
        return color_maps.get(system_name, 'viridis')