#!/usr/bin/env python3
"""
创建测试数据
"""

import requests
import json

def create_test_fix_plan():
    """创建测试修复方案"""
    base_url = "http://localhost:8001"

    fix_plan = {
        "id": "plan_1",
        "issue": "系统负载过高测试",
        "description": "用于测试命令编辑功能的测试方案",
        "priority": "medium",
        "commands": [
            {
                "step": 1,
                "description": "显示系统进程",
                "command": "top -b -n 1 | head -n 17",
                "timeout": 30
            }
        ],
        "risk_level": "low",
        "preconditions": [],
        "rollback_commands": [],
        "verification_commands": []
    }

    # 保存修复方案
    response = requests.post(
        f"{base_url}/api/save-fix-plans",
        json={"fix_plans": [fix_plan]}
    )

    print(f"保存修复方案响应: {response.status_code}")
    print(f"响应内容: {response.text}")

    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print("✅ 测试修复方案创建成功!")
            return True
        else:
            print(f"❌ 创建失败: {result.get('error', '未知错误')}")
            return False
    else:
        print(f"❌ HTTP错误: {response.status_code}")
        return False

def test_command_edit():
    """测试命令编辑"""
    base_url = "http://localhost:8001"

    edit_data = {
        "plan_id": "plan_1",
        "command_index": 0,
        "new_command": "top -b -n 1 | head -n 20",
        "original_command": "top -b -n 1 | head -n 17"
    }

    response = requests.post(
        f"{base_url}/api/command/edit",
        json=edit_data
    )

    print(f"编辑命令响应: {response.status_code}")
    print(f"响应内容: {response.text}")

    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print("✅ 命令编辑测试成功!")
            return True
        else:
            print(f"❌ 编辑失败: {result.get('error', '未知错误')}")
            return False
    else:
        print(f"❌ HTTP错误: {response.status_code}")
        return False

def main():
    """主函数"""
    print("🧪 创建测试数据和验证代码编辑功能")
    print("=" * 50)

    # 创建测试数据
    if create_test_fix_plan():
        print()
        # 测试编辑功能
        test_command_edit()

    print("\n🎯 代码编辑功能验证完成!")

if __name__ == "__main__":
    main()