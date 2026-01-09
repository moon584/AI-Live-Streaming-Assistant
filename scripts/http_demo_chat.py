import requests, json

base='http://127.0.0.1:5000'

# create session
try:
    r = requests.post(base+'/api/session', json={
        'host_name':'demo_host', 'live_theme':'演示', 'products':[{'name':'示例商品','price':10}]
    }, timeout=10)
    print('create status', r.status_code)
    print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    session_id = r.json().get('session_id')

    # call chat
    r2 = requests.post(base+'/api/chat', json={'session_id': session_id, 'message':'请用温柔的语气介绍这款商品'}, timeout=30)
    print('chat status', r2.status_code)
    print(json.dumps(r2.json(), ensure_ascii=False, indent=2))
except Exception as e:
    print('HTTP demo failed:', e)
