"""
画像・動画アップロードモジュール
複数のアップロードサービスにフォールバック対応。
Catbox.moe → Litterbox → 0x0.st の順で試行。
"""

import requests
import os
import time

CATBOX_UPLOAD_URL = "https://catbox.moe/user/api.php"
LITTERBOX_UPLOAD_URL = "https://litterbox.catbox.moe/resources/internals/api.php"
OX0_UPLOAD_URL = "https://0x0.st"


def _upload_catbox(file_path: str, mime_type: str, timeout: int = 60) -> str:
    """Catbox.moeにアップロードする。"""
    with open(file_path, "rb") as f:
        files = {"fileToUpload": (os.path.basename(file_path), f, mime_type)}
        data = {"reqtype": "fileupload"}
        response = requests.post(CATBOX_UPLOAD_URL, data=data, files=files, timeout=timeout)

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
        response = requests.post(LITTERBOX_UPLOAD_URL, data=data, files=files, timeout=timeout)

    if response.status_code != 200:
        raise RuntimeError(f"Litterbox HTTP {response.status_code}: {response.text[:200]}")

    url = response.text.strip()
    if not url.startswith("https://"):
        raise RuntimeError(f"Litterbox 無効なレスポンス: {url[:200]}")
    return url


def _upload_0x0(file_path: str, mime_type: str, timeout: int = 60) -> str:
    """0x0.stにアップロードする。"""
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, mime_type)}
        response = requests.post(OX0_UPLOAD_URL, files=files, timeout=timeout)

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
        ("0x0.st", _upload_0x0),
    ]

    last_error = None
    for service_name, upload_func in services:
        for attempt in range(1, max_retries + 1):
            try:
                print(f"[{service_name}] アップロード中... (試行 {attempt}/{max_retries})")
                url = upload_func(file_path, mime_type, timeout)
                print(f"[{service_name}] アップロード完了: {url}")
                return url
            except Exception as e:
                last_error = e
                print(f"[{service_name}] 失敗 (試行 {attempt}): {e}")
                if attempt < max_retries:
                    time.sleep(3)
        print(f"[{service_name}] 全試行失敗、次のサービスへ...")

    raise RuntimeError(f"全アップロードサービスが失敗しました: {last_error}")


def upload_image(image_path: str) -> str:
    """
    画像をアップロードし、直リンクURLを返す。
    Catbox → Litterbox → 0x0.st の順でフォールバック。
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"画像ファイルが見つかりません: {image_path}")

    return _upload_with_fallback(image_path, "image/jpeg", timeout=60)


def upload_video(video_path: str) -> str:
    """
    動画をアップロードし、直リンクURLを返す。
    Catbox → Litterbox → 0x0.st の順でフォールバック。
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"動画ファイルが見つかりません: {video_path}")

    return _upload_with_fallback(video_path, "video/mp4", timeout=120)
