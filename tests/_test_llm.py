#!/usr/bin/env python3
"""Quick connectivity check for the active LLM client."""

import os


def load_env() -> None:
    env_file = ".env"
    if not os.path.exists(env_file):
        return

    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()


def main() -> None:
    load_env()

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if api_key:
        print(f"API Key: 已设置 ({api_key[:8]}...)")
    else:
        print("API Key: 未设置")

    try:
        from src.agent.llm_client import create_llm_integration

        llm = create_llm_integration()
        print(f"模型: {llm.model}")
        print("发送测试请求...")
        result = llm._generate_content("请只回复：OK")
        print(f"LLM 响应: {result[:100]}")
    except Exception as exc:
        import traceback

        print(f"失败: {exc}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
