#!/usr/bin/env python3
"""简单测试修复方案功能"""

import asyncio
import sys
import os
sys.path.insert(0, os.getcwd())

async def test_basic_functionality():
    """测试基本功能"""
    print("测试智能运维助手基本功能")
    print("=" * 40)

    try:
        # 测试导入
        print("1. 测试模块导入...")
        from ops_graph import OpsAssistantGraph
        from analyzer import SystemAnalyzer
        from states import AlertLevel, SystemStatus
        print("   导入成功")

        # 测试运维助手创建
        print("2. 测试运维助手创建...")
        ops_assistant = OpsAssistantGraph()
        print("   创建成功")

        # 测试分析器创建
        print("3. 测试AI分析器创建...")
        analyzer = SystemAnalyzer()
        print("   创建成功")

        # 测试当前状态获取
        print("4. 测试状态获取...")
        state = ops_assistant.get_current_state()
        print(f"   状态获取成功: {state['system_status'].value}")

        print("\n所有基本功能测试通过!")
        return True

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("智能运维助手简单测试")
    print("=" * 30)

    success = asyncio.run(test_basic_functionality())

    if success:
        print("\n测试完成 - 系统正常工作")
        print("可以使用以下命令启动:")
        print("  python start_web.py  # 启动Web界面")
        print("  python main.py -i    # 启动CLI界面")
    else:
        print("\n测试失败 - 请检查配置")

if __name__ == "__main__":
    main()
