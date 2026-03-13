"""
集成测试模块

提供端到端集成测试功能，验证整个系统的完整工作流程。
"""

from .test_end_to_end import EndToEndIntegrationTest

__all__ = ['EndToEndIntegrationTest']