"""
数据质量检查器

验证GO和KEGG文件格式，检查数据完整性和一致性，处理缺失数据和异常值。
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Any
from pathlib import Path
from collections import defaultdict, Counter
import json
from datetime import datetime

# 设置日志
logger = logging.getLogger(__name__)


@dataclass
class DataQualityIssue:
    """数据质量问题记录"""
    
    issue_type: str  # 问题类型: 'format', 'missing', 'invalid', 'inconsistent'
    severity: str    # 严重程度: 'error', 'warning', 'info'
    source_file: str # 源文件路径
    line_number: Optional[int] = None
    entry_id: Optional[str] = None
    field_name: Optional[str] = None
    description: str = ""
    suggested_fix: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'issue_type': self.issue_type,
            'severity': self.severity,
            'source_file': self.source_file,
            'line_number': self.line_number,
            'entry_id': self.entry_id,
            'field_name': self.field_name,
            'description': self.description,
            'suggested_fix': self.suggested_fix,
            'metadata': self.metadata
        }


@dataclass
class DataQualityReport:
    """数据质量报告"""
    
    report_id: str
    timestamp: datetime
    source_files: List[str]
    total_entries: int = 0
    valid_entries: int = 0
    issues: List[DataQualityIssue] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    
    def add_issue(self, issue: DataQualityIssue):
        """添加质量问题"""
        self.issues.append(issue)
    
    def get_issues_by_severity(self, severity: str) -> List[DataQualityIssue]:
        """按严重程度获取问题"""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def get_issues_by_type(self, issue_type: str) -> List[DataQualityIssue]:
        """按类型获取问题"""
        return [issue for issue in self.issues if issue.issue_type == issue_type]
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """获取摘要统计"""
        issue_counts = Counter(issue.severity for issue in self.issues)
        type_counts = Counter(issue.issue_type for issue in self.issues)
        
        return {
            'total_issues': len(self.issues),
            'error_count': issue_counts.get('error', 0),
            'warning_count': issue_counts.get('warning', 0),
            'info_count': issue_counts.get('info', 0),
            'issue_types': dict(type_counts),
            'data_quality_score': self.calculate_quality_score(),
            'completeness_rate': self.valid_entries / self.total_entries if self.total_entries > 0 else 0
        }
    
    def calculate_quality_score(self) -> float:
        """计算数据质量分数 (0-100)"""
        if self.total_entries == 0:
            return 0.0
        
        # 基础分数基于有效条目比例
        base_score = (self.valid_entries / self.total_entries) * 100
        
        # 根据问题严重程度扣分
        error_penalty = len(self.get_issues_by_severity('error')) * 5
        warning_penalty = len(self.get_issues_by_severity('warning')) * 2
        
        final_score = max(0, base_score - error_penalty - warning_penalty)
        return min(100, final_score)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'report_id': self.report_id,
            'timestamp': self.timestamp.isoformat(),
            'source_files': self.source_files,
            'total_entries': self.total_entries,
            'valid_entries': self.valid_entries,
            'issues': [issue.to_dict() for issue in self.issues],
            'statistics': self.statistics,
            'recommendations': self.recommendations,
            'summary': self.get_summary_statistics()
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class DataQualityChecker:
    """
    数据质量检查器
    
    验证GO和KEGG文件格式，检查数据完整性和一致性。
    """
    
    def __init__(self):
        """初始化数据质量检查器"""
        self.current_report: Optional[DataQualityReport] = None
        
        # GO文件格式规范
        self.go_required_fields = {'id', 'name', 'namespace'}
        self.go_valid_namespaces = {'biological_process', 'molecular_function', 'cellular_component'}
        self.go_id_pattern = re.compile(r'^GO:\d{7}$')
        
        # KEGG文件格式规范
        self.kegg_id_pattern = re.compile(r'^\d{4,5}$')
        self.kegg_line_patterns = {
            'class_a': re.compile(r'^A'),
            'class_b': re.compile(r'^B  '),
            'pathway': re.compile(r'^C    ')
        }
    
    def check_go_file_quality(self, go_file_path: str) -> DataQualityReport:
        """
        检查GO文件质量
        
        Args:
            go_file_path: GO文件路径
            
        Returns:
            数据质量报告
        """
        logger.info(f"开始检查GO文件质量: {go_file_path}")
        
        # 初始化报告
        report = DataQualityReport(
            report_id=f"go_quality_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now(),
            source_files=[go_file_path]
        )
        self.current_report = report
        
        # 检查文件存在性
        if not Path(go_file_path).exists():
            report.add_issue(DataQualityIssue(
                issue_type='missing',
                severity='error',
                source_file=go_file_path,
                description=f"GO文件不存在: {go_file_path}",
                suggested_fix="确保文件路径正确且文件存在"
            ))
            return report
        
        # 检查文件格式和内容
        self._check_go_file_format(go_file_path, report)
        self._check_go_content_quality(go_file_path, report)
        
        # 生成建议
        self._generate_go_recommendations(report)
        
        logger.info(f"GO文件质量检查完成，发现 {len(report.issues)} 个问题")
        return report
    
    def check_kegg_file_quality(self, kegg_file_path: str) -> DataQualityReport:
        """
        检查KEGG文件质量
        
        Args:
            kegg_file_path: KEGG文件路径
            
        Returns:
            数据质量报告
        """
        logger.info(f"开始检查KEGG文件质量: {kegg_file_path}")
        
        # 初始化报告
        report = DataQualityReport(
            report_id=f"kegg_quality_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now(),
            source_files=[kegg_file_path]
        )
        self.current_report = report
        
        # 检查文件存在性
        if not Path(kegg_file_path).exists():
            report.add_issue(DataQualityIssue(
                issue_type='missing',
                severity='error',
                source_file=kegg_file_path,
                description=f"KEGG文件不存在: {kegg_file_path}",
                suggested_fix="确保文件路径正确且文件存在"
            ))
            return report
        
        # 检查文件格式和内容
        self._check_kegg_file_format(kegg_file_path, report)
        self._check_kegg_content_quality(kegg_file_path, report)
        
        # 生成建议
        self._generate_kegg_recommendations(report)
        
        logger.info(f"KEGG文件质量检查完成，发现 {len(report.issues)} 个问题")
        return report
    
    def _check_go_file_format(self, file_path: str, report: DataQualityReport):
        """检查GO文件格式"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                current_term = {}
                line_number = 0
                term_count = 0
                valid_term_count = 0
                
                for line in f:
                    line_number += 1
                    line = line.strip()
                    
                    # 跳过空行和注释
                    if not line or line.startswith('!'):
                        continue
                    
                    # 检查条目开始
                    if line == '[Term]':
                        if current_term:
                            # 验证前一个条目
                            if self._validate_go_term(current_term, report, file_path):
                                valid_term_count += 1
                            term_count += 1
                        current_term = {}
                        continue
                    
                    # 检查其他节开始
                    if line.startswith('[') and line.endswith(']'):
                        if current_term:
                            if self._validate_go_term(current_term, report, file_path):
                                valid_term_count += 1
                            term_count += 1
                            current_term = {}
                        continue
                    
                    # 解析条目属性
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if key in current_term:
                            # 处理多值字段
                            if not isinstance(current_term[key], list):
                                current_term[key] = [current_term[key]]
                            current_term[key].append(value)
                        else:
                            current_term[key] = value
                    else:
                        # 格式错误的行
                        report.add_issue(DataQualityIssue(
                            issue_type='format',
                            severity='warning',
                            source_file=file_path,
                            line_number=line_number,
                            description=f"行格式不正确，缺少冒号分隔符: {line[:50]}...",
                            suggested_fix="确保每行都有正确的 'key: value' 格式"
                        ))
                
                # 处理最后一个条目
                if current_term:
                    if self._validate_go_term(current_term, report, file_path):
                        valid_term_count += 1
                    term_count += 1
                
                report.total_entries = term_count
                report.valid_entries = valid_term_count
                
        except UnicodeDecodeError as e:
            report.add_issue(DataQualityIssue(
                issue_type='format',
                severity='error',
                source_file=file_path,
                description=f"文件编码错误: {e}",
                suggested_fix="确保文件使用UTF-8编码"
            ))
        except Exception as e:
            report.add_issue(DataQualityIssue(
                issue_type='format',
                severity='error',
                source_file=file_path,
                description=f"文件读取错误: {e}",
                suggested_fix="检查文件是否损坏或权限问题"
            ))
    
    def _validate_go_term(self, term_dict: Dict, report: DataQualityReport, file_path: str) -> bool:
        """验证GO条目"""
        is_valid = True
        term_id = term_dict.get('id', 'unknown')
        
        # 检查必需字段
        for field in self.go_required_fields:
            if field not in term_dict or not term_dict[field]:
                report.add_issue(DataQualityIssue(
                    issue_type='missing',
                    severity='error',
                    source_file=file_path,
                    entry_id=term_id,
                    field_name=field,
                    description=f"缺少必需字段: {field}",
                    suggested_fix=f"为条目 {term_id} 添加 {field} 字段"
                ))
                is_valid = False
        
        # 验证ID格式
        if 'id' in term_dict:
            if not self.go_id_pattern.match(term_dict['id']):
                report.add_issue(DataQualityIssue(
                    issue_type='invalid',
                    severity='error',
                    source_file=file_path,
                    entry_id=term_id,
                    field_name='id',
                    description=f"GO ID格式不正确: {term_dict['id']}",
                    suggested_fix="GO ID应该是 'GO:' 后跟7位数字的格式"
                ))
                is_valid = False
        
        # 验证命名空间
        if 'namespace' in term_dict:
            if term_dict['namespace'] not in self.go_valid_namespaces:
                report.add_issue(DataQualityIssue(
                    issue_type='invalid',
                    severity='error',
                    source_file=file_path,
                    entry_id=term_id,
                    field_name='namespace',
                    description=f"无效的命名空间: {term_dict['namespace']}",
                    suggested_fix=f"命名空间应该是: {', '.join(self.go_valid_namespaces)}"
                ))
                is_valid = False
        
        # 检查名称长度
        if 'name' in term_dict:
            name_length = len(term_dict['name'])
            if name_length > 200:
                report.add_issue(DataQualityIssue(
                    issue_type='invalid',
                    severity='warning',
                    source_file=file_path,
                    entry_id=term_id,
                    field_name='name',
                    description=f"条目名称过长 ({name_length} 字符)",
                    suggested_fix="考虑缩短条目名称或检查是否有格式错误"
                ))
            elif name_length < 3:
                report.add_issue(DataQualityIssue(
                    issue_type='invalid',
                    severity='warning',
                    source_file=file_path,
                    entry_id=term_id,
                    field_name='name',
                    description=f"条目名称过短 ({name_length} 字符)",
                    suggested_fix="检查条目名称是否完整"
                ))
        
        return is_valid
    
    def _check_go_content_quality(self, file_path: str, report: DataQualityReport):
        """检查GO内容质量"""
        # 统计信息
        namespace_counts = defaultdict(int)
        obsolete_count = 0
        definition_missing = 0
        synonym_counts = defaultdict(int)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                current_term = {}
                
                for line in f:
                    line = line.strip()
                    
                    if line == '[Term]':
                        if current_term:
                            self._analyze_go_term_content(current_term, namespace_counts, 
                                                        obsolete_count, definition_missing, 
                                                        synonym_counts, report, file_path)
                        current_term = {}
                        continue
                    
                    if line.startswith('[') and line.endswith(']'):
                        if current_term:
                            self._analyze_go_term_content(current_term, namespace_counts, 
                                                        obsolete_count, definition_missing, 
                                                        synonym_counts, report, file_path)
                        current_term = {}
                        continue
                    
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        current_term[key] = value
                
                # 处理最后一个条目
                if current_term:
                    self._analyze_go_term_content(current_term, namespace_counts, 
                                                obsolete_count, definition_missing, 
                                                synonym_counts, report, file_path)
        
        except Exception as e:
            report.add_issue(DataQualityIssue(
                issue_type='format',
                severity='error',
                source_file=file_path,
                description=f"内容分析错误: {e}",
                suggested_fix="检查文件格式和内容完整性"
            ))
        
        # 保存统计信息
        report.statistics.update({
            'namespace_distribution': dict(namespace_counts),
            'obsolete_terms': obsolete_count,
            'missing_definitions': definition_missing,
            'synonym_distribution': dict(synonym_counts)
        })
    
    def _analyze_go_term_content(self, term_dict: Dict, namespace_counts: defaultdict, 
                               obsolete_count: int, definition_missing: int, 
                               synonym_counts: defaultdict, report: DataQualityReport, 
                               file_path: str):
        """分析GO条目内容"""
        term_id = term_dict.get('id', 'unknown')
        
        # 统计命名空间
        if 'namespace' in term_dict:
            namespace_counts[term_dict['namespace']] += 1
        
        # 检查过时条目
        if term_dict.get('is_obsolete') == 'true':
            obsolete_count += 1
        
        # 检查定义
        if 'def' not in term_dict or not term_dict['def']:
            definition_missing += 1
            report.add_issue(DataQualityIssue(
                issue_type='missing',
                severity='warning',
                source_file=file_path,
                entry_id=term_id,
                field_name='def',
                description="缺少条目定义",
                suggested_fix="为条目添加详细定义"
            ))
        
        # 统计同义词
        synonym_count = 0
        for key in term_dict:
            if key == 'synonym':
                synonym_count += 1
        synonym_counts[synonym_count] += 1
    
    def _check_kegg_file_format(self, file_path: str, report: DataQualityReport):
        """检查KEGG文件格式"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                line_number = 0
                pathway_count = 0
                valid_pathway_count = 0
                current_class_a = ""
                current_class_b = ""
                
                for line in f:
                    line_number += 1
                    line = line.rstrip()
                    
                    # 跳过空行和注释
                    if not line or line.startswith('!') or line.startswith('+'):
                        continue
                    
                    # 检查Class A行
                    if line.startswith('A'):
                        current_class_a = line[1:].strip()
                        if not current_class_a:
                            report.add_issue(DataQualityIssue(
                                issue_type='missing',
                                severity='warning',
                                source_file=file_path,
                                line_number=line_number,
                                description="Class A名称为空",
                                suggested_fix="为Class A行提供有效的分类名称"
                            ))
                        continue
                    
                    # 检查Class B行
                    if line.startswith('B  '):
                        current_class_b = line[3:].strip()
                        if not current_class_b:
                            report.add_issue(DataQualityIssue(
                                issue_type='missing',
                                severity='warning',
                                source_file=file_path,
                                line_number=line_number,
                                description="Class B名称为空",
                                suggested_fix="为Class B行提供有效的分类名称"
                            ))
                        continue
                    
                    # 检查通路行
                    if line.startswith('C    '):
                        pathway_info = line[6:].strip()
                        pathway_count += 1
                        
                        if self._validate_kegg_pathway(pathway_info, current_class_a, 
                                                     current_class_b, report, file_path, 
                                                     line_number):
                            valid_pathway_count += 1
                        continue
                    
                    # 检查未识别的行格式
                    if line.strip():
                        report.add_issue(DataQualityIssue(
                            issue_type='format',
                            severity='info',
                            source_file=file_path,
                            line_number=line_number,
                            description=f"未识别的行格式: {line[:50]}...",
                            suggested_fix="检查行是否符合KEGG层次结构格式"
                        ))
                
                report.total_entries = pathway_count
                report.valid_entries = valid_pathway_count
                
        except UnicodeDecodeError as e:
            report.add_issue(DataQualityIssue(
                issue_type='format',
                severity='error',
                source_file=file_path,
                description=f"文件编码错误: {e}",
                suggested_fix="确保文件使用UTF-8编码"
            ))
        except Exception as e:
            report.add_issue(DataQualityIssue(
                issue_type='format',
                severity='error',
                source_file=file_path,
                description=f"文件读取错误: {e}",
                suggested_fix="检查文件是否损坏或权限问题"
            ))
    
    def _validate_kegg_pathway(self, pathway_info: str, class_a: str, class_b: str, 
                             report: DataQualityReport, file_path: str, 
                             line_number: int) -> bool:
        """验证KEGG通路"""
        is_valid = True
        
        # 解析通路ID和名称
        match = re.match(r'^(\d{4,5})\s+(.+)$', pathway_info)
        if not match:
            report.add_issue(DataQualityIssue(
                issue_type='format',
                severity='error',
                source_file=file_path,
                line_number=line_number,
                description=f"通路格式不正确: {pathway_info}",
                suggested_fix="通路行应该是 'ID 名称' 的格式"
            ))
            return False
        
        pathway_id = match.group(1)
        pathway_name = match.group(2).strip()
        
        # 验证通路ID格式
        if not self.kegg_id_pattern.match(pathway_id):
            report.add_issue(DataQualityIssue(
                issue_type='invalid',
                severity='error',
                source_file=file_path,
                line_number=line_number,
                entry_id=f"KEGG:{pathway_id}",
                field_name='id',
                description=f"KEGG通路ID格式不正确: {pathway_id}",
                suggested_fix="通路ID应该是4-5位数字"
            ))
            is_valid = False
        
        # 检查通路名称
        if not pathway_name:
            report.add_issue(DataQualityIssue(
                issue_type='missing',
                severity='error',
                source_file=file_path,
                line_number=line_number,
                entry_id=f"KEGG:{pathway_id}",
                field_name='name',
                description="通路名称为空",
                suggested_fix="为通路提供有效的名称"
            ))
            is_valid = False
        elif len(pathway_name) > 200:
            report.add_issue(DataQualityIssue(
                issue_type='invalid',
                severity='warning',
                source_file=file_path,
                line_number=line_number,
                entry_id=f"KEGG:{pathway_id}",
                field_name='name',
                description=f"通路名称过长 ({len(pathway_name)} 字符)",
                suggested_fix="考虑缩短通路名称"
            ))
        
        # 检查层次信息
        if not class_a:
            report.add_issue(DataQualityIssue(
                issue_type='missing',
                severity='warning',
                source_file=file_path,
                line_number=line_number,
                entry_id=f"KEGG:{pathway_id}",
                field_name='class_a',
                description="缺少Class A分类信息",
                suggested_fix="确保通路在正确的Class A分类下"
            ))
        
        if not class_b:
            report.add_issue(DataQualityIssue(
                issue_type='missing',
                severity='warning',
                source_file=file_path,
                line_number=line_number,
                entry_id=f"KEGG:{pathway_id}",
                field_name='class_b',
                description="缺少Class B分类信息",
                suggested_fix="确保通路在正确的Class B分类下"
            ))
        
        return is_valid
    
    def _check_kegg_content_quality(self, file_path: str, report: DataQualityReport):
        """检查KEGG内容质量"""
        # 统计信息
        class_a_counts = defaultdict(int)
        class_b_counts = defaultdict(int)
        pathway_name_lengths = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                current_class_a = ""
                current_class_b = ""
                
                for line in f:
                    line = line.rstrip()
                    
                    if line.startswith('A'):
                        current_class_a = line[1:].strip()
                        continue
                    
                    if line.startswith('B  '):
                        current_class_b = line[3:].strip()
                        continue
                    
                    if line.startswith('C    '):
                        pathway_info = line[6:].strip()
                        match = re.match(r'^(\d{4,5})\s+(.+)$', pathway_info)
                        if match:
                            pathway_name = match.group(2).strip()
                            pathway_name_lengths.append(len(pathway_name))
                            
                            if current_class_a:
                                class_a_counts[current_class_a] += 1
                            if current_class_b:
                                class_b_counts[current_class_b] += 1
        
        except Exception as e:
            report.add_issue(DataQualityIssue(
                issue_type='format',
                severity='error',
                source_file=file_path,
                description=f"内容分析错误: {e}",
                suggested_fix="检查文件格式和内容完整性"
            ))
        
        # 保存统计信息
        report.statistics.update({
            'class_a_distribution': dict(class_a_counts),
            'class_b_distribution': dict(class_b_counts),
            'pathway_name_length_stats': {
                'min': min(pathway_name_lengths) if pathway_name_lengths else 0,
                'max': max(pathway_name_lengths) if pathway_name_lengths else 0,
                'avg': sum(pathway_name_lengths) / len(pathway_name_lengths) if pathway_name_lengths else 0
            }
        })
    
    def _generate_go_recommendations(self, report: DataQualityReport):
        """生成GO文件建议"""
        recommendations = []
        
        error_count = len(report.get_issues_by_severity('error'))
        warning_count = len(report.get_issues_by_severity('warning'))
        
        if error_count > 0:
            recommendations.append(f"发现 {error_count} 个严重错误，需要立即修复以确保数据可用性")
        
        if warning_count > 0:
            recommendations.append(f"发现 {warning_count} 个警告，建议修复以提高数据质量")
        
        # 检查命名空间分布
        namespace_dist = report.statistics.get('namespace_distribution', {})
        if 'biological_process' not in namespace_dist:
            recommendations.append("未找到生物过程条目，请检查文件完整性")
        elif namespace_dist.get('biological_process', 0) < 1000:
            recommendations.append("生物过程条目数量较少，可能文件不完整")
        
        # 检查过时条目比例
        obsolete_count = report.statistics.get('obsolete_terms', 0)
        if obsolete_count > report.total_entries * 0.1:
            recommendations.append("过时条目比例较高，建议使用更新的GO版本")
        
        # 检查缺失定义
        missing_def = report.statistics.get('missing_definitions', 0)
        if missing_def > report.total_entries * 0.05:
            recommendations.append("较多条目缺少定义，可能影响分类准确性")
        
        report.recommendations = recommendations
    
    def _generate_kegg_recommendations(self, report: DataQualityReport):
        """生成KEGG文件建议"""
        recommendations = []
        
        error_count = len(report.get_issues_by_severity('error'))
        warning_count = len(report.get_issues_by_severity('warning'))
        
        if error_count > 0:
            recommendations.append(f"发现 {error_count} 个严重错误，需要立即修复以确保数据可用性")
        
        if warning_count > 0:
            recommendations.append(f"发现 {warning_count} 个警告，建议修复以提高数据质量")
        
        # 检查Class A分布
        class_a_dist = report.statistics.get('class_a_distribution', {})
        if 'Metabolism' not in class_a_dist:
            recommendations.append("未找到代谢相关通路，请检查文件完整性")
        
        # 检查通路数量
        if report.total_entries < 100:
            recommendations.append("通路数量较少，可能文件不完整")
        elif report.total_entries > 1000:
            recommendations.append("通路数量较多，处理时注意性能优化")
        
        report.recommendations = recommendations
    
    def check_data_consistency(self, go_file_path: str, kegg_file_path: str) -> DataQualityReport:
        """
        检查GO和KEGG数据的一致性
        
        Args:
            go_file_path: GO文件路径
            kegg_file_path: KEGG文件路径
            
        Returns:
            数据一致性报告
        """
        logger.info("开始检查数据一致性")
        
        # 初始化报告
        report = DataQualityReport(
            report_id=f"consistency_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now(),
            source_files=[go_file_path, kegg_file_path]
        )
        
        # 分别检查两个文件
        go_report = self.check_go_file_quality(go_file_path)
        kegg_report = self.check_kegg_file_quality(kegg_file_path)
        
        # 合并问题
        report.issues.extend(go_report.issues)
        report.issues.extend(kegg_report.issues)
        
        # 合并统计信息
        report.statistics.update({
            'go_statistics': go_report.statistics,
            'kegg_statistics': kegg_report.statistics,
            'go_total_entries': go_report.total_entries,
            'kegg_total_entries': kegg_report.total_entries,
            'go_valid_entries': go_report.valid_entries,
            'kegg_valid_entries': kegg_report.valid_entries
        })
        
        report.total_entries = go_report.total_entries + kegg_report.total_entries
        report.valid_entries = go_report.valid_entries + kegg_report.valid_entries
        
        # 生成一致性建议
        consistency_recommendations = []
        
        # 检查数据规模平衡
        go_ratio = go_report.total_entries / report.total_entries if report.total_entries > 0 else 0
        if go_ratio < 0.7:
            consistency_recommendations.append("GO条目比例较低，可能影响分类平衡性")
        elif go_ratio > 0.95:
            consistency_recommendations.append("KEGG通路比例较低，可能影响分类覆盖度")
        
        # 检查质量分数差异
        go_quality = go_report.calculate_quality_score()
        kegg_quality = kegg_report.calculate_quality_score()
        quality_diff = abs(go_quality - kegg_quality)
        
        if quality_diff > 20:
            consistency_recommendations.append(f"GO和KEGG数据质量差异较大 (差异: {quality_diff:.1f}分)")
        
        report.recommendations = consistency_recommendations
        
        logger.info(f"数据一致性检查完成，总计 {len(report.issues)} 个问题")
        return report
    
    def save_report(self, report: DataQualityReport, output_path: str):
        """
        保存质量报告
        
        Args:
            report: 数据质量报告
            output_path: 输出文件路径
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report.to_json())
            
            logger.info(f"质量报告已保存到: {output_path}")
            
        except Exception as e:
            logger.error(f"保存报告失败: {e}")
            raise