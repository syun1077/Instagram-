"""
AI画像生成モジュール
Pollinations.ai (完全無料・APIキー不要) を使用して、
プロンプトからAI画像を生成する。
"""

import requests
import urllib.parse
import os


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
