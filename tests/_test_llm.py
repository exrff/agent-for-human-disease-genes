#!/usr/bin/env python3
"""快速测试 LLM 连通性"""
import os, sys

# 手动加载 .env
env_file = '.env'
if os.path.exists(env_file):
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()

api_key = os.getenv('DASHSCOPE_API_KEY')
print(f"API Key: {'已设置 (' + api_key[:8] + '...)' if api_key else '未设置！'}")

try:
    from src.agent.llm_integration import create_llm_integration
    llm = create_llm_integration()
    print(f"模型: {llm.model}")
    print("发送测试请求...")
    result = llm._generate_content("请回复：OK")
    print(f"✅ LLM 响应: {result[:100]}")
except Exception as e:
    import traceback
    print(f"❌ 失败: {e}")
    traceback.print_exc()
