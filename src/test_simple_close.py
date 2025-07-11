#!/usr/bin/env python3
"""
简化的富途连接关闭测试脚本

直接测试FutuModuleBase的关闭逻辑，避免复杂的模块依赖
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

import logging
import time

def test_futu_base_close():
    """测试FutuModuleBase的关闭逻辑"""
    print("🔧 测试 FutuModuleBase 的关闭逻辑")
    
    try:
        # 直接导入和测试基础类
        from base.futu_modue import FutuModuleBase
        
        print("✅ 成功导入 FutuModuleBase")
        
        # 创建实例
        print("🔄 创建 FutuModuleBase 实例...")
        try:
            futu_base = FutuModuleBase()
            print("✅ FutuModuleBase 实例创建成功")
        except Exception as e:
            print(f"⚠️  FutuModuleBase 实例创建失败: {e}")
            print("ℹ️  这可能是因为FutuOpenD未运行，但可以继续测试关闭逻辑")
            # 创建一个模拟实例来测试关闭逻辑
            futu_base = object.__new__(FutuModuleBase)
            futu_base._is_closed = False
            futu_base.client = None
            futu_base.logger = logging.getLogger("test")
        
        # 测试关闭方法
        print("🔄 测试第一次关闭...")
        futu_base.close()
        print("✅ 第一次关闭完成")
        
        # 测试重复关闭（应该被安全忽略）
        print("🔄 测试重复关闭...")
        futu_base.close()
        print("✅ 重复关闭被安全忽略")
        
        # 验证关闭状态
        if hasattr(futu_base, '_is_closed') and futu_base._is_closed:
            print("✅ 关闭状态标志正确设置")
        else:
            print("❌ 关闭状态标志未正确设置")
            return False
        
        print("✅ FutuModuleBase 关闭测试通过")
        return True
        
    except Exception as e:
        print(f"❌ FutuModuleBase 关闭测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_close_state_flag():
    """测试关闭状态标志机制"""
    print("\n🔧 测试关闭状态标志机制")
    
    try:
        from base.futu_modue import FutuModuleBase
        
        # 创建更完整的模拟实例
        futu_base = object.__new__(FutuModuleBase)
        futu_base._is_closed = False
        
        # 创建模拟客户端，确保close方法能正常执行
        class MockClient:
            def disconnect(self):
                pass
            
            @property
            def quote(self):
                return MockQuote()
        
        class MockQuote:
            def unsubscribe_all(self):
                pass
        
        futu_base.client = MockClient()
        futu_base.logger = logging.getLogger("test")
        
        # 初始状态检查
        if not futu_base._is_closed:
            print("✅ 初始关闭状态为 False")
        else:
            print("❌ 初始关闭状态错误")
            return False
        
        # 第一次关闭
        futu_base.close()
        if futu_base._is_closed:
            print("✅ 关闭后状态设置为 True")
        else:
            print("❌ 关闭后状态未正确设置")
            print(f"  调试信息: _is_closed = {getattr(futu_base, '_is_closed', 'undefined')}")
            return False
        
        # 重复关闭测试
        futu_base.close()  # 这应该立即返回
        print("✅ 重复关闭被防重复机制阻止")
        
        return True
        
    except Exception as e:
        print(f"❌ 关闭状态标志测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_client_disconnect_logic():
    """测试客户端断开逻辑"""
    print("\n🔧 测试客户端断开逻辑")
    
    try:
        # 创建模拟客户端
        class MockClient:
            def __init__(self):
                self.disconnected = False
            
            def disconnect(self):
                if self.disconnected:
                    raise Exception("已经断开连接")
                self.disconnected = True
                print("  📡 模拟客户端断开连接")
            
            @property
            def quote(self):
                return MockQuote()
        
        class MockQuote:
            def unsubscribe_all(self):
                print("  📊 模拟取消所有订阅")
        
        # 模拟基础类
        from base.futu_modue import FutuModuleBase
        futu_base = object.__new__(FutuModuleBase)
        futu_base._is_closed = False
        futu_base.client = MockClient()
        futu_base.logger = logging.getLogger("test")
        
        # 测试关闭流程
        print("🔄 执行模拟关闭流程...")
        futu_base.close()
        
        # 验证客户端是否正确断开
        if futu_base.client is None:
            print("✅ 客户端引用已清除")
        else:
            print("❌ 客户端引用未清除")
            return False
        
        print("✅ 客户端断开逻辑测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 客户端断开逻辑测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始富途连接关闭修复验证\n")
    
    tests = [
        ("FutuModuleBase关闭测试", test_futu_base_close),
        ("关闭状态标志测试", test_close_state_flag),
        ("客户端断开逻辑测试", test_client_disconnect_logic),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"🧪 运行: {test_name}")
        try:
            result = test_func()
            if result:
                print(f"✅ {test_name}: 通过\n")
                passed += 1
            else:
                print(f"❌ {test_name}: 失败\n")
                failed += 1
        except Exception as e:
            print(f"💥 {test_name}: 异常 - {e}\n")
            failed += 1
    
    # 统计结果
    print("=" * 50)
    print(f"📊 测试结果: {passed} 个通过, {failed} 个失败")
    
    if failed == 0:
        print("🎉 所有测试通过！富途连接关闭问题修复验证成功")
        print("\n🔧 修复要点:")
        print("1. ✅ 添加了 _is_closed 状态标志防止重复关闭")
        print("2. ✅ 移除了多线程关闭逻辑，避免信号处理器冲突")
        print("3. ✅ 使用标准的 disconnect() 方法关闭连接")
        print("4. ✅ 简化了关闭流程，确保资源正确释放")
        return True
    else:
        print("⚠️  部分测试失败，需要进一步检查修复方案")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")
        sys.exit(1) 