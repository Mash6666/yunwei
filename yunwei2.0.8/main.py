#!/usr/bin/env python3
"""
智能运维助手 - Web应用主程序
基于FastAPI的智能Linux系统运维工具

这是智能运维助手的主入口文件，提供Web界面访问。
运行此文件将启动Web服务器，用户可以通过浏览器访问智能运维功能。
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

# 导入日志系统
from logger_config import get_logger, log_operation, log_system_info

# 获取主logger
main_logger = get_logger("main")

def check_dependencies():
    """检查依赖是否安装"""
    print("检查Web应用依赖...")
    log_operation("开始检查依赖包")

    required_packages = [
        'fastapi',
        'uvicorn',
        'websockets',
        'pydantic'
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
            print(f"[OK] {package} 已安装")
            main_logger.info(f"依赖包检查通过: {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"[ERROR] {package} 未安装")
            main_logger.error(f"依赖包缺失: {package}")

    if missing_packages:
        error_msg = f"缺少依赖包: {', '.join(missing_packages)}"
        print(f"\n{error_msg}")
        print("请运行: pip install -r requirements.txt")
        log_operation("依赖检查失败", {"missing_packages": missing_packages}, level="error")
        return False

    success_msg = "所有依赖检查通过!"
    print(success_msg)
    log_operation("依赖检查成功", {"checked_packages": required_packages})
    return True

def start_web_server():
    """启动Web服务器"""
    print("\n" + "=" * 60)
    print("Web服务信息:")
    print("-" * 40)
    print("  地址: http://localhost:8000")
    print("  功能: 智能运维分析、监控、诊断")
    print("  状态: 正在启动...")
    print("=" * 60)

    # 设置环境变量
    env = os.environ.copy()
    env['PYTHONPATH'] = str(Path(__file__).parent)

    try:
        # 启动uvicorn服务器
        cmd = [
            sys.executable, '-m', 'uvicorn',
            'web_app:app',
            '--host', '0.0.0.0',
            '--port', '8000',
            '--reload',
            '--log-level', 'info'
        ]

        print("\n✅ Web服务已启动成功!")
        print("📱 访问地址: http://localhost:8000")
        print("🛑 按 Ctrl+C 停止服务")

        # 等待服务器启动
        subprocess.run(cmd, env=env)

    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"启动失败: {e}")
        return False

    return True

def open_browser():
    """打开浏览器"""
    def delayed_open():
        time.sleep(2)  # 等待服务器启动
        try:
            webbrowser.open('http://localhost:8000')
            print("已在浏览器中打开 http://localhost:8000")
        except:
            print("无法自动打开浏览器，请手动访问 http://localhost:8000")

    import threading
    thread = threading.Thread(target=delayed_open)
    thread.daemon = True
    thread.start()

def main():
    """智能运维助手主程序入口"""
    # 记录系统启动信息
    log_system_info()

    print("=" * 60)
    print("           智能运维助手 v1.0 - Web版")
    print("        Smart Operations Assistant - Web Edition")
    print("=" * 60)
    print("正在启动Web服务...")

    log_operation("智能运维助手启动", {"version": "1.0", "mode": "web"})

    # 检查依赖
    if not check_dependencies():
        log_operation("系统启动失败 - 依赖检查未通过", level="error")
        sys.exit(1)

    # 自动打开浏览器
    print("正在自动打开浏览器...")
    open_browser()
    log_operation("正在启动Web服务器", {"host": "0.0.0.0", "port": 8000})

    # 启动服务器
    try:
        start_web_server()
    except Exception as e:
        main_logger.error(f"Web服务器启动失败: {e}")
        log_operation("Web服务器启动失败", {"error": str(e)}, level="error")
        sys.exit(1)

if __name__ == "__main__":
    main()