#!/usr/bin/env python3
"""
简单的测试运行脚本
直接运行监控模块的测试
"""

import unittest
import sys
import os

# 确保在src目录下运行
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_test_module(module_name):
    """运行单个测试模块"""
    print(f"\n{'='*60}")
    print(f"运行测试: {module_name}")
    print(f"{'='*60}")
    
    try:
        # 导入测试模块
        module = __import__(f'tests.{module_name}', fromlist=[''])
        
        # 创建测试套件
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(module)
        
        # 运行测试
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        # 返回结果
        success = result.wasSuccessful()
        print(f"\n{'✅' if success else '❌'} {module_name}: {result.testsRun} 测试, {len(result.failures)} 失败, {len(result.errors)} 错误")
        
        return success
        
    except Exception as e:
        print(f"❌ 无法运行测试 {module_name}: {e}")
        return False

def main():
    """主函数"""
    print("🚀 监控模块测试运行器")
    
    # 定义测试模块
    test_modules = [
        'test_indicators',
        'test_ui_components', 
        'test_data_flow',
        'test_performance',
        'test_futu_interface',
        'test_monitor_integration'
    ]
    
    if len(sys.argv) > 1:
        # 运行指定的测试模块
        test_modules = [arg for arg in sys.argv[1:] if arg.startswith('test_')]
    
    success_count = 0
    total_count = len(test_modules)
    
    # 运行每个测试模块
    for module in test_modules:
        success = run_test_module(module)
        if success:
            success_count += 1
    
    # 打印总结
    print(f"\n{'='*60}")
    print(f"测试总结: {success_count}/{total_count} 个模块通过")
    print(f"{'='*60}")
    
    if success_count == total_count:
        print("🎉 所有测试通过!")
        return 0
    else:
        print(f"💥 {total_count - success_count} 个模块失败!")
        return 1

if __name__ == '__main__':
    sys.exit(main())