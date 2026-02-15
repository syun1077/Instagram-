"""
AI画像/動画生成モジュール
Pollinations.ai (無料・APIキー不要) + Together.ai (無料枠) を使用して、
プロンプトからAI画像を生成する。
ffmpegでスライドショー動画（リール用）を作成する。
"""

import requests
import urllib.parse
import os
import subprocess
import shutil
import time
import base64

from dotenv import load_dotenv

load_dotenv()

# Pollinations.ai 設定
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"
DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1080

# Pollinationsで試すモデルの優先順位（nanobanana優先）
POLLINATIONS_MODELS = ["nanobanana", "nanobanana-pro", "flux", "turbo"]


def _try_pollinations(prompt: str, width: int, height: int) -> bytes | None:
    """Pollinations.aiで画像生成を試行する。全モデルを順に試す。"""
    encoded_prompt = urllib.parse.quote(prompt)
    url = POLLINATIONS_URL.format(prompt=encoded_prompt)

    # サーバーダウン時は素早くスキップするため、最初のモデルで500が出たらカウント
    server_errors = 0

    for model in POLLINATIONS_MODELS:
        # 2モデル連続で500エラーならサーバー自体がダウンしている
        if server_errors >= 2:
            print("[Pollinations] サーバーダウン検出 → スキップ")
            return None

        params = {
            "width": width,
            "height": height,
            "nologo": "true",
            "enhance": "true",
            "model": model,
            "seed": int(time.time() * 1000) % 2147483647,
        }

        try:
            print(f"[Pollinations] モデル: {model}")
            response = requests.get(url, params=params, timeout=120)

            if response.status_code >= 500:
                print(f"[Pollinations] サーバーエラー (HTTP {response.status_code})")
                server_errors += 1
                continue

            if response.status_code != 200:
                print(f"[Pollinations] HTTPエラー ({response.status_code})")
                continue

            content_type = response.headers.get("content-type", "")
            if "image" not in content_type:
                print(f"[Pollinations] 画像以外 (Content-Type: {content_type})")
                continue

            if len(response.content) < 1000:
                print(f"[Pollinations] データ小 ({len(response.content)} bytes)")
                continue

            print(f"[Pollinations] 成功! ({len(response.content) / 1024:.0f} KB, モデル: {model})")
            return response.content

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print(f"[Pollinations] 接続エラー: {e}")
            server_errors += 1

    return None


def _try_together(prompt: str, width: int, height: int) -> bytes | None:
    """Together.ai (無料FLUX) で画像生成を試行する。"""
    api_key = os.getenv("TOGETHER_API_KEY", "")
    if not api_key:
        print("[Together] APIキー未設定 → スキップ")
        return None

    url = "https://api.together.xyz/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Together.aiの解像度制限に合わせる
    # FLUX.1-schnell-Freeは特定の解像度のみ対応
    if width == height:
        tw, th = 1024, 1024
    elif width > height:
        tw, th = 1280, 768
    else:
        tw, th = 768, 1280

    data = {
        "model": "black-forest-labs/FLUX.1-schnell-Free",
        "prompt": prompt,
        "width": tw,
        "height": th,
        "steps": 4,
        "n": 1,
        "response_format": "b64_json",
    }

    for attempt in range(1, 4):  # 3回リトライ
        try:
            print(f"[Together] FLUX.1-schnell で生成中... (試行 {attempt}/3)")
            response = requests.post(url, json=data, headers=headers, timeout=120)

            if response.status_code == 200:
                result = response.json()
                if "data" in result and len(result["data"]) > 0:
                    # b64_json形式の場合
                    b64_data = result["data"][0].get("b64_json", "")
                    if b64_data:
                        image_bytes = base64.b64decode(b64_data)
                        print(f"[Together] 成功! ({len(image_bytes) / 1024:.0f} KB)")
                        return image_bytes

                    # URL形式の場合
                    img_url = result["data"][0].get("url", "")
                    if img_url:
                        img_resp = requests.get(img_url, timeout=60)
                        if img_resp.status_code == 200:
                            print(f"[Together] 成功! ({len(img_resp.content) / 1024:.0f} KB)")
                            return img_resp.content

            elif response.status_code == 401:
                print("[Together] APIキーが無効 → スキップ")
                return None
            elif response.status_code == 429:
                print("[Together] レートリミット → 30秒待機")
                time.sleep(30)
                continue
            else:
                error_msg = response.json().get("error", {}).get("message", response.text[:200])
                print(f"[Together] エラー ({response.status_code}): {error_msg}")

        except Exception as e:
            print(f"[Together] エラー: {e}")

        if attempt < 3:
            time.sleep(10)

    return None


def _try_stable_horde(prompt: str, width: int, height: int) -> bytes | None:
    """Stable Horde (完全無料・APIキー不要・コミュニティ運営) で画像生成する。"""
    # 解像度を1024に調整（Stable Horde推奨）
    hw = 1024 if width >= 1024 else width
    hh = 1024 if height >= 1024 else height

    # ステップ数を減らして処理を速くする（キュー優先度が上がる）
    submit_url = "https://stablehorde.net/api/v2/generate/async"
    data = {
        "prompt": prompt,
        "params": {
            "width": hw,
            "height": hh,
            "steps": 20,
            "sampler_name": "k_euler",
            "cfg_scale": 7,
        },
        "nsfw": False,
        "models": ["AlbedoBase XL (SDXL)", "SDXL 1.0", "Deliberate", "DreamShaper"],
        "r2": True,
    }
    headers = {"apikey": "0000000000", "Content-Type": "application/json"}

    try:
        print("[StableHorde] ジョブ送信中...")
        r = requests.post(submit_url, json=data, headers=headers, timeout=30)
        if r.status_code != 202:
            print(f"[StableHorde] 送信失敗 ({r.status_code}): {r.text[:200]}")
            return None

        job_id = r.json().get("id")
        print(f"[StableHorde] ジョブID: {job_id}")

        # 最大10分待機（GitHub Actionsのtimeout-minutes: 15に対して余裕を持たせる）
        for i in range(120):
            time.sleep(5)
            try:
                check = requests.get(
                    f"https://stablehorde.net/api/v2/generate/check/{job_id}",
                    timeout=15,
                )
                info = check.json()
            except Exception as e:
                print(f"[StableHorde] チェックエラー: {e}")
                continue

            wait = info.get("wait_time", 0)
            queue = info.get("queue_position", 0)

            if i % 6 == 0:  # 30秒ごとにログ
                print(f"[StableHorde] 待機中... (キュー: {queue}, 予想: {wait}s, 経過: {i*5}s)")

            if info.get("done"):
                # 結果取得
                result = requests.get(
                    f"https://stablehorde.net/api/v2/generate/status/{job_id}",
                    timeout=30,
                )
                generations = result.json().get("generations", [])
                if generations:
                    img_data = generations[0].get("img", "")
                    if img_data.startswith("http"):
                        img_resp = requests.get(img_data, timeout=60)
                        if img_resp.status_code == 200:
                            print(f"[StableHorde] 成功! ({len(img_resp.content) / 1024:.0f} KB)")
                            return img_resp.content
                    else:
                        image_bytes = base64.b64decode(img_data)
                        print(f"[StableHorde] 成功! ({len(image_bytes) / 1024:.0f} KB)")
                        return image_bytes
                break

            if info.get("faulted"):
                print("[StableHorde] ジョブが失敗しました")
                break

        print("[StableHorde] タイムアウト（10分）")

    except Exception as e:
        print(f"[StableHorde] エラー: {e}")

    return None


def _try_picogen(prompt: str, width: int, height: int) -> bytes | None:
    """Pollinations.ai の別エンドポイント (text2img) で画像生成を試行する。"""
    try:
        # Pollinations text2img API（別エンドポイント）
        url = "https://text.pollinations.ai/openai/images/generations"
        data = {
            "prompt": prompt,
            "model": "flux",
            "size": f"{min(width, 1024)}x{min(height, 1024)}",
            "n": 1,
        }
        headers = {"Content-Type": "application/json"}

        print("[Pollinations-Alt] text2img APIで試行中...")
        response = requests.post(url, json=data, headers=headers, timeout=120)

        if response.status_code == 200:
            result = response.json()
            if "data" in result and len(result["data"]) > 0:
                img_url = result["data"][0].get("url", "")
                if img_url:
                    img_resp = requests.get(img_url, timeout=60)
                    if img_resp.status_code == 200 and len(img_resp.content) > 1000:
                        print(f"[Pollinations-Alt] 成功! ({len(img_resp.content) / 1024:.0f} KB)")
                        return img_resp.content

                b64_data = result["data"][0].get("b64_json", "")
                if b64_data:
                    image_bytes = base64.b64decode(b64_data)
                    print(f"[Pollinations-Alt] 成功! ({len(image_bytes) / 1024:.0f} KB)")
                    return image_bytes
        else:
            print(f"[Pollinations-Alt] HTTPエラー ({response.status_code})")

    except Exception as e:
        print(f"[Pollinations-Alt] エラー: {e}")

    return None


def _run_generation_chain(full_prompt: str, width: int, height: int) -> bytes | None:
    """全APIを順に試行して画像生成する。"""
    # 1. Pollinations.ai を試行
    print("[AI画像生成] === Pollinations.ai で試行 ===")
    image_data = _try_pollinations(full_prompt, width, height)

    # 2. Pollinations 別エンドポイント
    if not image_data:
        print("[AI画像生成] === Pollinations 別エンドポイント ===")
        image_data = _try_picogen(full_prompt, width, height)

    # 3. Together.ai
    if not image_data:
        print("[AI画像生成] === Together.ai にフォールバック ===")
        image_data = _try_together(full_prompt, width, height)

    # 4. Stable Horde（完全無料・キー不要）
    if not image_data:
        print("[AI画像生成] === Stable Horde にフォールバック（無料・キー不要） ===")
        image_data = _try_stable_horde(full_prompt, width, height)

    return image_data


def generate_ai_image(
    prompt: str,
    output_path: str = "temp_image.jpg",
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    style_suffix: str = (
        "photorealistic, professional product photography, "
        "sharp focus, studio lighting, high detail, no blur, no artifacts"
    ),
) -> str:
    """
    AIプロンプトから高画質画像を生成してローカルに保存する。
    全API失敗時は60秒待って1回リトライする（計2回試行）。
    """
    full_prompt = f"{prompt}, {style_suffix}"

    print(f"[AI画像生成] プロンプト: {prompt}")
    print(f"[AI画像生成] 解像度: {width}x{height}")

    # 1回目の試行
    image_data = _run_generation_chain(full_prompt, width, height)

    # 全て失敗 → 60秒待ってリトライ（API一時障害対策）
    if not image_data:
        print("[AI画像生成] === 全API失敗。60秒後にリトライ ===")
        time.sleep(60)
        image_data = _run_generation_chain(full_prompt, width, height)

    if not image_data:
        raise RuntimeError(
            "AI画像生成に全API（Pollinations/Together/StableHorde）で2回失敗しました。"
        )

    with open(output_path, "wb") as f:
        f.write(image_data)

    file_size = os.path.getsize(output_path)
    print(f"[AI画像生成] 保存完了: {output_path} ({file_size / 1024:.0f} KB)")
    return output_path


# --- プロンプトのヒント集 ---
PROMPT_EXAMPLES = [
    "A serene Japanese garden with cherry blossoms at sunset",
    "Cyberpunk city skyline at night with neon lights",
    "Cute cat sitting in a cozy coffee shop, warm lighting",
    "Minimalist flat lay photography of workspace with laptop and coffee",
    "Beautiful ocean sunset with dramatic clouds, golden hour",
    "Aesthetic food photography of a matcha latte with latte art",
    "Modern architecture building with glass reflection",
    "Fantasy landscape with floating islands and waterfalls",
]


def show_prompt_examples() -> None:
    """プロンプト例を表示する。"""
    print("\n--- プロンプト例（英語推奨） ---")
    for i, example in enumerate(PROMPT_EXAMPLES, 1):
        print(f"  {i}. {example}")
    print()


# --- リール動画生成（スライドショー） ---

def generate_slideshow_video(
    image_paths: list[str],
    output_path: str = "temp_reel.mp4",
    duration_per_image: float = 3.0,
    fps: int = 30,
    width: int = 1080,
    height: int = 1920,
) -> str:
    """
    複数の画像からズーム/パンエフェクト付きスライドショー動画を生成する。
    Instagram Reels用（9:16縦長）。
    """
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "ffmpegがインストールされていません。\n"
            "Ubuntu: sudo apt install ffmpeg\n"
            "Windows: https://ffmpeg.org/download.html"
        )

    if not image_paths:
        raise ValueError("画像パスが空です")

    print(f"[動画生成] {len(image_paths)}枚からスライドショー動画を生成中...")

    total_duration = duration_per_image * len(image_paths)
    frames = int(duration_per_image * fps)

    # ズームエフェクトのパターン（画像ごとに変える）
    zoom_effects = [
        f"zoompan=z='min(zoom+0.002,1.3)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps}",
        f"zoompan=z='if(eq(on,1),1.3,max(zoom-0.002,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps}",
        f"zoompan=z='1.2':x='if(eq(on,1),0,min(x+2,iw-iw/zoom))':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps}",
        f"zoompan=z='min(zoom+0.0015,1.25)':x='iw/3-(iw/zoom/3)':y='ih/3-(ih/zoom/3)':d={frames}:s={width}x{height}:fps={fps}",
    ]

    clip_paths = []
    for i, img_path in enumerate(image_paths):
        clip_path = f"temp_clip_{i}.mp4"
        clip_paths.append(clip_path)
        effect = zoom_effects[i % len(zoom_effects)]

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", img_path,
            "-vf", effect,
            "-t", str(duration_per_image),
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            clip_path,
        ]
        print(f"[動画生成] クリップ {i+1}/{len(image_paths)} 作成中...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpegクリップ作成エラー: {result.stderr[-500:]}")

    concat_file = "temp_concat.txt"
    with open(concat_file, "w") as f:
        for clip_path in clip_paths:
            f.write(f"file '{clip_path}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ]
    print("[動画生成] クリップを結合中...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg結合エラー: {result.stderr[-500:]}")

    for clip_path in clip_paths:
        if os.path.exists(clip_path):
            os.remove(clip_path)
    if os.path.exists(concat_file):
        os.remove(concat_file)

    file_size = os.path.getsize(output_path)
    print(f"[動画生成] 完了: {output_path} ({file_size / 1024 / 1024:.1f} MB, {total_duration:.0f}秒)")
    return output_path


def generate_reel_images(
    prompt: str,
    output_dir: str = ".",
    num_images: int = 4,
    width: int = 1080,
    height: int = 1920,
) -> list[str]:
    """リール用の縦長画像を複数生成する。"""
    reel_angles = [
        "",
        ", close-up detail shot showing fabric texture and material quality",
        ", full body outfit view from slightly low angle, dynamic pose",
        ", artistic overhead flat lay with styling accessories, dark moody background",
        ", side profile view emphasizing silhouette and proportions",
    ]

    image_paths = []
    for i in range(num_images):
        angle = reel_angles[i % len(reel_angles)]
        full_prompt = prompt.rsplit(", 8K", 1)[0] + angle + ", vertical composition 9:16, 8K"

        img_path = os.path.join(output_dir, f"temp_reel_img_{i}.jpg")
        print(f"[リール画像] {i+1}/{num_images} 生成中...")
        generate_ai_image(full_prompt, img_path, width=width, height=height)
        image_paths.append(img_path)

    return image_paths
