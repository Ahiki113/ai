"""
聊天客户端 - 集成链式工具调用系统

教学目标：
1. 学习链式工具调用机制
2. 理解上下文管理器设计
3. 掌握多步骤工具调用流程
4. 实现LLM自主决策的工具调用链
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
        'temperature': float(os.getenv('LLM_TEMPERATURE', 0.3)),
        'max_tokens': int(os.getenv('LLM_MAX_TOKENS', 2000)),
        'stream': False,
        'max_turns': 5,
        'max_context_length': 3000,
        'max_iterations': 10
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

# ========== 链式调用相关工具函数 ==========

def search_files_with_keyword(directory, keyword):
    """搜索目录下包含指定关键词的文件"""
    results = []
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if keyword in content:
                                results.append({
                                    'file': file_path,
                                    'line_count': len(content.split('\n'))
                                })
                    except Exception:
                        continue
    except Exception as e:
        return "搜索失败: " + str(e)
    
    if not results:
        return "未找到包含关键词'" + keyword + "'的文件"
    
    return json.dumps(results, ensure_ascii=False)

def read_file_content(file_path):
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        return "读取文件失败: " + str(e)

def write_file_content(file_path, content):
    """写入文件内容"""
    try:
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return "文件写入成功: " + file_path
    except Exception as e:
        return "写入文件失败: " + str(e)

def fetch_web_page(url):
    """获取网页内容"""
    try:
        response = requests.get(url, timeout=10)
        response.encoding = response.apparent_encoding
        return response.text
    except Exception as e:
        return "获取网页失败: " + str(e)

def extract_web_title(html_content):
    """从HTML内容中提取标题"""
    match = re.search(r'<title[^>]*>([^<]+)</title>', html_content, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "未找到标题"

# ========== 链式调用上下文管理器 ==========

class ChainedCallContext:
    """链式调用上下文管理器"""
    
    def __init__(self, max_iterations=10):
        self.steps = []
        self.variables = {}
        self.max_iterations = max_iterations
        self.current_iteration = 0
    
    def add_step(self, tool_name, arguments, result):
        """记录一步工具调用"""
        step = {
            'iteration': self.current_iteration,
            'tool_name': tool_name,
            'arguments': arguments,
            'result': result,
            'timestamp': time.time()
        }
        self.steps.append(step)
        self.current_iteration += 1
    
    def get_history(self):
        """获取完整的调用历史"""
        return self.steps
    
    def get_last_result(self):
        """获取上一步的结果"""
        if self.steps:
            return self.steps[-1]['result']
        return None
    
    def set_variable(self, name, value):
        """设置上下文变量"""
        self.variables[name] = value
    
    def get_variable(self, name):
        """获取上下文变量"""
        return self.variables.get(name)
    
    def has_more_iterations(self):
        """检查是否还有迭代次数"""
        return self.current_iteration < self.max_iterations
    
    def get_summary(self):
        """获取上下文摘要"""
        summary = "已执行步骤 (" + str(len(self.steps)) + "/" + str(self.max_iterations) + "):\n"
        for step in self.steps:
            summary += "步骤" + str(step['iteration']) + ": " + step['tool_name'] + " -> " + str(step['arguments'])[:50] + "...\n"
        return summary

# ========== 工具映射 ==========

TOOL_MAP = {
    "search_files_with_keyword": search_files_with_keyword,
    "read_file_content": read_file_content,
    "write_file_content": write_file_content,
    "fetch_web_page": fetch_web_page,
    "extract_web_title": extract_web_title,
    "load_skill_content": load_skill_content,
    "anythingllm_query": anythingllm_query,
    "anythingllm_get_workspaces": anythingllm_get_workspaces,
    "anythingllm_get_documents": anythingllm_get_documents
}

TOOL_DESCRIPTIONS = [
    {
        "name": "search_files_with_keyword",
        "description": "搜索目录下包含指定关键词的Python文件",
        "parameters": {
            "directory": {"description": "要搜索的目录路径", "required": True},
            "keyword": {"description": "要搜索的关键词", "required": True}
        }
    },
    {
        "name": "read_file_content",
        "description": "读取指定文件的内容",
        "parameters": {
            "file_path": {"description": "文件路径", "required": True}
        }
    },
    {
        "name": "write_file_content",
        "description": "将内容写入指定文件",
        "parameters": {
            "file_path": {"description": "文件路径", "required": True},
            "content": {"description": "要写入的内容", "required": True}
        }
    },
    {
        "name": "fetch_web_page",
        "description": "获取指定URL的网页内容",
        "parameters": {
            "url": {"description": "网页URL", "required": True}
        }
    },
    {
        "name": "extract_web_title",
        "description": "从HTML内容中提取网页标题",
        "parameters": {
            "html_content": {"description": "HTML内容", "required": True}
        }
    },
    {
        "name": "load_skill_content",
        "description": "加载指定技能的内容",
        "parameters": {
            "skill_name": {"description": "技能名称", "required": True}
        }
    }
]

# ========== 分析提示词构建函数 ==========

def build_analysis_prompt(user_request, context):
    """构建分析提示词"""
    history = context.get_history()
    
    history_text = ""
    if history:
        history_text = "【已执行步骤】\n"
        for step in history:
            history_text += "步骤" + str(step['iteration']) + ": " + step['tool_name'] + "\n"
            history_text += "  参数: " + json.dumps(step['arguments'], ensure_ascii=False) + "\n"
            result_str = str(step['result'])
            if len(result_str) > 200:
                result_str = result_str[:200] + "..."
            history_text += "  结果: " + result_str + "\n\n"
    
    tools_text = "【可用工具】\n"
    for tool in TOOL_DESCRIPTIONS:
        tools_text += "- " + tool['name'] + ": " + tool['description'] + "\n"
        if tool['parameters']:
            tools_text += "  参数: " + ", ".join([p for p in tool['parameters'].keys()]) + "\n"
    
    prompt = """你是一个智能助手，具备链式工具调用能力。

【用户请求】
""" + user_request + """

""" + history_text + """

""" + tools_text + """

【决策规则】
1. 根据用户请求和已执行步骤，判断是否需要继续调用工具
2. 如果当前信息足够回答用户问题，返回完成状态和最终答案
3. 如果需要更多信息，选择合适的工具继续调用
4. 可以使用上一步工具的输出作为下一步工具的输入

【输出格式】
请严格按照以下JSON格式输出：

1. 完成任务时：
{"done": true, "answer": "最终回答内容"}

2. 继续调用工具时：
{"done": false, "tool_call": {"name": "工具名称", "arguments": {"参数名": "参数值"}}}

注意：输出必须是有效的JSON格式，不要包含其他内容。
"""
    
    return prompt

# ========== LLM调用函数（非流式） ==========

def call_llm(messages):
    """调用LLM获取响应"""
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
        "stream": False
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return "LLM调用失败: " + str(e)

# ========== 链式调用执行函数 ==========

def execute_chained_tool_call(user_request, max_iterations=10):
    """执行链式工具调用"""
    print("开始链式工具调用...")
    print("用户请求:", user_request)
    print()
    
    context = ChainedCallContext(max_iterations=max_iterations)
    
    for iteration in range(max_iterations):
        print("=" * 50)
        print("迭代", iteration + 1, "/", max_iterations)
        
        # 构建分析提示词
        prompt = build_analysis_prompt(user_request, context)
        
        # 调用LLM决策
        messages = [{"role": "system", "content": prompt}]
        response = call_llm(messages)
        
        print("LLM响应:", response[:100], "..." if len(response) > 100 else "")
        print()
        
        # 解析响应
        try:
            decision = json.loads(response)
        except json.JSONDecodeError:
            print("无法解析LLM响应，尝试提取JSON...")
            # 尝试从响应中提取JSON
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                try:
                    decision = json.loads(match.group(0))
                except:
                    print("解析失败，结束调用")
                    return "解析LLM响应失败: " + response
            else:
                print("未找到JSON，结束调用")
                return "未找到有效JSON响应"
        
        # 判断是否完成
        if decision.get('done'):
            print("任务完成!")
            print("最终答案:", decision.get('answer', ''))
            return decision.get('answer', '')
        
        # 执行工具调用
        tool_call = decision.get('tool_call', {})
        tool_name = tool_call.get('name')
        arguments = tool_call.get('arguments', {})
        
        if not tool_name or tool_name not in TOOL_MAP:
            print("无效的工具名称:", tool_name)
            break
        
        print("执行工具:", tool_name)
        print("参数:", arguments)
        
        # 执行工具
        tool_func = TOOL_MAP[tool_name]
        try:
            if tool_name == "search_files_with_keyword":
                result = tool_func(arguments.get('directory', ''), arguments.get('keyword', ''))
            elif tool_name == "read_file_content":
                result = tool_func(arguments.get('file_path', ''))
            elif tool_name == "write_file_content":
                result = tool_func(arguments.get('file_path', ''), arguments.get('content', ''))
            elif tool_name == "fetch_web_page":
                result = tool_func(arguments.get('url', ''))
            elif tool_name == "extract_web_title":
                result = tool_func(arguments.get('html_content', ''))
            elif tool_name == "load_skill_content":
                result = tool_func(arguments.get('skill_name', ''))
            elif tool_name == "anythingllm_query":
                result = tool_func(arguments.get('message', ''))
            elif tool_name == "anythingllm_get_workspaces":
                result = tool_func()
            elif tool_name == "anythingllm_get_documents":
                result = tool_func(arguments.get('workspace', ''))
            else:
                result = "未知工具"
        except Exception as e:
            result = "工具执行失败: " + str(e)
        
        # 记录到上下文
        context.add_step(tool_name, arguments, result)
        
        print("工具执行结果:", str(result)[:100], "..." if len(str(result)) > 100 else "")
        print()
    
    print("达到最大迭代次数，结束调用")
    return context.get_summary()

# ========== 获取系统提示词 ==========

def get_system_prompt():
    """生成系统提示词，包含链式调用说明"""
    skills = list_available_skills()
    skills_json = json.dumps({"skills": skills}, ensure_ascii=False, indent=2)
    
    tools_description = "\n可用工具列表：\n"
    for tool in TOOL_DESCRIPTIONS + ANYTHINGLLM_TOOLS:
        tools_description += "- " + tool['name'] + ": " + tool['description'] + "\n"
        if tool.get('parameters'):
            tools_description += "  参数：\n"
            for param_name, param_info in tool['parameters'].items():
                required = "（必填）" if param_info.get('required') else "（可选）"
                tools_description += "    - " + param_name + ": " + param_info['description'] + required + "\n"
    
    system_prompt = """你是一个智能助手，具备调用外部工具和使用技能的能力，支持链式工具调用。

【可用技能列表】
""" + skills_json + """

【链式调用规则】
1. 你可以进行多步工具调用，前一个工具的输出可以作为后一个工具的输入
2. 每一步调用后，分析结果并决定下一步操作
3. 如果信息足够，直接回答用户问题
4. 如果需要更多信息，继续调用合适的工具

【链式调用示例】
用户请求："查找包含'def'的文件并总结内容"
步骤1: search_files_with_keyword(directory="practice05", keyword="def") -> 获取文件列表
步骤2: read_file_content(file_path="practice05/chat_client.py") -> 读取文件内容
步骤3: 总结回答用户

【可用工具】
""" + tools_description + """

【何时使用技能】
- notice技能：当用户需要撰写通知、修改通知、润色通知时使用

请根据用户的问题，判断是否需要调用工具或使用技能。如果需要，按照指定格式输出工具调用；如果不需要，直接回答即可。
"""
    
    return system_prompt

# ========== 主函数 ==========

def main():
    print("=== LLM 聊天客户端 (集成链式工具调用) ===")
    print("输入消息后按回车发送")
    print("按 Ctrl+C 退出程序")
    print("支持链式工具调用：文件搜索、网页抓取、技能加载等")
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
    
    print("可用工具:")
    for tool in TOOL_DESCRIPTIONS:
        print("  - " + tool['name'] + ": " + tool['description'][:50] + "...")
    print()
    
    signal.signal(signal.SIGINT, lambda s, f: (print("\n\n感谢使用！对话结束。"), sys.exit(0)))
    
    while True:
        try:
            user_input = input("你：")
        except KeyboardInterrupt:
            print("\n\n感谢使用！对话结束。")
            break
        
        if not user_input.strip():
            print("请输入内容")
            continue
        
        # 检测是否需要链式调用
        if any(keyword in user_input for keyword in ["查找", "搜索", "总结", "访问", "提取", "保存"]):
            print("\n检测到复杂请求，启动链式工具调用...")
            result = execute_chained_tool_call(user_input, max_iterations=config['max_iterations'])
            print("\n最终结果:")
            print(result)
            print()
        else:
            # 普通对话
            messages = [
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": user_input}
            ]
            response = call_llm(messages)
            print("LLM：", response)
            print()

if __name__ == "__main__":
    main()
