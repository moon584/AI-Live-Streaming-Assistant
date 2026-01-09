"""
统计路由 - 处理FAQ统计和推荐
"""
from flask import Blueprint, request, jsonify
import uuid
from db_backend import db
from utils.logger import get_logger

logger = get_logger(__name__)

stats_bp = Blueprint('stats', __name__, url_prefix='/api/session')

@stats_bp.route('/<session_id>/faq-statistics', methods=['GET'])
def get_faq_statistics(session_id):
    """获取FAQ统计信息"""
    try:
        # 验证session_id
        try:
            uuid.UUID(session_id)
        except ValueError:
            return jsonify({"error": "无效的会话ID"}), 400
        
        # 验证会话是否存在
        session = db.get_session(session_id)
        if not session:
            return jsonify({"error": "会话不存在"}), 404
        
        logger.info(f"获取FAQ统计 - 会话: {session_id}")
        
        # 获取统计信息
        stats = db.get_faq_statistics(session_id)
        
        if stats is None:
            return jsonify({"error": "获取统计信息失败"}), 500
        
        logger.info(f"✅ FAQ统计获取成功 - 会话: {session_id}")
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"获取FAQ统计异常: {str(e)}", exc_info=True)
        return jsonify({"error": f"服务器错误: {str(e)}"}), 500

@stats_bp.route('/<session_id>/faq-recommendations', methods=['GET'])
def get_faq_recommendations(session_id):
    """获取FAQ推荐（高频但未被覆盖的问题）"""
    try:
        # 验证session_id
        try:
            uuid.UUID(session_id)
        except ValueError:
            return jsonify({"error": "无效的会话ID"}), 400
        
        # 验证会话是否存在
        session = db.get_session(session_id)
        if not session:
            return jsonify({"error": "会话不存在"}), 404
        
        min_hit_count = request.args.get('min_hit_count', 10, type=int)
        
        logger.info(f"获取FAQ推荐 - 会话: {session_id}, 最小命中: {min_hit_count}")
        
        # 获取推荐
        recommendations = db.get_faq_recommendations(session_id, min_hit_count)
        
        logger.info(f"✅ 找到 {len(recommendations)} 条FAQ推荐 - 会话: {session_id}")
        return jsonify({
            "session_id": session_id,
            "recommendations": recommendations,
            "count": len(recommendations)
        })
        
    except Exception as e:
        logger.error(f"获取FAQ推荐异常: {str(e)}", exc_info=True)
        return jsonify({"error": f"服务器错误: {str(e)}"}), 500
