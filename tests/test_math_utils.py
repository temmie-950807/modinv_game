import sys
import os
import unittest
import random
from unittest.mock import patch

# 添加專案根目錄到 Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.math_utils import is_prime, get_primes, extended_gcd, mod_inverse, generate_question

class TestMathUtils(unittest.TestCase):
    """測試 math_utils.py 中的數學函數"""

    def test_is_prime(self):
        """測試質數檢查函數"""
        # 測試一些已知的質數
        known_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
        for prime in known_primes:
            self.assertTrue(is_prime(prime), f"{prime} 應該是質數")
        
        # 測試一些已知的非質數
        known_non_primes = [1, 4, 6, 8, 9, 10, 12, 14, 15, 16, 18, 20, 21, 22]
        for non_prime in known_non_primes:
            self.assertFalse(is_prime(non_prime), f"{non_prime} 不應該是質數")

    def test_get_primes(self):
        """測試獲取指定範圍內的質數函數"""
        # 測試範圍內的質數
        primes_2_to_20 = [2, 3, 5, 7, 11, 13, 17, 19]
        self.assertEqual(get_primes(2, 20), primes_2_to_20)
        
        # 測試邊界情況
        self.assertEqual(get_primes(1, 1), [])  # 1 不是質數
        self.assertEqual(get_primes(2, 2), [2])
        
        # 測試空範圍
        self.assertEqual(get_primes(4, 4), [])  # 4 不是質數
        self.assertEqual(get_primes(14, 16), [])  # 此範圍內沒有質數

    def test_extended_gcd(self):
        """測試擴展歐幾里德算法"""
        # 測試已知結果的情況
        self.assertEqual(extended_gcd(35, 15), (5, 1, -2))  # gcd(35, 15) = 5, 1*35 - 2*15 = 5
        self.assertEqual(extended_gcd(12, 8), (4, 1, -1))   # gcd(12, 8) = 4, 1*12 - 1*8 = 4
        self.assertEqual(extended_gcd(3, 5), (1, 2, -1))    # gcd(3, 5) = 1, 2*3 + (-1)*5 = 1
        
        # 測試最大公約數為1的情況（互質）
        gcd, x, y = extended_gcd(7, 13)
        self.assertEqual(gcd, 1)
        self.assertEqual(7*x + 13*y, 1)
        
        # 測試當 a 為 0 的情況
        self.assertEqual(extended_gcd(0, 5), (5, 0, 1))

    def test_mod_inverse(self):
        """測試模反元素計算函數"""
        # 測試已知的模反元素
        self.assertEqual(mod_inverse(3, 11), 4)  # 3 * 4 ≡ 1 (mod 11)
        self.assertEqual(mod_inverse(5, 11), 9)  # 5 * 9 ≡ 1 (mod 11)
        self.assertEqual(mod_inverse(7, 11), 8)  # 7 * 8 ≡ 1 (mod 11)
        
        # 測試結果的有效性
        a, m = 17, 23
        inv = mod_inverse(a, m)
        self.assertEqual((a * inv) % m, 1)
        
        # 測試當不存在模反元素時（a 和 m 不互質）
        self.assertIsNone(mod_inverse(2, 4))
        self.assertIsNone(mod_inverse(6, 9))

    @patch('random.choice')
    @patch('random.randint')
    def test_generate_question(self, mock_randint, mock_choice):
        """測試問題生成函數"""
        # 設置模擬返回值
        mock_choice.return_value = 11  # p = 11
        mock_randint.return_value = 3  # a = 3
        
        # 測試問題生成
        DIFFICULTY_BOUNDS = {
            'easy': 50,
            'medium': 100,
            'hard': 200
        }
        
        question = generate_question('easy', DIFFICULTY_BOUNDS)
        
        # 驗證問題內容
        self.assertEqual(question['p'], 11)
        self.assertEqual(question['a'], 3)
        self.assertEqual(question['answer'], 4)  # 3 * 4 ≡ 1 (mod 11)
        self.assertIn('time_started', question)

    def test_real_generate_question(self):
        """測試實際問題生成（隨機情況）"""
        DIFFICULTY_BOUNDS = {
            'easy': 50,
            'medium': 100,
            'hard': 200
        }
        
        # 測試不同難度的問題生成
        for difficulty in DIFFICULTY_BOUNDS:
            question = generate_question(difficulty, DIFFICULTY_BOUNDS)
            
            # 驗證問題格式
            self.assertIn('p', question)
            self.assertIn('a', question)
            self.assertIn('answer', question)
            self.assertIn('time_started', question)
            
            # 驗證問題中質數與答案的有效性
            self.assertTrue(is_prime(question['p']))
            self.assertTrue(1 < question['a'] < question['p'])
            
            # 驗證答案的正確性
            self.assertEqual((question['a'] * question['answer']) % question['p'], 1)
            
            # 驗證難度邊界
            self.assertLessEqual(question['p'], DIFFICULTY_BOUNDS[difficulty])

if __name__ == '__main__':
    unittest.main()