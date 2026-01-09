"""Simple exporter: dump blacklist/whitelist from DB to data/blacklist.json and data/whitelist.json.

Usage (PowerShell):
    python ./scripts/export_lists.py

Note: This will overwrite files under `data/`. Back them up if needed.
"""
import json
import os
import sys

# Ensure project root is on sys.path so `from database import db` works when running the script
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db_backend import db

OUT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'data'))
BLACKOUT = os.path.join(OUT_DIR, 'blacklist.json')
WHITEOUT = os.path.join(OUT_DIR, 'whitelist.json')

if __name__ == '__main__':
    os.makedirs(OUT_DIR, exist_ok=True)
    # 导出 blacklist
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT session_id, pattern, type FROM blacklist")
        rows = cursor.fetchall()
        data = {}
        for session_id, pattern, type_ in rows:
            data.setdefault(session_id, []).append({'pattern': pattern, 'type': type_})
        with open(BLACKOUT, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print('导出 blacklist 完成 ->', BLACKOUT)
    except Exception as e:
        print('导出 blacklist 失败:', e)
    finally:
        try:
            conn.close()
        except:
            pass

    # 导出 whitelist
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT session_id, pattern, answer FROM whitelist")
        rows = cursor.fetchall()
        data = {}
        for session_id, pattern, answer in rows:
            data.setdefault(session_id, []).append({'pattern': pattern, 'answer': answer})
        with open(WHITEOUT, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print('导出 whitelist 完成 ->', WHITEOUT)
    except Exception as e:
        print('导出 whitelist 失败:', e)
    finally:
        try:
            conn.close()
        except:
            pass
