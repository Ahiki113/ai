"""
聊天客户端 - 集成AnythingLLM工具调用

教学目标：
1. 学习工具调用机制
2. 理解系统提示词设计
3. 掌握多工具集成方法
4. 实现智能工具选择
"""
import os
import sys
import json
import signal
import time
from dotenv import load_dotenv
import requests

# 导入AnythingLLM工具
from anythingllm_tools import anythingllm_query, anythingllm_get_workspaces, anythingllm_get_documents, ANYTHINGLLM_TOOLS

LOG_FILE_PATH = r"D:\llm_traeproject1\log.txt"

def load_config():
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
    print("\n🔍 正在提取5W关键信息...")
    info_5w = extract_5w_info(messages)
    
    if info_5w:
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_entry = "\n" + "="*60 + "\n"
        log_entry += "【时间】" + current_time + "\n"
        log_entry += info_5w + "\n"
        
        recent_messages = messages[-4:]
        log_entry += "\n【原始对话摘要】\n"
        for msg in recent_messages:
            role = "用户" if msg['role'] == 'user' else "助手"
            content = msg['content'][:200] + "..." if len(msg['content']) > 200 else msg['content']
            log_entry += role + ": " + content + "\n"
        
        with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        print(f"✅ 日志已更新: {LOG_FILE_PATH}")
        return info_5w
    return None

def search_chat_history(query):
    if not os.path.exists(LOG_FILE_PATH):
        return "❌ 聊天历史文件不存在，请先进行对话"
    
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
    user_input_lower = user_input.lower()
    
    if user_input_lower.startswith('/search'):
        return True
    
    search_keywords = [
        '查找聊天历史', '搜索历史', '历史记录', '之前的对话',
        '之前说的', '之前聊的', '回顾一下', '查一下'
    ]
    
    for keyword in search_keywords:
        if keyword in user_input_lower:
            return True
    
    return False

def is_anythingllm_request(user_input):
    """检测是否需要调用AnythingLLM工具"""
    user_input_lower = user_input.lower()
    
    # 检测触发词：文档仓库、文件仓库、仓库
    trigger_keywords = [
        '文档仓库', '文件仓库', '仓库',
        '查找文档', '搜索文档', '查询文档',
        '知识库', '资料', '文档'
    ]
    
    for keyword in trigger_keywords:
        if keyword in user_input_lower:
            return True
    
    return False

def calculate_context_length(messages):
    total_length = 0
    for msg in messages:
        total_length += len(msg.get('content', ''))
    return total_length

def summarize_conversation(messages):
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

def get_system_prompt():
    """生成系统提示词，包含工具使用说明"""
    
    tools_description = "\n可用工具列表：\n"
    for tool in ANYTHINGLLM_TOOLS:
        tools_description += f"- {tool['name']}: {tool['description']}\n"
        if tool['parameters']:
            tools_description += "  参数：\n"
            for param_name, param_info in tool['parameters'].items():
                required = "（必填）" if param_info.get('required') else "（可选）"
                tools_description += f"    - {param_name}: {param_info['description']}{required}\n"
    
    system_prompt = """你是一个智能助手，具备调用外部工具的能力。

【工具使用规则】
1. 工具调用格式：<function name="工具名称">(参数)</function>
2. 如果不需要调用工具，直接回答用户问题

【何时使用AnythingLLM工具】
- 当用户提到"文档仓库"、"文件仓库"、"仓库"时，使用 anythingllm_query 工具
- 当用户询问与文档、知识库、资料相关的问题时，使用 anythingllm_query 工具
- 当用户需要查找特定文档内容时，使用 anythingllm_query 工具
- 当用户需要查看工作空间列表时，使用 anythingllm_get_workspaces 工具
- 当用户需要查看文档列表时，使用 anythingllm_get_documents 工具

【工具调用示例】
- <function name="anythingllm_query">(帮我查找文档仓库中的Python相关资料)</function>
- <function name="anythingllm_get_workspaces">()</function>
- <function name="anythingllm_get_documents">()</function>

{tools_description}

请根据用户的问题，判断是否需要调用工具。如果需要调用工具，请按照指定格式输出；如果不需要，直接回答即可。
""".format(tools_description=tools_description)
    
    return system_prompt

def extract_tool_call(user_input):
    """从用户输入或LLM响应中提取工具调用"""
    import re
    
    # 查找工具调用格式 <function name="xxx">(xxx)</function>
    match = re.search(r'<function name="(\w+)">\((.*?)\)</function>', user_input)
    if match:
        tool_name = match.group(1)
        params = match.group(2)
        return {"tool_name": tool_name, "params": params}
    
    # 检查是否需要调用anythingllm工具（基于用户意图）
    if is_anythingllm_request(user_input):
        return {"tool_name": "anythingllm_query", "params": user_input}
    
    return None

def execute_tool(tool_name, params):
    """执行工具调用"""
    tool_map = {
        "anythingllm_query": anythingllm_query,
        "anythingllm_get_workspaces": anythingllm_get_workspaces,
        "anythingllm_get_documents": anythingllm_get_documents
    }
    
    if tool_name not in tool_map:
        return "错误：未知的工具名称: " + tool_name
    
    try:
        tool_func = tool_map[tool_name]
        if tool_name == "anythingllm_query":
            return tool_func(params)
        elif tool_name == "anythingllm_get_workspaces":
            return tool_func()
        elif tool_name == "anythingllm_get_documents":
            if params.strip():
                return tool_func(params.strip())
            else:
                return tool_func()
        else:
            return "错误：工具调用失败"
    except Exception as e:
        return "工具执行错误: " + str(e)

def stream_chat_response(messages):
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
    print("\n\n👋 感谢使用！对话结束。")
    sys.exit(0)

def main():
    print("=== LLM 聊天客户端 (集成AnythingLLM) ===")
    print("📌 输入消息后按回车发送")
    print("📌 按 Ctrl+C 退出程序")
    print("📌 输入 /search 或 '查找聊天历史' 可搜索本地历史记录")
    print("📌 提到'文档仓库'、'文件仓库'、'仓库'可查询AnythingLLM")
    print("📌 自动记录5W信息到日志文件")
    print("========================================\n")
    
    config = load_config()
    print(f"已连接到: {config['base_url']}")
    print(f"使用模型: {config['model']}")
    print(f"日志文件: {LOG_FILE_PATH}\n")
    
    signal.signal(signal.SIGINT, signal_handler)
    
    history_messages = []
    turn_count = 0
    
    # 添加系统提示词
    system_message = {"role": "system", "content": get_system_prompt()}
    history_messages.append(system_message)
    
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
            
            # 检测本地搜索请求
            if is_search_request(user_input):
                print("\n🔍 检测到本地搜索请求，正在查找聊天历史...")
                if user_input.lower().startswith('/search'):
                    query = user_input[7:].strip()
                else:
                    query = user_input
                
                search_result = search_chat_history(query)
                print(f"\n📋 搜索结果：")
                print(search_result)
                print()
                continue
            
            # 检测是否需要调用AnythingLLM工具
            if is_anythingllm_request(user_input):
                print("\n📚 检测到文档仓库查询请求，正在调用AnythingLLM...")
                tool_result = anythingllm_query(user_input)
                print(f"\n📋 查询结果：")
                print(tool_result)
                print()
                continue
            
            history_messages.append({
                "role": "user", 
                "content": user_input
            })
            
            turn_count += 1
            
            context_length = calculate_context_length(history_messages)
            should_compress = False
            
            if turn_count > config['max_turns']:
                print(f"\n⚠️ 检测到超过{config['max_turns']}轮对话")
                should_compress = True
            elif context_length > config['max_context_length']:
                print(f"\n⚠️ 检测到上下文长度超过{config['max_context_length']}字符")
                should_compress = True
            
            if should_compress:
                append_to_log(history_messages)
                history_messages = compress_context(history_messages)
                history_messages.insert(0, {"role": "system", "content": get_system_prompt()})
                turn_count = 0
            
            current_length = calculate_context_length(history_messages)
            print(f"\n📊 当前上下文：{len(history_messages)}条消息，{current_length}字符")
            
            response = stream_chat_response(history_messages)
            
            history_messages.append({
                "role": "assistant",
                "content": response
            })
            
            # 检查响应是否包含工具调用
            tool_call = extract_tool_call(response)
            if tool_call:
                print(f"\n🔧 检测到工具调用: {tool_call['tool_name']}")
                tool_result = execute_tool(tool_call['tool_name'], tool_call['params'])
                print(f"\n📋 工具执行结果：")
                print(tool_result)
                print()
                
                history_messages.append({
                    "role": "user",
                    "content": f"工具执行结果：\n{tool_result}"
                })
                
                response = stream_chat_response(history_messages)
                history_messages.append({
                    "role": "assistant",
                    "content": response
                })
            
    except Exception as e:
        print(f"\n程序异常退出: {str(e)}")

if __name__ == "__main__":
    main()
