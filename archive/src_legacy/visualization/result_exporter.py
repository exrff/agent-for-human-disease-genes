"""
分类结果导出模块

实现五大功能系统分类结果的标准化导出功能，支持CSV格式输出、
批量导出和增量更新。

Requirements: 8.1, 8.2
"""

import csv
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import logging

from ..models.classification_result import ClassificationResult
from ..models.biological_entry import BiologicalEntry


class ResultExporter:
    """
    分类结果导出器
    
    提供多种格式的分类结果导出功能，包括CSV、JSON等格式，
    支持批量导出、增量更新和元数据管理。
    """
    
    def __init__(self, output_dir: Union[str, Path] = "results/classification"):
        """
        初始化导出器
        
        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # CSV字段定义
        self.csv_fields = [
            'ID',
            'Name', 
            'Definition',
            'Source',
            'Namespace',
            'Primary_System',
            'Subsystem',
            'All_Systems',
            'Inflammation_Polarity',
            'Confidence_Score',
            'Decision_Path',
            'Classification_Date',
            'Version'
        ]
    
    def export_to_csv(self, 
                     results: List[ClassificationResult],
                     entries: List[BiologicalEntry],
                     filename: str = "classification_results.csv",
                     version: str = "v8.0") -> Path:
        """
        导出分类结果到CSV文件
        
        Args:
            results: 分类结果列表
            entries: 生物学条目列表
            filename: 输出文件名
            version: 分类版本号
            
        Returns:
            输出文件路径
        """
        # 创建条目ID到条目的映射
        entry_map = {entry.id: entry for entry in entries}
        
        # 准备CSV数据
        csv_data = []
        classification_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for result in results:
            entry = entry_map.get(result.entry_id)
            if not entry:
                self.logger.warning(f"Entry not found for ID: {result.entry_id}")
                continue
            
            row = {
                'ID': result.entry_id,
                'Name': entry.name,
                'Definition': entry.definition,
                'Source': entry.source,
                'Namespace': entry.namespace or '',
                'Primary_System': result.primary_system,
                'Subsystem': result.subsystem or '',
                'All_Systems': '; '.join(result.all_systems),
                'Inflammation_Polarity': result.inflammation_polarity or '',
                'Confidence_Score': f"{result.confidence_score:.3f}",
                'Decision_Path': ' -> '.join(result.decision_path),
                'Classification_Date': classification_date,
                'Version': version
            }
            csv_data.append(row)
        
        # 写入CSV文件
        output_path = self.output_dir / filename
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.csv_fields)
            writer.writeheader()
            writer.writerows(csv_data)
        
        self.logger.info(f"Exported {len(csv_data)} results to {output_path}")
        return output_path
    
    def export_to_json(self,
                      results: List[ClassificationResult],
                      entries: List[BiologicalEntry],
                      filename: str = "classification_results.json",
                      version: str = "v8.0") -> Path:
        """
        导出分类结果到JSON文件
        
        Args:
            results: 分类结果列表
            entries: 生物学条目列表
            filename: 输出文件名
            version: 分类版本号
            
        Returns:
            输出文件路径
        """
        # 创建条目ID到条目的映射
        entry_map = {entry.id: entry for entry in entries}
        
        # 准备JSON数据
        export_data = {
            'metadata': {
                'version': version,
                'export_date': datetime.now().isoformat(),
                'total_entries': len(results),
                'source_counts': self._count_sources(entries)
            },
            'results': []
        }
        
        for result in results:
            entry = entry_map.get(result.entry_id)
            if not entry:
                continue
            
            result_data = {
                'entry': entry.to_dict(),
                'classification': result.to_dict()
            }
            export_data['results'].append(result_data)
        
        # 写入JSON文件
        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(export_data, jsonfile, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Exported {len(results)} results to {output_path}")
        return output_path
    
    def export_batch(self,
                    results_batches: List[List[ClassificationResult]],
                    entries_batches: List[List[BiologicalEntry]],
                    base_filename: str = "classification_batch",
                    version: str = "v8.0") -> List[Path]:
        """
        批量导出分类结果
        
        Args:
            results_batches: 分类结果批次列表
            entries_batches: 生物学条目批次列表
            base_filename: 基础文件名
            version: 分类版本号
            
        Returns:
            输出文件路径列表
        """
        output_paths = []
        
        for i, (results, entries) in enumerate(zip(results_batches, entries_batches)):
            filename = f"{base_filename}_{i+1:03d}.csv"
            output_path = self.export_to_csv(results, entries, filename, version)
            output_paths.append(output_path)
        
        self.logger.info(f"Exported {len(output_paths)} batch files")
        return output_paths
    
    def export_incremental(self,
                          new_results: List[ClassificationResult],
                          new_entries: List[BiologicalEntry],
                          existing_file: Optional[Path] = None,
                          version: str = "v8.0") -> Path:
        """
        增量导出分类结果
        
        Args:
            new_results: 新的分类结果
            new_entries: 新的生物学条目
            existing_file: 现有文件路径
            version: 分类版本号
            
        Returns:
            更新后的文件路径
        """
        if existing_file and existing_file.exists():
            # 读取现有数据
            existing_df = pd.read_csv(existing_file)
            existing_ids = set(existing_df['ID'].tolist())
            
            # 过滤新数据，只保留不存在的条目
            filtered_results = []
            filtered_entries = []
            entry_map = {entry.id: entry for entry in new_entries}
            
            for result in new_results:
                if result.entry_id not in existing_ids:
                    filtered_results.append(result)
                    if result.entry_id in entry_map:
                        filtered_entries.append(entry_map[result.entry_id])
            
            if not filtered_results:
                self.logger.info("No new results to add")
                return existing_file
            
            # 导出新数据到临时文件
            temp_file = self.output_dir / "temp_incremental.csv"
            self.export_to_csv(filtered_results, filtered_entries, 
                             temp_file.name, version)
            
            # 合并数据
            new_df = pd.read_csv(temp_file)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            
            # 写入原文件
            combined_df.to_csv(existing_file, index=False)
            
            # 清理临时文件
            temp_file.unlink()
            
            self.logger.info(f"Added {len(filtered_results)} new results to {existing_file}")
            return existing_file
        else:
            # 没有现有文件，直接导出
            filename = "classification_results_incremental.csv"
            return self.export_to_csv(new_results, new_entries, filename, version)
    
    def export_by_system(self,
                        results: List[ClassificationResult],
                        entries: List[BiologicalEntry],
                        version: str = "v8.0") -> Dict[str, Path]:
        """
        按系统分别导出分类结果
        
        Args:
            results: 分类结果列表
            entries: 生物学条目列表
            version: 分类版本号
            
        Returns:
            系统名到文件路径的映射
        """
        # 按系统分组
        system_groups = {}
        entry_map = {entry.id: entry for entry in entries}
        
        for result in results:
            system = result.primary_system
            if system not in system_groups:
                system_groups[system] = []
            system_groups[system].append(result)
        
        # 为每个系统导出文件
        output_paths = {}
        for system, system_results in system_groups.items():
            # 获取对应的条目
            system_entries = []
            for result in system_results:
                if result.entry_id in entry_map:
                    system_entries.append(entry_map[result.entry_id])
            
            # 生成文件名
            system_letter = system_results[0].get_system_letter()
            filename = f"classification_system_{system_letter}.csv"
            
            # 导出
            output_path = self.export_to_csv(system_results, system_entries, 
                                           filename, version)
            output_paths[system] = output_path
        
        self.logger.info(f"Exported results for {len(system_groups)} systems")
        return output_paths
    
    def export_summary_metadata(self,
                               results: List[ClassificationResult],
                               entries: List[BiologicalEntry],
                               version: str = "v8.0") -> Path:
        """
        导出分类结果的汇总元数据
        
        Args:
            results: 分类结果列表
            entries: 生物学条目列表
            version: 分类版本号
            
        Returns:
            元数据文件路径
        """
        # 计算统计信息
        system_counts = {}
        source_counts = self._count_sources(entries)
        inflammation_counts = {}
        subsystem_counts = {}
        
        for result in results:
            # 系统统计
            system = result.primary_system
            system_counts[system] = system_counts.get(system, 0) + 1
            
            # 炎症极性统计
            if result.inflammation_polarity:
                polarity = result.inflammation_polarity
                inflammation_counts[polarity] = inflammation_counts.get(polarity, 0) + 1
            
            # 子系统统计
            if result.subsystem:
                subsystem = result.subsystem
                subsystem_counts[subsystem] = subsystem_counts.get(subsystem, 0) + 1
        
        # 创建元数据
        metadata = {
            'export_info': {
                'version': version,
                'export_date': datetime.now().isoformat(),
                'total_entries': len(results)
            },
            'system_distribution': system_counts,
            'source_distribution': source_counts,
            'inflammation_distribution': inflammation_counts,
            'subsystem_distribution': subsystem_counts,
            'quality_metrics': {
                'classified_percentage': (len([r for r in results if not r.is_unclassified()]) / len(results)) * 100,
                'average_confidence': sum(r.confidence_score for r in results) / len(results),
                'inflammation_annotated_percentage': (len([r for r in results if r.has_inflammation_annotation()]) / len(results)) * 100
            }
        }
        
        # 写入元数据文件
        output_path = self.output_dir / "classification_metadata.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Exported metadata to {output_path}")
        return output_path
    
    def _count_sources(self, entries: List[BiologicalEntry]) -> Dict[str, int]:
        """计算数据源分布"""
        source_counts = {}
        for entry in entries:
            source = entry.source
            source_counts[source] = source_counts.get(source, 0) + 1
        return source_counts
    
    def validate_export(self, file_path: Path) -> Dict[str, Any]:
        """
        验证导出文件的完整性
        
        Args:
            file_path: 导出文件路径
            
        Returns:
            验证结果
        """
        validation_result = {
            'file_exists': file_path.exists(),
            'file_size': 0,
            'row_count': 0,
            'required_fields_present': False,
            'errors': []
        }
        
        if not file_path.exists():
            validation_result['errors'].append("File does not exist")
            return validation_result
        
        try:
            # 检查文件大小
            validation_result['file_size'] = file_path.stat().st_size
            
            # 读取CSV文件
            df = pd.read_csv(file_path)
            validation_result['row_count'] = len(df)
            
            # 检查必需字段
            required_fields = ['ID', 'Name', 'Primary_System', 'Source']
            missing_fields = [field for field in required_fields if field not in df.columns]
            
            if not missing_fields:
                validation_result['required_fields_present'] = True
            else:
                validation_result['errors'].append(f"Missing required fields: {missing_fields}")
            
            # 检查数据完整性
            if df['ID'].isnull().any():
                validation_result['errors'].append("Found null IDs")
            
            if df['Primary_System'].isnull().any():
                validation_result['errors'].append("Found null Primary_System values")
            
        except Exception as e:
            validation_result['errors'].append(f"Error reading file: {str(e)}")
        
        return validation_result