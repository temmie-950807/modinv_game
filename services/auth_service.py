# services/auth_service.py
from models.database import find_user, register_user, verify_user_credentials

def find_account(username):
    """查詢使用者帳號"""
    return find_user(username)

def register_account(username, password):
    """註冊新帳號
    
    Args:
        username: 使用者名稱
        password: 使用者密碼
        
    Returns:
        bool: 註冊是否成功
    """
    return register_user(username, password)

def verify_account(username, password):
    """驗證帳號密碼
    
    Args:
        username: 使用者名稱
        password: 使用者密碼
        
    Returns:
        bool: 驗證是否成功
    """
    return verify_user_credentials(username, password)