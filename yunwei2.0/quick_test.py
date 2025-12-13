print("测试修复方案生成")
import asyncio
import sys
import os
sys.path.insert(0, os.getcwd())

async def test():
    try:
        from ops_graph import OpsAssistantGraph
        ops_assistant = OpsAssistantGraph()
        result = await ops_assistant.run("执行系统检查")
        
        if result["success"]:
            state = result.get("state", {})
            fix_plans = state.get("fix_plans", [])
            print(f"系统检查完成，修复方案数量: {len(fix_plans)}")
            
            if fix_plans:
                for i, plan in enumerate(fix_plans, 1):
                    print(f"方案 {i}: {plan.get('issue', '未指定')}")
                    print(f"  优先级: {plan.get('priority', 'medium')}")
                    print(f"  命令数: {len(plan.get('commands', []))}")
            else:
                print("当前系统状态良好，无需修复方案")
        else:
            print(f"检查失败: {result.get('error', '未知错误')}")
            
    except Exception as e:
        print(f"测试失败: {e}")

asyncio.run(test())
