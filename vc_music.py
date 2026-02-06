import discord
import asyncio
import os
from dotenv import load_dotenv
from typing import Optional, Dict, List
from collections import deque
import yt_dlp

# 環境変数の読み込み
load_dotenv()

# ギルドごとの音楽キュー
music_queues: Dict[int, deque] = {}
# 現在再生中の情報
now_playing: Dict[int, dict] = {}

def get_queue(guild_id: int) -> deque:
    """ギルドのキューを取得（なければ作成）"""
    if guild_id not in music_queues:
        music_queues[guild_id] = deque()
    return music_queues[guild_id]


async def play_next(guild: discord.Guild, voice_client: discord.VoiceClient) -> None:
    """キューから次の曲を再生"""
    queue = get_queue(guild.id)
    
    if len(queue) == 0:
        now_playing.pop(guild.id, None)
        return
    
    # 次の曲を取得
    next_song = queue.popleft()
    now_playing[guild.id] = next_song
    
    try:
        # yt-dlp で音声URL取得
        ytdl_format_options = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0',
        }
        
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }
        
        with yt_dlp.YoutubeDL(ytdl_format_options) as ydl:
            info = ydl.extract_info(next_song['url'], download=False)
            audio_url = info['url']
        
        # 再生
        source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
        
        def after_playing(error):
            if error:
                print(f"Player error: {error}")
            # 次の曲を再生（asyncio loop で実行）
            coro = play_next(guild, voice_client)
            asyncio.run_coroutine_threadsafe(coro, voice_client.loop)
        
        voice_client.play(source, after=after_playing)
        
        # チャンネルに通知
        if next_song.get('channel'):
            await next_song['channel'].send(f"🎵 再生中: {next_song['title']}")
    
    except Exception as e:
        print(f"再生エラー: {e}")
        if next_song.get('channel'):
            await next_song['channel'].send(f"再生エラー: {e}")
        # エラーでも次の曲を試す
        await play_next(guild, voice_client)


async def play_url_from_message(message: discord.Message, url: str) -> None:
    """メッセージ送信者のいるVCで指定URLの音声を再生する。

    message.guild.voice_client を使って接続・再生を行う。エラー時はメッセージで通知する。
    """
    # ユーザーがVCに参加しているか確認
    if not message.author.voice or not message.author.voice.channel:
        await message.channel.send("VCに参加してから実行してください。")
        return

    channel = message.author.voice.channel

    # そのギルドに対する voice_client を取得
    voice_client: Optional[discord.VoiceClient] = message.guild.voice_client

    try:
        if voice_client is None:
            voice_client = await channel.connect()
        elif voice_client.channel != channel:
            await voice_client.move_to(channel)

        # 曲情報を取得
        loading_msg = await message.channel.send("🔍 曲情報を取得中...")
        
        ytdl_format_options = {
            'format': 'bestaudio/best',
            'noplaylist': False,  # 再生リストを許可
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0',
            'extract_flat': 'in_playlist',  # 再生リスト内の動画情報を高速取得
        }
        
        with yt_dlp.YoutubeDL(ytdl_format_options) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # 再生リストかどうか確認
            if 'entries' in info:
                # 再生リスト
                playlist_title = info.get('title', 'Unknown Playlist')
                entries = info['entries']
                
                await loading_msg.edit(content=f"📋 再生リスト「{playlist_title}」を処理中... ({len(entries)}曲)")
                
                queue = get_queue(message.guild.id)
                added_count = 0
                
                for entry in entries:
                    if entry:  # エントリーが有効な場合
                        song_info = {
                            'url': entry.get('url') or f"https://www.youtube.com/watch?v={entry['id']}",
                            'title': entry.get('title', 'Unknown'),
                            'duration': entry.get('duration', 0),
                            'channel': message.channel,
                            'requester': message.author
                        }
                        queue.append(song_info)
                        added_count += 1
                
                # 再生中でなければ再生開始
                if not voice_client.is_playing() and not voice_client.is_paused():
                    await loading_msg.edit(content=f"✅ 再生リスト「{playlist_title}」から{added_count}曲を追加して再生を開始します。")
                    await play_next(message.guild, voice_client)
                else:
                    await loading_msg.edit(content=f"✅ 再生リスト「{playlist_title}」から{added_count}曲をキューに追加しました。")
            
            else:
                # 単一の動画
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                
                # キューに追加
                queue = get_queue(message.guild.id)
                song_info = {
                    'url': url,
                    'title': title,
                    'duration': duration,
                    'channel': message.channel,
                    'requester': message.author
                }
                queue.append(song_info)
                
                # 再生中でなければ再生開始
                if not voice_client.is_playing() and not voice_client.is_paused():
                    await loading_msg.edit(content=f"✅ 再生を開始します: {title}")
                    await play_next(message.guild, voice_client)
                else:
                    position = len(queue)
                    await loading_msg.edit(content=f"✅ キューに追加しました: {title}\n📝 キュー位置: {position}")

    except Exception as e:
        await message.channel.send(f"エラー: {e}")


async def skip_song(message: discord.Message) -> None:
    """現在の曲をスキップ"""
    voice_client: Optional[discord.VoiceClient] = message.guild.voice_client
    
    if not voice_client or not voice_client.is_connected():
        await message.channel.send("Botはボイスチャンネルに接続していません。")
        return
    
    if not voice_client.is_playing():
        await message.channel.send("現在再生中の曲はありません。")
        return
    
    voice_client.stop()
    await message.channel.send("⏭️ 曲をスキップしました。")


async def pause_song(message: discord.Message) -> None:
    """再生を一時停止"""
    voice_client: Optional[discord.VoiceClient] = message.guild.voice_client
    
    if not voice_client or not voice_client.is_connected():
        await message.channel.send("Botはボイスチャンネルに接続していません。")
        return
    
    if voice_client.is_paused():
        await message.channel.send("既に一時停止中です。")
        return
    
    if not voice_client.is_playing():
        await message.channel.send("現在再生中の曲はありません。")
        return
    
    voice_client.pause()
    await message.channel.send("⏸️ 再生を一時停止しました。")


async def resume_song(message: discord.Message) -> None:
    """再生を再開"""
    voice_client: Optional[discord.VoiceClient] = message.guild.voice_client
    
    if not voice_client or not voice_client.is_connected():
        await message.channel.send("Botはボイスチャンネルに接続していません。")
        return
    
    if not voice_client.is_paused():
        await message.channel.send("一時停止中ではありません。")
        return
    
    voice_client.resume()
    await message.channel.send("▶️ 再生を再開しました。")


async def show_queue(message: discord.Message) -> None:
    """キューを表示"""
    queue = get_queue(message.guild.id)
    current = now_playing.get(message.guild.id)
    
    if not current and len(queue) == 0:
        await message.channel.send("キューは空です。")
        return
    
    msg = "📜 **音楽キュー**\n\n"
    
    if current:
        msg += f"🎵 **現在再生中:**\n{current['title']}\n\n"
    
    if len(queue) > 0:
        msg += "**次の曲:**\n"
        for i, song in enumerate(list(queue)[:10], 1):
            msg += f"{i}. {song['title']}\n"
        
        if len(queue) > 10:
            msg += f"\n...他 {len(queue) - 10} 曲"
    
    await message.channel.send(msg)


async def clear_queue(message: discord.Message) -> None:
    """キューをクリア"""
    queue = get_queue(message.guild.id)
    queue.clear()
    await message.channel.send("🗑️ キューをクリアしました。")


async def stop_and_disconnect(guild: discord.Guild) -> None:
    """指定ギルドのVC接続を停止して切断する。"""
    voice_client: Optional[discord.VoiceClient] = guild.voice_client
    if voice_client:
        try:
            if voice_client.is_playing():
                voice_client.stop()
            
            # キューもクリア
            queue = get_queue(guild.id)
            queue.clear()
            now_playing.pop(guild.id, None)
            
            await voice_client.disconnect()
        except Exception as e:
            print(f"切断エラー: {e}")


async def disconnect_from_message(message: discord.Message) -> None:
    """メッセージからVC切断"""
    voice_client: Optional[discord.VoiceClient] = message.guild.voice_client
    
    if not voice_client or not voice_client.is_connected():
        await message.channel.send("Botはボイスチャンネルに接続していません。")
        return
    
    await stop_and_disconnect(message.guild)
    await message.channel.send("👋 ボイスチャンネルから切断しました。")


# vc_music.py は単体で client.run を実行しない（main.py が実行する）