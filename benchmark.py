import subprocess
import time
import os
import re
import sys

# ================= 設定エリア =================
# テストしたいモデル名
# 速度比較用（軽量）: gemma3:4b, llama3
# 本気テスト用（重量）: llama3:8b-instruct-q8_0, mistral-nemo
MODEL_NAME = "gemma3:27b" 

# プロンプト (少し長めに生成させる)
PROMPT = "Explain the theory of relativity in simple terms for a 5-year-old in about 100 words."
# ==============================================

def run_command(command, env=None):
    """コマンドを実行し、リアルタイムで表示しつつ出力を返す"""
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env
        )
        
        full_output = ""
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                print(line.strip()) # 進行状況を表示
                full_output += line
        
        return full_output
    except Exception as e:
        return str(e)

def parse_metrics(output):
    """ログから生成速度と読解速度を抽出する"""
    metrics = {
        "eval_rate": 0.0,       # 生成速度 (重要: チャットの滑らかさ)
        "prompt_eval_rate": 0.0 # 読解速度 (入力の処理)
    }
    
    # 正規表現で数値を抽出
    # "prompt eval rate" を先に探す
    prompt_match = re.search(r'prompt eval rate:\s+([\d\.]+)\s+tokens/s', output)
    if prompt_match:
        metrics["prompt_eval_rate"] = float(prompt_match.group(1))

    # "eval rate" (promptがつかない純粋なもの) を探す
    # 行頭、または改行直後の eval rate を狙う
    eval_match = re.search(r'(?<!prompt )eval rate:\s+([\d\.]+)\s+tokens/s', output)
    if eval_match:
        metrics["eval_rate"] = float(eval_match.group(1))
        
    return metrics

def benchmark(config_name, gpu_ids):
    print(f"\n--- {config_name} のテストを開始 ---")
    current_env = os.environ.copy()
    current_env["CUDA_VISIBLE_DEVICES"] = gpu_ids
    
    # サーバー起動
    print(f"Ollamaサーバーを起動中 (GPU: {gpu_ids})...")
    server_process = subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=current_env
    )
    time.sleep(5) # 起動待ち
    
    try:
        print(f"モデル '{MODEL_NAME}' で推論を実行中...")
        cmd = f'ollama run {MODEL_NAME} --verbose "{PROMPT}"'
        output = run_command(cmd, env=current_env)
        
        metrics = parse_metrics(output)
        print(f"計測結果 -> 生成: {metrics['eval_rate']} t/s, 読込: {metrics['prompt_eval_rate']} t/s")
        return metrics
        
    finally:
        # サーバー停止
        server_process.terminate()
        server_process.wait()
        time.sleep(2)

def main():
    print("=== Ollama マルチGPU ベンチマーク (修正版) ===")
    print(f"Target Model: {MODEL_NAME}")
    print("※事前に 'sudo systemctl stop ollama' を実行済みであることを確認してください。")
    
    results = []
    configs = [
        ("GTX 1660 Ti (Single)", "0"),
        ("GTX 1070 (Single)",    "1"),
        ("Dual GPU (Both)",      "0,1")
    ]

    for name, gpu_id in configs:
        metrics = benchmark(name, gpu_id)
        results.append((name, metrics))

    # === 結果発表 ===
    print("\n" + "="*65)
    print(f"ベンチマーク結果 (Model: {MODEL_NAME})")
    print("="*65)
    print(f"{'構成':<22} | {'生成速度 (Tokens/s)':<20} | {'読解速度 (Tokens/s)':<20}")
    print("-" * 65)
    for name, m in results:
        # 生成速度（eval_rate）がチャットの速さです
        print(f"{name:<22} | {m['eval_rate']:<20.2f} | {m['prompt_eval_rate']:<20.2f}")
    print("="*65)
    print("※ 生成速度が大きいほどチャットが快適です。")

if __name__ == "__main__":
    main()