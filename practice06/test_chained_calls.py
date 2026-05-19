"""
链式工具调用测试脚本
"""
import sys
sys.path.append('.')

from chat_client import execute_chained_tool_call

def test_file_search_chain():
    """测试1：文件搜索链式调用"""
    print("=== 测试1：文件搜索链式调用 ===")
    print("用户请求：查找 practice05目录下所有包含'def'关键词的文件，并总结这些文件的主要内容")
    print("=" * 60)
    
    result = execute_chained_tool_call(
        "查找 practice05目录下所有包含'def'关键词的文件，并总结这些文件的主要内容",
        max_iterations=5
    )
    
    print("\n测试结果:")
    print(result)
    print("\n" + "=" * 60 + "\n")

def test_skill_query():
    """测试2：技能查询链式调用"""
    print("=== 测试2：技能查询链式调用 ===")
    print("用户请求：我想了解 notice 技能的详细规则")
    print("=" * 60)
    
    result = execute_chained_tool_call(
        "我想了解 notice 技能的详细规则",
        max_iterations=3
    )
    
    print("\n测试结果:")
    print(result)
    print("\n" + "=" * 60 + "\n")

def test_web_page_chain():
    """测试3：网页处理链式调用"""
    print("=== 测试3：网页处理链式调用 ===")
    print("用户请求：访问 http://163.com/news/article/KRGTR2H0000189FH.html 并提取页面标题，保存到 practice06/title.txt")
    print("=" * 60)
    
    result = execute_chained_tool_call(
        "访问 http://163.com/news/article/KRGTR2H0000189FH.html 并提取页面标题，保存到 practice06/title.txt",
        max_iterations=5
    )
    
    print("\n测试结果:")
    print(result)
    print("\n" + "=" * 60 + "\n")

def main():
    print("=== 链式工具调用测试 ===")
    print()
    
    # 测试1：文件搜索链式调用
    test_file_search_chain()
    
    # 测试2：技能查询链式调用
    test_skill_query()
    
    # 测试3：网页处理链式调用
    test_web_page_chain()
    
    print("=== 所有测试完成 ===")

if __name__ == "__main__":
    main()
