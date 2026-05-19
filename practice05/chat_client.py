"""
聊天客户端 - 集成技能加载系统
"""
import os
import sys
import json
import signal
import time
import re
from dotenv import load_dotenv
import requests

sys.path.append(os.path.dirname(os.path.dirname(__file__)) + '/practice04')
try:
    from anythingllm_tools import anythingllm_query, anythingllm_get_workspaces, anythingllm_get_documents, ANYTHINGLLM_TOOLS
except:
    ANYTHINGLLM_TOOLS = []
    def anythingllm_query(msg): return "AnythingLLM未配置"
    def anythingllm_get_workspaces(): return "AnythingLLM未配置"
    def anythingllm_get_documents(w=None): return "AnythingLLM未配置"

LOG_FILE_PATH = r"D:\llm_traeproject1\log.txt"
SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.agents', 'skills')

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

def parse_yaml_front_matter(content):
    lines = content.split('\n')
    if len(lines) < 3 or lines[0] != '---':
        return {}
    
    front_matter_lines = []
    for i in range(1, len(lines)):
        if lines[i] == '---':
            break
        front_matter_lines.append(lines[i])
    
    result = {}
    for line in front_matter_lines:
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip()] = value.strip()
    
    return result

def list_available_skills():
    skills = []
    if not os.path.exists(SKILLS_DIR):
        return skills
    
    try:
        for skill_dir in os.listdir(SKILLS_DIR):
            skill_path = os.path.join(SKILLS_DIR, skill_dir)
            if not os.path.isdir(skill_path):
                continue
            
            skill_file = os.path.join(skill_path, 'SKILL.md')
            if os.path.exists(skill_file):
                try:
                    with open(skill_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    front_matter = parse_yaml_front_matter(content)
                    if 'name' in front_matter:
                        skills.append({
                            'name': front_matter['name'],
                            'description': front_matter.get('description', '')
                        })
                except Exception as e:
                    print("读取技能文件失败", skill_file, str(e))
    
    except Exception as e:
        print("读取技能目录失败:", str(e))
    
    return skills

def load_skill_content(skill_name):
    skill_path = os.path.join(SKILLS_DIR, skill_name)
    
    if not os.path.isdir(skill_path):
        return None
    
    skill_file = os.path.join(skill_path, 'SKILL.md')
    if not os.path.exists(skill_file):
        return None
    
    try:
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        if len(lines) < 3 or lines[0] != '---':
            return content
        
        content_start = 0
        dash_count = 0
        for i, line in enumerate(lines):
            if line == '---':
                dash_count += 1
                if dash_count == 2:
                    content_start = i + 1
                    break
        
        if content_start > 0:
            return '\n'.join(lines[content_start:])
        else:
            return content
    
    except Exception as e:
        print("加载技能内容失败:", str(e))
        return None

def is_skill_request(user_input):
    user_input_lower = user_input.lower()
    skill_triggers = {
        'notice': ['通知', '撰写通知', '修改通知', '润色通知', '写通知']
    }
    
    for skill_name, triggers in skill_triggers.items():
        for trigger in triggers:
            if trigger in user_input_lower:
                return skill_name
    return None

def calculate_context_length(messages):
    total_length = 0
    for msg in messages:
        total_length += len(msg.get('content', ''))
    return total_length

def get_system_prompt():
    skills = list_available_skills()
    skills_json = json.dumps({"skills": skills}, ensure_ascii=False, indent=2)
    
    tools_description = "\n可用工具列表：\n"
    for tool in ANYTHINGLLM_TOOLS:
        tools_description += "- " + tool['name'] + ": " + tool['description'] + "\n"
        if tool['parameters']:
            tools_description += "  参数：\n"
            for param_name, param_info in tool['parameters'].items():
                required = "（必填）" if param_info.get('required') else "（可选）"
                tools_description += "    - " + param_name + ": " + param_info['description'] + required + "\n"
    
    system_prompt = """你是一个智能助手，具备调用外部工具和使用技能的能力。

【可用技能列表】
""" + skills_json + """

【技能使用规则】
1. 当用户的请求与某个技能的description匹配时，使用该技能
2. 如需使用技能，请调用 <function name="load_skill_content">(技能名称)</function> 加载技能内容
3. 加载技能内容后，遵照技能中的规则响应用户

【工具使用规则】
1. 工具调用格式：<function name="工具名称">(参数)</function>
2. 如果不需要调用工具，直接回答用户问题

【何时使用技能】
- notice技能：当用户需要撰写通知、修改通知、润色通知时使用

""" + tools_description + """

请根据用户的问题，判断是否需要调用工具或使用技能。如果需要，按照指定格式输出工具调用；如果不需要，直接回答即可。
"""
    
    return system_prompt

def stream_chat_response(messages):
    config = load_config()
    url = config['base_url'] + "/v1/chat/completions"
    headers = {
        "Authorization": "Bearer " + config['api_key'],
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
        response = requests.post(url, json=data, headers=headers, timeout=60, stream=True)
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
        
    except Exception as e:
        error_msg = "错误：" + str(e)
        print("\n", error_msg)
        return error_msg

def signal_handler(signal_num, frame):
    print("\n\n感谢使用！对话结束。")
    sys.exit(0)

def main():
    print("=== LLM 聊天客户端 (集成技能系统) ===")
    print("输入消息后按回车发送")
    print("按 Ctrl+C 退出程序")
    print("提到'通知'、'撰写通知'可调用notice技能")
    print("========================================\n")
    
    config = load_config()
    print("已连接到:", config['base_url'])
    print("使用模型:", config['model'])
    print()
    
    skills = list_available_skills()
    if skills:
        print("可用技能:")
        for skill in skills:
            print("  - " + skill['name'] + ": " + skill['description'][:50] + "...")
    else:
        print("未找到可用技能")
    print()
    
    signal.signal(signal.SIGINT, signal_handler)
    
    history_messages = []
    system_message = {"role": "system", "content": get_system_prompt()}
    history_messages.append(system_message)
    
    while True:
        try:
            user_input = input("你：")
        except KeyboardInterrupt:
            print("\n\n感谢使用！对话结束。")
            break
        
        if not user_input.strip():
            print("请输入内容")
            continue
        
        skill_name = is_skill_request(user_input)
        if skill_name:
            print("\n检测到技能请求，正在加载", skill_name, "技能...")
            skill_content = load_skill_content(skill_name)
            
            if skill_content:
                print("\n技能内容已加载，正在生成响应...")
                
                skill_prompt = """
【当前使用技能】
技能名称：""" + skill_name + """

【技能内容】
""" + skill_content + """

请根据以上技能内容，按照技能规则响应用户请求：

用户请求：""" + user_input + """
"""
                skill_messages = [{"role": "system", "content": skill_prompt}]
                response = stream_chat_response(skill_messages)
                history_messages.append({"role": "user", "content": user_input})
                history_messages.append({"role": "assistant", "content": response})
                continue
            else:
                print("无法加载技能", skill_name)
        
        history_messages.append({"role": "user", "content": user_input})
        
        current_length = calculate_context_length(history_messages)
        print("\n当前上下文：", len(history_messages), "条消息，", current_length, "字符")
        
        response = stream_chat_response(history_messages)
        history_messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()
