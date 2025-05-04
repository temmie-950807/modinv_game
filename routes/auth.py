# routes/auth.py
from flask import render_template, request, session, redirect, url_for
from functools import wraps
from services.auth_service import verify_account, register_account, find_account

def login_required(f):
    """確保使用者已登入的裝飾器"""
    @wraps(f)
    def wrapped(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapped

def init_auth_routes(app):
    """初始化與認證相關的路由"""
    @app.route('/register', methods=['GET','POST'])
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
                return redirect(url_for('login'))
        return render_template('register.html', error=error)

    @app.route('/login', methods=['GET','POST'])
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
                return redirect(url_for('index'))
            error = '帳號或密碼錯誤'
        return render_template('login.html', error=error)

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))