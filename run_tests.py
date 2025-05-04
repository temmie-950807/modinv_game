#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import unittest
import pytest

def run_unittest():
    """執行所有單元測試（使用 unittest 框架）"""
    print("=" * 70)
    print("執行單元測試（unittest 框架）")
    print("=" * 70)
    
    # 發現並執行所有測試
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests', pattern='test_*.py')
    
    # 運行測試
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # 返回測試結果
    return result.wasSuccessful()

def run_pytest():
    """執行所有單元測試（使用 pytest 框架）"""
    print("=" * 70)
    print("執行單元測試（pytest 框架）")
    print("=" * 70)
    
    # 使用 pytest 運行測試
    result = pytest.main(['-xvs', 'tests'])
    
    # 返回測試結果 (0 表示成功)
    return result == 0

def run_specific_test(test_path):
    """執行指定的測試文件或目錄"""
    print(f"執行指定測試：{test_path}")
    
    if test_path.endswith('.py'):
        # 執行單個測試文件
        return pytest.main(['-xvs', test_path])
    else:
        # 執行整個目錄
        return pytest.main(['-xvs', test_path])

if __name__ == '__main__':
    # 檢查命令行參數
    if len(sys.argv) > 1:
        # 如果指定了測試路徑，僅執行該測試
        test_path = sys.argv[1]
        success = run_specific_test(test_path) == 0
    else:
        # 否則執行所有測試
        # 可以選擇使用 unittest 或 pytest
        # success = run_unittest()
        success = run_pytest()
    
    # 退出碼
    sys.exit(0 if success else 1)