import sqlite3, os
DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'local_db.sqlite3')
DB = os.path.normpath(DB)
print('Using DB:', DB)
if not os.path.exists(DB):
    print('DB not found'); raise SystemExit(1)
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
for kw in ['湖北','山东','陕西']:
    print('\nConversations mentioning', kw)
    cur.execute('SELECT id, ai_response FROM conversations WHERE ai_response LIKE ? ORDER BY id DESC LIMIT 20', ('%'+kw+'%',))
    for r in cur.fetchall():
        print(r['id'], r['ai_response'][:300].replace('\n',' '))
conn.close()
