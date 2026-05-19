"""
LLM流式对话脚本 - 支持流式输出、历史记录管理、终端交互
教学目标：学习流式响应处理、上下文管理、信号处理
"""
import os
import sys
import json
import time
import signal
from dotenv import load_dotenv
import requests

def load_config():
    """加载配置文件"""
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
    
    config = {
        'base_url': os.getenv('LLM_BASE_URL', 'http://127.0.0.1:1234').rstrip('/'),
        'model': os.getenv('LLM_MODEL', 'gemma-3-4b-it'),
        'api_key': os.getenv('LLM_API_KEY', 'sk-no-key-required'),
        'temperature': float(os.getenv('LLM_TEMPERATURE', 0.7)),
        'max_tokens': int(os.getenv('LLM_MAX_TOKENS', 2000)),
        'stream': True  # 启用流式输出
    }
    return config

def stream_chat_response(messages):
    """流式获取LLM响应"""
    config = load_config()
    
    url = f"{config['base_url']}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": config['model'],
        "messages": messages,
        "temperature": config['temperature'],
        "max_tokens": config['max_tokens'],
        "stream": config['stream']
    }

    try:
        response = requests.post(
            url, 
            json=data, 
            headers=headers, 
            timeout=60,
            stream=True  # 启用流式响应
        )
        response.raise_for_status()
        
        full_response = ""
        print("LLM：", end="", flush=True)
        
        # 逐块读取流式响应
        for chunk in response.iter_lines(chunk_size=1024):
            if chunk:
                chunk_str = chunk.decode('utf-8').strip()
                # 移除数据前缀
                if chunk_str.startswith('data: '):
                    chunk_str = chunk_str[6:]
                
                if chunk_str == '[DONE]':
                    break
                
                try:
                    chunk_data = json.loads(chunk_str)
                    if 'choices' in chunk_data and chunk_data['choices']:
                        delta = chunk_data['choices'][0].get('delta', {})
                        content = delta.get('content', '')
                        if content:
                            print(content, end="", flush=True)
                            full_response += content
                except json.JSONDecodeError:
                    continue
        
        print("\n")
        return full_response
        
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP错误 - {e}"
        print(f"\n❌ {error_msg}")
        return error_msg
    except requests.exceptions.ConnectionError:
        error_msg = "无法连接到服务器，请检查服务是否启动！"
        print(f"\n❌ {error_msg}")
        return error_msg
    except Exception as e:
        error_msg = f"错误：{str(e)}"
        print(f"\n❌ {error_msg}")
        return error_msg

def signal_handler(signal_num, frame):
    """信号处理函数 - 捕获Ctrl+C"""
    print("\n\n👋 感谢使用！对话结束。")
    sys.exit(0)

def main():
    """主函数 - 终端交互式聊天"""
    print("=== LLM 流式对话程序 ===")
    print("📌 输入消息后按回车发送")
    print("📌 按 Ctrl+C 退出程序")
    print("========================\n")
    
    config = load_config()
    print(f"已连接到: {config['base_url']}")
    print(f"使用模型: {config['model']}\n")
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    
    # 初始化历史消息列表
    history_messages = []
    
    try:
        while True:
            # 获取用户输入
            try:
                user_input = input("你：")
            except KeyboardInterrupt:
                print("\n\n👋 感谢使用！对话结束。")
                break
            
            if not user_input.strip():
                print("⚠️ 请输入内容")
                continue
            
            # 添加用户消息到历史
            history_messages.append({
                "role": "user", 
                "content": user_input
            })
            
            # 限制历史记录长度（保留最近10轮对话）
            if len(history_messages) > 20:  # 20条 = 10轮
                history_messages = history_messages[-20:]
            
            # 获取流式响应
            response = stream_chat_response(history_messages)
            
            # 添加助手回复到历史
            history_messages.append({
                "role": "assistant",
                "content": response
            })
            
    except Exception as e:
        print(f"\n程序异常退出: {str(e)}")

if __name__ == "__main__":
    main()
