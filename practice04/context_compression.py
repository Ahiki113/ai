"""
LLM对话上下文压缩脚本 - 自动总结长对话历史

教学目标：
1. 学习聊天记录总结与压缩技术
2. 掌握上下文长度管理策略
3. 理解对话历史优化方法
4. 实现智能上下文压缩机制
"""
import os
import sys
import json
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
        'temperature': float(os.getenv('LLM_TEMPERATURE', 0.3)),  # 总结用较低温度
        'max_tokens': int(os.getenv('LLM_MAX_TOKENS', 2000)),
        'stream': True,
        'max_turns': 5,           # 超过5轮触发总结
        'max_context_length': 3000  # 上下文超过3K字符触发总结
    }
    return config

def calculate_context_length(messages):
    """计算上下文总长度"""
    total_length = 0
    for msg in messages:
        total_length += len(msg.get('content', ''))
    return total_length

def summarize_conversation(messages):
    """调用LLM总结对话历史"""
    config = load_config()
    
    # 构建总结提示词
    conversation_text = "\n".join([
        f"{msg['role']}: {msg['content']}" 
        for msg in messages
    ])
    
    summary_prompt = f"""请总结以下对话内容，提取关键信息和讨论要点：

{conversation_text}

总结要求：
1. 保持核心信息完整
2. 去除冗余内容
3. 用简洁的语言概括
4. 保留关键决策和结论
"""
    
    url = f"{config['base_url']}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": config['model'],
        "messages": [{"role": "user", "content": summary_prompt}],
        "temperature": 0.3,
        "max_tokens": 500
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"\n❌ 总结失败: {str(e)}")
        return None

def compress_context(messages):
    """
    压缩上下文：前75%内容总结压缩，最后30%保留原文
    
    策略：
    1. 计算总消息数
    2. 将消息分为两部分：需要总结的部分 + 需要保留的部分
    3. 对需要总结的部分调用LLM进行总结
    4. 返回：[总结消息] + [保留的原始消息]
    """
    if len(messages) <= 2:
        return messages
    
    # 计算分割点：保留最后30%的消息
    split_index = int(len(messages) * 0.7)
    
    # 需要总结的部分（前70%）
    messages_to_summarize = messages[:split_index]
    # 需要保留的部分（后30%）
    messages_to_keep = messages[split_index:]
    
    print("\n🔄 正在总结对话历史...")
    summary = summarize_conversation(messages_to_summarize)
    
    if summary:
        # 创建总结消息
        summary_message = {
            "role": "system",
            "content": f"对话总结：{summary}"
        }
        # 返回压缩后的上下文
        compressed = [summary_message] + messages_to_keep
        print(f"✅ 上下文压缩完成：原始{len(messages)}条 → 压缩后{len(compressed)}条")
        return compressed
    else:
        # 如果总结失败，保留原始消息
        return messages

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
            stream=True
        )
        response.raise_for_status()
        
        full_response = ""
        print("LLM：", end="", flush=True)
        
        for chunk in response.iter_lines(chunk_size=1024):
            if chunk:
                chunk_str = chunk.decode('utf-8').strip()
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
    """主函数 - 带上下文压缩的终端交互式聊天"""
    print("=== LLM 上下文压缩对话程序 ===")
    print("📌 输入消息后按回车发送")
    print("📌 按 Ctrl+C 退出程序")
    print("📌 自动总结：超过5轮对话或上下文超过3K字符时触发")
    print("==============================\n")
    
    config = load_config()
    print(f"已连接到: {config['base_url']}")
    print(f"使用模型: {config['model']}")
    print(f"总结阈值: {config['max_turns']}轮 或 {config['max_context_length']}字符\n")
    
    signal.signal(signal.SIGINT, signal_handler)
    
    history_messages = []
    turn_count = 0
    
    try:
        while True:
            try:
                user_input = input("你：")
            except KeyboardInterrupt:
                print("\n\n👋 感谢使用！对话结束。")
                break
            
            if not user_input.strip():
                print("⚠️ 请输入内容")
                continue
            
            history_messages.append({
                "role": "user", 
                "content": user_input
            })
            
            turn_count += 1
            
            # 检查是否需要压缩上下文
            context_length = calculate_context_length(history_messages)
            should_compress = False
            
            if turn_count > config['max_turns']:
                print(f"\n⚠️ 检测到超过{config['max_turns']}轮对话，触发上下文压缩")
                should_compress = True
            elif context_length > config['max_context_length']:
                print(f"\n⚠️ 检测到上下文长度({context_length}字符)超过{config['max_context_length']}，触发上下文压缩")
                should_compress = True
            
            if should_compress:
                history_messages = compress_context(history_messages)
                turn_count = 0  # 重置轮次计数
            
            # 显示当前上下文状态
            current_length = calculate_context_length(history_messages)
            print(f"\n📊 当前上下文：{len(history_messages)}条消息，{current_length}字符")
            
            # 获取流式响应
            response = stream_chat_response(history_messages)
            
            history_messages.append({
                "role": "assistant",
                "content": response
            })
            
    except Exception as e:
        print(f"\n程序异常退出: {str(e)}")

if __name__ == "__main__":
    main()
