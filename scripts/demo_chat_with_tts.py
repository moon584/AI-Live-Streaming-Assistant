"""Demo: create a session and call /api/chat to exercise Baidu TTS integration.
This runs in-process using Flask test_client so it doesn't require the server to be
running separately.
"""
import json
from pathlib import Path
import dotenv

dotenv.load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / '.env')

from app import app


def main():
    with app.test_client() as c:
        # create session
        resp = c.post('/api/session', json={
            'host_name': 'demo_host',
            'live_theme': '测试专场',
            'products': [{'name': '测试商品', 'price': 9.9}]
        })
        print('create session status:', resp.status_code)
        print(resp.get_json())
        session_id = resp.get_json().get('session_id')

        # call chat
        chat_resp = c.post('/api/chat', json={
            'session_id': session_id,
            'message': '请用温柔的语气简单介绍一下商品'
        })
        print('chat status:', chat_resp.status_code)
        data = chat_resp.get_json()
        print(json.dumps(data, ensure_ascii=False, indent=2))

        # check audio file
        audio_url = data.get('audio_url')
        if audio_url:
            # map url to file path
            file_path = Path('.') / audio_url.lstrip('/')
            print('audio exists?', file_path.exists(), str(file_path))


if __name__ == '__main__':
    main()
