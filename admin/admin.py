"""FundQuant 管理后台"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, render_template, session, redirect, url_for, send_from_directory
from datetime import timedelta

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'fundquant_admin_secret_key_2026'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

# 注册蓝图
from admin.routes.auth import auth_bp
from admin.routes.holdings import holdings_bp
from admin.routes.ai_models import models_bp
from admin.routes.api_manage import apis_bp
from admin.routes.feishu import feishu_bp
from admin.routes.settings import settings_bp
from admin.routes.operation_logs import logs_bp

app.register_blueprint(auth_bp, url_prefix='/admin/api/auth')
app.register_blueprint(holdings_bp, url_prefix='/admin/api/holdings')
app.register_blueprint(models_bp, url_prefix='/admin/api/models')
app.register_blueprint(apis_bp, url_prefix='/admin/api/apis')
app.register_blueprint(feishu_bp, url_prefix='/admin/api/feishu')
app.register_blueprint(settings_bp, url_prefix='/admin/api/settings')
app.register_blueprint(logs_bp, url_prefix='/admin/api/logs')

@app.route('/admin/login')
def login_page():
    """登录页面"""
    return render_template('login.html')

@app.route('/admin/')
def index():
    """管理后台首页"""
    if 'admin_id' not in session:
        return redirect('/admin/login')
    return render_template('dashboard.html')

@app.route('/admin/holdings')
def holdings_page():
    if 'admin_id' not in session:
        return redirect('/admin/login')
    return render_template('holdings.html')

@app.route('/admin/models')
def models_page():
    if 'admin_id' not in session:
        return redirect('/admin/login')
    return render_template('ai_models.html')

@app.route('/admin/feishu')
def feishu_page():
    if 'admin_id' not in session:
        return redirect('/admin/login')
    return render_template('feishu.html')

@app.route('/admin/apis')
def apis_page():
    if 'admin_id' not in session:
        return redirect('/admin/login')
    return render_template('api_manage.html')

@app.route('/admin/settings')
def settings_page():
    if 'admin_id' not in session:
        return redirect('/admin/login')
    return render_template('settings.html')

@app.route('/admin/logs')
def logs_page():
    if 'admin_id' not in session:
        return redirect('/admin/login')
    return render_template('operation_logs.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081, debug=False)
