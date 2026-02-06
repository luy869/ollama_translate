import re

RE_HIRAGANA = re.compile(r"[\u3040-\u309F]")
RE_KATAKANA = re.compile(r"[\u30A0-\u30FF]")
RE_HANGUL = re.compile(r"[\u3130-\u318F\u1100-\u11FF\uA960-\uA97F\uAC00-\uD7AF\uD7B0-\uD7FF]")
RE_CJK = re.compile(r"[\u4E00-\u9FFF\u3400-\u4DBF\uF900-\uFAFF]")

def detect_language(text):
    has_hiragana = bool(RE_HIRAGANA.search(text))
    has_katakana = bool(RE_KATAKANA.search(text))
    has_hangul = bool(RE_HANGUL.search(text))
    has_cjk = bool(RE_CJK.search(text))

    if has_hangul:
        return "korean"
    elif has_hiragana or has_katakana or has_cjk:
        return "japanese"
    else:
        return "unknown"