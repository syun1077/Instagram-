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


def create_carousel_item(image_url: str, max_retries: int = 3) -> str:
    """カルーセル用の子メディアコンテナを作成する（リトライ付き）。"""
    access_token, account_id = _get_credentials()
    url = f"{GRAPH_API_BASE}/{account_id}/media"
    params = {
        "image_url": image_url,
        "is_carousel_item": "true",
        "access_token": access_token,
    }

    last_error = None
    for attempt in range(1, max_retries + 1):
        response = requests.post(url, params=params, timeout=60)
        data = response.json()
        if "error" not in data and "id" in data:
            return data["id"]

        error_msg = data.get("error", {}).get("message", "不明なエラー")
        last_error = error_msg
        print(f"[Instagram] 子コンテナ作成失敗 (試行 {attempt}/{max_retries}): {error_msg}")

        if attempt < max_retries:
            wait = 10 * attempt
            print(f"[Instagram] {wait}秒待機してリトライ...")
            time.sleep(wait)

    raise RuntimeError(f"カルーセル子コンテナ作成エラー: {last_error}")


def create_carousel_container(children_ids: list[str], caption: str) -> str:
    """カルーセル親コンテナを作成する。"""
    access_token, account_id = _get_credentials()
    url = f"{GRAPH_API_BASE}/{account_id}/media"
    params = {
        "media_type": "CAROUSEL",
        "children": ",".join(children_ids),
        "caption": caption,
        "access_token": access_token,
    }
    response = requests.post(url, params=params, timeout=60)
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"カルーセル親コンテナ作成エラー: {data['error'].get('message')}")
    return data["id"]


def post_carousel_to_instagram(
    image_urls: list[str], caption: str, max_retries: int = 3
) -> str:
    """複数画像をカルーセル投稿する。失敗時は単一画像投稿にフォールバック。"""
    print(f"[Instagram] カルーセル投稿 ({len(image_urls)}枚)...")

    try:
        # 子コンテナを作成
        children_ids = []
        for i, url in enumerate(image_urls):
            print(f"[Instagram] 子コンテナ作成中... ({i+1}/{len(image_urls)})")
            child_id = create_carousel_item(url)
            children_ids.append(child_id)
            # Instagram APIの処理時間を確保（画像URLのフェッチに時間がかかる場合がある）
            time.sleep(5)

        # 親コンテナを作成
        print("[Instagram] カルーセルコンテナ作成中...")
        creation_id = create_carousel_container(children_ids, caption)

        # 公開（リトライ付き）
        for attempt in range(1, max_retries + 1):
            try:
                wait_sec = 10 * attempt
                print(f"[Instagram] コンテナ処理待機中... ({wait_sec}秒)")
                time.sleep(wait_sec)
                return publish_media(creation_id)
            except RuntimeError as e:
                if "not ready" in str(e).lower() and attempt < max_retries:
                    print(f"[Instagram] リトライ {attempt}/{max_retries}...")
                    continue
                raise

        raise RuntimeError("カルーセル投稿の公開に失敗しました。")

    except RuntimeError as e:
        # カルーセルが失敗した場合、1枚目の画像で通常投稿にフォールバック
        print(f"[Instagram] カルーセル失敗: {e}")
        print("[Instagram] 単一画像投稿にフォールバック...")
        return post_to_instagram(image_urls[0], caption)


def create_reel_container(video_url: str, caption: str, cover_url: str = "") -> str:
    """リール用メディアコンテナを作成する。"""
    access_token, account_id = _get_credentials()
    url = f"{GRAPH_API_BASE}/{account_id}/media"
    params = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": access_token,
        "share_to_feed": "true",
    }
    if cover_url:
        params["cover_url"] = cover_url
    response = requests.post(url, params=params, timeout=120)
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"リールコンテナ作成エラー: {data['error'].get('message')}")
    return data["id"]


def check_container_status(creation_id: str) -> str:
    """コンテナの処理状態を確認する。"""
    access_token, _ = _get_credentials()
    url = f"{GRAPH_API_BASE}/{creation_id}"
    params = {
        "fields": "status_code",
        "access_token": access_token,
    }
    response = requests.get(url, params=params, timeout=30)
    data = response.json()
    return data.get("status_code", "UNKNOWN")


def post_reel_to_instagram(
    video_url: str, caption: str, cover_url: str = "", max_retries: int = 10
) -> str:
    """リール動画をInstagramに投稿する（動画処理待ち付き）。"""
    print(f"[Instagram] リール投稿中...")
    creation_id = create_reel_container(video_url, caption, cover_url)

    # 動画は処理に時間がかかるため、ステータスチェックしながら待機
    for attempt in range(1, max_retries + 1):
        wait_sec = 15  # 動画は15秒間隔でチェック
        print(f"[Instagram] 動画処理待機中... ({attempt}/{max_retries}, {wait_sec}秒)")
        time.sleep(wait_sec)

        status = check_container_status(creation_id)
        print(f"[Instagram] ステータス: {status}")

        if status == "FINISHED":
            return publish_media(creation_id)
        elif status == "ERROR":
            raise RuntimeError("リール動画の処理に失敗しました。")
        # IN_PROGRESS or other → continue waiting

    raise RuntimeError("リール動画の処理がタイムアウトしました。")


def create_story_container(image_url: str) -> str:
    """ストーリー用メディアコンテナを作成する。"""
    access_token, account_id = _get_credentials()
    url = f"{GRAPH_API_BASE}/{account_id}/media"
    params = {
        "media_type": "STORIES",
        "image_url": image_url,
        "access_token": access_token,
    }
    response = requests.post(url, params=params, timeout=60)
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"ストーリーコンテナ作成エラー: {data['error'].get('message')}")
    return data["id"]


def create_story_video_container(video_url: str) -> str:
    """ストーリー用動画コンテナを作成する。"""
    access_token, account_id = _get_credentials()
    url = f"{GRAPH_API_BASE}/{account_id}/media"
    params = {
        "media_type": "STORIES",
        "video_url": video_url,
        "access_token": access_token,
    }
    response = requests.post(url, params=params, timeout=120)
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"ストーリー動画コンテナ作成エラー: {data['error'].get('message')}")
    return data["id"]


def post_story_to_instagram(image_url: str, max_retries: int = 3) -> str:
    """画像をストーリーに投稿する。"""
    print("[Instagram] ストーリー投稿中...")
    creation_id = create_story_container(image_url)

    for attempt in range(1, max_retries + 1):
        try:
            wait_sec = 5 * attempt
            print(f"[Instagram] ストーリー処理待機中... ({wait_sec}秒)")
            time.sleep(wait_sec)
            return publish_media(creation_id)
        except RuntimeError as e:
            if "not ready" in str(e).lower() and attempt < max_retries:
                print(f"[Instagram] リトライ {attempt}/{max_retries}...")
                continue
            raise

    raise RuntimeError("ストーリー投稿に失敗しました。")


def post_story_video_to_instagram(video_url: str, max_retries: int = 10) -> str:
    """動画をストーリーに投稿する。"""
    print("[Instagram] ストーリー動画投稿中...")
    creation_id = create_story_video_container(video_url)

    for attempt in range(1, max_retries + 1):
        wait_sec = 15
        print(f"[Instagram] ストーリー動画処理待機中... ({attempt}/{max_retries}, {wait_sec}秒)")
        time.sleep(wait_sec)

        status = check_container_status(creation_id)
        print(f"[Instagram] ステータス: {status}")

        if status == "FINISHED":
            return publish_media(creation_id)
        elif status == "ERROR":
            raise RuntimeError("ストーリー動画の処理に失敗しました。")
        # IN_PROGRESS or other → continue waiting

    raise RuntimeError("ストーリー動画の処理がタイムアウトしました。")


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
