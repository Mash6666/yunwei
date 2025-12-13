#!/usr/bin/env python3
"""
测试所有组件的导入
"""

import sys
import os

def test_imports():
    """测试所有组件导入"""
    print("Testing imports...")

    try:
        print("1. Testing config module...")
        from config import Config
        print("   Config imported successfully")

        print("2. Testing states module...")
        from states import OpsAssistantState, StateManager, MetricValue, SystemAlert, AlertLevel, SystemStatus
        print("   States imported successfully")

        print("3. Testing monitoring module...")
        from monitoring import PrometheusClient
        print("   Monitoring imported successfully")

        print("4. Testing remote_executor module...")
        from remote_executor import RemoteExecutor
        print("   Remote executor imported successfully")

        print("5. Testing analyzer module...")
        from analyzer import SystemAnalyzer
        print("   Analyzer imported successfully")

        print("6. Testing ops_graph module...")
        from ops_graph import OpsAssistantGraph
        print("   Ops graph imported successfully")

        print("7. Testing main module...")
        from main import SmartOpsAssistant
        print("   Main module imported successfully")

        print("\nAll imports successful! [OK]")

        # Test instantiation (without network operations)
        print("\nTesting instantiation...")
        state_manager = StateManager()
        print("StateManager created successfully")

        prometheus_client = PrometheusClient()
        print("PrometheusClient created successfully")

        system_analyzer = SystemAnalyzer()
        print("SystemAnalyzer created successfully")

        ops_graph = OpsAssistantGraph()
        print("OpsAssistantGraph created successfully")

        print("\nAll components created successfully! [OK]")
        return True

    except Exception as e:
        print(f"\nError during import: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)