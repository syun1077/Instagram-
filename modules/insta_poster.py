"""
Instagram投稿モジュール
Instagram Graph APIを使用して画像を投稿する。
"""

import time
import requests
import os
from dotenv import load_dotenv

load_dotenv()

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


def _get_credentials() -> tuple[str, str]:
    """環境変数から認証情報を取得する。"""
    access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    account_id = os.getenv("INSTAGRAM_ACCOUNT_ID")

    if not access_token:
        raise ValueError("INSTAGRAM_ACCESS_TOKEN が .env に設定されていません。")
    if not account_id:
        raise ValueError("INSTAGRAM_ACCOUNT_ID が .env に設定されていません。")

    return access_token, account_id


def create_media_container(image_url: str, caption: str) -> str:
    """
    Step 1: メディアコンテナを作成し、creation_id を返す。

    Args:
        image_url: Web上の画像URL
        caption: 投稿キャプション

    Returns:
        creation_id (コンテナID)
    """
    access_token, account_id = _get_credentials()

    url = f"{GRAPH_API_BASE}/{account_id}/media"
    params = {
        "image_url": image_url,
        "caption": caption,
        "access_token": access_token,
    }

    print("[Instagram] メディアコンテナを作成中...")
    response = requests.post(url, params=params, timeout=60)
    data = response.json()

    if "error" in data:
        error = data["error"]
        error_msg = error.get("message", "不明なエラー")
        error_code = error.get("code", "N/A")

        # よくあるエラーの日本語ガイド
        if error_code == 190:
            raise RuntimeError(
                f"アクセストークンが無効または期限切れです。\n"
                f"Meta Developers で新しいトークンを生成してください。\n"
                f"詳細: {error_msg}"
            )
        if "aspect ratio" in error_msg.lower():
            raise RuntimeError(
                f"画像のアスペクト比がInstagramの要件を満たしていません。\n"
                f"推奨: 正方形(1:1), 横長(1.91:1), 縦長(4:5)\n"
                f"詳細: {error_msg}"
            )
        raise RuntimeError(f"Instagram APIエラー (code={error_code}): {error_msg}")

    creation_id = data.get("id")
    if not creation_id:
        raise RuntimeError(f"creation_id を取得できませんでした。レスポンス: {data}")

    print(f"[Instagram] コンテナ作成完了: {creation_id}")
    return creation_id


def publish_media(creation_id: str) -> str:
    """
    Step 2: メディアコンテナを公開する。

    Args:
        creation_id: Step 1 で取得したコンテナID

    Returns:
        公開された投稿のID
    """
    access_token, account_id = _get_credentials()

    url = f"{GRAPH_API_BASE}/{account_id}/media_publish"
    params = {
        "creation_id": creation_id,
        "access_token": access_token,
    }

    print("[Instagram] 投稿を公開中...")
    response = requests.post(url, params=params, timeout=60)
    data = response.json()

    if "error" in data:
        error = data["error"]
        error_msg = error.get("message", "不明なエラー")
        error_code = error.get("code", "N/A")

        if "not ready" in error_msg.lower() or error_code == 9007:
            raise RuntimeError(
                f"メディアの処理がまだ完了していません。\n"
                f"数秒待ってから再試行してください。\n"
                f"詳細: {error_msg}"
            )
        raise RuntimeError(f"Instagram 公開エラー (code={error_code}): {error_msg}")

    post_id = data.get("id")
    if not post_id:
        raise RuntimeError(f"投稿IDを取得できませんでした。レスポンス: {data}")

    print(f"[Instagram] 投稿完了! Post ID: {post_id}")
    return post_id


def post_to_instagram(image_url: str, caption: str, max_retries: int = 3) -> str:
    """
    画像URLとキャプションでInstagramに投稿する（リトライ機能付き）。

    Args:
        image_url: Web上の画像URL
        caption: 投稿キャプション
        max_retries: 公開リトライ回数

    Returns:
        公開された投稿のID
    """
    creation_id = create_media_container(image_url, caption)

    # コンテナ処理待ち + リトライ
    for attempt in range(1, max_retries + 1):
        try:
            # APIが画像を処理する時間を確保
            wait_sec = 5 * attempt
            print(f"[Instagram] コンテナ処理待機中... ({wait_sec}秒)")
            time.sleep(wait_sec)
            return publish_media(creation_id)
        except RuntimeError as e:
            if "not ready" in str(e).lower() and attempt < max_retries:
                print(f"[Instagram] リトライ {attempt}/{max_retries}...")
                continue
            raise

    raise RuntimeError("投稿の公開に失敗しました。時間をおいて再試行してください。")
