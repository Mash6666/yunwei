#!/usr/bin/env python3
"""
启动Web应用脚本
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def check_dependencies():
    """检查依赖是否安装"""
    print("检查Web应用依赖...")

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
        except ImportError:
            missing_packages.append(package)
            print(f"[ERROR] {package} 未安装")

    if missing_packages:
        print(f"\n缺少依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False

    print("所有依赖检查通过!")
    return True

def start_web_server():
    """启动Web服务器"""
    print("\n启动智能运维助手Web服务...")
    print("=" * 50)

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

        print("服务器地址: http://localhost:8000")
        print("按 Ctrl+C 停止服务器")
        print("=" * 50)

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
    """主函数"""
    print("智能运维助手Web应用启动器")
    print("=" * 50)

    # 检查依赖
    if not check_dependencies():
        sys.exit(1)

    # 询问是否打开浏览器
    try:
        response = input("\n是否自动打开浏览器? (y/n): ").lower().strip()
        if response in ['y', 'yes', '是']:
            open_browser()
    except KeyboardInterrupt:
        print("\n启动取消")
        sys.exit(0)

    # 启动服务器
    start_web_server()

if __name__ == "__main__":
    main()