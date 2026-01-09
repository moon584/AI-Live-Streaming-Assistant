"""
聊天路由 - 处理AI对话
"""
from flask import Blueprint, request, jsonify
import uuid
import json
from db_backend import db
from services import ai_service
from utils.logger import get_logger
import os
from services import bullet_ws as _bullet_ws
from services import baidu_tts

logger = get_logger(__name__)

chat_bp = Blueprint('chat', __name__, url_prefix='/api')


def _synthesize_audio_for_text(text: str):
    """尝试为给定文本合成短语音，保存到 static/audio 并返回可访问的 URL；失败返回 None。"""
    try:
        out_dir = os.path.join(os.getcwd(), 'static', 'audio')
        os.makedirs(out_dir, exist_ok=True)
        filename = f"tts_{uuid.uuid4().hex}.wav"
        out_path = os.path.join(out_dir, filename)
        # baidu_tts.synthesize 会在成功时返回 out_path 或抛错
        baidu_tts.synthesize(text, out_path=out_path)
        return f"/static/audio/{filename}"
    except Exception as e:
        logger.warning(f'Baidu TTS 合成失败: {e}', exc_info=True)
        return None



@chat_bp.route('/chat', methods=['POST'])
def chat():
    """与AI对话"""
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "请求数据不能为空"}), 400
        
        session_id = data.get('session_id')
        message = data.get('message')
        
        # 验证session_id格式
        if not session_id:
            return jsonify({"error": "会话ID不能为空"}), 400
        
        try:
            uuid.UUID(session_id)
        except ValueError:
            return jsonify({"error": "无效的会话ID格式"}), 400
        
        # 验证消息
        if not message or not isinstance(message, str):
            return jsonify({"error": "消息不能为空"}), 400
        
        message = message.strip()
        if not message:
            return jsonify({"error": "消息不能为空"}), 400
        
        if len(message) > 500:
            return jsonify({"error": "消息长度不能超过500字符"}), 400
        
        logger.info(f"收到聊天请求 - 会话: {session_id}, 消息长度: {len(message)}")
        
        # ========== 第一步：检查敏感词 ==========
        is_sensitive, matched_words = db.check_sensitive_words(message)
        if is_sensitive:
            logger.warning(f"⚠️ 消息包含敏感词: {matched_words}")
            return jsonify({
                "error": "您的消息包含不当内容，请文明用语。",
                "sensitive": True
            }), 400
        
        # 在继续之前获取会话信息（以便读取商品属性、防止 AI 编造）
        session = db.get_session(session_id)
        if not session:
            return jsonify({"error": "会话不存在"}), 404

        # 确定目标商品（优先使用请求里显式指明的 product_index/product_id/product_name）
        products = session.get('products', [])
        target_product = None
        if isinstance(data.get('product_index'), int) or (isinstance(data.get('product_index'), str) and data.get('product_index').isdigit()):
            try:
                idx = int(data.get('product_index'))
                if 0 <= idx < len(products):
                    target_product = products[idx]
            except Exception:
                target_product = None
        elif data.get('product_id'):
            pid = data.get('product_id')
            for p in products:
                if str(p.get('id')) == str(pid) or str(p.get('session_id')) == str(pid):
                    target_product = p
                    break
        elif data.get('product_name'):
            pname = data.get('product_name')
            for p in products:
                if p.get('product_name') == pname or p.get('name') == pname:
                    target_product = p
                    break
        elif len(products) == 1:
            target_product = products[0]

        # 解析 product attributes（可能存为 JSON 字符串），并提取常用字段：origin, sweetness, price, type
        product_origin = None
        product_price = None
        product_type = None
        product_sweetness = None
        if target_product:
            attrs = target_product.get('attributes') or {}
            try:
                if isinstance(attrs, str) and attrs:
                    attrs = json.loads(attrs)
            except Exception:
                attrs = {}
            # 常用字段
            product_origin = attrs.get('origin') or attrs.get('产地') or attrs.get('place_of_origin')
            product_sweetness = attrs.get('sweetness') or attrs.get('甜度')
            # 价格与类型可能在顶层或attributes里
            product_price = target_product.get('price') if target_product.get('price') not in (None, '') else attrs.get('price')
            product_type = target_product.get('product_type') or target_product.get('type') or attrs.get('type')

        # ========== 第二步：检查FAQ白名单 ==========
        faq_answer = db.get_whitelist_answer(session_id, message)
        if faq_answer:
            logger.info(f"✅ 返回FAQ答案 - 会话: {session_id}")
            # 始终为返回文本合成语音（失败则返回 null），并把 audio_url 一并保存到缓存与会话
            audio_url = _synthesize_audio_for_text(faq_answer)
            try:
                db.cache_qa_with_origin(session_id, message, faq_answer, audio_url, product_origin)
            except Exception:
                # 保持向后兼容
                try:
                    db.cache_qa(session_id, message, faq_answer, audio_url)
                except Exception:
                    logger.debug('缓存 FAQ 答案失败')
            db.save_conversation(session_id, message, faq_answer, audio_url)
            return jsonify({"response": faq_answer, "faq": True, "audio_url": audio_url})
        
        # ========== 第三步：检查问答缓存 ==========
        # ========== 第三步：检查问答缓存（包含商品产地作为缓存键） ==========
        try:
            cached = db.get_cached_answer_with_origin(session_id, message, product_origin)
        except AttributeError:
            # 兼容旧接口
            cached = db.get_cached_answer(session_id, message)
        if cached:
            # cached 现在为 {'answer': ..., 'audio_url': ...}
            answer = cached.get('answer') if isinstance(cached, dict) else cached
            audio_url = cached.get('audio_url') if isinstance(cached, dict) else None
            logger.info(f"✅ 返回缓存答案 - 会话: {session_id}")
            # 若缓存中没有 audio_url，则合成并回写缓存
            if not audio_url:
                audio_url = _synthesize_audio_for_text(answer)
                try:
                    db.cache_qa_with_origin(session_id, message, answer, audio_url, product_origin)
                except Exception:
                    try:
                        db.cache_qa(session_id, message, answer, audio_url)
                    except Exception:
                        logger.debug('更新缓存 audio_url 失败')
            db.save_conversation(session_id, message, answer, audio_url)
            return jsonify({"response": answer, "cached": True, "audio_url": audio_url})
        
        # ========== 第四步：调用AI API ==========
        logger.info(f"调用AI API - 会话: {session_id}")

        # 如果用户在询问产地但当前商品没有 origin，我们不直接让模型编造答案，
        # 而是提示前端向用户提问并把结果存起来。
        origin_query_keywords = ['产地', '哪里', '来自', '哪里的']
        need_info_flag = None
        if (any(k in message for k in origin_query_keywords)) and (not product_origin):
            # 记录需要补充的信息，但继续让AI基于现有信息尝试回答
            product_candidates = [p.get('product_name') or p.get('name') for p in products]
            need_info_flag = {
                "info_key": "origin",
                "prompt": "请告知该商品的产地，我会保存并在后续回答中使用。",
                "product_candidates": product_candidates
            }

        # 检查甜度（仅对水果生效）
        sweetness_query_keywords = ['甜度', '甜', '多甜', '甜吗']
        if product_type and str(product_type).lower() == 'fruit' and any(k in message for k in sweetness_query_keywords) and (not product_sweetness):
            product_candidates = [p.get('product_name') or p.get('name') for p in products]
            need_info_flag = {
                "info_key": "sweetness",
                "prompt": "请告诉我该水果的甜度（例如：微甜/适中/很甜），我会保存并在后续回答中使用。",
                "product_candidates": product_candidates
            }

        # 检查价格询问关键字
        price_query_keywords = ['价格', '多少钱', '价钱', '价位']
        if any(k in message for k in price_query_keywords) and (product_price in (None, '', 0)):
            product_candidates = [p.get('product_name') or p.get('name') for p in products]
            need_info_flag = {
                "info_key": "price",
                "prompt": "该商品的价格目前未提供，请输入价格（数字即可，例如：39.9），我会保存并在后续回答中使用。",
                "product_candidates": product_candidates
            }

        # 将每个商品的补充信息（包括 origin）合并到 session.products 的 attributes
        try:
            merged_products = []
            for p in session.get('products', []):
                # 兼容不同字段名
                pname = p.get('product_name') or p.get('name')
                pid = p.get('id')
                merged_attrs = {}
                try:
                    merged_attrs = db.get_product_info(session_id, product_name=pname, product_id=pid) or {}
                except Exception:
                    merged_attrs = {}

                # existing attrs可能为字符串或dict
                existing = p.get('attributes') or {}
                try:
                    if isinstance(existing, str) and existing:
                        existing = json.loads(existing)
                except Exception:
                    existing = {}

                # 合并：以 product_info 中的键为准（已由 save_product_info 保证不覆盖用户已有值）
                merged = dict(existing)
                for k, v in (merged_attrs or {}).items():
                    if k and v is not None:
                        merged[k] = v

                newp = dict(p)
                newp['attributes'] = merged
                merged_products.append(newp)

            session['products'] = merged_products
        except Exception:
            logger.debug('合并产品信息失败，继续使用原始 session')

        ai_response = ai_service.call_api(message, session)

        if not ai_response:
            return jsonify({"error": "AI服务暂时不可用，请稍后重试"}), 503

        logger.info(f"✅ AI响应成功 - 会话: {session_id}")

        # ========== 第五步：缓存问答对 ==========
        # 先合成语音并把 audio_url 一并保存到缓存与会话，避免重复合成
        audio_url = _synthesize_audio_for_text(ai_response)
        db.cache_qa(session_id, message, ai_response, audio_url)
        db.save_conversation(session_id, message, ai_response, audio_url)

        resp_body = {
            "response": ai_response,
            "status": "success",
            "audio_url": audio_url
        }
        # 若先前检测到需要补充的字段，附带该标记以便前端可以提示用户（但不阻止返回回答）
        if need_info_flag:
            resp_body['need_info'] = True
            resp_body['info_key'] = need_info_flag.get('info_key')
            resp_body['prompt'] = need_info_flag.get('prompt')
            resp_body['product_candidates'] = need_info_flag.get('product_candidates')

        return jsonify(resp_body)
        
    except Exception as e:
        logger.error(f"聊天处理异常: {str(e)}", exc_info=True)
        return jsonify({"error": f"服务器错误: {str(e)}"}), 500


@chat_bp.route('/bullet-screen', methods=['POST'])
def add_bullet_screen():
    """添加弹幕"""
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "请求数据不能为空"}), 400
        
        session_id = data.get('session_id')
        username = data.get('username')
        message = data.get('message')
        
        if not session_id or not username or not message:
            return jsonify({"error": "缺少必要参数"}), 400
        
        # 验证session_id格式
        try:
            uuid.UUID(session_id)
        except ValueError:
            return jsonify({"error": "无效的会话ID"}), 400
        
        logger.info(f"收到弹幕 - 会话: {session_id}, 用户: {username}")
        
        # 检查是否在黑名单（兼容 db.is_blacklisted 返回 bool 或 (bool, reason)）
        try:
            res = db.is_blacklisted(session_id, username, message)
            if isinstance(res, (list, tuple)):
                is_blocked, reason = res[0], (res[1] if len(res) > 1 else None)
            else:
                is_blocked, reason = bool(res), None
        except Exception as e:
            logger.warning(f"检查黑名单时出错: {e}")
            is_blocked, reason = False, None

        if is_blocked:
            logger.warning(f"⚠️ 弹幕被拦截 - 原因: {reason}")
            return jsonify({"status": "blocked", "reason": reason})
        
        # 添加弹幕
        if db.add_bullet_screen(session_id, username, message):
            # 广播到 WebSocket 客户端（若已启用）以实现实时推送
            try:
                if _bullet_ws:
                    _bullet_ws.broadcast({
                        'type': 'bullet',
                        'session_id': session_id,
                        'username': username,
                        'message': message
                    })
            except Exception:
                logger.warning('弹幕广播失败', exc_info=True)
            return jsonify({"status": "success"})
        else:
            return jsonify({"error": "添加弹幕失败"}), 500
            
    except Exception as e:
        logger.error(f"添加弹幕异常: {str(e)}", exc_info=True)
        return jsonify({"error": f"服务器错误: {str(e)}"}), 500

@chat_bp.route('/bullet-screen/pending', methods=['GET'])
def get_pending_bullet_screens():
    """获取待处理的弹幕"""
    try:
        session_id = request.args.get('session_id')
        limit = request.args.get('limit', 10, type=int)
        
        if not session_id:
            return jsonify({"error": "缺少session_id参数"}), 400
        
        # 验证session_id格式
        try:
            uuid.UUID(session_id)
        except ValueError:
            return jsonify({"error": "无效的会话ID"}), 400
        
        logger.info(f"获取待处理弹幕 - 会话: {session_id}, 限制: {limit}")
        
        # 获取弹幕
        bullet_screens = db.get_pending_bullet_screens(session_id, limit)
        
        return jsonify({
            "session_id": session_id,
            "bullet_screens": bullet_screens,
            "count": len(bullet_screens)
        })
        
    except Exception as e:
        logger.error(f"获取弹幕异常: {str(e)}", exc_info=True)
        return jsonify({"error": f"服务器错误: {str(e)}"}), 500


# 语音模块已移除：/api/tts 文件与状态端点不再提供。
