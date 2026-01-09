from flask import Blueprint, jsonify

meta_bp = Blueprint('meta', __name__, url_prefix='/api/meta')

# 与前端 static/script.js 中的 productTypeConfig 保持一致，供前端动态加载字段配置
product_type_config = {
    'fruit': {
        'name': '水果',
        'attributes': [
            {'key': 'variety', 'label': '品种/ cultivar', 'type': 'text', 'placeholder': '例如：红富士/烟台富士'},
            {'key': 'maturity', 'label': '成熟度', 'type': 'select', 'options': ['未熟', '待熟', '适中', '完全熟']},
            {'key': 'sweetness', 'label': '甜度', 'type': 'select', 'options': ['偏酸', '微甜', '适中', '很甜', '特别甜']},
            {'key': 'texture', 'label': '口感', 'type': 'select', 'options': ['脆爽', '软糯', '多汁', '绵密', '清脆']},
            {'key': 'origin', 'label': '产地', 'type': 'text', 'placeholder': '例如：山东烟台'},
            {'key': 'size', 'label': '大小规格', 'type': 'text', 'placeholder': '例如：单果200-250g'},
            {'key': 'grade', 'label': '等级', 'type': 'text', 'placeholder': '例如：一级/二级'},
            {'key': 'harvest_date', 'label': '采摘日期', 'type': 'text', 'placeholder': '例如：2025-09-12'},
            {'key': 'storage', 'label': '储存建议', 'type': 'textarea', 'placeholder': '冷藏保存，建议3天内食用'}
        ]
    },
    'vegetable': {
        'name': '蔬菜',
        'attributes': [
            {'key': 'variety', 'label': '品种', 'type': 'text', 'placeholder': '例如：小青菜/大白菜'},
            {'key': 'freshness', 'label': '新鲜度', 'type': 'select', 'options': ['当日采摘', '隔日送达', '冷链保鲜']},
            {'key': 'maturity', 'label': '成熟度/嫩度', 'type': 'select', 'options': ['幼嫩', '适中', '成熟']},
            {'key': 'cooking', 'label': '推荐烹饪方式', 'type': 'select', 'options': ['清炒', '炖煮', '凉拌', '蒸制', '煲汤']},
            {'key': 'origin', 'label': '产地', 'type': 'text', 'placeholder': '例如：本地大棚'},
            {'key': 'season', 'label': '时令季节', 'type': 'text', 'placeholder': '例如：春季'},
            {'key': 'storage', 'label': '储存建议', 'type': 'textarea', 'placeholder': '冷藏保存，建议尽快食用'}
        ]
    },
    'meat': {
        'name': '禽蛋肉类',
        'attributes': [
            {'key': 'raising', 'label': '饲养方式', 'type': 'select', 'options': ['散养', '圈养', '有机养殖', '放养']},
            {'key': 'part', 'label': '部位', 'type': 'text', 'placeholder': '例如：鸡胸肉、猪里脊'},
            {'key': 'quality', 'label': '肉质/等级', 'type': 'text', 'placeholder': '例如：鲜嫩/紧实'},
            {'key': 'slaughter_date', 'label': '宰杀/处理日期', 'type': 'text', 'placeholder': '例如：2025-10-01'},
            {'key': 'origin', 'label': '来源地', 'type': 'text', 'placeholder': '例如：山东某养殖场'},
            {'key': 'storage', 'label': '储存建议', 'type': 'textarea', 'placeholder': '冷冻保存，解冻后请尽快食用'}
        ]
    },
    'grain': {
        'name': '五谷杂粮',
        'attributes': [
            {'key': 'variety', 'label': '品种', 'type': 'text', 'placeholder': '例如：东北大米/胚芽米'},
            {'key': 'origin', 'label': '产地', 'type': 'text', 'placeholder': '例如：黑龙江'},
            {'key': 'moisture', 'label': '水分含量', 'type': 'text', 'placeholder': '例如：12%'},
            {'key': 'processing', 'label': '加工方式', 'type': 'select', 'options': ['精加工', '粗加工', '保留胚芽', '无添加']},
            {'key': 'cooking', 'label': '食用/烹煮建议', 'type': 'textarea', 'placeholder': '浸泡时间/水米比等'},
            {'key': 'storage', 'label': '储存建议', 'type': 'textarea', 'placeholder': '阴凉干燥处保存'}
        ]
    },
    'handicraft': {
        'name': '手工艺品',
        'attributes': [
            {'key': 'material', 'label': '材质', 'type': 'text', 'placeholder': '例如：竹编、陶瓷、布料'},
            {'key': 'craft', 'label': '工艺', 'type': 'text', 'placeholder': '例如：手工编织/传统烧制'},
            {'key': 'origin', 'label': '产地/产区', 'type': 'text', 'placeholder': '例如：江苏苏州'},
            {'key': 'purpose', 'label': '用途', 'type': 'select', 'options': ['装饰', '实用', '收藏', '礼品']},
            {'key': 'size', 'label': '尺寸（长×宽×高）', 'type': 'dimensions', 'subtype': 'lwh'},
            {'key': 'care', 'label': '保养建议', 'type': 'textarea', 'placeholder': '避免潮湿/避免阳光直射'},
            {'key': 'making_time', 'label': '制作时长', 'type': 'text', 'placeholder': '例如：3天'}
        ]
    },
    'processed': {
        'name': '加工食品',
        'attributes': [
            {'key': 'ingredients', 'label': '主要原料', 'type': 'textarea', 'placeholder': '列出主要原料'},
            {'key': 'allergens', 'label': '过敏原', 'type': 'text', 'placeholder': '例如：含坚果/含麸质'},
            {'key': 'shelf_life', 'label': '保质期', 'type': 'text', 'placeholder': '例如：6个月'},
            {'key': 'flavor', 'label': '风味', 'type': 'select', 'options': ['甜', '咸', '辣', '酸', '鲜', '原味']},
            {'key': 'usage', 'label': '食用/加热建议', 'type': 'textarea', 'placeholder': '开袋即食或加热食用'},
            {'key': 'manufacturer', 'label': '生产商/厂家', 'type': 'text', 'placeholder': '例如：某某食品有限公司'},
            {'key': 'storage', 'label': '储存建议', 'type': 'textarea', 'placeholder': '阴凉干燥处保存'}
        ]
    }
}


@meta_bp.route('/product-types', methods=['GET'])
def get_product_types():
    return jsonify(product_type_config)
