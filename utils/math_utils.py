# utils/math_utils.py
import math

def is_prime(n):
    """檢查一個數是否為質數
    
    Args:
        n: 要檢查的數字
        
    Returns:
        bool: 是否為質數
    """
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
    """獲取指定範圍內的所有質數
    
    Args:
        start: 範圍起始（含）
        end: 範圍結束（含）
        
    Returns:
        list: 範圍內的所有質數
    """
    return [num for num in range(start, end + 1) if is_prime(num)]

def gcd(a, b):
    """計算最大公約數
    
    Args:
        a: 第一個數
        b: 第二個數
        
    Returns:
        int: 最大公約數
    """
    while b:
        a, b = b, a % b
    return a

def extended_gcd(a, b):
    """擴展歐幾里得算法，用於計算模反元素
    
    該算法計算 ax + by = gcd(a, b) 中的 x 和 y
    
    Args:
        a: 第一個數
        b: 第二個數
        
    Returns:
        tuple: (gcd, x, y) 其中 ax + by = gcd(a, b)
    """
    if a == 0:
        return b, 0, 1
    else:
        gcd_val, x, y = extended_gcd(b % a, a)
        return gcd_val, y - (b // a) * x, x

def mod_inverse(a, m):
    """計算模反元素
    
    計算 a 在模 m 下的模反元素 x，使得 ax ≡ 1 (mod m)
    
    Args:
        a: 要計算模反元素的數
        m: 模數
        
    Returns:
        int: 模反元素，如果不存在則返回 None
    """
    if math.gcd(a, m) != 1:
        return None  # 不存在模反元素
    else:
        _, x, _ = extended_gcd(a, m)
        return (x % m + m) % m  # 確保結果為正數

def fermat_mod_inverse(a, p):
    """使用費馬小定理計算模反元素
    
    僅適用於 p 為質數且 a 與 p 互質的情況
    根據費馬小定理，a^(p-1) ≡ 1 (mod p)，因此 a^(p-2) ≡ a^(-1) (mod p)
    
    Args:
        a: 要計算模反元素的數
        p: 質數模數
        
    Returns:
        int: 模反元素
    """
    if not is_prime(p) or a % p == 0:
        return None
    
    return pow(a, p - 2, p)

def brute_force_mod_inverse(a, m):
    """暴力法計算模反元素
    
    試算 1 到 m-1 中哪個數乘以 a 後 mod m 得到 1
    
    Args:
        a: 要計算模反元素的數
        m: 模數
        
    Returns:
        int: 模反元素，如果不存在則返回 None
    """
    a = a % m
    for x in range(1, m):
        if (a * x) % m == 1:
            return x
    return None