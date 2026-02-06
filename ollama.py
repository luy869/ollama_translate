import requests
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")

def _post_process_output(text: str) -> str:
    """以前と同じ整形処理（念のため残す）"""
    if not text: return text
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    
    # 発音行を探して抽出するロジック（DeepSeekやGemmaが余計なことを言った時用）
    pronunciation_index = -1
    for i, line in enumerate(lines):
        if "発音:" in line or "발음:" in line:
            pronunciation_index = i
            break
    
    if pronunciation_index > 0:
        return f"{lines[pronunciation_index - 1]}\n{lines[pronunciation_index]}"
    return "\n".join(lines[:2])

def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    # ★変更点: 作成したカスタムモデル名を指定
    model_name = "my-translator"

    # プロンプトは「翻訳したい文」だけでOK
    # 言語指定は念のため入れますが、システムプロンプトが強力なら不要な場合も多いです
    if target_lang == "ko":
        prompt = f"韓国語に翻訳: {text}"
    else:
        prompt = f"日本語に翻訳: {text}"

    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return _post_process_output(data.get("response", ""))
    except Exception as e:
        return f"翻訳エラー: {e}"