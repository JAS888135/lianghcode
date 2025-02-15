from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from ..models import db, User
import logging

logger = logging.getLogger(__name__)
auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user, remember=remember)
            logger.info(f'用户 {username} 登录成功')
            
            # 更新最后登录时间
            from datetime import datetime
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('用户名或密码错误', 'danger')
            logger.warning(f'用户 {username} 登录失败')
    
    return render_template('auth/login.html')

@auth.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    logger.info(f'用户 {username} 已登出')
    flash('您已成功登出', 'success')
    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # 验证输入
        if not all([username, email, password, confirm_password]):
            flash('请填写所有必填字段', 'danger')
            return render_template('auth/register.html')
            
        if password != confirm_password:
            flash('两次输入的密码不一致', 'danger')
            return render_template('auth/register.html')
            
        # 检查用户名和邮箱是否已存在
        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'danger')
            return render_template('auth/register.html')
            
        if User.query.filter_by(email=email).first():
            flash('邮箱已被注册', 'danger')
            return render_template('auth/register.html')
            
        # 创建新用户
        try:
            new_user = User(
                username=username,
                email=email,
                password=generate_password_hash(password),
                role='user'
            )
            db.session.add(new_user)
            db.session.commit()
            
            logger.info(f'新用户注册成功: {username}')
            flash('注册成功，请登录', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            logger.error(f'用户注册失败: {str(e)}')
            db.session.rollback()
            flash('注册失败，请稍后重试', 'danger')
            
    return render_template('auth/register.html')

@auth.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # 更新个人信息
        email = request.form.get('email')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        try:
            # 更新邮箱
            if email and email != current_user.email:
                if User.query.filter_by(email=email).first():
                    flash('该邮箱已被使用', 'danger')
                else:
                    current_user.email = email
                    db.session.commit()
                    flash('邮箱更新成功', 'success')
            
            # 更新密码
            if current_password and new_password and confirm_password:
                if not check_password_hash(current_user.password, current_password):
                    flash('当前密码错误', 'danger')
                elif new_password != confirm_password:
                    flash('两次输入的新密码不一致', 'danger')
                else:
                    current_user.password = generate_password_hash(new_password)
                    db.session.commit()
                    flash('密码更新成功', 'success')
                    
            logger.info(f'用户 {current_user.username} 更新了个人信息')
            
        except Exception as e:
            logger.error(f'更新个人信息失败: {str(e)}')
            db.session.rollback()
            flash('更新失败，请稍后重试', 'danger')
            
    return render_template('auth/profile.html') 