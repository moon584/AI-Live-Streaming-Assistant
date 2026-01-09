"""Run a quick Baidu TTS demo and save audio to static/audio."""
import os
from pathlib import Path
import dotenv

# Load .env from project root
dotenv.load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / '.env')

from services import baidu_tts


def main():
    text = '这是一条用于测试百度短文本在线合成的语音。'
    out_dir = Path(__file__).resolve().parents[1] / 'static' / 'audio'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'baidu_demo_{os.getpid()}.wav'
    try:
        path = baidu_tts.synthesize(text, out_path=str(out_path))
        print('Saved audio to:', path)
    except Exception as e:
        print('Baidu TTS failed:', e)


if __name__ == '__main__':
    main()
