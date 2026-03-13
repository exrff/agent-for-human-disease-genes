#!/usr/bin/env python3
"""
可视化 LangGraph 工作流
"""

from disease_analysis_agent import create_disease_analysis_graph


def visualize_workflow():
    """可视化工作流图"""
    try:
        # 创建工作流
        app = create_disease_analysis_graph()
        
        # 生成 Mermaid 图
        print("LangGraph 工作流图 (Mermaid 格式):")
        print("="*80)
        print(app.get_graph().draw_mermaid())
        print("="*80)
        
        # 如果安装了 graphviz，可以生成 PNG
        try:
            from IPython.display import Image, display
            display(Image(app.get_graph().draw_mermaid_png()))
            print("\n图片已生成！")
        except ImportError:
            print("\n提示: 安装 graphviz 和 IPython 可以生成 PNG 图片")
            print("pip install graphviz ipython")
        
    except Exception as e:
        print(f"可视化失败: {e}")


if __name__ == "__main__":
    visualize_workflow()
