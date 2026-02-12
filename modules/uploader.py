"""
画像・動画アップロードモジュール
複数のアップロードサービスにフォールバック対応。
優先順位: Catbox → Litterbox → freeimage → imgBB → Imgur → file.io
"""

import requests
import os
import time
import base64
import logging

CATBOX_UPLOAD_URL = "https://catbox.moe/user/api.php"
LITTERBOX_UPLOAD_URL = "https://litterbox.catbox.moe/resources/internals/api.php"
IMGBB_UPLOAD_URL = "https://api.imgbb.com/1/upload"
FILEIO_UPLOAD_URL = "https://file.io"
FREEIMAGE_UPLOAD_URL = "https://freeimage.host/api/1/upload"
IMGUR_UPLOAD_URL = "https://api.imgur.com/3/image"

# サービスごとに適切なUser-Agentを使い分ける
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
SIMPLE_UA = "Instagram-AutoPost/2.0"

BROWSER_HEADERS = {"User-Agent": BROWSER_UA}
SIMPLE_HEADERS = {"User-Agent": SIMPLE_UA}


def _upload_catbox(file_path: str, mime_type: str, timeout: int = 60) -> str:
    """Catbox.moeにアップロードする。"""
    with open(file_path, "rb") as f:
        files = {"fileToUpload": (os.path.basename(file_path), f, mime_type)}
        data = {"reqtype": "fileupload"}
        response = requests.post(
            CATBOX_UPLOAD_URL, data=data, files=files,
            headers=SIMPLE_HEADERS, timeout=timeout
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
            headers=SIMPLE_HEADERS, timeout=timeout
        )

    if response.status_code != 200:
        raise RuntimeError(f"Litterbox HTTP {response.status_code}: {response.text[:200]}")

    url = response.text.strip()
    if not url.startswith("https://"):
        raise RuntimeError(f"Litterbox 無効なレスポンス: {url[:200]}")
    return url


def _upload_freeimage(file_path: str, mime_type: str, timeout: int = 60) -> str:
    """freeimage.hostにアップロードする（画像のみ対応、公開匿名キー使用）。"""
    if not mime_type.startswith("image/"):
        raise RuntimeError("freeimage.hostは画像のみ対応")

    with open(file_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    data = {
        "key": "6d207e02198a847aa98d0a2a901485a5",  # 公開匿名キー
        "action": "upload",
        "source": image_data,
        "format": "json",
    }
    response = requests.post(
        FREEIMAGE_UPLOAD_URL, data=data,
        headers=BROWSER_HEADERS, timeout=timeout
    )

    if response.status_code != 200:
        raise RuntimeError(f"freeimage.host HTTP {response.status_code}: {response.text[:200]}")

    json_data = response.json()
    if json_data.get("status_code") != 200:
        raise RuntimeError(f"freeimage.host エラー: {json_data.get('error', {}).get('message', 'unknown')}")

    return json_data["image"]["url"]


def _upload_imgbb(file_path: str, mime_type: str, timeout: int = 60) -> str:
    """imgBBにアップロードする（画像のみ対応）。"""
    if not mime_type.startswith("image/"):
        raise RuntimeError("imgBBは画像のみ対応")

    with open(file_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    api_key = os.getenv("IMGBB_API_KEY", "")
    if not api_key:
        raise RuntimeError("IMGBB_API_KEY が設定されていません")

    data = {
        "key": api_key,
        "image": image_data,
        "expiration": 600,  # 10分で消える
    }
    response = requests.post(
        IMGBB_UPLOAD_URL, data=data,
        headers=BROWSER_HEADERS, timeout=timeout
    )

    if response.status_code != 200:
        raise RuntimeError(f"imgBB HTTP {response.status_code}: {response.text[:200]}")

    json_data = response.json()
    if not json_data.get("success"):
        raise RuntimeError(f"imgBB エラー: {json_data}")

    return json_data["data"]["url"]


def _upload_imgur(file_path: str, mime_type: str, timeout: int = 60) -> str:
    """Imgur匿名アップロード（画像のみ対応）。Client-ID不要の匿名API。"""
    if not mime_type.startswith("image/"):
        raise RuntimeError("Imgurは画像のみ対応")

    with open(file_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    # Imgur匿名アップロード用のClient-ID（公開用）
    client_id = os.getenv("IMGUR_CLIENT_ID", "546c25a59c58ad7")
    headers = {
        "Authorization": f"Client-ID {client_id}",
        "User-Agent": SIMPLE_UA,
    }
    data = {"image": image_data, "type": "base64"}

    response = requests.post(
        IMGUR_UPLOAD_URL, data=data,
        headers=headers, timeout=timeout
    )

    if response.status_code not in (200, 201):
        raise RuntimeError(f"Imgur HTTP {response.status_code}: {response.text[:200]}")

    json_data = response.json()
    if not json_data.get("success"):
        raise RuntimeError(f"Imgur エラー: {json_data.get('data', {}).get('error', 'unknown')}")

    return json_data["data"]["link"]


def _upload_fileio(file_path: str, mime_type: str, timeout: int = 60) -> str:
    """file.ioにアップロードする（1回ダウンロードで自動削除）。"""
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, mime_type)}
        response = requests.post(
            FILEIO_UPLOAD_URL, files=files,
            headers=BROWSER_HEADERS, timeout=timeout
        )

    if response.status_code != 200:
        raise RuntimeError(f"file.io HTTP {response.status_code}: {response.text[:200]}")

    json_data = response.json()
    if not json_data.get("success"):
        raise RuntimeError(f"file.io エラー: {json_data}")

    return json_data["link"]


def _upload_with_fallback(file_path: str, mime_type: str, timeout: int = 60, max_retries: int = 2) -> str:
    """複数サービスでフォールバックしながらアップロードする。"""
    if mime_type.startswith("image/"):
        services = [
            ("Catbox", _upload_catbox),
            ("Litterbox", _upload_litterbox),
            ("freeimage", _upload_freeimage),
            ("imgBB", _upload_imgbb),
            ("Imgur", _upload_imgur),
            ("file.io", _upload_fileio),
        ]
    else:
        # 動画は画像専用サービスを除外
        services = [
            ("Catbox", _upload_catbox),
            ("Litterbox", _upload_litterbox),
            ("file.io", _upload_fileio),
        ]

    last_error = None
    for service_name, upload_func in services:
        for attempt in range(1, max_retries + 1):
            try:
                logging.info(f"[{service_name}] アップロード中... (試行 {attempt}/{max_retries})")
                url = upload_func(file_path, mime_type, timeout)
                logging.info(f"アップロード完了: {url}")
                return url
            except Exception as e:
                last_error = e
                logging.warning(f"[{service_name}] 失敗 (試行 {attempt}): {e}")
                if attempt < max_retries:
                    time.sleep(2)
        logging.info(f"[{service_name}] 全試行失敗、次のサービスへ...")

    raise RuntimeError(f"全アップロードサービスが失敗しました: {last_error}")


def upload_image(image_path: str) -> str:
    """
    画像をアップロードし、直リンクURLを返す。
    Catbox → Litterbox → freeimage → imgBB → Imgur → file.io の順でフォールバック。
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"画像ファイルが見つかりません: {image_path}")

    return _upload_with_fallback(image_path, "image/jpeg", timeout=60)


def upload_video(video_path: str) -> str:
    """
    動画をアップロードし、直リンクURLを返す。
    Catbox → Litterbox → file.io の順でフォールバック。
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"動画ファイルが見つかりません: {video_path}")

    return _upload_with_fallback(video_path, "video/mp4", timeout=120)
