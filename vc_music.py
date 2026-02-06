import discord
import asyncio
import os
from dotenv import load_dotenv
from typing import Optional

# 環境変数の読み込み
load_dotenv()


async def play_url_from_message(message: discord.Message, url: str) -> None:
    """メッセージ送信者のいるVCで指定URLの音声を再生する。

    message.guild.voice_client を使って接続・再生を行う。エラー時はメッセージで通知する。
    """
    # ユーザーがVCに参加しているか確認
    if not message.author.voice or not message.author.voice.channel:
        await message.channel.send("VCに参加してから実行してください。")
        return

    channel = message.author.voice.channel

    # そのギルドに対する voice_client を取得（message.guild.voice_client を利用して client の参照を避ける）
    voice_client: Optional[discord.VoiceClient] = message.guild.voice_client

    try:
        if voice_client is None:
            voice_client = await channel.connect()
        elif voice_client.channel != channel:
            await voice_client.move_to(channel)

        # 再生中なら停止
        if voice_client.is_playing():
            voice_client.stop()

        # YouTube URL の場合は yt-dlp を使って音声URLを取得
        ytdl_format_options = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0',
        }
        
        ffmpeg_options = {
            'options': '-vn'
        }

        # yt-dlp で音声URL取得
        import yt_dlp
        with yt_dlp.YoutubeDL(ytdl_format_options) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info['url']
            title = info.get('title', 'Unknown')
        
        # FFmpeg で再生
        source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
        voice_client.play(source, after=lambda e: print(f"Player error: {e}") if e else None)

        await message.channel.send(f"音楽を再生中: {title}")

    except Exception as e:
        await message.channel.send(f"再生エラー: {e}")


async def stop_and_disconnect(guild: discord.Guild) -> None:
    """指定ギルドのVC接続を停止して切断する。"""
    voice_client: Optional[discord.VoiceClient] = guild.voice_client
    if voice_client:
        try:
            if voice_client.is_playing():
                voice_client.stop()
            await voice_client.disconnect()
        except Exception as e:
            print(f"切断エラー: {e}")


# vc_music.py は単体で client.run を実行しない（main.py が実行する）