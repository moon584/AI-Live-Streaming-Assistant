"""
Baidu TTS helper

Provides a simple function to obtain an access token and synthesize short text
using Baidu's text2audio endpoint. Saves the audio to a file and returns the
path. Reads credentials from environment variables (see project `.env`).

Note: Baidu's TTS `aue` mapping may vary by account/region. This helper uses
reasonable defaults and returns raw bytes when successful.
"""
import os
import requests
import logging

logger = logging.getLogger(__name__)

BAIDU_OAUTH_URL = 'https://aip.baidubce.com/oauth/2.0/token'
BAIDU_TTS_URL = 'https://tsn.baidu.com/text2audio'


def _get_env(key, default=None):
    return os.environ.get(key, default)


def get_access_token(api_key=None, secret_key=None):
    """Get Baidu access token from API Key and Secret Key.

    Returns access_token string on success or raises RuntimeError on failure.
    """
    api_key = api_key or _get_env('BAIDU_TTS_API_KEY')
    secret_key = secret_key or _get_env('BAIDU_TTS_SECRET_KEY')
    if not api_key or not secret_key:
        raise RuntimeError('BAIDU_TTS_API_KEY or BAIDU_TTS_SECRET_KEY not set')

    params = {
        'grant_type': 'client_credentials',
        'client_id': api_key,
        'client_secret': secret_key,
    }
    r = requests.post(BAIDU_OAUTH_URL, params=params, timeout=10)
    r.raise_for_status()
    j = r.json()
    token = j.get('access_token')
    if not token:
        raise RuntimeError(f'Failed to obtain Baidu access token: {j}')
    return token


def _format_to_aue(format_name: str):
    fmt = (format_name or '').lower()
    if fmt in ('mp3',):
        return 4
    return 3


def synthesize(text: str,
               out_path: str = None,
               voice: int = None,
               fmt: str = None,
               sample_rate: int = None,
               token: str = None,
               rate: float = None):
    """Synthesize `text` to audio using Baidu TTS.

    If `out_path` is provided the audio will be saved there and the path is
    returned. Otherwise the function returns the audio bytes.
    """
    if not text:
        raise ValueError('text must be provided')

    token = token or get_access_token()

    voice = voice or int(_get_env('BAIDU_TTS_VOICE', 0))
    fmt = fmt or _get_env('BAIDU_TTS_FORMAT', 'wav')
    sample_rate = sample_rate or int(_get_env('BAIDU_TTS_SAMPLE_RATE', 24000))
    rate = rate or float(_get_env('BAIDU_TTS_RATE', 1.0))

    aue = _format_to_aue(fmt)

    params = {
        'tex': text,
        'tok': token,
        'cuid': _get_env('BAIDU_TTS_CUID', 'pj-local'),
        'ctp': 1,
        'lan': 'zh',
        'per': voice,
        'aue': aue,
        'spd': int(max(0, min(9, round(rate * 5)))),
    }

    try:
        params['tex'] = text
        r = requests.get(BAIDU_TTS_URL, params=params, timeout=30)
        content_type = r.headers.get('Content-Type', '')
        if 'application/json' in content_type or r.status_code != 200:
            try:
                j = r.json()
            except Exception:
                j = {'status_code': r.status_code, 'text': r.text}
            raise RuntimeError(f'Baidu TTS error: {j}')

        audio = r.content
        if out_path:
            out_dir = os.path.dirname(out_path)
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)
            with open(out_path, 'wb') as f:
                f.write(audio)
            logger.info(f'Baidu TTS saved to {out_path}')
            return out_path
        return audio
    except requests.RequestException as e:
        raise RuntimeError(f'Network error when calling Baidu TTS: {e}')
