"""
通知技能测试脚本
"""
import sys
sys.path.append('.')

from chat_client import load_config, stream_chat_response, load_skill_content

def test_notice_without_department():
    """测试：用户不指定部门，撰写五一节放假通知"""
    print("=== 测试1：用户不指定部门 ===")
    print("用户请求：帮我撰写关于五一节放假的通知")
    
    skill_content = load_skill_content("notice")
    if not skill_content:
        print("错误：无法加载notice技能")
        return
    
    skill_prompt = """
【当前使用技能】
技能名称：notice

【技能内容】
""" + skill_content + """

请根据以上技能内容，按照技能规则响应用户请求：

用户请求：帮我撰写关于五一节放假的通知
"""
    
    messages = [{"role": "system", "content": skill_prompt}]
    response = stream_chat_response(messages)
    
    print("\n=== 测试结果 ===")
    if response.startswith("XX部通知"):
        print("通过！通知以XX部通知开头")
    else:
        print("失败！通知应以XX部通知开头")
        print("实际开头:", response[:20])
    
    return response

def test_notice_with_department():
    """测试：用户指定部门为销售部，撰写五一节放假通知"""
    print("\n=== 测试2：用户指定部门 ===")
    print("用户请求：我是销售部的，帮我撰写关于五一节放假的通知")
    
    skill_content = load_skill_content("notice")
    if not skill_content:
        print("错误：无法加载notice技能")
        return
    
    skill_prompt = """
【当前使用技能】
技能名称：notice

【技能内容】
""" + skill_content + """

请根据以上技能内容，按照技能规则响应用户请求：

用户请求：我是销售部的，帮我撰写关于五一节放假的通知
"""
    
    messages = [{"role": "system", "content": skill_prompt}]
    response = stream_chat_response(messages)
    
    print("\n=== 测试结果 ===")
    if response.startswith("销售部通知"):
        print("通过！通知以销售部通知开头")
    else:
        print("失败！通知应以销售部通知开头")
        print("实际开头:", response[:20])
    
    return response

if __name__ == "__main__":
    print("=== 通知技能测试 ===")
    print("测试场景：")
    print("1. 用户不指定部门，撰写五一节放假通知")
    print("2. 用户指定部门为销售部，撰写五一节放假通知")
    print()
    
    response1 = test_notice_without_department()
    print("\n" + "="*50 + "\n")
    response2 = test_notice_with_department()
    
    print("\n=== 测试完成 ===")
