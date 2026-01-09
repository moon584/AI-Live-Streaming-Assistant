# diagnostic script to test MySQL connection pool
import os
from dotenv import load_dotenv
load_dotenv()
from mysql.connector import pooling

host=os.getenv('DB_HOST','localhost')
user=os.getenv('DB_USER','root')
password=os.getenv('DB_PASSWORD','')
database=os.getenv('DB_NAME','live_assistant')
pool_size=int(os.getenv('DB_POOL_SIZE','5'))

print('Testing DB connection with:')
print('HOST=',host)
print('USER=',user)
print('DATABASE=',database)
print('POOL_SIZE=',pool_size)
print('PASSWORD set?', bool(password))

try:
    pool = pooling.MySQLConnectionPool(pool_name='testpool', pool_size=max(1,pool_size), host=host, user=user, password=password, database=database)
    print('Pool created OK')
    conn = pool.get_connection()
    print('Got connection OK')
    cur = conn.cursor()
    cur.execute('SELECT 1')
    print('Query ok, result:', cur.fetchone())
    conn.close()
except Exception as e:
    print('ERROR creating pool or connecting:', repr(e))
    import traceback
    traceback.print_exc()
