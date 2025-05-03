# routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, session
from functools import wraps
from datetime import timedelta
from services.auth_service import verify_account, register_account

auth_routes = Blueprint('auth', __name__)

# 登入驗證裝飾器
def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapped

@auth_routes.before_request
def refresh_permanent_session():
    if 'username' in session:
        session.permanent = True
        session.permanent_session_lifetime = timedelta(days=30)

@auth_routes.route('/register', methods=['GET','POST'])
def register():
    error = ''
    if request.method=='POST':
        u = request.form['username'].strip()
        p = request.form['password']
        if not u or not p:
            error = '帳號密碼不可空'
        elif not register_account(u, p):
            error = '使用者已存在'
        else:
            return redirect(url_for('auth.login'))
    return render_template('register.html', error=error)

@auth_routes.route('/login', methods=['GET','POST'])
def login():
    error = ''
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        remember = request.form.get('remember')  # 來自前端的 checkbox
        if verify_account(u, p):
            session['username'] = u
            # 如果使用者勾選「記住我」，把這個 Session 設為永久
            session.permanent = bool(remember)
            return redirect(url_for('game.index'))
        error = '帳號或密碼錯誤'
    return render_template('login.html', error=error)

@auth_routes.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))