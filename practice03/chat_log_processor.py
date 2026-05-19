"""
聊天记录处理器 - 支持5W信息提取和历史搜索

教学目标：
1. 学习关键信息提取技术（5W规则）
2. 掌握文件增量写入和日志管理
3. 理解历史记录搜索机制
4. 实现智能搜索触发逻辑
"""
import os
import sys
import json
import signal
import time
from dotenv import load_dotenv
import requests

# 日志文件路径
LOG_FILE_PATH = r"D:\llm_traeproject1\log.txt"

def load_config():
    """加载配置文件"""
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
    
    config = {
        'base_url': os.getenv('LLM_BASE_URL', 'http://127.0.0.1:1234').rstrip('/'),
        'model': os.getenv('LLM_MODEL', 'gemma-3-4b-it'),
        'api_key': os.getenv('LLM_API_KEY', 'sk-no-key-required'),
        'temperature': float(os.getenv('LLM_TEMPERATURE', 0.7)),
        'max_tokens': int(os.getenv('LLM_MAX_TOKENS', 2000)),
        'stream': True,
        'max_turns': 5,
        'max_context_length': 3000
    }
    return config

def extract_5w_info(messages):
    """
    从对话记录中提取5W关键信息
    
    5W规则：
    - Who: 谁（对话参与者）
    - What: 做了什么事
    - When: 什么时候（可选）
    - Where: 在何处（可选）
    - Why: 为什么要做（可选）
    """
    config = load_config()
    
    conversation_text = "\n".join([
        f"{msg['role']}: {msg['content']}" 
        for msg in messages
        if msg['role'] in ['user', 'assistant']
    ])
    
    extract_prompt = """请从以下对话中提取关键信息，按照5W规则：

对话内容：
{conversation}

请按照以下格式输出提取结果：
【Who】谁（对话参与者或提到的人物）
【What】做了什么事（核心事件或动作）
【When】什么时候（如果提到时间）
【Where】在何处（如果提到地点）
【Why】为什么（目的或原因，如果提到）

如果某个项目没有相关信息，请填写"未提及"。
""".format(conversation=conversation_text)
    
    url = f"{config['base_url']}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": config['model'],
        "messages": [{"role": "user", "content": extract_prompt}],
        "temperature": 0.3,
        "max_tokens": 500
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"\n❌ 5W提取失败: {str(e)}")
        return None

def append_to_log(messages):
    """将聊天记录增量写入日志文件"""
    print("\n🔍 正在提取5W关键信息...")
    info_5w = extract_5w_info(messages)
    
    if info_5w:
        # 获取当前时间
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        
        # 准备日志内容
        log_entry = "\n" + "="*60 + "\n"
        log_entry += "【时间】" + current_time + "\n"
        log_entry += info_5w + "\n"
        
        # 添加最近的对话内容
        recent_messages = messages[-4:]
        log_entry += "\n【原始对话摘要】\n"
        for msg in recent_messages:
            role = "用户" if msg['role'] == 'user' else "助手"
            content = msg['content'][:200] + "..." if len(msg['content']) > 200 else msg['content']
            log_entry += role + ": " + content + "\n"
        
        # 增量写入日志
        with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        print(f"✅ 日志已更新: {LOG_FILE_PATH}")
        return info_5w
    return None

def search_chat_history(query):
    """
    搜索聊天历史记录
    
    Args:
        query: 用户的搜索查询
        
    Returns:
        搜索结果字符串
    """
    # 检查日志文件是否存在
    if not os.path.exists(LOG_FILE_PATH):
        return "❌ 聊天历史文件不存在，请先进行对话"
    
    # 读取日志文件内容
    with open(LOG_FILE_PATH, 'r', encoding='utf-8') as f:
        log_content = f.read()
    
    if not log_content.strip():
        return "❌ 聊天历史为空"
    
    config = load_config()
    
    search_prompt = """请从以下聊天历史中查找与用户查询相关的信息：

【聊天历史】
{log_content}

【用户查询】
{query}

请总结找到的相关信息，用自然、友好的语言回答。如果没有找到相关信息，请说明。
""".format(log_content=log_content, query=query)
    
    url = f"{config['base_url']}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": config['model'],
        "messages": [{"role": "user", "content": search_prompt}],
        "temperature": 0.3,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ 搜索失败: {str(e)}"

def is_search_request(user_input):
    """检测是否为搜索请求"""
    user_input_lower = user_input.lower()
    
    # 检查是否以/search开头
    if user_input_lower.startswith('/search'):
        return True
    
    # 检查是否表达了查找历史的意图
    search_keywords = [
        '查找聊天历史', '搜索历史', '历史记录', '之前的对话',
        '之前说的', '之前聊的', '回顾一下', '查一下'
    ]
    
    for keyword in search_keywords:
        if keyword in user_input_lower:
            return True
    
    return False

def calculate_context_length(messages):
    """计算上下文总长度"""
    total_length = 0
    for msg in messages:
        total_length += len(msg.get('content', ''))
    return total_length

def summarize_conversation(messages):
    """调用LLM总结对话历史"""
    config = load_config()
    
    conversation_text = "\n".join([
        f"{msg['role']}: {msg['content']}" 
        for msg in messages
    ])
    
    summary_prompt = """请总结以下对话内容，提取关键信息和讨论要点：

{conversation}

总结要求：
1. 保持核心信息完整
2. 去除冗余内容
3. 用简洁的语言概括
4. 保留关键决策和结论
""".format(conversation=conversation_text)
    
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
    """压缩上下文"""
    if len(messages) <= 2:
        return messages
    
    split_index = int(len(messages) * 0.7)
    messages_to_summarize = messages[:split_index]
    messages_to_keep = messages[split_index:]
    
    print("\n🔄 正在总结对话历史...")
    summary = summarize_conversation(messages_to_summarize)
    
    if summary:
        summary_message = {
            "role": "system",
            "content": "对话总结：" + summary
        }
        compressed = [summary_message] + messages_to_keep
        print(f"✅ 上下文压缩完成：原始{len(messages)}条 → 压缩后{len(compressed)}条")
        return compressed
    else:
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
        error_msg = "HTTP错误 - " + str(e)
        print(f"\n❌ {error_msg}")
        return error_msg
    except requests.exceptions.ConnectionError:
        error_msg = "无法连接到服务器，请检查服务是否启动！"
        print(f"\n❌ {error_msg}")
        return error_msg
    except Exception as e:
        error_msg = "错误：" + str(e)
        print(f"\n❌ {error_msg}")
        return error_msg

def signal_handler(signal_num, frame):
    """信号处理函数"""
    print("\n\n👋 感谢使用！对话结束。")
    sys.exit(0)

def main():
    """主函数 - 带日志记录和历史搜索的聊天程序"""
    print("=== LLM 聊天日志处理器 ===")
    print("📌 输入消息后按回车发送")
    print("📌 按 Ctrl+C 退出程序")
    print("📌 输入 /search 或 '查找聊天历史' 可搜索历史记录")
    print("📌 自动记录5W信息到日志文件")
    print("============================\n")
    
    config = load_config()
    print(f"已连接到: {config['base_url']}")
    print(f"使用模型: {config['model']}")
    print(f"日志文件: {LOG_FILE_PATH}\n")
    
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
            
            # 检测搜索请求
            if is_search_request(user_input):
                print("\n🔍 检测到搜索请求，正在查找聊天历史...")
                # 提取搜索关键词（去除/search前缀）
                if user_input.lower().startswith('/search'):
                    query = user_input[7:].strip()
                else:
                    query = user_input
                
                search_result = search_chat_history(query)
                print(f"\n📋 搜索结果：")
                print(search_result)
                print()
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
                print(f"\n⚠️ 检测到超过{config['max_turns']}轮对话")
                should_compress = True
            elif context_length > config['max_context_length']:
                print(f"\n⚠️ 检测到上下文长度超过{config['max_context_length']}字符")
                should_compress = True
            
            if should_compress:
                # 在压缩前先记录日志
                append_to_log(history_messages)
                history_messages = compress_context(history_messages)
                turn_count = 0
            
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
