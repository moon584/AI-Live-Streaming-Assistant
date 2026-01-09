"""
AI服务模块 - 处理与DeepSeek API的交互
"""
import requests
from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

class AIService:
    """AI服务类 - 封装DeepSeek API调用"""
    
    def __init__(self):
        self.api_key = Config.DEEPSEEK_API_KEY
        self.api_url = Config.DEEPSEEK_API_URL
        self.model = Config.DEEPSEEK_MODEL
    
    def call_api(self, prompt, session_context=None):
        """
        调用DeepSeek API
        
        Args:
            prompt: 用户问题
            session_context: 会话上下文（主播、主题、商品等）
            
        Returns:
            AI回复内容，失败返回None
        """
        try:
            # 构建系统提示词
            system_prompt = self._build_system_prompt(session_context)
            
            # 构建请求
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            payload = {
                'model': self.model,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.7,
                'max_tokens': 500
            }
            
            logger.info(f"调用AI API - 模型: {self.model}")
            
            # 发送请求
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 提取回复
            if 'choices' in result and len(result['choices']) > 0:
                ai_response = result['choices'][0]['message']['content']
                logger.info(f"✅ AI API调用成功")
                return ai_response
            else:
                logger.error(f"AI API响应格式异常: {result}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("AI API调用超时")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"AI API请求失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"AI API调用异常: {str(e)}", exc_info=True)
            return None
    
    def _build_system_prompt(self, session_context):
        """构建系统提示词"""
        if not session_context:
            return (
                "你是直播销售助手“小聚”。请使用第一人称自然口语表达，语气亲切专业；"
                "不必每次说明“我是小聚”，只有在首次问候或被用户询问身份时，才简短自我介绍；"
                "回答简洁、分句清楚，适合直播口播；如不确定，请提示以主播口径为准。"
            )
        
        host_name = session_context.get('host_name', '主播')
        live_theme = session_context.get('live_theme', '直播')
        products = session_context.get('products', [])

        prompt = f"""你是直播销售助手“小聚”，正在协助{host_name}进行“{live_theme}”直播。

请遵循：
1. 使用第一人称，语气亲切、专业、自然口语化；不必每次强调“我是小聚”；
2. 只有在首次问候或被询问身份时，才简短自我介绍；
3. 内容简洁、分句清楚，适合直播口播；
4. 涉及价格或规格以已知信息为准，不确定则提示以主播口径为准；
5. 注意品牌与适用人群的合规表述，避免医疗/夸大承诺；
6. 当被询问商品的某个属性（如产地、甜度、价格）而该属性在提供的商品信息中不存在时，请不要自行编造或推测数据：应直接回答“我不知道”或说明“该信息未提供”，并提示可以让主播/用户补充该信息以便后续更精确回答；如果后端明确要求收集信息（例如返回 need_info），请等待并使用用户补充后的信息。"""

        if products:
            prompt += "本次直播的商品清单（下列为已知事实，模型应将其视为事实）：\n"
            for idx, product in enumerate(products or []):
                # 支持多种命名
                name = product.get('product_name') or product.get('name') or ''
                price = product.get('price', '')
                unit = product.get('unit', '元')
                product_type = product.get('product_type') or product.get('type') or ''

                # 标注商品序号，便于用户或系统引用“第n号商品”
                prompt += f"- 第{idx+1}号商品 名称={name}"
                if price is not None and price != '':
                    prompt += f", 价格={price}{unit}"
                else:
                    prompt += f", 价格=未知"
                if product_type:
                    prompt += f", 类型={product_type}"

                # attributes 解析
                attrs = product.get('attributes') or {}
                try:
                    if isinstance(attrs, str) and attrs:
                        import json as _json
                        attrs = _json.loads(attrs)
                except Exception:
                    attrs = {}

                if isinstance(attrs, dict) and attrs:
                    parts = []
                    for k, v in attrs.items():
                        if v is None or v == '':
                            continue
                        parts.append(f"{k}={v}")
                    if parts:
                        prompt += f"，属性：{'；'.join(parts)}"
                    else:
                        # 列出已知键但值缺失的关键属性
                        missing_keys = [k for k, v in attrs.items() if v is None or v == '']
                        if missing_keys:
                            prompt += f"，缺失属性：{','.join(missing_keys)}"

                prompt += "\n"

            # 指示模型处理缺失关键字段的策略（甜度/产地/价格）
            prompt += (
                "注意：对于水果类商品，如果被询问甜度(sweetness)且该字段缺失，模型应直接回答“我不知道该商品的甜度”，"
                "并可友好提示让主播或用户提供甜度信息以便更新事实；不要擅自猜测。\n"
                "同理，若被问及价格而价格为未知，请回答“我不知道价格”，并提示等待主播确认或由系统补充价格。\n"
            )

        return prompt

# 单例
ai_service = AIService()
