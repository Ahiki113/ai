"""
技能系统测试脚本
"""
import sys
sys.path.append('.')

from chat_client import list_available_skills, load_skill_content, is_skill_request

def test_skills():
    print("=== 技能系统测试 ===")
    
    print("\n1. 测试 list_available_skills()")
    skills = list_available_skills()
    print("找到", len(skills), "个技能:")
    for skill in skills:
        print("  -", skill['name'] + ":", skill['description'])
    
    print("\n2. 测试 load_skill_content()")
    if skills:
        skill_name = skills[0]['name']
        content = load_skill_content(skill_name)
        if content:
            print("成功加载技能", skill_name, "的内容")
            print("内容预览:")
            print(content[:200], "...")
        else:
            print("无法加载技能", skill_name)
    
    print("\n3. 测试 is_skill_request()")
    test_cases = [
        "帮我写一个通知",
        "撰写关于五一节放假的通知",
        "修改通知内容",
        "润色一下通知",
        "你好",
        "帮我查一下资料"
    ]
    
    for test in test_cases:
        result = is_skill_request(test)
        print("  '", test, "' ->", result)
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_skills()
