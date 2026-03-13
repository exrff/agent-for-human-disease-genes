"""
配置模块测试

简单测试配置模块的基本功能。
"""

import sys
import os
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    get_settings, 
    default_classification_rules,
    VERSION,
    PROJECT_METADATA,
    get_version_info
)


def test_settings():
    """测试设置模块"""
    print("测试设置模块...")
    
    settings = get_settings()
    print(f"数据目录: {settings.data_dir}")
    print(f"本体目录: {settings.ontology_dir}")
    print(f"结果目录: {settings.results_dir}")
    print(f"置信度阈值: {settings.min_confidence_threshold}")
    print(f"启用子系统分类: {settings.enable_subsystem_classification}")
    print(f"启用炎症标注: {settings.enable_inflammation_annotation}")
    
    # 测试路径方法
    go_path = settings.get_go_basic_path()
    kegg_path = settings.get_kegg_hierarchy_path()
    print(f"GO文件路径: {go_path}")
    print(f"KEGG文件路径: {kegg_path}")
    
    print("设置模块测试通过 ✓\n")


def test_classification_rules():
    """测试分类规则模块"""
    print("测试分类规则模块...")
    
    rules = default_classification_rules
    
    # 测试系统模式
    print(f"System A 模式数量: {len(rules.system_a_patterns)}")
    print(f"System B 模式数量: {len(rules.system_b_patterns)}")
    print(f"System C 模式数量: {len(rules.system_c_patterns)}")
    
    # 测试模式匹配
    test_text = "DNA repair and genome stability"
    matches = rules.match_system_patterns(test_text, "A")
    print(f"测试文本 '{test_text}' 匹配System A模式: {len(matches)}个")
    
    # 测试炎症模式
    inflammation_text = "pro-inflammatory cytokine response"
    inflammation_matches = rules.match_inflammation_patterns(inflammation_text)
    print(f"炎症文本匹配结果: {list(inflammation_matches.keys())}")
    
    # 测试优先级
    systems = ["A", "B", "C"]
    sorted_systems = rules.sort_systems_by_priority(systems)
    print(f"系统优先级排序: {sorted_systems}")
    
    print("分类规则模块测试通过 ✓\n")


def test_version_info():
    """测试版本信息模块"""
    print("测试版本信息模块...")
    
    print(f"项目版本: {VERSION}")
    print(f"项目名称: {PROJECT_METADATA['name']}")
    print(f"项目描述: {PROJECT_METADATA['description']}")
    
    version_info = get_version_info()
    print(f"完整版本信息包含 {len(version_info)} 个部分")
    
    print("版本信息模块测试通过 ✓\n")


def test_integration():
    """集成测试"""
    print("执行集成测试...")
    
    # 测试配置组合使用
    settings = get_settings()
    rules = default_classification_rules
    
    # 模拟分类过程
    test_entries = [
        "DNA damage response and repair",
        "innate immune response to pathogen",
        "glucose metabolic process",
        "neural signal transmission",
        "reproductive behavior"
    ]
    
    for entry in test_entries:
        print(f"\n分析条目: {entry}")
        
        # 检查是否为排除术语
        if rules.is_excluded_term(entry):
            print("  -> 排除的通用术语")
            continue
        
        # 匹配各系统
        system_matches = {}
        for system in ["A", "B", "C", "D", "E"]:
            matches = rules.match_system_patterns(entry, system)
            if matches:
                system_matches[system] = len(matches)
        
        if system_matches:
            # 按优先级排序
            sorted_systems = rules.sort_systems_by_priority(list(system_matches.keys()))
            primary_system = sorted_systems[0]
            print(f"  -> 主要系统: System {primary_system}")
            print(f"  -> 所有匹配: {system_matches}")
        else:
            print("  -> 未匹配任何系统")
    
    print("\n集成测试通过 ✓")


if __name__ == "__main__":
    print("=" * 50)
    print("五大功能系统分类 - 配置模块测试")
    print("=" * 50)
    
    try:
        test_settings()
        test_classification_rules()
        test_version_info()
        test_integration()
        
        print("\n" + "=" * 50)
        print("所有测试通过！配置模块工作正常。")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)