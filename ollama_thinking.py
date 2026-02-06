import requests
import json
import os
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# Ollama APIのエンドポイント
url = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")

def think_text(text: str) -> str:
    prompt = (f"{text}")

    payload = {
        "model": "gemma3:12b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_predict": 1000,
            "enable_thinking": False,  # 推論モードを無効化
        },
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()

        data = response.json()
        raw = data.get("response", "")
        raw2 = data.get("thinking", "")
        
        # print(f"thio: response data: {data}")  # デバッグ出力
        return raw

    except requests.exceptions.RequestException as e:
        print(f"APIリクエストエラー: {e}")
        return f"翻訳エラー: {e}"
    except json.JSONDecodeError as e:
        print(f"JSON解析エラー: {e}")
        return f"翻訳エラー: JSON解析失敗"
    except Exception as e:
        print(f"予期しないエラー: {e}")
        return f"翻訳エラー: {e}"
