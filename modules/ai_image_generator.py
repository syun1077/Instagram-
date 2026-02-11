"""
AI画像/動画生成モジュール
Pollinations.ai (完全無料・APIキー不要) を使用して、
プロンプトからAI画像を生成する。
ffmpegでスライドショー動画（リール用）を作成する。
"""

import requests
import urllib.parse
import os
import subprocess
import shutil


# Pollinations.ai 設定
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"
DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1080


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

    Pollinations.ai を使用（完全無料・登録不要・APIキー不要）。
    内部でStable Diffusion / Fluxモデルが動作。

    Args:
        prompt: 画像生成プロンプト（英語推奨）
        output_path: 保存先パス
        width: 画像の幅 (px)
        height: 画像の高さ (px)
        style_suffix: プロンプトに自動追加するスタイル指定

    Returns:
        保存した画像のファイルパス
    """
    # プロンプト構築（高画質キーワード付き）
    full_prompt = f"{prompt}, {style_suffix}"
    encoded_prompt = urllib.parse.quote(full_prompt)

    url = POLLINATIONS_URL.format(prompt=encoded_prompt)
    import time
    params = {
        "width": width,
        "height": height,
        "nologo": "true",
        "enhance": "true",
        "model": "flux",
        "seed": int(time.time() * 1000) % 2147483647,
    }

    print(f"[AI画像生成] プロンプト: {prompt}")
    print(f"[AI画像生成] 解像度: {width}x{height}")
    print(f"[AI画像生成] 高画質モードで生成中（1〜3分かかる場合があります）...")

    response = requests.get(url, params=params, timeout=300)

    if response.status_code != 200:
        raise RuntimeError(
            f"AI画像生成に失敗しました (HTTP {response.status_code})"
        )

    # Content-Typeで画像かどうか確認
    content_type = response.headers.get("content-type", "")
    if "image" not in content_type:
        raise RuntimeError(
            f"画像データを受信できませんでした (Content-Type: {content_type})"
        )

    with open(output_path, "wb") as f:
        f.write(response.content)

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

    Args:
        image_paths: 入力画像パスのリスト
        output_path: 出力動画パス
        duration_per_image: 各画像の表示時間（秒）
        fps: フレームレート
        width: 動画の幅
        height: 動画の高さ

    Returns:
        生成した動画のファイルパス
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
        # ズームイン（中心から）
        f"zoompan=z='min(zoom+0.002,1.3)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps}",
        # ズームアウト
        f"zoompan=z='if(eq(on,1),1.3,max(zoom-0.002,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps}",
        # 左から右へパン
        f"zoompan=z='1.2':x='if(eq(on,1),0,min(x+2,iw-iw/zoom))':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps}",
        # 右上からズームイン
        f"zoompan=z='min(zoom+0.0015,1.25)':x='iw/3-(iw/zoom/3)':y='ih/3-(ih/zoom/3)':d={frames}:s={width}x{height}:fps={fps}",
    ]

    # 各画像を個別に動画クリップに変換
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

    # クリップを結合
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

    # 一時ファイル削除
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
    """
    リール用の縦長画像を複数生成する。

    Args:
        prompt: ベースプロンプト
        output_dir: 画像保存先ディレクトリ
        num_images: 生成枚数
        width: 画像幅
        height: 画像高さ

    Returns:
        生成した画像パスのリスト
    """
    # リール用のアングルバリエーション
    reel_angles = [
        "",  # オリジナル
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
