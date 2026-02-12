"""
画像・動画アップロードモジュール
複数のアップロードサービスにフォールバック対応。
Catbox → Litterbox → imgBB → file.io → 0x0.st の順で試行。
"""

import requests
import os
import time
import base64
import logging

CATBOX_UPLOAD_URL = "https://catbox.moe/user/api.php"
LITTERBOX_UPLOAD_URL = "https://litterbox.catbox.moe/resources/internals/api.php"
OX0_UPLOAD_URL = "https://0x0.st"
IMGBB_UPLOAD_URL = "https://api.imgbb.com/1/upload"
FILEIO_UPLOAD_URL = "https://file.io"

# GitHub Actions からのリクエストがブロックされないよう User-Agent を設定
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def _upload_catbox(file_path: str, mime_type: str, timeout: int = 60) -> str:
    """Catbox.moeにアップロードする。"""
    with open(file_path, "rb") as f:
        files = {"fileToUpload": (os.path.basename(file_path), f, mime_type)}
        data = {"reqtype": "fileupload"}
        response = requests.post(
            CATBOX_UPLOAD_URL, data=data, files=files,
            headers=HEADERS, timeout=timeout
        )

    if response.status_code != 200:
        raise RuntimeError(f"Catbox HTTP {response.status_code}: {response.text[:200]}")

    url = response.text.strip()
    if not url.startswith("https://"):
        raise RuntimeError(f"Catbox 無効なレスポンス: {url[:200]}")
    return url


def _upload_litterbox(file_path: str, mime_type: str, timeout: int = 60) -> str:
    """Litterbox（Catbox姉妹サイト、72時間保持）にアップロードする。"""
    with open(file_path, "rb") as f:
        files = {"fileToUpload": (os.path.basename(file_path), f, mime_type)}
        data = {"reqtype": "fileupload", "time": "72h"}
        response = requests.post(
            LITTERBOX_UPLOAD_URL, data=data, files=files,
            headers=HEADERS, timeout=timeout
        )

    if response.status_code != 200:
        raise RuntimeError(f"Litterbox HTTP {response.status_code}: {response.text[:200]}")

    url = response.text.strip()
    if not url.startswith("https://"):
        raise RuntimeError(f"Litterbox 無効なレスポンス: {url[:200]}")
    return url


def _upload_imgbb(file_path: str, mime_type: str, timeout: int = 60) -> str:
    """imgBBにアップロードする（画像のみ対応）。"""
    if not mime_type.startswith("image/"):
        raise RuntimeError("imgBBは画像のみ対応")

    with open(file_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    # 無料APIキー（匿名アップロード用）
    api_key = os.getenv("IMGBB_API_KEY", "")
    if not api_key:
        raise RuntimeError("IMGBB_API_KEY が設定されていません")

    data = {
        "key": api_key,
        "image": image_data,
        "expiration": 600,  # 10分で消える（投稿後は不要）
    }
    response = requests.post(
        IMGBB_UPLOAD_URL, data=data,
        headers=HEADERS, timeout=timeout
    )

    if response.status_code != 200:
        raise RuntimeError(f"imgBB HTTP {response.status_code}: {response.text[:200]}")

    json_data = response.json()
    if not json_data.get("success"):
        raise RuntimeError(f"imgBB エラー: {json_data}")

    return json_data["data"]["url"]


def _upload_fileio(file_path: str, mime_type: str, timeout: int = 60) -> str:
    """file.ioにアップロードする（1回ダウンロードで自動削除）。"""
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, mime_type)}
        response = requests.post(
            FILEIO_UPLOAD_URL, files=files,
            headers=HEADERS, timeout=timeout
        )

    if response.status_code != 200:
        raise RuntimeError(f"file.io HTTP {response.status_code}: {response.text[:200]}")

    json_data = response.json()
    if not json_data.get("success"):
        raise RuntimeError(f"file.io エラー: {json_data}")

    return json_data["link"]


def _upload_0x0(file_path: str, mime_type: str, timeout: int = 60) -> str:
    """0x0.stにアップロードする。"""
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, mime_type)}
        response = requests.post(
            OX0_UPLOAD_URL, files=files,
            headers=HEADERS, timeout=timeout
        )

    if response.status_code != 200:
        raise RuntimeError(f"0x0.st HTTP {response.status_code}: {response.text[:200]}")

    url = response.text.strip()
    if not url.startswith("https://") and not url.startswith("http://"):
        raise RuntimeError(f"0x0.st 無効なレスポンス: {url[:200]}")
    return url


def _upload_with_fallback(file_path: str, mime_type: str, timeout: int = 60, max_retries: int = 2) -> str:
    """複数サービスでフォールバックしながらアップロードする。"""
    services = [
        ("Catbox", _upload_catbox),
        ("Litterbox", _upload_litterbox),
        ("imgBB", _upload_imgbb),
        ("file.io", _upload_fileio),
        ("0x0.st", _upload_0x0),
    ]

    last_error = None
    for service_name, upload_func in services:
        for attempt in range(1, max_retries + 1):
            try:
                logging.info(f"[{service_name}] アップロード中... (試行 {attempt}/{max_retries})")
                url = upload_func(file_path, mime_type, timeout)
                logging.info(f"[{service_name}] アップロード完了: {url}")
                return url
            except Exception as e:
                last_error = e
                logging.warning(f"[{service_name}] 失敗 (試行 {attempt}): {e}")
                if attempt < max_retries:
                    time.sleep(3)
        logging.info(f"[{service_name}] 全試行失敗、次のサービスへ...")

    raise RuntimeError(f"全アップロードサービスが失敗しました: {last_error}")


def upload_image(image_path: str) -> str:
    """
    画像をアップロードし、直リンクURLを返す。
    Catbox → Litterbox → imgBB → file.io → 0x0.st の順でフォールバック。
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"画像ファイルが見つかりません: {image_path}")

    return _upload_with_fallback(image_path, "image/jpeg", timeout=60)


def upload_video(video_path: str) -> str:
    """
    動画をアップロードし、直リンクURLを返す。
    Catbox → Litterbox → file.io → 0x0.st の順でフォールバック。
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"動画ファイルが見つかりません: {video_path}")

    return _upload_with_fallback(video_path, "video/mp4", timeout=120)
