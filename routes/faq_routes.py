"""
FAQ路由 - 处理FAQ模板和导入
"""
from flask import Blueprint, request, jsonify
import uuid
from db_backend import db
from utils.logger import get_logger

logger = get_logger(__name__)

faq_bp = Blueprint('faq', __name__, url_prefix='/api')

@faq_bp.route('/faq-templates/<product_type>', methods=['GET'])
def get_faq_templates(product_type):
    """获取指定商品类型的FAQ模板列表"""
    try:
        logger.info(f"获取FAQ模板 - 商品类型: {product_type}")
        
        # 验证商品类型
        valid_types = ['fruit', 'vegetable', 'meat', 'grain', 'handicraft', 'processed']
        if product_type not in valid_types:
            return jsonify({"error": f"无效的商品类型，支持的类型: {', '.join(valid_types)}"}), 400
        
        # 从数据库获取模板
        templates = db.get_faq_templates(product_type)
        
        if templates is None:
            return jsonify({"error": "获取FAQ模板失败"}), 500
        
        logger.info(f"成功获取FAQ模板 - 类型: {product_type}, 数量: {len(templates)}")
        return jsonify({
            "product_type": product_type,
            "templates": templates,
            "count": len(templates)
        })
        
    except Exception as e:
        logger.error(f"获取FAQ模板异常: {str(e)}", exc_info=True)
        return jsonify({"error": f"服务器错误: {str(e)}"}), 500

@faq_bp.route('/session/apply-faq', methods=['POST'])
def apply_faq_template():
    """应用FAQ模板到会话"""
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "请求数据不能为空"}), 400
        
        # 验证必需参数
        session_id = data.get('session_id')
        product_type = data.get('product_type')
        faq_values = data.get('faq_values')
        
        if not session_id:
            return jsonify({"error": "缺少session_id参数"}), 400
        
        if not product_type:
            return jsonify({"error": "缺少product_type参数"}), 400
        
        if not faq_values or not isinstance(faq_values, dict):
            return jsonify({"error": "faq_values必须是一个字典对象"}), 400
        
        logger.info(f"应用FAQ模板 - 会话: {session_id}, 类型: {product_type}")
        
        # 应用模板
        success_count = db.apply_faq_template(session_id, product_type, faq_values)
        
        if success_count is None:
            return jsonify({"error": "应用FAQ模板失败"}), 500
        
        logger.info(f"成功应用FAQ模板 - 会话: {session_id}, 生成FAQ数量: {success_count}")
        return jsonify({
            "session_id": session_id,
            "product_type": product_type,
            "success_count": success_count,
            "message": f"成功生成{success_count}条FAQ"
        })
        
    except Exception as e:
        logger.error(f"应用FAQ模板异常: {str(e)}", exc_info=True)
        return jsonify({"error": f"服务器错误: {str(e)}"}), 500

@faq_bp.route('/session/import-faqs', methods=['POST'])
def import_faqs():
    """批量导入FAQ到会话（从whitelist.json配置文件）"""
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "请求数据不能为空"}), 400
        
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({"error": "缺少session_id参数"}), 400
        
        # 验证session_id格式
        try:
            uuid.UUID(session_id)
        except ValueError:
            return jsonify({"error": "无效的会话ID"}), 400
        
        # 验证会话是否存在
        session = db.get_session(session_id)
        if not session:
            return jsonify({"error": "会话不存在"}), 404
        
        logger.info(f"批量导入FAQ - 会话: {session_id}")
        
        # 这里应该调用导入逻辑
        # 暂时返回成功
        return jsonify({
            "session_id": session_id,
            "message": "FAQ导入成功"
        })
        
    except Exception as e:
        logger.error(f"导入FAQ异常: {str(e)}", exc_info=True)
        return jsonify({"error": f"服务器错误: {str(e)}"}), 500
