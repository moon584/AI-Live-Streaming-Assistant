#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入FAQ白名单到数据库
自动将whitelist.json中按商品类型分类的FAQ导入到指定会话
"""

import sys
import os
import json

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_backend import db

def import_faqs_to_session(session_id, product_types=None):
    """
    将FAQ导入到指定会话
    
    Args:
        session_id: 会话ID
        product_types: 商品类型列表，如 ['fruit', 'vegetable']。如果为None，只导入通用FAQ
    
    Returns:
        int: 成功导入的FAQ数量
    """
    # 读取whitelist.json
    whitelist_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'whitelist.json')
    
    with open(whitelist_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    faqs_to_import = []
    
    # 1. 导入通用FAQ
    global_faqs = data.get('_global_faqs', [])
    faqs_to_import.extend(global_faqs)
    print(f"✅ 已添加 {len(global_faqs)} 条通用FAQ")
    
    # 2. 根据商品类型导入专属FAQ
    if product_types:
        type_mapping = {
            'fruit': '_fruit_faqs',
            'vegetable': '_vegetable_faqs',
            'meat': '_meat_faqs',
            'grain': '_grain_faqs',
            'handicraft': '_handicraft_faqs',
            'processed': '_processed_faqs'
        }
        
        for ptype in product_types:
            faq_key = type_mapping.get(ptype)
            if faq_key and faq_key in data:
                type_faqs = data[faq_key]
                faqs_to_import.extend(type_faqs)
                print(f"✅ 已添加 {len(type_faqs)} 条 {ptype} 类型FAQ")
    
    # 3. 批量插入数据库
    conn = db.get_connection()
    if not conn:
        print("❌ 数据库连接失败")
        return 0
    
    try:
        cursor = conn.cursor()
        success_count = 0
        
        for faq in faqs_to_import:
            pattern = faq.get('pattern')
            answer = faq.get('answer')
            priority = faq.get('priority', 50)
            product_types_str = faq.get('product_types', '')
            
            # 检查是否已存在
            cursor.execute(
                "SELECT COUNT(*) FROM whitelist WHERE session_id = %s AND pattern = %s",
                (session_id, pattern)
            )
            if cursor.fetchone()[0] > 0:
                print(f"⏭️  跳过重复FAQ: {pattern}")
                continue
            
            # 插入FAQ
            cursor.execute(
                "INSERT INTO whitelist (session_id, pattern, answer, priority, product_types) VALUES (%s, %s, %s, %s, %s)",
                (session_id, pattern, answer, priority, product_types_str)
            )
            success_count += 1
        
        conn.commit()
        print(f"\n🎉 成功导入 {success_count} 条FAQ到会话 {session_id}")
        return success_count
        
    except Exception as e:
        print(f"❌ 导入FAQ失败: {e}")
        return 0
    finally:
        conn.close()

def show_available_faqs():
    """显示可用的FAQ统计"""
    whitelist_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'whitelist.json')
    
    with open(whitelist_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("\n" + "="*60)
    print("📋 可用FAQ统计")
    print("="*60)
    
    categories = {
        '_global_faqs': '通用FAQ',
        '_fruit_faqs': '水果类FAQ',
        '_vegetable_faqs': '蔬菜类FAQ',
        '_meat_faqs': '禽蛋肉类FAQ',
        '_grain_faqs': '五谷杂粮FAQ',
        '_handicraft_faqs': '手工艺品FAQ',
        '_processed_faqs': '加工食品FAQ'
    }
    
    total = 0
    for key, name in categories.items():
        if key in data:
            count = len(data[key])
            total += count
            print(f"{name}: {count} 条")
    
    print(f"\n总计: {total} 条FAQ")
    print("="*60 + "\n")

def interactive_import():
    """交互式导入"""
    print("\n" + "="*60)
    print("🔧 FAQ导入工具")
    print("="*60)
    
    # 显示可用FAQ
    show_available_faqs()
    
    # 获取会话ID
    session_id = input("请输入会话ID (留空查看所有会话): ").strip()
    
    if not session_id:
        # 显示所有会话
        conn = db.get_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, host_name, live_theme, created_at FROM sessions ORDER BY created_at DESC LIMIT 10")
            sessions = cursor.fetchall()
            conn.close()
            
            if sessions:
                print("\n最近的会话:")
                print("-" * 60)
                for s in sessions:
                    print(f"ID: {s['id']}")
                    print(f"主播: {s['host_name']} | 主题: {s['live_theme']}")
                    print(f"创建时间: {s['created_at']}")
                    print("-" * 60)
                
                session_id = input("\n请输入要导入的会话ID: ").strip()
            else:
                print("❌ 没有找到会话")
                return
    
    if not session_id:
        print("❌ 会话ID不能为空")
        return
    
    # 选择商品类型
    print("\n可用商品类型:")
    print("1. fruit - 水果")
    print("2. vegetable - 蔬菜")
    print("3. meat - 禽蛋肉类")
    print("4. grain - 五谷杂粮")
    print("5. handicraft - 手工艺品")
    print("6. processed - 加工食品")
    print("7. 全部类型")
    print("0. 仅通用FAQ")
    
    choice = input("\n请选择商品类型 (多个用逗号分隔，如: 1,2): ").strip()
    
    type_map = {
        '1': 'fruit',
        '2': 'vegetable',
        '3': 'meat',
        '4': 'grain',
        '5': 'handicraft',
        '6': 'processed'
    }
    
    product_types = None
    if choice == '7':
        product_types = list(type_map.values())
    elif choice != '0':
        selected = [c.strip() for c in choice.split(',')]
        product_types = [type_map[s] for s in selected if s in type_map]
    
    # 确认
    print(f"\n将导入到会话: {session_id}")
    print(f"商品类型: {product_types or '仅通用FAQ'}")
    confirm = input("确认导入? (y/n): ").strip().lower()
    
    if confirm == 'y':
        import_faqs_to_session(session_id, product_types)
    else:
        print("❌ 已取消导入")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 命令行模式
        session_id = sys.argv[1]
        product_types = sys.argv[2:] if len(sys.argv) > 2 else None
        
        print(f"导入FAQ到会话: {session_id}")
        print(f"商品类型: {product_types or '仅通用FAQ'}")
        
        import_faqs_to_session(session_id, product_types)
    else:
        # 交互模式
        interactive_import()
