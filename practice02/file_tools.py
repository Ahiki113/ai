"""
文件操作工具模块 - 提供基础的文件系统操作功能

功能列表：
1. list_files - 列出目录下文件及其属性
2. rename_file - 重命名文件
3. delete_file - 删除文件
4. create_file - 创建文件并写入内容
5. read_file - 读取文件内容
"""
import os
import stat
import time
from typing import Dict, List, Any

def list_files(directory: str) -> str:
    """
    列出指定目录下的所有文件和子目录
    
    Args:
        directory: 目标目录路径
        
    Returns:
        文件列表字符串，包含文件名、大小、修改时间等信息
    """
    try:
        # 检查目录是否存在
        if not os.path.exists(directory):
            return f"❌ 错误：目录 '{directory}' 不存在"
        
        if not os.path.isdir(directory):
            return f"❌ 错误：'{directory}' 不是有效的目录"
        
        # 获取目录内容
        entries = os.listdir(directory)
        if not entries:
            return f"📂 目录 '{directory}' 为空"
        
        # 构建结果列表
        result = [f"📂 目录 '{directory}' 的内容："]
        result.append("-" * 80)
        result.append(f"{'文件名':<30} {'类型':<10} {'大小':<12} {'修改时间':<20}")
        result.append("-" * 80)
        
        for entry in sorted(entries):
            full_path = os.path.join(directory, entry)
            
            # 获取文件属性
            try:
                file_stat = os.stat(full_path)
                
                # 判断类型
                if os.path.isdir(full_path):
                    file_type = "目录"
                    size = "-"
                elif os.path.isfile(full_path):
                    file_type = "文件"
                    size = format_size(file_stat.st_size)
                elif os.path.islink(full_path):
                    file_type = "链接"
                    size = "-"
                else:
                    file_type = "其他"
                    size = "-"
                
                # 获取修改时间
                mtime = time.localtime(file_stat.st_mtime)
                modify_time = time.strftime("%Y-%m-%d %H:%M:%S", mtime)
                
                result.append(f"{entry:<30} {file_type:<10} {size:<12} {modify_time:<20}")
            except Exception as e:
                result.append(f"{entry:<30} {'未知':<10} {'-':<12} {'-':<20}")
        
        result.append("-" * 80)
        result.append(f"总计：{len(entries)} 个项目")
        
        return "\n".join(result)
        
    except Exception as e:
        return f"❌ 列出文件失败：{str(e)}"

def rename_file(old_path: str, new_name: str) -> str:
    """
    重命名指定文件
    
    Args:
        old_path: 原文件完整路径
        new_name: 新文件名（仅文件名，不含路径）
        
    Returns:
        操作结果消息
    """
    try:
        # 检查原文件是否存在
        if not os.path.exists(old_path):
            return f"❌ 错误：文件 '{old_path}' 不存在"
        
        if not os.path.isfile(old_path):
            return f"❌ 错误：'{old_path}' 不是有效的文件"
        
        # 获取目录路径
        directory = os.path.dirname(old_path)
        new_path = os.path.join(directory, new_name)
        
        # 检查新文件是否已存在
        if os.path.exists(new_path):
            return f"❌ 错误：文件 '{new_path}' 已存在"
        
        # 执行重命名
        os.rename(old_path, new_path)
        
        return f"✅ 文件重命名成功：\n   原路径：{old_path}\n   新路径：{new_path}"
        
    except Exception as e:
        return f"❌ 重命名失败：{str(e)}"

def delete_file(file_path: str) -> str:
    """
    删除指定文件
    
    Args:
        file_path: 要删除的文件完整路径
        
    Returns:
        操作结果消息
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return f"❌ 错误：文件 '{file_path}' 不存在"
        
        if not os.path.isfile(file_path):
            return f"❌ 错误：'{file_path}' 不是有效的文件"
        
        # 执行删除
        os.remove(file_path)
        
        return f"✅ 文件删除成功：{file_path}"
        
    except Exception as e:
        return f"❌ 删除失败：{str(e)}"

def create_file(directory: str, file_name: str, content: str = "") -> str:
    """
    在指定目录下创建新文件并写入内容
    
    Args:
        directory: 目标目录路径
        file_name: 新文件名
        content: 要写入的内容（可选）
        
    Returns:
        操作结果消息
    """
    try:
        # 检查目录是否存在
        if not os.path.exists(directory):
            return f"❌ 错误：目录 '{directory}' 不存在"
        
        if not os.path.isdir(directory):
            return f"❌ 错误：'{directory}' 不是有效的目录"
        
        # 构建完整路径
        full_path = os.path.join(directory, file_name)
        
        # 检查文件是否已存在
        if os.path.exists(full_path):
            return f"❌ 错误：文件 '{full_path}' 已存在"
        
        # 创建文件并写入内容
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"✅ 文件创建成功：{full_path}\n   写入内容长度：{len(content)} 字符"
        
    except Exception as e:
        return f"❌ 创建文件失败：{str(e)}"

def read_file(file_path: str) -> str:
    """
    读取指定文件的内容
    
    Args:
        file_path: 要读取的文件完整路径
        
    Returns:
        文件内容或错误消息
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return f"❌ 错误：文件 '{file_path}' 不存在"
        
        if not os.path.isfile(file_path):
            return f"❌ 错误：'{file_path}' 不是有效的文件"
        
        # 获取文件大小
        file_size = os.path.getsize(file_path)
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 如果文件较大，只显示前2000字符
        if file_size > 2000:
            preview = content[:2000] + "\n\n...（文件内容已截断，共 {} 字符）".format(len(content))
            return f"📄 文件内容（{file_path}）：\n{preview}"
        else:
            return f"📄 文件内容（{file_path}）：\n{content}"
        
    except UnicodeDecodeError:
        return f"❌ 无法读取文件：文件不是UTF-8编码格式"
    except Exception as e:
        return f"❌ 读取文件失败：{str(e)}"

def format_size(bytes_size: int) -> str:
    """
    格式化文件大小为人类可读的字符串
    
    Args:
        bytes_size: 字节数
        
    Returns:
        格式化后的大小字符串
    """
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.2f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.2f} MB"
    else:
        return f"{bytes_size / (1024 * 1024 * 1024):.2f} GB"

# 工具注册列表 - 用于LLM工具调用
TOOLS = [
    {
        "name": "list_files",
        "description": "列出指定目录下的所有文件和子目录，包含文件名、大小、类型、修改时间等信息",
        "parameters": {
            "directory": {
                "type": "string",
                "description": "目标目录的完整路径",
                "required": True
            }
        }
    },
    {
        "name": "rename_file",
        "description": "重命名指定的文件",
        "parameters": {
            "old_path": {
                "type": "string",
                "description": "原文件的完整路径",
                "required": True
            },
            "new_name": {
                "type": "string",
                "description": "新的文件名（仅文件名，不含路径）",
                "required": True
            }
        }
    },
    {
        "name": "delete_file",
        "description": "删除指定的文件",
        "parameters": {
            "file_path": {
                "type": "string",
                "description": "要删除的文件完整路径",
                "required": True
            }
        }
    },
    {
        "name": "create_file",
        "description": "在指定目录下创建新文件并写入内容",
        "parameters": {
            "directory": {
                "type": "string",
                "description": "目标目录的完整路径",
                "required": True
            },
            "file_name": {
                "type": "string",
                "description": "新文件的名称",
                "required": True
            },
            "content": {
                "type": "string",
                "description": "要写入文件的内容（可选）",
                "required": False
            }
        }
    },
    {
        "name": "read_file",
        "description": "读取指定文件的内容",
        "parameters": {
            "file_path": {
                "type": "string",
                "description": "要读取的文件完整路径",
                "required": True
            }
        }
    }
]

def get_tool_by_name(name: str):
    """根据工具名称获取工具定义"""
    for tool in TOOLS:
        if tool["name"] == name:
            return tool
    return None

if __name__ == "__main__":
    # 测试工具函数
    print("=== 文件工具模块测试 ===")
    
    # 测试 list_files
    print("\n1. 测试列出文件：")
    print(list_files("."))
    
    # 测试 create_file
    print("\n2. 测试创建文件：")
    print(create_file(".", "test_file.txt", "Hello, World!\n这是一个测试文件。"))
    
    # 测试 read_file
    print("\n3. 测试读取文件：")
    print(read_file("./test_file.txt"))
    
    # 测试 rename_file
    print("\n4. 测试重命名文件：")
    print(rename_file("./test_file.txt", "renamed_file.txt"))
    
    # 测试 delete_file
    print("\n5. 测试删除文件：")
    print(delete_file("./renamed_file.txt"))
