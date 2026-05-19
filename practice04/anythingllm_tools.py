"""
AnythingLLM 工具模块 - 纯requests实现，无编码问题
"""
import os
import json
import requests
from dotenv import load_dotenv

def load_config():
    """加载配置文件"""
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
    
    config = {
        'anythingllm_url': os.getenv('ANYTHINGLLM_URL', 'http://localhost:3001'),
        'anythingllm_api_key': os.getenv('ANYTHINGLLM_API_KEY', '168HZGR-ZG0M3H5-GP5270V-NVH9B9M'),
        'default_workspace': os.getenv('ANYTHINGLLM_WORKSPACE', 'default')
    }
    return config

def anythingllm_query(message, workspace_slug=None):
    """
    调用 AnythingLLM 聊天API（无编码问题版本）
    """
    config = load_config()
    workspace = workspace_slug or config['default_workspace']
    api_url = f"{config['anythingllm_url']}/api/v1/workspace/{workspace}/chat"
    
    headers = {
        "Authorization": f"Bearer {config['anythingllm_api_key']}",
        "Content-Type": "application/json; charset=utf-8"
    }
    request_data = {
        "message": message,
        "format": "json"
    }
    
    try:
        # 设置编码为utf-8，避免Windows的GBK问题
        response = requests.post(
            api_url, 
            headers=headers, 
            json=request_data, 
            timeout=10
        )
        
        if response.status_code == 200:
            # 强制用utf-8解码响应内容
            response.encoding = 'utf-8'
            response_data = response.json()
            
            if 'response' in response_data:
                return response_data['response']
            elif 'content' in response_data:
                return response_data['content']
            elif 'text' in response_data:
                return response_data['text']
            else:
                return json.dumps(response_data, ensure_ascii=False, indent=2)
        else:
            return f"❌ 请求失败 (状态码: {response.status_code})\n错误信息: {response.text}"
            
    except requests.exceptions.ConnectionError:
        return "❌ 连接失败：无法连接到 AnythingLLM 服务，请确认服务已启动且端口正确"
    except requests.exceptions.Timeout:
        return "❌ 请求超时，请稍后重试"
    except Exception as e:
        return f"❌ 请求发生错误: {str(e)}"

def anythingllm_get_workspaces():
    """获取所有工作空间列表"""
    config = load_config()
    api_url = f"{config['anythingllm_url']}/api/v1/workspace"
    
    headers = {
        "Authorization": f"Bearer {config['anythingllm_api_key']}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            response_data = response.json()
            return json.dumps(response_data, ensure_ascii=False, indent=2)
        else:
            return f"❌ 获取失败 (状态码: {response.status_code})\n错误信息: {response.text}"
            
    except Exception as e:
        return f"❌ 获取工作空间失败: {str(e)}"

def anythingllm_get_documents(workspace_slug=None):
    """获取指定工作空间的文档列表"""
    config = load_config()
    workspace = workspace_slug or config['default_workspace']
    api_url = f"{config['anythingllm_url']}/api/v1/workspace/{workspace}/documents"
    
    headers = {
        "Authorization": f"Bearer {config['anythingllm_api_key']}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            response_data = response.json()
            return json.dumps(response_data, ensure_ascii=False, indent=2)
        else:
            return f"❌ 获取失败 (状态码: {response.status_code})\n错误信息: {response.text}"
            
    except Exception as e:
        return f"❌ 获取文档失败: {str(e)}"

# 工具注册列表
ANYTHINGLLM_TOOLS = [
    {
        "name": "anythingllm_query",
        "description": "查询AnythingLLM文档仓库，获取文档相关信息和回答",
        "parameters": {
            "message": {
                "type": "string",
                "description": "用户的查询消息",
                "required": True
            },
            "workspace_slug": {
                "type": "string",
                "description": "工作空间标识，可选，默认为默认工作空间",
                "required": False
            }
        }
    },
    {
        "name": "anythingllm_get_workspaces",
        "description": "获取所有工作空间列表",
        "parameters": {}
    },
    {
        "name": "anythingllm_get_documents",
        "description": "获取指定工作空间的文档列表",
        "parameters": {
            "workspace_slug": {
                "type": "string",
                "description": "工作空间标识，可选，默认为默认工作空间",
                "required": False
            }
        }
    }
]

if __name__ == "__main__":
    print("=== 测试 AnythingLLM 工具 ===")
    print("\n1. 测试查询功能:")
    result = anythingllm_query("你好")
    print(result)
    
    print("\n2. 测试获取工作空间:")
    result = anythingllm_get_workspaces()
    print(result)
    
    print("\n3. 测试获取文档列表:")
    result = anythingllm_get_documents()
    print(result)