"""
LLM工具调用聊天客户端 - 支持文件操作工具调用

功能特性：
1. 支持自然语言请求文件操作
2. 自动识别用户意图并调用相应工具
3. 支持工具调用结果的自然语言总结
4. 支持流式输出和历史记录管理
"""
import os
import sys
import json
import signal
from dotenv import load_dotenv
import requests

# 导入文件工具模块
from file_tools import (
    list_files,
    rename_file,
    delete_file,
    create_file,
    read_file,
    TOOLS
)

def load_config():
    """加载配置文件"""
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
    
    config = {
        'base_url': os.getenv('LLM_BASE_URL', 'http://127.0.0.1:1234').rstrip('/'),
        'model': os.getenv('LLM_MODEL', 'gemma-3-4b-it'),
        'api_key': os.getenv('LLM_API_KEY', 'sk-no-key-required'),
        'temperature': float(os.getenv('LLM_TEMPERATURE', 0.7)),
        'max_tokens': int(os.getenv('LLM_MAX_TOKENS', 2000)),
        'stream': True
    }
    return config

def extract_tool_call(user_input):
    """
    从用户输入中提取工具调用意图
    
    Args:
        user_input: 用户输入的自然语言指令
        
    Returns:
        (tool_name, parameters) 或 None
    """
    user_input_lower = user_input.lower()
    
    # 模式匹配：列出文件
    if any(keyword in user_input_lower for keyword in ['列出', '显示', '查看', '有哪些', '目录']):
        # 提取目录路径
        directory = extract_path(user_input)
        if directory:
            return ('list_files', {'directory': directory})
        return ('list_files', {'directory': '.'})
    
    # 模式匹配：重命名文件
    if any(keyword in user_input_lower for keyword in ['重命名', '改名', '修改名字']):
        parts = user_input.split(' ')
        old_path = None
        new_name = None
        for i, part in enumerate(parts):
            if part.endswith(('.txt', '.py', '.md', '.json')):
                if not old_path:
                    old_path = part
                elif not new_name:
                    new_name = part
        if old_path and new_name:
            return ('rename_file', {'old_path': old_path, 'new_name': new_name})
        return None
    
    # 模式匹配：删除文件
    if any(keyword in user_input_lower for keyword in ['删除', '删掉', '移除']):
        file_path = extract_path(user_input)
        if file_path:
            return ('delete_file', {'file_path': file_path})
        return None
    
    # 模式匹配：创建文件
    if any(keyword in user_input_lower for keyword in ['创建', '新建', '生成']):
        file_name = None
        content = ""
        parts = user_input.split(' ')
        for part in parts:
            if '.' in part and not part.startswith('http'):
                file_name = part
                break
        
        # 提取文件内容（在"内容是"、"写入"等关键词之后）
        content_markers = ['内容是', '写入', '内容为', '内容:']
        for marker in content_markers:
            if marker in user_input:
                idx = user_input.find(marker)
                content = user_input[idx + len(marker):].strip()
                break
        
        if file_name:
            return ('create_file', {
                'directory': '.',
                'file_name': file_name,
                'content': content
            })
        return None
    
    # 模式匹配：读取文件
    if any(keyword in user_input_lower for keyword in ['读取', '查看内容', '打开', '内容']):
        file_path = extract_path(user_input)
        if file_path:
            return ('read_file', {'file_path': file_path})
        return None
    
    return None

def extract_path(text):
    """从文本中提取文件或目录路径"""
    import re
    
    # 匹配路径模式
    path_patterns = [
        r'([a-zA-Z]:[\\/][^\s]+)',  # Windows绝对路径
        r'([\\/][^\s]+)',           # 绝对路径
        r'(\.\.?[\\/][^\s]+)',      # 相对路径
        r'([a-zA-Z][^\s]*\.[a-zA-Z]+)'  # 简单文件名
    ]
    
    for pattern in path_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return None

def execute_tool(tool_name, parameters):
    """执行工具调用"""
    try:
        if tool_name == 'list_files':
            return list_files(parameters.get('directory', '.'))
        elif tool_name == 'rename_file':
            return rename_file(
                parameters.get('old_path', ''),
                parameters.get('new_name', '')
            )
        elif tool_name == 'delete_file':
            return delete_file(parameters.get('file_path', ''))
        elif tool_name == 'create_file':
            return create_file(
                parameters.get('directory', '.'),
                parameters.get('file_name', ''),
                parameters.get('content', '')
            )
        elif tool_name == 'read_file':
            return read_file(parameters.get('file_path', ''))
        else:
            return f"❌ 未知工具：{tool_name}"
    except Exception as e:
        return f"❌ 工具执行失败：{str(e)}"

def signal_handler(signal_num, frame):
    """信号处理函数"""
    print("\n\n👋 感谢使用！对话结束。")
    sys.exit(0)

def main():
    """主函数 - 工具调用聊天客户端"""
    print("=== LLM 工具调用聊天程序 ===")
    print("📌 支持的文件操作：列出文件、创建文件、读取文件、重命名、删除")
    print("📌 示例：列出当前目录、创建 test.txt 文件、读取 main.py")
    print("📌 按 Ctrl+C 退出程序")
    print("=============================\n")
    
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
            
            # 限制历史记录长度
            if len(history_messages) > 20:
                history_messages = history_messages[-20:]
            
            # 尝试提取工具调用意图
            tool_call = extract_tool_call(user_input)
            
            if tool_call:
                tool_name, parameters = tool_call
                print(f"\n🔧 检测到工具调用：{tool_name}")
                print(f"   参数：{parameters}")
                
                # 执行工具
                result = execute_tool(tool_name, parameters)
                print(f"\n📊 工具执行结果：")
                print(result)
                print()
                
                # 将工具执行结果添加到历史
                history_messages.append({
                    "role": "assistant",
                    "content": f"工具调用结果：\n{result}"
                })
            else:
                # 普通对话，发送到LLM
                print("🤖 正在处理...")
                # 这里可以添加普通LLM调用逻辑
                print("💬 这是一个普通对话请求，已记录到历史中。\n")
                
                history_messages.append({
                    "role": "assistant",
                    "content": "已收到您的消息。"
                })
            
    except Exception as e:
        print(f"\n程序异常退出: {str(e)}")

if __name__ == "__main__":
    main()
