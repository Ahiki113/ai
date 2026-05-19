"""
LLM对话脚本 - 读取.env配置，使用requests库访问OpenAI兼容协议的LLM
"""
import os
import json
from dotenv import load_dotenv
import requests

def load_config():
    """加载配置文件"""
    # 加载.env文件（修复路径问题，确保从项目根目录加载）
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

    # 读取配置（修复默认URL，去掉/v1，避免重复拼接）
    config = {
        'base_url': os.getenv('LLM_BASE_URL', 'http://127.0.0.1:1234').rstrip('/'),
        'model': os.getenv('LLM_MODEL', 'gemma-3-4b-it'),
        'api_key': os.getenv('LLM_API_KEY', 'sk-no-key-required'),
        'temperature': float(os.getenv('LLM_TEMPERATURE', 0.7)),
        'max_tokens': int(os.getenv('LLM_MAX_TOKENS', 1000))
    }
    return config

def chat_with_llm(messages):
    """与LLM对话"""
    config = load_config()
    
    # 修复URL拼接，避免重复/v1
    url = "http://127.0.0.1:1234/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": config['model'],
        "messages": messages,
        "temperature": config['temperature'],
        "max_tokens": config['max_tokens']
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        return f"LLM: 错误：HTTP错误 - {e}\n错误详情：{response.text if 'response' in locals() else '无响应'}"
    except Exception as e:
        return f"LLM: 错误：{str(e)}"

def main():
    print("=== LLM 对话程序 ===")
    config = load_config()
    print(f"已加载配置：\n- 服务地址：{config['base_url']}\n- 模型：{config['model']}\n")
    
    while True:
        user_input = input("你：")
        if user_input.lower() in ["exit", "quit", "退出"]:
            print("对话结束")
            break
        messages = [{"role": "user", "content": user_input}]
        reply = chat_with_llm(messages)
        print(f"LLM：{reply}\n")

if __name__ == "__main__":
    main()