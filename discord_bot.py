#!/usr/bin/env python3
import os
import discord
from dotenv import load_dotenv
import re

import ollama
import ollama_thinking  
from vc_music import play_url_from_message

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    if CHANNEL_ID:
        channel = client.get_channel(CHANNEL_ID)
        if not channel:
            try:
                channel = await client.fetch_channel(CHANNEL_ID)
            except Exception as e:
                print(f"Failed to fetch channel {CHANNEL_ID}: {e}")
        # if channel:
            await channel.send("起動しました！")
        else:
            print(f"Channel {CHANNEL_ID} not found. Ensure the bot is in the server and has access.")
    else:
        print("CHANNEL_ID not set")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    elif message.channel.id != CHANNEL_ID:
        return

    elif message.content.startswith(("!p", "！ｐ")):
        await play_url_from_message(message, message.content[2:].strip())

    # message_content を最初に初期化
    message_content = message.content

    if message.content.startswith(("!", "！")):
        return

    elif message.content.startswith(("?", "？")):
        # 1文字目を削除
        trimmed_content = message.content[1:]
        think_text = ollama_thinking.think_text(trimmed_content)
        await message.channel.send(f"{think_text}")

    # 翻訳処理（日本語/韓国語のみ想定）
    elif message_content.strip():
        RE_HIRAGANA = re.compile(r"[\u3040-\u309F]")
        RE_KATAKANA = re.compile(r"[\u30A0-\u30FF]")
        RE_HANGUL = re.compile(r"[\u3130-\u318F\u1100-\u11FF\uA960-\uA97F\uAC00-\uD7AF\uD7B0-\uD7FF]")
        RE_CJK = re.compile(r"[\u4E00-\u9FFF\u3400-\u4DBF\uF900-\uFAFF]")

        has_hiragana = bool(RE_HIRAGANA.search(message_content))
        has_katakana = bool(RE_KATAKANA.search(message_content))
        has_hangul = bool(RE_HANGUL.search(message_content))
        has_cjk = bool(RE_CJK.search(message_content))

        if has_hangul:
            translated_text = ollama.translate_text(message_content, "ko", "ja")
            await message.channel.send(f"翻訳結果 (韓国語→日本語):\n{translated_text}")
        elif has_hiragana or has_katakana or has_cjk:
            translated_text = ollama.translate_text(message_content, "ja", "ko")
            await message.channel.send(f"翻訳結果 (日本語→韓国語):\n{translated_text}")
        else:
            await message.channel.send("翻訳できません。日本語または韓国語を入力してください。")

# client.run(TOKEN) は main.py で実行