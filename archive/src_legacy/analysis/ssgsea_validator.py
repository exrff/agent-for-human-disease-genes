"""
ssGSEA验证模块

实现基于ssGSEA的五大功能系统分类验证，包括：
1. ssGSEA计算引擎
2. 验证数据集处理
3. 时间序列分析
4. 疾病对比分析

作者: AI Assistant
日期: 2025-12-24
"""

import pandas as pd
import numpy as np
import gzip
import json
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
import logging

import gseapy as gp
from scipy import stats
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns

from ..config.settings import get_settings
from ..models.validation_result import ValidationResult

warnings.filterwarnings('ignore')

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TimeSeriesResult:
    """时间序列分析结果"""
    dataset_name: str
    system_scores: pd.DataFrame  # time_point × system
    time_points: List[str]
    statistics: Dict[str, Any]
    trends: Dict[str, str]  # system → trend (increasing/decreasing/stable)
    correlations: Dict[str, float]  # system → correlation with time
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'dataset_name': self.dataset_name,
            'system_scores': self.system_scores.to_dict(),
            'time_points': self.time_points,
            'statistics': self.statistics,
            'trends': self.trends,
            'correlations': self.correlations
        }


@dataclass
class ComparisonResult:
    """疾病对比分析结果"""
    dataset_name: str
    disease_scores: pd.DataFrame  # sample × system
    control_scores: pd.DataFrame  # sample × system
    fold_changes: Dict[str, float]  # system → log2(disease/control)
    p_values: Dict[str, float]  # system → p_value
    effect_sizes: Dict[str, float]  # system → Cohen's d
    significant_systems: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'dataset_name': self.dataset_name,
            'disease_scores': self.disease_scores.to_dict(),
            'control_scores': self.control_scores.to_dict(),
            'fold_changes': self.fold_changes,
            'p_values': self.p_values,
            'effect_sizes': self.effect_sizes,
            'significant_systems': self.significant_systems
        }


class ssGSEAValidator:
    """
    ssGSEA验证器
    
    实现基于ssGSEA的五大功能系统分类验证。
    """
    
    def __init__(self, settings=None):
        """
        初始化ssGSEA验证器
        
        Args:
            settings: 系统设置，如果为None则使用默认设置
        """
        self.settings = settings or get_settings()
        self.gene_sets = {}
        self.expression_cache = {}
        self.annotation_cache = {}
        
        logger.info("ssGSEA验证器初始化完成")
    
    def load_system_gene_sets(self, gene_sets_path: Optional[str] = None) -> Dict[str, List[str]]:
        """
        加载五大系统基因集
        
        Args:
            gene_sets_path: 基因集文件路径，如果为None则使用默认路径
            
        Returns:
            Dict[str, List[str]]: 系统名称到基因列表的映射
        """
        if gene_sets_path is None:
            gene_sets_path = self.settings.data_dir / "gene_sets" / "system_gene_sets_v7.5_final.json"
        
        logger.info(f"加载系统基因集: {gene_sets_path}")
        
        try:
            with open(gene_sets_path, 'r', encoding='utf-8') as f:
                gene_sets = json.load(f)
            
            # 验证基因集格式
            for system, genes in gene_sets.items():
                if not isinstance(genes, list):
                    raise ValueError(f"系统 {system} 的基因集必须是列表格式")
                if len(genes) < self.settings.ssgsea_min_gene_set_size:
                    logger.warning(f"系统 {system} 的基因数量 ({len(genes)}) 小于最小阈值 ({self.settings.ssgsea_min_gene_set_size})")
            
            self.gene_sets = gene_sets
            logger.info(f"成功加载 {len(gene_sets)} 个系统的基因集")
            
            # 打印基因集统计信息
            for system, genes in gene_sets.items():
                logger.info(f"  {system}: {len(genes)} 个基因")
            
            return gene_sets
            
        except Exception as e:
            logger.error(f"加载基因集失败: {e}")
            raise
    
    def load_series_matrix(self, filepath: Union[str, Path]) -> pd.DataFrame:
        """
        解析GEO series_matrix文件为表达矩阵
        
        Args:
            filepath: series_matrix文件路径 (.txt.gz)
            
        Returns:
            pd.DataFrame: 表达矩阵 (probe × sample)
        """
        filepath = Path(filepath)
        logger.info(f"解析series_matrix文件: {filepath}")
        
        # 检查缓存
        cache_key = str(filepath)
        if cache_key in self.expression_cache:
            logger.info("使用缓存的表达矩阵")
            return self.expression_cache[cache_key]
        
        try:
            # 读取文件（自动处理.gz压缩）
            if filepath.suffix == '.gz':
                with gzip.open(filepath, 'rt', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
            else:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
            
            logger.info(f"读取了 {len(lines)} 行")
            
            # 跳过所有以!开头的注释行，找到数据起始位置
            data_start_idx = None
            for i, line in enumerate(lines):
                if not line.startswith('!'):
                    data_start_idx = i
                    break
            
            if data_start_idx is None:
                raise ValueError("未找到数据起始行（所有行都是注释）")
            
            logger.info(f"数据起始行: {data_start_idx + 1}")
            
            # 提取数据部分
            data_lines = lines[data_start_idx:]
            
            # 找到列名行
            header_line = None
            header_idx = 0
            for i, line in enumerate(data_lines):
                if line.strip() and not line.startswith('!'):
                    header_line = line.strip().split('\t')
                    header_idx = i
                    break
            
            if header_line is None:
                raise ValueError("未找到列名行")
            
            # 清洗列名：删除引号和可能的前缀
            clean_headers = []
            for h in header_line:
                h = h.strip('"').strip()
                # 删除常见的前缀（如"X", "x"）
                if h.startswith('X') and len(h) > 1 and h[1:].startswith('GSM'):
                    h = h[1:]
                elif h.startswith('x') and len(h) > 1 and h[1:].startswith('GSM'):
                    h = h[1:]
                clean_headers.append(h)
            
            logger.info(f"列数: {len(clean_headers)}")
            
            # 解析数据行
            data_rows = []
            for line in data_lines[header_idx + 1:]:
                if line.strip():  # 跳过空行
                    parts = line.strip().split('\t')
                    # 清洗每个值（删除引号）
                    clean_parts = [p.strip('"').strip() for p in parts]
                    # 确保列数匹配
                    if len(clean_parts) == len(clean_headers):
                        data_rows.append(clean_parts)
            
            logger.info(f"数据行数: {len(data_rows)}")
            
            # 创建DataFrame
            df = pd.DataFrame(data_rows, columns=clean_headers)
            
            # 第一列是probe ID，设为索引
            df = df.set_index(df.columns[0])
            df.index.name = 'probe_id'
            
            # 将表达值转换为数值类型
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            logger.info(f"表达矩阵: {df.shape}")
            logger.info(f"Probe数: {len(df)}, 样本数: {len(df.columns)}")
            logger.info(f"缺失值: {df.isnull().sum().sum()}")
            
            # 缓存结果
            self.expression_cache[cache_key] = df
            
            return df
            
        except Exception as e:
            logger.error(f"解析series_matrix文件失败: {e}")
            raise
    
    def load_gpl_annotation(self, gpl_filepath: Union[str, Path], 
                           probe_col_candidates: Optional[List[str]] = None,
                           gene_col_candidates: Optional[List[str]] = None) -> pd.DataFrame:
        """
        解析GPL平台注释文件，提取probe → gene映射
        
        Args:
            gpl_filepath: GPL注释文件路径
            probe_col_candidates: probe ID列名候选（自动检测）
            gene_col_candidates: gene symbol列名候选（自动检测）
            
        Returns:
            pd.DataFrame: 包含probe_id和gene_symbol的映射表
        """
        gpl_filepath = Path(gpl_filepath)
        logger.info(f"解析GPL平台注释: {gpl_filepath}")
        
        # 检查缓存
        cache_key = str(gpl_filepath)
        if cache_key in self.annotation_cache:
            logger.info("使用缓存的注释映射")
            return self.annotation_cache[cache_key]
        
        # 默认候选列名
        if probe_col_candidates is None:
            probe_col_candidates = ['ID', 'Probe_ID', 'ProbeID', 'PROBE_ID', 'probe_id']
        
        if gene_col_candidates is None:
            gene_col_candidates = [
                'Gene Symbol', 'GENE_SYMBOL', 'Gene_Symbol', 'Symbol', 
                'SYMBOL', 'gene_symbol', 'Gene', 'GENE', 'gene'
            ]
        
        try:
            # 读取文件（跳过注释行）
            with open(gpl_filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # 找到数据起始行（跳过#或!开头的注释）
            data_start_idx = None
            for i, line in enumerate(lines):
                if not line.startswith('#') and not line.startswith('!'):
                    data_start_idx = i
                    break
            
            if data_start_idx is None:
                raise ValueError("未找到数据起始行")
            
            logger.info(f"数据起始行: {data_start_idx + 1}")
            
            # 读取为DataFrame
            df = pd.read_csv(
                gpl_filepath, 
                sep='\t', 
                skiprows=data_start_idx,
                low_memory=False
            )
            
            logger.info(f"原始行数: {len(df)}, 列数: {len(df.columns)}")
            
            # 自动识别probe ID列
            probe_col = None
            for candidate in probe_col_candidates:
                if candidate in df.columns:
                    probe_col = candidate
                    break
            
            if probe_col is None:
                # 如果没找到，使用第一列
                probe_col = df.columns[0]
                logger.warning(f"未找到标准probe ID列，使用第一列: {probe_col}")
            else:
                logger.info(f"Probe ID列: {probe_col}")
            
            # 自动识别gene symbol列
            gene_col = None
            for candidate in gene_col_candidates:
                if candidate in df.columns:
                    gene_col = candidate
                    break
            
            if gene_col is None:
                raise ValueError(f"未找到gene symbol列，可用列: {list(df.columns)}")
            
            logger.info(f"Gene Symbol列: {gene_col}")
            
            # 提取映射关系
            mapping = df[[probe_col, gene_col]].copy()
            mapping.columns = ['probe_id', 'gene_symbol']
            
            # 清洗gene symbol
            # 1. 删除空值
            mapping = mapping.dropna(subset=['gene_symbol'])
            
            # 2. 删除空字符串和"---"
            mapping = mapping[mapping['gene_symbol'].str.strip() != '']
            mapping = mapping[mapping['gene_symbol'].str.strip() != '---']
            
            # 3. 处理多个基因符号（用///或//分隔）
            # 策略：只保留第一个基因符号
            mapping['gene_symbol'] = mapping['gene_symbol'].str.split('///').str[0]
            mapping['gene_symbol'] = mapping['gene_symbol'].str.split('//').str[0]
            mapping['gene_symbol'] = mapping['gene_symbol'].str.strip()
            
            logger.info(f"映射关系: 有效映射数={len(mapping)}, 唯一probe数={mapping['probe_id'].nunique()}, 唯一gene数={mapping['gene_symbol'].nunique()}")
            
            # 缓存结果
            self.annotation_cache[cache_key] = mapping
            
            return mapping
            
        except Exception as e:
            logger.error(f"解析GPL注释文件失败: {e}")
            raise
    
    def map_probe_to_gene(self, expr_df: pd.DataFrame, mapping_df: pd.DataFrame, 
                         method: str = 'mean') -> pd.DataFrame:
        """
        将probe表达矩阵映射为gene表达矩阵
        
        Args:
            expr_df: probe × sample表达矩阵
            mapping_df: probe → gene映射表
            method: 多个probe映射到同一基因时的聚合方法
                   'mean' (默认): 取平均值
                   'max': 取最大值
                   'median': 取中位数
                   
        Returns:
            pd.DataFrame: gene × sample表达矩阵
        """
        logger.info(f"Probe → Gene映射，聚合方法: {method}")
        
        # 合并表达数据和映射关系
        expr_df_reset = expr_df.reset_index()
        merged = expr_df_reset.merge(
            mapping_df, 
            left_on='probe_id', 
            right_on='probe_id', 
            how='inner'
        )
        
        logger.info(f"合并后保留的probe数: {len(merged)}")
        logger.info(f"丢弃的probe数: {len(expr_df) - len(merged)}")
        
        # 删除probe_id列，只保留gene_symbol和表达值
        merged = merged.drop('probe_id', axis=1)
        
        # 按gene_symbol分组聚合
        if method == 'mean':
            gene_expr = merged.groupby('gene_symbol').mean()
        elif method == 'max':
            gene_expr = merged.groupby('gene_symbol').max()
        elif method == 'median':
            gene_expr = merged.groupby('gene_symbol').median()
        else:
            raise ValueError(f"不支持的聚合方法: {method}")
        
        logger.info(f"Gene表达矩阵: {gene_expr.shape}")
        logger.info(f"基因数: {len(gene_expr)}, 样本数: {len(gene_expr.columns)}")
        
        # 统计多个probe映射到同一基因的情况
        probe_per_gene = merged.groupby('gene_symbol').size()
        multi_probe_genes = probe_per_gene[probe_per_gene > 1]
        logger.info(f"多probe基因数: {len(multi_probe_genes)}")
        if len(multi_probe_genes) > 0:
            logger.info(f"最多probe数: {multi_probe_genes.max()}")
        
        return gene_expr
    
    def compute_system_scores(self, gene_expr_df: pd.DataFrame, 
                            gene_sets: Optional[Dict[str, List[str]]] = None) -> pd.DataFrame:
        """
        计算五大系统的ssGSEA得分
        
        Args:
            gene_expr_df: gene × sample表达矩阵
            gene_sets: 系统基因集，如果为None则使用已加载的基因集
            
        Returns:
            pd.DataFrame: system × sample ssGSEA得分矩阵
        """
        if gene_sets is None:
            if not self.gene_sets:
                raise ValueError("未加载基因集，请先调用load_system_gene_sets()或提供gene_sets参数")
            gene_sets = self.gene_sets
        
        logger.info(f"计算ssGSEA得分")
        logger.info(f"输入矩阵: {gene_expr_df.shape}")
        logger.info(f"基因集数: {len(gene_sets)}")
        
        try:
            # 运行ssGSEA
            logger.info("开始计算ssGSEA...")
            
            ss = gp.ssgsea(
                data=gene_expr_df,
                gene_sets=gene_sets,
                outdir=None,  # 不保存中间文件
                sample_norm_method='rank',  # 标准化方法
                no_plot=True,  # 不生成图表
                threads=4,  # 并行线程数（替代processes）
                min_size=self.settings.ssgsea_min_gene_set_size,  # 最小基因集大小
                max_size=self.settings.ssgsea_max_gene_set_size,  # 最大基因集大小
                permutation_num=0  # ssGSEA不需要permutation
            )
            
            # 提取结果
            res_df = ss.res2d
            logger.info(f"原始结果: {res_df.shape}")
            
            # 转换为system × sample矩阵
            # 使用pivot将长格式转换为宽格式
            ssgsea_scores = res_df.pivot(index='Term', columns='Name', values='NES')
            
            logger.info(f"ssGSEA计算完成: {ssgsea_scores.shape}")
            logger.info(f"系统数: {len(ssgsea_scores)}, 样本数: {len(ssgsea_scores.columns)}")
            
            # 验证得分范围
            min_score = ssgsea_scores.min().min()
            max_score = ssgsea_scores.max().max()
            logger.info(f"得分范围: [{min_score:.3f}, {max_score:.3f}]")
            
            return ssgsea_scores
            
        except Exception as e:
            logger.error(f"ssGSEA计算失败: {e}")
            raise
    
    def process_validation_dataset(self, dataset_name: str, 
                                 series_matrix_path: Union[str, Path],
                                 gpl_path: Union[str, Path],
                                 output_dir: Optional[Union[str, Path]] = None) -> pd.DataFrame:
        """
        处理验证数据集的完整流程
        
        Args:
            dataset_name: 数据集名称
            series_matrix_path: series_matrix文件路径
            gpl_path: GPL注释文件路径
            output_dir: 输出目录，如果为None则不保存中间文件
            
        Returns:
            pd.DataFrame: system × sample ssGSEA得分矩阵
        """
        logger.info(f"处理验证数据集: {dataset_name}")
        
        # 创建输出目录
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Step 1: 加载表达矩阵
            expr_df = self.load_series_matrix(series_matrix_path)
            
            # Step 2: 加载GPL注释并映射
            mapping_df = self.load_gpl_annotation(gpl_path)
            
            # 映射probe → gene
            gene_expr_df = self.map_probe_to_gene(expr_df, mapping_df, method='mean')
            
            # Step 3: 计算ssGSEA
            ssgsea_scores = self.compute_system_scores(gene_expr_df)
            
            # 保存结果
            if output_dir:
                # 保存probe表达矩阵
                probe_expr_path = output_dir / 'probe_expression.csv'
                expr_df.to_csv(probe_expr_path, encoding='utf-8-sig')
                logger.info(f"Probe表达矩阵已保存: {probe_expr_path}")
                
                # 保存gene表达矩阵
                gene_expr_path = output_dir / 'gene_expression.csv'
                gene_expr_df.to_csv(gene_expr_path, encoding='utf-8-sig')
                logger.info(f"Gene表达矩阵已保存: {gene_expr_path}")
                
                # 保存ssGSEA得分
                ssgsea_path = output_dir / 'ssgsea_scores.csv'
                ssgsea_scores.to_csv(ssgsea_path, encoding='utf-8-sig')
                logger.info(f"ssGSEA得分已保存: {ssgsea_path}")
            
            logger.info(f"{dataset_name} 处理完成")
            return ssgsea_scores
            
        except Exception as e:
            logger.error(f"{dataset_name} 处理失败: {e}")
            raise
    
    def analyze_time_series(self, ssgsea_scores: pd.DataFrame, 
                           time_points: List[str],
                           dataset_name: str = "Unknown") -> TimeSeriesResult:
        """
        分析时间序列数据的系统得分变化
        
        Args:
            ssgsea_scores: system × sample ssGSEA得分矩阵
            time_points: 时间点列表，与样本顺序对应
            dataset_name: 数据集名称
            
        Returns:
            TimeSeriesResult: 时间序列分析结果
        """
        logger.info(f"分析时间序列数据: {dataset_name}")
        
        if len(time_points) != len(ssgsea_scores.columns):
            raise ValueError(f"时间点数量 ({len(time_points)}) 与样本数量 ({len(ssgsea_scores.columns)}) 不匹配")
        
        # 转置矩阵：sample × system
        scores_df = ssgsea_scores.T
        scores_df.index = time_points
        
        # 按时间点分组计算平均得分
        time_scores = scores_df.groupby(scores_df.index).mean()
        
        # 计算趋势和相关性
        trends = {}
        correlations = {}
        statistics = {}
        
        # 为时间点创建数值编码
        unique_times = sorted(time_scores.index)
        time_numeric = list(range(len(unique_times)))
        
        for system in time_scores.columns:
            system_values = [time_scores.loc[t, system] for t in unique_times]
            
            # 计算与时间的相关性
            correlation, p_value = stats.pearsonr(time_numeric, system_values)
            correlations[system] = correlation
            
            # 判断趋势
            if correlation > 0.3 and p_value < 0.05:
                trends[system] = "increasing"
            elif correlation < -0.3 and p_value < 0.05:
                trends[system] = "decreasing"
            else:
                trends[system] = "stable"
            
            # 计算统计信息
            statistics[f"{system}_correlation"] = correlation
            statistics[f"{system}_p_value"] = p_value
            statistics[f"{system}_mean"] = np.mean(system_values)
            statistics[f"{system}_std"] = np.std(system_values)
            statistics[f"{system}_range"] = max(system_values) - min(system_values)
        
        logger.info(f"时间序列分析完成，检测到趋势: {trends}")
        
        return TimeSeriesResult(
            dataset_name=dataset_name,
            system_scores=time_scores,
            time_points=unique_times,
            statistics=statistics,
            trends=trends,
            correlations=correlations
        )
    
    def compare_disease_control(self, ssgsea_scores: pd.DataFrame,
                              disease_samples: List[str],
                              control_samples: List[str],
                              dataset_name: str = "Unknown") -> ComparisonResult:
        """
        比较疾病组与对照组的系统得分差异
        
        Args:
            ssgsea_scores: system × sample ssGSEA得分矩阵
            disease_samples: 疾病组样本名称列表
            control_samples: 对照组样本名称列表
            dataset_name: 数据集名称
            
        Returns:
            ComparisonResult: 疾病对比分析结果
        """
        logger.info(f"疾病对比分析: {dataset_name}")
        logger.info(f"疾病组样本数: {len(disease_samples)}, 对照组样本数: {len(control_samples)}")
        
        # 检查样本是否存在
        missing_disease = [s for s in disease_samples if s not in ssgsea_scores.columns]
        missing_control = [s for s in control_samples if s not in ssgsea_scores.columns]
        
        if missing_disease:
            logger.warning(f"缺失疾病组样本: {missing_disease}")
        if missing_control:
            logger.warning(f"缺失对照组样本: {missing_control}")
        
        # 过滤存在的样本
        disease_samples = [s for s in disease_samples if s in ssgsea_scores.columns]
        control_samples = [s for s in control_samples if s in ssgsea_scores.columns]
        
        if len(disease_samples) == 0 or len(control_samples) == 0:
            raise ValueError("疾病组或对照组样本数量为0")
        
        # 提取疾病组和对照组得分
        disease_scores = ssgsea_scores[disease_samples].T  # sample × system
        control_scores = ssgsea_scores[control_samples].T  # sample × system
        
        # 计算统计指标
        fold_changes = {}
        p_values = {}
        effect_sizes = {}
        significant_systems = []
        
        for system in ssgsea_scores.index:
            disease_vals = disease_scores[system].values
            control_vals = control_scores[system].values
            
            # 计算fold change (log2)
            disease_mean = np.mean(disease_vals)
            control_mean = np.mean(control_vals)
            
            if control_mean != 0:
                fold_change = np.log2(disease_mean / control_mean) if disease_mean > 0 and control_mean > 0 else 0
            else:
                fold_change = 0
            fold_changes[system] = fold_change
            
            # 计算p值 (t-test)
            try:
                t_stat, p_val = stats.ttest_ind(disease_vals, control_vals)
                p_values[system] = p_val
            except:
                p_values[system] = 1.0
            
            # 计算效应量 (Cohen's d)
            pooled_std = np.sqrt(((len(disease_vals) - 1) * np.var(disease_vals, ddof=1) + 
                                 (len(control_vals) - 1) * np.var(control_vals, ddof=1)) / 
                                (len(disease_vals) + len(control_vals) - 2))
            
            if pooled_std > 0:
                cohens_d = (disease_mean - control_mean) / pooled_std
            else:
                cohens_d = 0
            effect_sizes[system] = cohens_d
            
            # 判断是否显著
            if p_val < self.settings.statistical_alpha and abs(cohens_d) > 0.2:
                significant_systems.append(system)
        
        logger.info(f"显著差异系统数: {len(significant_systems)}")
        logger.info(f"显著系统: {significant_systems}")
        
        return ComparisonResult(
            dataset_name=dataset_name,
            disease_scores=disease_scores,
            control_scores=control_scores,
            fold_changes=fold_changes,
            p_values=p_values,
            effect_sizes=effect_sizes,
            significant_systems=significant_systems
        )
    
    def validate_ssgsea_accuracy(self, gene_expr_df: pd.DataFrame,
                               known_gene_sets: Dict[str, List[str]],
                               test_gene_sets: Dict[str, List[str]]) -> ValidationResult:
        """
        验证ssGSEA计算的准确性
        
        Args:
            gene_expr_df: gene × sample表达矩阵
            known_gene_sets: 已知的基因集（用作参考）
            test_gene_sets: 待测试的基因集
            
        Returns:
            ValidationResult: 验证结果
        """
        logger.info("验证ssGSEA计算准确性")
        
        try:
            # 计算已知基因集的ssGSEA得分
            known_scores = self.compute_system_scores(gene_expr_df, known_gene_sets)
            
            # 计算测试基因集的ssGSEA得分
            test_scores = self.compute_system_scores(gene_expr_df, test_gene_sets)
            
            # 验证得分范围
            score_range_valid = True
            for scores in [known_scores, test_scores]:
                min_score = scores.min().min()
                max_score = scores.max().max()
                if min_score < -3 or max_score > 3:  # ssGSEA得分通常在[-3, 3]范围内
                    score_range_valid = False
                    logger.warning(f"ssGSEA得分超出预期范围: [{min_score:.3f}, {max_score:.3f}]")
            
            # 计算相关性（如果基因集有重叠）
            correlations = {}
            for known_system, known_genes in known_gene_sets.items():
                for test_system, test_genes in test_gene_sets.items():
                    # 计算基因集重叠度
                    overlap = len(set(known_genes) & set(test_genes))
                    jaccard = overlap / len(set(known_genes) | set(test_genes)) if len(set(known_genes) | set(test_genes)) > 0 else 0
                    
                    if jaccard > 0.1:  # 只计算有一定重叠的基因集
                        # 计算得分相关性
                        known_vals = known_scores.loc[known_system].values
                        test_vals = test_scores.loc[test_system].values
                        
                        correlation, p_val = stats.pearsonr(known_vals, test_vals)
                        correlations[f"{known_system}_vs_{test_system}"] = {
                            'correlation': correlation,
                            'p_value': p_val,
                            'jaccard_index': jaccard,
                            'overlap_genes': overlap
                        }
            
            # 创建验证结果
            validation_result = ValidationResult(
                validation_type='ssgsea',
                validation_date=datetime.now()
            )
            
            # 添加性能指标
            validation_result.add_performance_metric('score_range_valid', float(score_range_valid))
            validation_result.add_performance_metric('known_systems_count', len(known_gene_sets))
            validation_result.add_performance_metric('test_systems_count', len(test_gene_sets))
            validation_result.add_performance_metric('samples_count', len(gene_expr_df.columns))
            validation_result.add_performance_metric('genes_count', len(gene_expr_df))
            
            # 添加相关性统计
            if correlations:
                avg_correlation = np.mean([c['correlation'] for c in correlations.values() if not np.isnan(c['correlation'])])
                validation_result.add_performance_metric('avg_correlation', avg_correlation)
                
                for key, stats_dict in correlations.items():
                    validation_result.add_statistical_test(f"correlation_{key}", stats_dict['p_value'])
            
            # 添加元数据
            validation_result.metadata.update({
                'known_gene_sets': list(known_gene_sets.keys()),
                'test_gene_sets': list(test_gene_sets.keys()),
                'correlations': correlations
            })
            
            logger.info("ssGSEA准确性验证完成")
            return validation_result
            
        except Exception as e:
            logger.error(f"ssGSEA准确性验证失败: {e}")
            raise
    
    def generate_time_series_visualization(self, time_series_result: TimeSeriesResult,
                                         output_path: Optional[Union[str, Path]] = None) -> None:
        """
        生成时间序列可视化图表
        
        Args:
            time_series_result: 时间序列分析结果
            output_path: 输出路径，如果为None则显示图表
        """
        logger.info(f"生成时间序列可视化: {time_series_result.dataset_name}")
        
        # 设置图表样式
        plt.style.use('default')
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'Time Series Analysis: {time_series_result.dataset_name}', fontsize=16)
        
        # 1. 系统得分随时间变化的线图
        ax1 = axes[0, 0]
        for system in time_series_result.system_scores.columns:
            ax1.plot(time_series_result.time_points, 
                    time_series_result.system_scores[system], 
                    marker='o', label=system, linewidth=2)
        ax1.set_title('System Scores Over Time')
        ax1.set_xlabel('Time Points')
        ax1.set_ylabel('ssGSEA Score')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 系统间相关性热图
        ax2 = axes[0, 1]
        correlation_matrix = time_series_result.system_scores.corr()
        sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0,
                   ax=ax2, square=True, fmt='.2f')
        ax2.set_title('System Correlation Matrix')
        
        # 3. 趋势条形图
        ax3 = axes[1, 0]
        trend_counts = {}
        for trend in ['increasing', 'decreasing', 'stable']:
            trend_counts[trend] = list(time_series_result.trends.values()).count(trend)
        
        bars = ax3.bar(trend_counts.keys(), trend_counts.values(), 
                      color=['green', 'red', 'gray'])
        ax3.set_title('Trend Distribution')
        ax3.set_ylabel('Number of Systems')
        
        # 添加数值标签
        for bar in bars:
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}', ha='center', va='bottom')
        
        # 4. 相关性分布
        ax4 = axes[1, 1]
        correlations = list(time_series_result.correlations.values())
        ax4.hist(correlations, bins=10, alpha=0.7, color='skyblue', edgecolor='black')
        ax4.set_title('Correlation with Time Distribution')
        ax4.set_xlabel('Correlation Coefficient')
        ax4.set_ylabel('Frequency')
        ax4.axvline(x=0, color='red', linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            logger.info(f"时间序列图表已保存: {output_path}")
        else:
            plt.show()
        
        plt.close()
    
    def generate_comparison_visualization(self, comparison_result: ComparisonResult,
                                        output_path: Optional[Union[str, Path]] = None) -> None:
        """
        生成疾病对比可视化图表
        
        Args:
            comparison_result: 疾病对比分析结果
            output_path: 输出路径，如果为None则显示图表
        """
        logger.info(f"生成疾病对比可视化: {comparison_result.dataset_name}")
        
        # 设置图表样式
        plt.style.use('default')
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'Disease vs Control Comparison: {comparison_result.dataset_name}', fontsize=16)
        
        systems = list(comparison_result.fold_changes.keys())
        
        # 1. Fold Change条形图
        ax1 = axes[0, 0]
        fold_changes = [comparison_result.fold_changes[s] for s in systems]
        colors = ['red' if fc > 0 else 'blue' for fc in fold_changes]
        bars = ax1.bar(range(len(systems)), fold_changes, color=colors, alpha=0.7)
        ax1.set_title('Log2 Fold Change (Disease vs Control)')
        ax1.set_xlabel('Systems')
        ax1.set_ylabel('Log2 Fold Change')
        ax1.set_xticks(range(len(systems)))
        ax1.set_xticklabels(systems, rotation=45)
        ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        ax1.grid(True, alpha=0.3)
        
        # 2. P值条形图
        ax2 = axes[0, 1]
        p_values = [comparison_result.p_values[s] for s in systems]
        colors = ['red' if p < 0.05 else 'gray' for p in p_values]
        bars = ax2.bar(range(len(systems)), [-np.log10(p) for p in p_values], 
                      color=colors, alpha=0.7)
        ax2.set_title('-Log10(P-value)')
        ax2.set_xlabel('Systems')
        ax2.set_ylabel('-Log10(P-value)')
        ax2.set_xticks(range(len(systems)))
        ax2.set_xticklabels(systems, rotation=45)
        ax2.axhline(y=-np.log10(0.05), color='red', linestyle='--', alpha=0.7, label='p=0.05')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. 效应量条形图
        ax3 = axes[1, 0]
        effect_sizes = [comparison_result.effect_sizes[s] for s in systems]
        colors = ['red' if abs(es) > 0.5 else 'orange' if abs(es) > 0.2 else 'gray' for es in effect_sizes]
        bars = ax3.bar(range(len(systems)), effect_sizes, color=colors, alpha=0.7)
        ax3.set_title("Cohen's d (Effect Size)")
        ax3.set_xlabel('Systems')
        ax3.set_ylabel("Cohen's d")
        ax3.set_xticks(range(len(systems)))
        ax3.set_xticklabels(systems, rotation=45)
        ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        ax3.axhline(y=0.2, color='orange', linestyle='--', alpha=0.7, label='Small effect')
        ax3.axhline(y=0.5, color='red', linestyle='--', alpha=0.7, label='Medium effect')
        ax3.axhline(y=-0.2, color='orange', linestyle='--', alpha=0.7)
        ax3.axhline(y=-0.5, color='red', linestyle='--', alpha=0.7)
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. 火山图 (Fold Change vs P-value)
        ax4 = axes[1, 1]
        fold_changes = [comparison_result.fold_changes[s] for s in systems]
        p_values = [comparison_result.p_values[s] for s in systems]
        
        # 根据显著性着色
        colors = []
        for i, system in enumerate(systems):
            if system in comparison_result.significant_systems:
                colors.append('red')
            else:
                colors.append('gray')
        
        scatter = ax4.scatter(fold_changes, [-np.log10(p) for p in p_values], 
                            c=colors, alpha=0.7, s=50)
        ax4.set_title('Volcano Plot')
        ax4.set_xlabel('Log2 Fold Change')
        ax4.set_ylabel('-Log10(P-value)')
        ax4.axhline(y=-np.log10(0.05), color='red', linestyle='--', alpha=0.7)
        ax4.axvline(x=0, color='black', linestyle='-', alpha=0.3)
        ax4.grid(True, alpha=0.3)
        
        # 添加系统标签
        for i, system in enumerate(systems):
            if system in comparison_result.significant_systems:
                ax4.annotate(system, (fold_changes[i], -np.log10(p_values[i])), 
                           xytext=(5, 5), textcoords='offset points', fontsize=8)
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            logger.info(f"疾病对比图表已保存: {output_path}")
        else:
            plt.show()
        
        plt.close()
    
    def save_results(self, results: Dict[str, Any], output_path: Union[str, Path]) -> None:
        """
        保存分析结果到文件
        
        Args:
            results: 分析结果字典
            output_path: 输出文件路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 转换结果为可序列化格式
        serializable_results = {}
        for key, value in results.items():
            if isinstance(value, (TimeSeriesResult, ComparisonResult)):
                serializable_results[key] = value.to_dict()
            elif isinstance(value, pd.DataFrame):
                serializable_results[key] = value.to_dict()
            elif isinstance(value, ValidationResult):
                serializable_results[key] = value.to_dict()
            else:
                serializable_results[key] = value
        
        # 保存为JSON文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"分析结果已保存: {output_path}")
    def parse_sample_metadata(self, series_matrix_path: Union[str, Path]) -> Dict[str, Any]:
        """
        解析GEO series_matrix文件中的样本元数据
        
        Args:
            series_matrix_path: series_matrix文件路径
            
        Returns:
            Dict[str, Any]: 样本元数据字典
        """
        filepath = Path(series_matrix_path)
        logger.info(f"解析样本元数据: {filepath}")
        
        metadata = {
            'sample_titles': {},
            'sample_characteristics': {},
            'sample_groups': {},
            'time_points': {},
            'dataset_info': {}
        }
        
        try:
            # 读取文件
            if filepath.suffix == '.gz':
                with gzip.open(filepath, 'rt', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
            else:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
            
            # 解析元数据行（以!开头的注释行）
            for line in lines:
                line = line.strip()
                if not line.startswith('!'):
                    break  # 到达数据部分，停止解析元数据
                
                # 解析数据集信息
                if line.startswith('!Series_title'):
                    metadata['dataset_info']['title'] = line.split('\t')[1].strip('"') if '\t' in line else ""
                elif line.startswith('!Series_summary'):
                    metadata['dataset_info']['summary'] = line.split('\t')[1].strip('"') if '\t' in line else ""
                elif line.startswith('!Series_overall_design'):
                    metadata['dataset_info']['design'] = line.split('\t')[1].strip('"') if '\t' in line else ""
                
                # 解析样本标题
                elif line.startswith('!Sample_title'):
                    parts = line.split('\t')
                    if len(parts) > 1:
                        titles = [p.strip('"') for p in parts[1:]]
                        for i, title in enumerate(titles):
                            sample_id = f"GSM{i+1}"  # 临时ID，后续会被实际ID替换
                            metadata['sample_titles'][sample_id] = title
                
                # 解析样本特征
                elif line.startswith('!Sample_characteristics_ch1'):
                    parts = line.split('\t')
                    if len(parts) > 1:
                        characteristics = [p.strip('"') for p in parts[1:]]
                        for i, char in enumerate(characteristics):
                            sample_id = f"GSM{i+1}"
                            if sample_id not in metadata['sample_characteristics']:
                                metadata['sample_characteristics'][sample_id] = []
                            metadata['sample_characteristics'][sample_id].append(char)
                
                # 解析样本来源名称
                elif line.startswith('!Sample_source_name_ch1'):
                    parts = line.split('\t')
                    if len(parts) > 1:
                        sources = [p.strip('"') for p in parts[1:]]
                        for i, source in enumerate(sources):
                            sample_id = f"GSM{i+1}"
                            metadata['sample_groups'][sample_id] = source
            
            # 从样本特征中提取时间点和分组信息
            self._extract_time_and_groups(metadata)
            
            logger.info(f"解析到 {len(metadata['sample_titles'])} 个样本的元数据")
            return metadata
            
        except Exception as e:
            logger.error(f"解析样本元数据失败: {e}")
            return metadata
    
    def _extract_time_and_groups(self, metadata: Dict[str, Any]) -> None:
        """
        从样本特征中提取时间点和分组信息
        
        Args:
            metadata: 样本元数据字典（会被修改）
        """
        for sample_id, characteristics in metadata['sample_characteristics'].items():
            time_point = None
            group = None
            
            for char in characteristics:
                char_lower = char.lower()
                
                # 提取时间点信息
                if 'time' in char_lower or 'day' in char_lower or 'hour' in char_lower:
                    # 尝试提取数字
                    import re
                    time_match = re.search(r'(\d+)\s*(day|hour|h|d)', char_lower)
                    if time_match:
                        time_point = f"{time_match.group(1)}{time_match.group(2)[0]}"
                    else:
                        time_point = char
                
                # 提取分组信息
                elif any(keyword in char_lower for keyword in ['control', 'treatment', 'disease', 'normal', 'patient']):
                    group = char
                elif 'group' in char_lower:
                    group = char
            
            # 如果没有找到明确的时间点，尝试从样本标题中提取
            if time_point is None and sample_id in metadata['sample_titles']:
                title = metadata['sample_titles'][sample_id].lower()
                import re
                time_match = re.search(r'(\d+)\s*(day|hour|h|d)', title)
                if time_match:
                    time_point = f"{time_match.group(1)}{time_match.group(2)[0]}"
            
            # 如果没有找到明确的分组，尝试从样本来源中提取
            if group is None and sample_id in metadata['sample_groups']:
                group = metadata['sample_groups'][sample_id]
            
            metadata['time_points'][sample_id] = time_point
            if group:
                metadata['sample_groups'][sample_id] = group
    
    def identify_dataset_type(self, metadata: Dict[str, Any]) -> str:
        """
        识别数据集类型（时间序列、疾病对比等）
        
        Args:
            metadata: 样本元数据
            
        Returns:
            str: 数据集类型 ('time_series', 'disease_control', 'other')
        """
        # 检查是否有时间点信息
        time_points = [tp for tp in metadata['time_points'].values() if tp is not None]
        unique_time_points = len(set(time_points))
        
        # 检查是否有分组信息
        groups = list(metadata['sample_groups'].values())
        unique_groups = len(set(groups))
        
        if unique_time_points >= 3:
            return 'time_series'
        elif unique_groups >= 2:
            # 检查是否包含疾病相关关键词
            group_text = ' '.join(groups).lower()
            if any(keyword in group_text for keyword in ['disease', 'patient', 'control', 'normal', 'treatment']):
                return 'disease_control'
        
        return 'other'
    
    def process_all_validation_datasets(self, output_base_dir: Optional[Union[str, Path]] = None) -> Dict[str, pd.DataFrame]:
        """
        处理所有验证数据集
        
        Args:
            output_base_dir: 输出基础目录
            
        Returns:
            Dict[str, pd.DataFrame]: 数据集名称到ssGSEA得分矩阵的映射
        """
        if output_base_dir is None:
            output_base_dir = self.settings.results_dir / "ssgsea_results"
        
        output_base_dir = Path(output_base_dir)
        
        # 定义验证数据集配置
        datasets_config = {
            'GSE28914': {
                'series_matrix': self.settings.validation_dir / 'GSE28914' / 'GSE28914_series_matrix.txt.gz',
                'gpl': self.settings.validation_dir / 'GSE28914' / 'GPL570-55999.txt',
                'description': 'Wound healing time series'
            },
            'GSE65682': {
                'series_matrix': self.settings.validation_dir / 'GSE65682' / 'GSE65682_series_matrix.txt.gz',
                'gpl': self.settings.validation_dir / 'GSE65682' / 'GPL13667-15572.txt',
                'description': 'Sepsis disease comparison'
            },
            'GSE21899': {
                'series_matrix': self.settings.validation_dir / 'GSE21899' / 'GSE21899_series_matrix.txt.gz',
                'gpl': self.settings.validation_dir / 'GSE21899' / 'GPL6480-9577.txt',
                'description': 'Gaucher disease comparison'
            }
        }
        
        results = {}
        
        # 确保基因集已加载
        if not self.gene_sets:
            self.load_system_gene_sets()
        
        for dataset_name, config in datasets_config.items():
            logger.info(f"处理数据集: {dataset_name} - {config['description']}")
            
            try:
                # 检查文件是否存在
                if not config['series_matrix'].exists():
                    logger.warning(f"数据集 {dataset_name} 的series_matrix文件不存在: {config['series_matrix']}")
                    continue
                
                if not config['gpl'].exists():
                    logger.warning(f"数据集 {dataset_name} 的GPL文件不存在: {config['gpl']}")
                    continue
                
                # 创建输出目录
                dataset_output_dir = output_base_dir / dataset_name
                dataset_output_dir.mkdir(parents=True, exist_ok=True)
                
                # 处理数据集
                ssgsea_scores = self.process_validation_dataset(
                    dataset_name=dataset_name,
                    series_matrix_path=config['series_matrix'],
                    gpl_path=config['gpl'],
                    output_dir=dataset_output_dir
                )
                
                results[dataset_name] = ssgsea_scores
                
                # 解析样本元数据
                metadata = self.parse_sample_metadata(config['series_matrix'])
                dataset_type = self.identify_dataset_type(metadata)
                
                logger.info(f"{dataset_name} 数据集类型: {dataset_type}")
                
                # 保存元数据
                metadata_path = dataset_output_dir / 'metadata.json'
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'dataset_name': dataset_name,
                        'dataset_type': dataset_type,
                        'description': config['description'],
                        'metadata': metadata
                    }, f, ensure_ascii=False, indent=2, default=str)
                
                logger.info(f"{dataset_name} 处理完成")
                
            except Exception as e:
                logger.error(f"处理数据集 {dataset_name} 失败: {e}")
                continue
        
        logger.info(f"所有验证数据集处理完成，成功处理 {len(results)} 个数据集")
        return results
    
    def create_sample_info_mapping(self, metadata: Dict[str, Any], 
                                 sample_columns: List[str]) -> pd.DataFrame:
        """
        创建样本信息映射表
        
        Args:
            metadata: 样本元数据
            sample_columns: 实际的样本列名列表
            
        Returns:
            pd.DataFrame: 样本信息映射表
        """
        sample_info = []
        
        for i, sample_col in enumerate(sample_columns):
            # 尝试从元数据中获取信息
            sample_id = f"GSM{i+1}"  # 临时ID
            
            info = {
                'sample_id': sample_col,
                'sample_index': i,
                'title': metadata['sample_titles'].get(sample_id, sample_col),
                'group': metadata['sample_groups'].get(sample_id, 'Unknown'),
                'time_point': metadata['time_points'].get(sample_id, None),
                'characteristics': metadata['sample_characteristics'].get(sample_id, [])
            }
            
            sample_info.append(info)
        
        return pd.DataFrame(sample_info)
    
    def generate_validation_summary_report(self, results: Dict[str, pd.DataFrame],
                                         output_path: Optional[Union[str, Path]] = None) -> str:
        """
        生成验证数据集处理摘要报告
        
        Args:
            results: 处理结果字典
            output_path: 输出路径，如果为None则返回字符串
            
        Returns:
            str: 摘要报告内容
        """
        report_lines = [
            "# ssGSEA验证数据集处理摘要报告",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 处理概况",
            f"- 成功处理数据集数量: {len(results)}",
            f"- 使用的基因集数量: {len(self.gene_sets)}",
            ""
        ]
        
        # 添加每个数据集的详细信息
        for dataset_name, scores in results.items():
            report_lines.extend([
                f"## {dataset_name}",
                f"- 系统数量: {scores.shape[0]}",
                f"- 样本数量: {scores.shape[1]}",
                f"- 得分范围: [{scores.min().min():.3f}, {scores.max().max():.3f}]",
                ""
            ])
            
            # 添加每个系统的统计信息
            for system in scores.index:
                system_scores = scores.loc[system]
                report_lines.append(f"  - {system}: 均值={system_scores.mean():.3f}, 标准差={system_scores.std():.3f}")
            
            report_lines.append("")
        
        # 添加基因集信息
        report_lines.extend([
            "## 使用的基因集",
            ""
        ])
        
        for system, genes in self.gene_sets.items():
            report_lines.append(f"- {system}: {len(genes)} 个基因")
        
        report_content = "\n".join(report_lines)
        
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            logger.info(f"验证摘要报告已保存: {output_path}")
        
        return report_content
    def advanced_time_series_analysis(self, ssgsea_scores: pd.DataFrame,
                                     sample_info: pd.DataFrame,
                                     dataset_name: str = "Unknown") -> TimeSeriesResult:
        """
        高级时间序列分析，包括趋势检测、变化点分析等
        
        Args:
            ssgsea_scores: system × sample ssGSEA得分矩阵
            sample_info: 样本信息DataFrame，包含time_point列
            dataset_name: 数据集名称
            
        Returns:
            TimeSeriesResult: 详细的时间序列分析结果
        """
        logger.info(f"执行高级时间序列分析: {dataset_name}")
        
        # 确保样本信息包含时间点
        if 'time_point' not in sample_info.columns:
            raise ValueError("样本信息中缺少time_point列")
        
        # 过滤有时间点信息的样本
        valid_samples = sample_info[sample_info['time_point'].notna()]
        if len(valid_samples) == 0:
            raise ValueError("没有找到有效的时间点信息")
        
        # 提取对应的得分数据
        valid_sample_ids = valid_samples['sample_id'].tolist()
        time_scores = ssgsea_scores[valid_sample_ids].T  # sample × system
        time_scores.index = valid_samples['time_point'].tolist()
        
        # 按时间点分组并计算平均值
        time_grouped = time_scores.groupby(time_scores.index).mean()
        
        # 对时间点进行排序（尝试数值排序）
        try:
            # 提取数值部分进行排序
            import re
            time_numeric = []
            for tp in time_grouped.index:
                match = re.search(r'(\d+)', str(tp))
                if match:
                    time_numeric.append((int(match.group(1)), tp))
                else:
                    time_numeric.append((0, tp))
            
            time_numeric.sort()
            sorted_times = [tp for _, tp in time_numeric]
            time_grouped = time_grouped.reindex(sorted_times)
        except:
            # 如果数值排序失败，使用字符串排序
            time_grouped = time_grouped.sort_index()
        
        # 计算高级统计指标
        trends = {}
        correlations = {}
        change_points = {}
        statistics = {}
        
        time_indices = list(range(len(time_grouped)))
        
        for system in time_grouped.columns:
            system_values = time_grouped[system].values
            
            # 1. 线性趋势分析
            correlation, p_value = stats.pearsonr(time_indices, system_values)
            correlations[system] = correlation
            
            # 2. 趋势分类
            if correlation > 0.3 and p_value < 0.05:
                trends[system] = "increasing"
            elif correlation < -0.3 and p_value < 0.05:
                trends[system] = "decreasing"
            else:
                trends[system] = "stable"
            
            # 3. 变化点检测（简单的方法：检测最大变化）
            if len(system_values) > 2:
                diffs = np.diff(system_values)
                max_change_idx = np.argmax(np.abs(diffs))
                change_points[system] = {
                    'time_point': time_grouped.index[max_change_idx + 1],
                    'change_magnitude': diffs[max_change_idx],
                    'change_type': 'increase' if diffs[max_change_idx] > 0 else 'decrease'
                }
            
            # 4. 详细统计信息
            statistics[f"{system}_correlation"] = correlation
            statistics[f"{system}_p_value"] = p_value
            statistics[f"{system}_mean"] = np.mean(system_values)
            statistics[f"{system}_std"] = np.std(system_values)
            statistics[f"{system}_range"] = np.max(system_values) - np.min(system_values)
            statistics[f"{system}_cv"] = np.std(system_values) / np.mean(system_values) if np.mean(system_values) != 0 else 0
            
            # 5. 单调性检验
            if len(system_values) > 2:
                # Mann-Kendall趋势检验
                mk_stat, mk_p = self._mann_kendall_test(system_values)
                statistics[f"{system}_mk_statistic"] = mk_stat
                statistics[f"{system}_mk_p_value"] = mk_p
        
        # 6. 系统间相关性分析
        system_correlations = time_grouped.corr()
        statistics['system_correlations'] = system_correlations.to_dict()
        
        # 7. 整体变异性分析
        overall_variance = time_grouped.var(axis=0).mean()
        statistics['overall_variance'] = overall_variance
        
        logger.info(f"时间序列分析完成，检测到趋势: {trends}")
        
        result = TimeSeriesResult(
            dataset_name=dataset_name,
            system_scores=time_grouped,
            time_points=list(time_grouped.index),
            statistics=statistics,
            trends=trends,
            correlations=correlations
        )
        
        # 添加变化点信息到结果中
        result.change_points = change_points
        
        return result
    
    def _mann_kendall_test(self, data: np.ndarray) -> Tuple[float, float]:
        """
        Mann-Kendall趋势检验
        
        Args:
            data: 时间序列数据
            
        Returns:
            Tuple[float, float]: (统计量, p值)
        """
        n = len(data)
        if n < 3:
            return 0.0, 1.0
        
        # 计算S统计量
        S = 0
        for i in range(n - 1):
            for j in range(i + 1, n):
                if data[j] > data[i]:
                    S += 1
                elif data[j] < data[i]:
                    S -= 1
        
        # 计算方差
        var_S = n * (n - 1) * (2 * n + 5) / 18
        
        # 计算标准化统计量
        if S > 0:
            Z = (S - 1) / np.sqrt(var_S)
        elif S < 0:
            Z = (S + 1) / np.sqrt(var_S)
        else:
            Z = 0
        
        # 计算p值（双尾检验）
        p_value = 2 * (1 - stats.norm.cdf(abs(Z)))
        
        return float(S), float(p_value)
    
    def generate_time_series_statistics_report(self, time_series_result: TimeSeriesResult,
                                             output_path: Optional[Union[str, Path]] = None) -> str:
        """
        生成时间序列统计报告
        
        Args:
            time_series_result: 时间序列分析结果
            output_path: 输出路径
            
        Returns:
            str: 报告内容
        """
        result = time_series_result
        
        report_lines = [
            f"# 时间序列分析报告: {result.dataset_name}",
            f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 基本信息",
            f"- 数据集: {result.dataset_name}",
            f"- 时间点数量: {len(result.time_points)}",
            f"- 系统数量: {len(result.system_scores.columns)}",
            f"- 时间点: {', '.join(map(str, result.time_points))}",
            "",
            "## 趋势分析",
            ""
        ]
        
        # 趋势统计
        trend_counts = {}
        for trend in ['increasing', 'decreasing', 'stable']:
            count = list(result.trends.values()).count(trend)
            trend_counts[trend] = count
            report_lines.append(f"- {trend.capitalize()}: {count} 个系统")
        
        report_lines.extend(["", "## 各系统详细分析", ""])
        
        # 各系统详细信息
        for system in result.system_scores.columns:
            correlation = result.correlations.get(system, 0)
            trend = result.trends.get(system, 'unknown')
            
            report_lines.extend([
                f"### {system}",
                f"- 趋势: {trend}",
                f"- 与时间相关性: {correlation:.4f}",
                f"- 平均得分: {result.statistics.get(f'{system}_mean', 0):.4f}",
                f"- 标准差: {result.statistics.get(f'{system}_std', 0):.4f}",
                f"- 变异系数: {result.statistics.get(f'{system}_cv', 0):.4f}",
                f"- 得分范围: {result.statistics.get(f'{system}_range', 0):.4f}",
                ""
            ])
            
            # 添加Mann-Kendall检验结果
            mk_p = result.statistics.get(f'{system}_mk_p_value')
            if mk_p is not None:
                significance = "显著" if mk_p < 0.05 else "不显著"
                report_lines.append(f"- Mann-Kendall检验: p={mk_p:.4f} ({significance})")
            
            # 添加变化点信息
            if hasattr(result, 'change_points') and system in result.change_points:
                cp = result.change_points[system]
                report_lines.extend([
                    f"- 最大变化点: {cp['time_point']}",
                    f"- 变化幅度: {cp['change_magnitude']:.4f} ({cp['change_type']})",
                ])
            
            report_lines.append("")
        
        # 系统间相关性
        if 'system_correlations' in result.statistics:
            report_lines.extend([
                "## 系统间相关性",
                ""
            ])
            
            corr_matrix = result.statistics['system_correlations']
            systems = list(corr_matrix.keys())
            
            for i, sys1 in enumerate(systems):
                for j, sys2 in enumerate(systems):
                    if i < j:  # 只显示上三角
                        corr = corr_matrix[sys1][sys2]
                        if abs(corr) > 0.5:  # 只显示中等以上相关性
                            report_lines.append(f"- {sys1} vs {sys2}: {corr:.4f}")
        
        # 整体统计
        report_lines.extend([
            "",
            "## 整体统计",
            f"- 整体变异性: {result.statistics.get('overall_variance', 0):.4f}",
            ""
        ])
        
        report_content = "\n".join(report_lines)
        
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            logger.info(f"时间序列统计报告已保存: {output_path}")
        
        return report_content
    
    def create_time_series_csv_output(self, time_series_result: TimeSeriesResult,
                                    output_path: Union[str, Path]) -> None:
        """
        创建时间序列分析的CSV输出文件
        
        Args:
            time_series_result: 时间序列分析结果
            output_path: 输出文件路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存系统得分矩阵
        scores_path = output_path.parent / f"{output_path.stem}_scores.csv"
        time_series_result.system_scores.to_csv(scores_path, encoding='utf-8-sig')
        
        # 保存统计摘要
        summary_data = []
        for system in time_series_result.system_scores.columns:
            row = {
                'System': system,
                'Trend': time_series_result.trends.get(system, 'unknown'),
                'Correlation': time_series_result.correlations.get(system, 0),
                'Mean_Score': time_series_result.statistics.get(f'{system}_mean', 0),
                'Std_Score': time_series_result.statistics.get(f'{system}_std', 0),
                'CV': time_series_result.statistics.get(f'{system}_cv', 0),
                'Range': time_series_result.statistics.get(f'{system}_range', 0),
                'MK_P_Value': time_series_result.statistics.get(f'{system}_mk_p_value', None)
            }
            
            # 添加变化点信息
            if hasattr(time_series_result, 'change_points') and system in time_series_result.change_points:
                cp = time_series_result.change_points[system]
                row['Change_Point'] = cp['time_point']
                row['Change_Magnitude'] = cp['change_magnitude']
                row['Change_Type'] = cp['change_type']
            
            summary_data.append(row)
        
        summary_df = pd.DataFrame(summary_data)
        summary_path = output_path.parent / f"{output_path.stem}_summary.csv"
        summary_df.to_csv(summary_path, index=False, encoding='utf-8-sig')
        
        logger.info(f"时间序列CSV文件已保存: {scores_path}, {summary_path}")
    
    def run_comprehensive_validation(self, output_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """
        运行完整的ssGSEA验证流程
        
        Args:
            output_dir: 输出目录
            
        Returns:
            Dict[str, Any]: 完整的验证结果
        """
        if output_dir is None:
            output_dir = self.settings.results_dir / "ssgsea_validation"
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("开始完整的ssGSEA验证流程")
        
        # 1. 处理所有验证数据集
        logger.info("步骤1: 处理验证数据集")
        dataset_scores = self.process_all_validation_datasets(output_dir / "datasets")
        
        # 2. 生成验证摘要报告
        logger.info("步骤2: 生成验证摘要报告")
        summary_report = self.generate_validation_summary_report(
            dataset_scores, 
            output_dir / "validation_summary.md"
        )
        
        # 3. 对每个数据集进行详细分析
        logger.info("步骤3: 详细分析各数据集")
        analysis_results = {}
        
        for dataset_name, scores in dataset_scores.items():
            logger.info(f"分析数据集: {dataset_name}")
            
            dataset_output_dir = output_dir / "analysis" / dataset_name
            dataset_output_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                # 加载样本元数据
                metadata_path = output_dir / "datasets" / dataset_name / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        dataset_metadata = json.load(f)
                    
                    dataset_type = dataset_metadata.get('dataset_type', 'other')
                    metadata = dataset_metadata.get('metadata', {})
                    
                    # 创建样本信息映射
                    sample_info = self.create_sample_info_mapping(metadata, list(scores.columns))
                    
                    if dataset_type == 'time_series':
                        # 时间序列分析
                        time_result = self.advanced_time_series_analysis(scores, sample_info, dataset_name)
                        analysis_results[f"{dataset_name}_time_series"] = time_result
                        
                        # 生成时间序列报告和可视化
                        self.generate_time_series_statistics_report(
                            time_result, 
                            dataset_output_dir / "time_series_report.md"
                        )
                        
                        self.create_time_series_csv_output(
                            time_result,
                            dataset_output_dir / "time_series_analysis.csv"
                        )
                        
                        self.generate_time_series_visualization(
                            time_result,
                            dataset_output_dir / "time_series_plot.png"
                        )
                    
                    elif dataset_type == 'disease_control':
                        # 疾病对比分析
                        # 识别疾病组和对照组样本
                        disease_samples = []
                        control_samples = []
                        
                        for _, row in sample_info.iterrows():
                            group = str(row['group']).lower()
                            if any(keyword in group for keyword in ['disease', 'patient', 'treatment']):
                                disease_samples.append(row['sample_id'])
                            elif any(keyword in group for keyword in ['control', 'normal', 'healthy']):
                                control_samples.append(row['sample_id'])
                        
                        if len(disease_samples) > 0 and len(control_samples) > 0:
                            comparison_result = self.compare_disease_control(
                                scores, disease_samples, control_samples, dataset_name
                            )
                            analysis_results[f"{dataset_name}_disease_control"] = comparison_result
                            
                            # 生成疾病对比可视化
                            self.generate_comparison_visualization(
                                comparison_result,
                                dataset_output_dir / "disease_control_plot.png"
                            )
                        else:
                            logger.warning(f"数据集 {dataset_name} 无法识别疾病组和对照组")
                
            except Exception as e:
                logger.error(f"分析数据集 {dataset_name} 失败: {e}")
                continue
        
        # 4. 保存完整结果
        logger.info("步骤4: 保存完整结果")
        complete_results = {
            'dataset_scores': {k: v.to_dict() for k, v in dataset_scores.items()},
            'analysis_results': analysis_results,
            'summary_report': summary_report,
            'validation_date': datetime.now().isoformat(),
            'gene_sets_used': self.gene_sets
        }
        
        self.save_results(complete_results, output_dir / "complete_validation_results.json")
        
        logger.info(f"完整的ssGSEA验证流程完成，结果保存在: {output_dir}")
        
        return complete_results