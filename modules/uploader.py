"""
画像アップロードモジュール
Catbox.moe を使用してローカル画像をWebにアップロードし、直リンクURLを返す。
登録不要・APIキー不要・完全無料。
"""

import requests
import os

CATBOX_UPLOAD_URL = "https://catbox.moe/user/api.php"


def upload_image(image_path: str) -> str:
    """
    画像をCatbox.moeにアップロードし、直リンクURLを返す。

    Args:
        image_path: アップロードする画像のローカルパス

    Returns:
        アップロードされた画像の直リンクURL

    Raises:
        RuntimeError: アップロードに失敗した場合
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"画像ファイルが見つかりません: {image_path}")

    print("[Catbox] 画像をアップロード中...")

    with open(image_path, "rb") as f:
        files = {
            "fileToUpload": (os.path.basename(image_path), f, "image/jpeg"),
        }
        data = {
            "reqtype": "fileupload",
        }
        response = requests.post(CATBOX_UPLOAD_URL, data=data, files=files, timeout=60)

    if response.status_code != 200:
        raise RuntimeError(
            f"Catbox アップロード失敗 (HTTP {response.status_code}): {response.text}"
        )

    image_url = response.text.strip()

    if not image_url.startswith("https://"):
        raise RuntimeError(f"Catbox からURLを取得できませんでした: {image_url}")

    print(f"[Catbox] アップロード完了: {image_url}")
    return image_url


def upload_video(video_path: str) -> str:
    """
    動画をCatbox.moeにアップロードし、直リンクURLを返す。

    Args:
        video_path: アップロードする動画のローカルパス

    Returns:
        アップロードされた動画の直リンクURL
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"動画ファイルが見つかりません: {video_path}")

    print("[Catbox] 動画をアップロード中...")

    with open(video_path, "rb") as f:
        files = {
            "fileToUpload": (os.path.basename(video_path), f, "video/mp4"),
        }
        data = {
            "reqtype": "fileupload",
        }
        response = requests.post(CATBOX_UPLOAD_URL, data=data, files=files, timeout=120)

    if response.status_code != 200:
        raise RuntimeError(
            f"Catbox 動画アップロード失敗 (HTTP {response.status_code}): {response.text}"
        )

    video_url = response.text.strip()

    if not video_url.startswith("https://"):
        raise RuntimeError(f"Catbox からURLを取得できませんでした: {video_url}")

    print(f"[Catbox] 動画アップロード完了: {video_url}")
    return video_url
