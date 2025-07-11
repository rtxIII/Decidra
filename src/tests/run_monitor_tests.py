#!/usr/bin/env python3
"""
监控模块测试运行脚本
提供统一的测试运行入口和结果报告
"""

import unittest
import sys
import os
import argparse
import time
from datetime import datetime
from typing import List, Dict, Any

# 添加src目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_config import TestSuite, TestConfig


class TestRunner:
    """测试运行器"""
    
    def __init__(self, verbosity: int = 2):
        self.verbosity = verbosity
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def run_single_test(self, test_module: str) -> bool:
        """运行单个测试模块"""
        print(f"\n{'='*50}")
        print(f"运行测试模块: {test_module}")
        print(f"{'='*50}")
        
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        try:
            # 动态导入测试模块
            module = __import__(f'tests.{test_module}', fromlist=[''])
            tests = loader.loadTestsFromModule(module)
            suite.addTests(tests)
            
            # 运行测试
            runner = unittest.TextTestRunner(verbosity=self.verbosity)
            result = runner.run(suite)
            
            # 记录结果
            self.results[test_module] = {
                'success': result.wasSuccessful(),
                'tests_run': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors),
                'skipped': len(result.skipped) if hasattr(result, 'skipped') else 0
            }
            
            return result.wasSuccessful()
            
        except ImportError as e:
            print(f"❌ 无法导入测试模块 {test_module}: {e}")
            self.results[test_module] = {
                'success': False,
                'tests_run': 0,
                'failures': 0,
                'errors': 1,
                'skipped': 0,
                'import_error': str(e)
            }
            return False
        except Exception as e:
            print(f"❌ 运行测试模块 {test_module} 时发生错误: {e}")
            self.results[test_module] = {
                'success': False,
                'tests_run': 0,
                'failures': 0,
                'errors': 1,
                'skipped': 0,
                'runtime_error': str(e)
            }
            return False
    
    def run_all_tests(self) -> bool:
        """运行所有测试"""
        print("🚀 开始运行监控模块测试套件")
        print(f"测试配置: {TestConfig.TEST_ENV}")
        
        self.start_time = datetime.now()
        
        # 定义测试模块列表
        test_modules = [
            'test_futu_interface',
            'test_indicators', 
            'test_ui_components',
            'test_data_flow',
            'test_performance',
            'test_monitor_integration'
        ]
        
        success_count = 0
        total_count = len(test_modules)
        
        # 运行每个测试模块
        for module in test_modules:
            success = self.run_single_test(module)
            if success:
                success_count += 1
        
        self.end_time = datetime.now()
        
        # 打印总结果
        self._print_summary(success_count, total_count)
        
        return success_count == total_count
    
    def run_specific_tests(self, test_patterns: List[str]) -> bool:
        """运行特定的测试"""
        print(f"🚀 运行特定测试: {test_patterns}")
        
        self.start_time = datetime.now()
        
        success_count = 0
        total_count = len(test_patterns)
        
        for pattern in test_patterns:
            if '.' in pattern:
                # 格式: module.TestClass.test_method
                parts = pattern.split('.')
                module_name = parts[0]
                success = self.run_single_test(module_name)
            else:
                # 格式: module
                success = self.run_single_test(pattern)
            
            if success:
                success_count += 1
        
        self.end_time = datetime.now()
        
        # 打印总结果
        self._print_summary(success_count, total_count)
        
        return success_count == total_count
    
    def _print_summary(self, success_count: int, total_count: int):
        """打印测试总结"""
        duration = (self.end_time - self.start_time).total_seconds()
        
        print(f"\n{'='*60}")
        print("📊 测试结果总结")
        print(f"{'='*60}")
        print(f"测试开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试结束时间: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总耗时: {duration:.2f} 秒")
        print(f"测试模块总数: {total_count}")
        print(f"成功模块数: {success_count}")
        print(f"失败模块数: {total_count - success_count}")
        print(f"成功率: {(success_count/total_count)*100:.1f}%")
        
        # 详细结果
        print(f"\n{'='*60}")
        print("📋 详细测试结果")
        print(f"{'='*60}")
        
        total_tests = 0
        total_failures = 0
        total_errors = 0
        total_skipped = 0
        
        for module, result in self.results.items():
            status = "✅ 通过" if result['success'] else "❌ 失败"
            print(f"{module:<25} {status}")
            
            if not result['success']:
                if 'import_error' in result:
                    print(f"  └─ 导入错误: {result['import_error']}")
                elif 'runtime_error' in result:
                    print(f"  └─ 运行错误: {result['runtime_error']}")
                else:
                    print(f"  └─ 测试: {result['tests_run']}, 失败: {result['failures']}, 错误: {result['errors']}")
            else:
                print(f"  └─ 测试: {result['tests_run']}, 跳过: {result['skipped']}")
            
            total_tests += result['tests_run']
            total_failures += result['failures']
            total_errors += result['errors']
            total_skipped += result['skipped']
        
        print(f"\n总计:")
        print(f"  测试用例: {total_tests}")
        print(f"  失败: {total_failures}")
        print(f"  错误: {total_errors}")
        print(f"  跳过: {total_skipped}")
        
        # 最终状态
        if success_count == total_count:
            print(f"\n🎉 所有测试通过! 共运行 {total_tests} 个测试用例")
        else:
            print(f"\n💥 测试失败! {total_count - success_count} 个模块失败")
            print("请查看上述详细信息以了解失败原因")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='监控模块测试运行器')
    parser.add_argument(
        '--module', '-m',
        help='运行特定的测试模块 (例如: test_futu_interface)',
        nargs='*'
    )
    parser.add_argument(
        '--verbosity', '-v',
        type=int,
        default=2,
        help='测试输出详细程度 (0-2, 默认: 2)'
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='列出所有可用的测试模块'
    )
    parser.add_argument(
        '--quick', '-q',
        action='store_true',
        help='快速测试模式 (跳过集成测试)'
    )
    parser.add_argument(
        '--coverage', '-c',
        action='store_true',
        help='运行测试覆盖率分析'
    )
    
    args = parser.parse_args()
    
    # 列出可用的测试模块
    if args.list:
        print("可用的测试模块:")
        modules = [
            'test_futu_interface - 富途接口测试',
            'test_indicators - 技术指标测试',
            'test_ui_components - UI组件测试',
            'test_data_flow - 数据流测试',
            'test_performance - 性能监控测试',
            'test_monitor_integration - 集成测试'
        ]
        for module in modules:
            print(f"  {module}")
        return
    
    # 创建测试运行器
    runner = TestRunner(verbosity=args.verbosity)
    
    # 运行测试覆盖率分析
    if args.coverage:
        try:
            import coverage
            cov = coverage.Coverage()
            cov.start()
            
            # 运行测试
            if args.module:
                success = runner.run_specific_tests(args.module)
            else:
                success = runner.run_all_tests()
            
            cov.stop()
            cov.save()
            
            print(f"\n{'='*60}")
            print("📈 测试覆盖率报告")
            print(f"{'='*60}")
            cov.report()
            
        except ImportError:
            print("❌ 需要安装coverage包来运行覆盖率分析: pip install coverage")
            return False
    else:
        # 运行特定模块测试
        if args.module:
            success = runner.run_specific_tests(args.module)
        else:
            # 运行所有测试
            success = runner.run_all_tests()
    
    # 退出代码
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()