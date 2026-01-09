"""
会话路由 - 处理会话创建和查询
"""
from flask import Blueprint, request, jsonify
import uuid
from db_backend import db
from typing import Dict, Any, List, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

session_bp = Blueprint('session', __name__, url_prefix='/api/session')

def _normalize_product_type(name: str, provided: Optional[str]) -> str:
    """根据商品名称或提供的类型，规范化product_type。
    规则：
    - 优先匹配名称关键词
    - 找不到强匹配则回退到provided且校验其有效性
    - 最终保证返回值在有效类型集合中
    """
    valid_types = {'fruit', 'vegetable', 'meat', 'grain', 'handicraft', 'processed'}
    name = (name or '').lower()
    provided = (provided or '').lower()

    # 关键词映射（包含常见同义词与中文关键词）
    keyword_map: Dict[str, set[str]] = {
        'fruit': {
            '苹果','梨','橙','橘','柑','香蕉','草莓','蓝莓','葡萄','西瓜','桃','樱桃','芒果','柚',
            '榴莲','菠萝','橙子','石榴','猕猴桃'
        },
        'vegetable': {
            '菜','青菜','白菜','番茄','西红柿','黄瓜','土豆','马铃薯','茄子','辣椒','菠菜','胡萝卜','芹菜','生菜','油麦'
        },
        'meat': {
            '猪','牛','羊','鸡','鸭','鹅','鱼','虾','蟹','贝','肉','鸡蛋','鸭蛋','鹅蛋','蛋'
        },
        'grain': {
            '花生','瓜子','核桃','杏仁','腰果','板栗','松子','大米','小米','玉米','大豆','黄豆','红豆','绿豆','黑豆','杂粮','坚果','豆类','谷物'
        },
        'handicraft': {
            '手工','工艺','编织','竹编','陶瓷','布艺','手作','非遗','雕刻','木艺','漆器'
        },
        'processed': {
            '腊肠','腊肉','豆干','果干','果脯','酱','酱菜','泡菜','腌菜','罐头','饼干','糕点','熟食','即食','半成品','酥糖','牛轧糖'
        }
    }

    # 名称强匹配
    for t, words in keyword_map.items():
        if any(w in name for w in words if w):
            return t

    # 提供的类型有效则使用
    if provided in valid_types:
        return provided

    # 兜底
    return 'grain' if '豆' in name or '米' in name or '坚果' in name else 'fruit'


def _normalize_products(raw_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """将前端传入的产品数据字段规范为 database.create_session 期望的结构。
    期望字段：name, price, unit, type, attributes
    """
    normalized: list[Dict[str, Any]] = []
    for p in raw_products or []:
        # 兼容字段名：name/product_name, type/product_type
        name = p.get('name') or p.get('product_name') or ''
        unit = p.get('unit') or '元'
        price = p.get('price') or 0
        provided_type = p.get('type') or p.get('product_type') or ''
        # 兼容可能把产地/origin 放在顶层的情形
        raw_attributes = p.get('attributes') or {}
        attributes = dict(raw_attributes) if isinstance(raw_attributes, dict) else {}

        # 支持多种命名的产地字段，优先保留到 attributes['origin']
        origin_candidates = [p.get('origin'), p.get('产地'), p.get('place_of_origin'), p.get('origin_place')]
        for oc in origin_candidates:
            if oc:
                attributes.setdefault('origin', oc)
                break

        norm_type = _normalize_product_type(str(name), str(provided_type))

        item = {
            'name': name,
            'price': float(price) if isinstance(price, (int, float, str)) and str(price) else 0.0,
            'unit': unit,
            'type': norm_type,
            'attributes': attributes
        }
        # 记录修正日志
        if provided_type and provided_type != norm_type:
            logger.warning(f"商品类型已纠正: {name} - 原: {provided_type} -> 新: {norm_type}")
        normalized.append(item)
    return normalized


@session_bp.route('', methods=['POST'])
def create_session():
    """创建新的直播会话"""
    try:
        data = request.json
        host_name = data.get('host_name')
        live_theme = data.get('live_theme')
        products = data.get('products', [])

        # 参数验证
        if not host_name or not live_theme:
            return jsonify({"error": "缺少必要参数"}), 400

        # 生成 session_id
        session_id = str(uuid.uuid4())

        logger.info(f"创建新会话 - ID: {session_id}, 主播: {host_name}, 主题: {live_theme}")

        # 规范化产品数据与类型
        products_normalized = _normalize_products(products)
        # 记录规范化后的产品以便调试（短期）
        logger.debug(f"规范化产品数据: {products_normalized}")

        # 保存会话
        if db.create_session(session_id, host_name, live_theme, products_normalized):
                # 返回给前端的 products 使用统一字段名（product_name/product_type/attributes）
                out_products = []
                for p in products_normalized:
                    out_products.append({
                        'product_name': p.get('name') or p.get('product_name') or '',
                        'price': float(p.get('price') or 0),
                        'unit': p.get('unit') or '元',
                        'product_type': p.get('type') or p.get('product_type') or '',
                        'attributes': p.get('attributes') or {}
                    })
                return jsonify({
                    "session_id": session_id,
                    "host_name": host_name,
                    "live_theme": live_theme,
                    "products": out_products
                })
        else:
            return jsonify({"error": "创建会话失败"}), 500

    except Exception as e:
        logger.error(f"创建会话异常: {str(e)}", exc_info=True)
        return jsonify({"error": f"服务器错误: {str(e)}"}), 500

@session_bp.route('/<session_id>', methods=['GET'])
def get_session(session_id):
    """获取会话信息"""
    try:
        # 验证session_id格式
        try:
            uuid.UUID(session_id)
        except ValueError:
            return jsonify({"error": "无效的会话ID"}), 400
        
        logger.info(f"查询会话 - ID: {session_id}")
        
        # 获取会话
        session = db.get_session(session_id)
        if not session:
            return jsonify({"error": "会话不存在"}), 404
        # 规范化返回结构：确保 products 中字段一致，attributes 为对象
        try:
            prods = session.get('products') or []
            normalized = []
            for p in prods:
                attrs = p.get('attributes') or {}
                if isinstance(attrs, str) and attrs:
                    try:
                        import json
                        attrs = json.loads(attrs)
                    except Exception:
                        attrs = {}
                normalized.append({
                    'product_name': p.get('product_name') or p.get('name') or '',
                    'price': float(p.get('price') or 0),
                    'unit': p.get('unit') or '元',
                    'product_type': p.get('product_type') or p.get('type') or '',
                    'attributes': attrs
                })
            session['products'] = normalized
        except Exception:
            # 若处理失败，保持原样返回，避免影响可用性
            pass

        return jsonify(session)
        
    except Exception as e:
        logger.error(f"查询会话异常: {str(e)}", exc_info=True)
        return jsonify({"error": f"服务器错误: {str(e)}"}), 500


@session_bp.route('/product-info', methods=['POST'])
def save_product_info():
    """保存商品补充信息（例如产地）。请求体应包含：session_id, product_name 或 product_id, key, value"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "请求数据不能为空"}), 400

        session_id = data.get('session_id')
        product_id = data.get('product_id')
        product_name = data.get('product_name')
        key = data.get('key')
        value = data.get('value')

        if not session_id or not key or value is None:
            return jsonify({"error": "缺少必要参数"}), 400

        ok = db.save_product_info(session_id, product_name=product_name, product_id=product_id, info_key=key, info_value=value)
        if ok:
            # 返回合并后的属性，便于前端即时更新 UI
            try:
                merged = db.get_product_info(session_id, product_name=product_name, product_id=product_id) or {}
            except Exception:
                merged = {}
            return jsonify({"status": "ok", "attributes": merged})
        else:
            return jsonify({"error": "保存失败"}), 500

    except Exception as e:
        logger.error(f"保存商品信息异常: {str(e)}", exc_info=True)
        return jsonify({"error": f"服务器错误: {str(e)}"}), 500
