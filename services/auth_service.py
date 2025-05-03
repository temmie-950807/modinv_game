# services/auth_service.py
from models.database import find_user, add_user, verify_user

def find_account(username):
    """查詢使用者帳號"""
    return find_user(username)

def register_account(username, password):
    """註冊新帳號"""
    return add_user(username, password)

def verify_account(username, password):
    """驗證帳號密碼"""
    return verify_user(username, password)