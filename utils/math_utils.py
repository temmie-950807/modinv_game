# utils/math_utils.py
import random
import math
import time

def is_prime(n):
    """檢查一個數是否為質數"""
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True

def get_primes(start, end):
    """獲取指定範圍內的所有質數"""
    return [num for num in range(start, end + 1) if is_prime(num)]

def extended_gcd(a, b):
    """擴展歐幾里得算法，用於計算模反元素"""
    if a == 0:
        return b, 0, 1
    else:
        gcd, x, y = extended_gcd(b % a, a)
        return gcd, y - (b // a) * x, x

def mod_inverse(a, m):
    """計算模反元素"""
    if math.gcd(a, m) != 1:
        return None  # 不存在模反元素
    else:
        _, x, _ = extended_gcd(a, m)
        return (x % m + m) % m  # 確保結果為正數

def generate_question(difficulty, difficulty_bounds):
    """生成一個有關模反元素的問題"""
    bound = difficulty_bounds[difficulty]
    primes = get_primes(11, bound - 1)
    p = random.choice(primes)
    
    # 選擇 a，確保 a 和 p 互質 (這裡小於 p 的數一定與 p 互質，因為 p 是質數)
    a = random.randint(2, p - 1)
    
    answer = mod_inverse(a, p)
    return {
        'p': p,
        'a': a,
        'answer': answer,
        'time_started': time.time()  # 記錄問題開始時間
    }