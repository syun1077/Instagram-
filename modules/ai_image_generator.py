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

    for model in POLLINATIONS_MODELS:
        params = {
            "width": width,
            "height": height,
            "nologo": "true",
            "enhance": "true",
            "model": model,
            "seed": int(time.time() * 1000) % 2147483647,
        }

        for attempt in range(1, 3):  # 各モデル2回
            try:
                print(f"[Pollinations] モデル: {model} (試行 {attempt}/2)")
                response = requests.get(url, params=params, timeout=300)

                if response.status_code >= 500:
                    print(f"[Pollinations] サーバーエラー (HTTP {response.status_code})")
                    if attempt < 2:
                        time.sleep(10)
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
                if attempt < 2:
                    time.sleep(10)

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

            elif response.status_code == 429:
                print(f"[Together] レートリミット → 30秒待機")
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

    1. Pollinations.ai（無料・APIキー不要）を複数モデルで試行
    2. 失敗時 → Together.ai（無料枠・APIキー必要）にフォールバック
    """
    full_prompt = f"{prompt}, {style_suffix}"

    print(f"[AI画像生成] プロンプト: {prompt}")
    print(f"[AI画像生成] 解像度: {width}x{height}")

    # 1. Pollinations.ai を試行
    print("[AI画像生成] === Pollinations.ai で試行 ===")
    image_data = _try_pollinations(full_prompt, width, height)

    # 2. Pollinations失敗 → Together.ai
    if not image_data:
        print("[AI画像生成] === Together.ai にフォールバック ===")
        image_data = _try_together(full_prompt, width, height)

    # 3. 全て失敗
    if not image_data:
        raise RuntimeError(
            "AI画像生成に全APIで失敗しました。"
            "Pollinations.aiがダウン中、かつTOGETHER_API_KEYが未設定の可能性があります。"
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
