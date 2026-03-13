#!/usr/bin/env python3
"""
智能体日志系统
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


class AgentLogger:
    """智能体日志记录器"""
    
    def __init__(self, log_dir: str = "logs/agent"):
        """
        初始化日志记录器
        
        Args:
            log_dir: 日志目录
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建日志文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"agent_{timestamp}.log"
        self.json_log_file = self.log_dir / f"agent_{timestamp}.json"
        
        # 配置文本日志
        self.logger = logging.getLogger("DiseaseAnalysisAgent")
        self.logger.setLevel(logging.DEBUG)
        
        # 文件处理器
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # JSON 日志存储
        self.json_logs = []
    
    def log_step(self, step_name: str, status: str, details: Dict[str, Any] = None):
        """
        记录步骤日志
        
        Args:
            step_name: 步骤名称
            status: 状态 (started, completed, failed)
            details: 详细信息
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step_name,
            "status": status,
            "details": details or {}
        }
        
        self.json_logs.append(log_entry)
        
        # 文本日志
        if status == "started":
            self.logger.info(f"开始执行: {step_name}")
        elif status == "completed":
            self.logger.info(f"完成: {step_name}")
            if details:
                self.logger.debug(f"详情: {json.dumps(details, ensure_ascii=False, indent=2)}")
        elif status == "failed":
            self.logger.error(f"失败: {step_name}")
            if details:
                self.logger.error(f"错误详情: {json.dumps(details, ensure_ascii=False, indent=2)}")
    
    def log_decision(self, decision_point: str, decision: str, reasoning: str):
        """
        记录决策日志
        
        Args:
            decision_point: 决策点
            decision: 决策结果
            reasoning: 决策理由
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "decision",
            "decision_point": decision_point,
            "decision": decision,
            "reasoning": reasoning
        }
        
        self.json_logs.append(log_entry)
        self.logger.info(f"决策 [{decision_point}]: {decision} - {reasoning}")
    
    def log_metric(self, metric_name: str, value: Any, context: Dict[str, Any] = None):
        """
        记录指标日志
        
        Args:
            metric_name: 指标名称
            value: 指标值
            context: 上下文信息
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "metric",
            "metric": metric_name,
            "value": value,
            "context": context or {}
        }
        
        self.json_logs.append(log_entry)
        self.logger.info(f"指标 [{metric_name}]: {value}")
    
    def log_error(self, error_type: str, error_message: str, traceback: str = None):
        """
        记录错误日志
        
        Args:
            error_type: 错误类型
            error_message: 错误消息
            traceback: 堆栈跟踪
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "error",
            "error_type": error_type,
            "message": error_message,
            "traceback": traceback
        }
        
        self.json_logs.append(log_entry)
        self.logger.error(f"错误 [{error_type}]: {error_message}")
        if traceback:
            self.logger.error(f"堆栈跟踪:\n{traceback}")
    
    def save_json_log(self):
        """保存 JSON 格式的日志"""
        with open(self.json_log_file, 'w', encoding='utf-8') as f:
            json.dump(self.json_logs, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"JSON 日志已保存: {self.json_log_file}")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取日志摘要
        
        Returns:
            日志摘要字典
        """
        total_steps = len([log for log in self.json_logs if log.get("type") != "error"])
        completed_steps = len([log for log in self.json_logs 
                              if log.get("status") == "completed"])
        failed_steps = len([log for log in self.json_logs 
                           if log.get("status") == "failed"])
        errors = len([log for log in self.json_logs if log.get("type") == "error"])
        decisions = len([log for log in self.json_logs if log.get("type") == "decision"])
        
        return {
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "errors": errors,
            "decisions": decisions,
            "log_file": str(self.log_file),
            "json_log_file": str(self.json_log_file)
        }
    
    def generate_timeline(self) -> List[Dict[str, Any]]:
        """
        生成时间线
        
        Returns:
            时间线列表
        """
        timeline = []
        
        for log in self.json_logs:
            if log.get("step"):
                timeline.append({
                    "time": log["timestamp"],
                    "event": f"{log['step']} - {log['status']}",
                    "type": "step"
                })
            elif log.get("type") == "decision":
                timeline.append({
                    "time": log["timestamp"],
                    "event": f"决策: {log['decision_point']} → {log['decision']}",
                    "type": "decision"
                })
            elif log.get("type") == "error":
                timeline.append({
                    "time": log["timestamp"],
                    "event": f"错误: {log['error_type']}",
                    "type": "error"
                })
        
        return timeline
