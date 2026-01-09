"""
小聚AI助手 - 主应用入口（模块化重构版本）
"""
from flask import Flask, send_from_directory
from flask_cors import CORS
from utils import setup_logging, get_logger
from config import Config

# 设置日志
setup_logging()
logger = get_logger(__name__)

# 创建Flask应用
app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# 注册路由蓝图
from routes import session_bp, faq_bp, chat_bp, stats_bp, meta_bp
# 可选：WebSocket 广播（实时弹幕推送）
# NOTE: 临时禁用自动启动 websockets 服务以避免在某些环境中因 asyncio loop 导致的线程异常。
bullet_ws = None

app.register_blueprint(session_bp)
app.register_blueprint(faq_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(stats_bp)
app.register_blueprint(meta_bp)

# 静态文件路由
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# 健康检查
@app.route('/api/health', methods=['GET'])
def health_check():
    return {"status": "ok", "message": "小聚AI助手运行中"}

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🚀 小聚AI助手启动中...")
    logger.info(f"📦 数据库: {Config.DB_NAME}")
    logger.info(f"🌐 端口: 5000")
    logger.info("=" * 60)
    
    # 启动可选的 WebSocket 广播服务（非强依赖）
    try:
        if bullet_ws:
            bullet_ws.start_server(host='127.0.0.1', port=6789)
    except Exception:
        logger.warning('启动 WebSocket 广播服务失败，继续以 HTTP 模式运行')

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=Config.DEBUG
    )
