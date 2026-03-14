# ollama-translate Discord Bot

OllamaのローカルLLMを使った日本語・韓国語翻訳 + 音楽再生 Discord Bot。

## 機能

- **自動翻訳**: 日本語 ↔ 韓国語をローカルLLMで翻訳（発音付き）
- **AI Q&A**: `?` プレフィックスでGemma 12Bに質問
- **音楽再生**: YouTubeのURL/プレイリストをVCで再生

## 前提条件

- [Ollama](https://ollama.ai/) がローカルで起動していること（デフォルト: `http://localhost:11434`）
- 以下の2つのモデルが利用可能なこと:
  - `my-translator` — `Modelfile` からビルド（ベース: `translategemma:12b`）
  - `gemma3:12b-it-qat` — AI Q&A用
- FFmpeg インストール済み（音楽再生に必要）
- Python パッケージ: `discord.py`, `python-dotenv`, `requests`, `yt-dlp`

## セットアップ

### 1. カスタム翻訳モデルのビルド

```bash
ollama create my-translator -f Modelfile
```

### 2. 環境変数の設定

`.env` ファイルを作成:

```
DISCORD_TOKEN=<Discordボットトークン>
DISCORD_CHANNEL_ID=<応答するチャンネルID>
OLLAMA_API_URL=http://localhost:11434/api/generate  # 省略可
```

### 3. 起動

```bash
python main.py
```

## コマンド一覧

| コマンド | 説明 |
|---|---|
| `!p [URL]` | 曲を再生 / キューに追加（YouTube URL・プレイリスト対応） |
| `!skip` | 現在の曲をスキップ |
| `!pause` | 一時停止 |
| `!resume` | 再開 |
| `!queue` | キューを表示 |
| `!clear` | キューをクリア |
| `!stop` / `!disconnect` | 再生停止・VC切断 |
| `?[質問]` | AI (Gemma 12B) に質問 |
| `!help` | コマンド一覧を表示 |
| テキスト送信 | 日本語・韓国語を自動検出して翻訳 |

## アーキテクチャ

```
main.py
└── discord_bot.py       # メッセージルーティング
    ├── ollama.py         # my-translator モデルで翻訳
    ├── ollama_thinking.py # gemma3:12b-it-qat で Q&A
    └── vc_music.py       # yt-dlp + FFmpeg で音楽再生
```

Botは `DISCORD_CHANNEL_ID` で指定した単一チャンネルのみ応答します。
言語検出はUnicode範囲（ひらがな・カタカナ・ハングル・CJK）でインライン判定。

## ユーティリティ

```bash
# GPUベンチマーク（事前にシステムのOllamaサービスを停止すること）
python benchmark.py
```
