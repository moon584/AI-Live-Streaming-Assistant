import sqlite3
import os
import json

DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'local_db.sqlite3')
DB = os.path.normpath(DB)
print('Using DB:', DB)
if not os.path.exists(DB):
    print('SQLite DB not found')
    raise SystemExit(1)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print('\nLast 10 products:')
for row in cur.execute('SELECT * FROM products ORDER BY id DESC LIMIT 10'):
    d = dict(row)
    # try to parse attributes if JSON
    attrs = d.get('attributes')
    try:
        d['attributes_parsed'] = json.loads(attrs) if isinstance(attrs, str) and attrs.strip().startswith('{') else attrs
    except Exception:
        d['attributes_parsed'] = attrs
    print(json.dumps(d, ensure_ascii=False, indent=2))

print('\nLast 10 conversations:')
for row in cur.execute('SELECT * FROM conversations ORDER BY id DESC LIMIT 10'):
    d = dict(row)
    print(json.dumps(d, ensure_ascii=False, indent=2))

conn.close()
