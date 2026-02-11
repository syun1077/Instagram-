"""
トークン自動管理モジュール
- トークンの有効性チェック
- 長期トークンへの自動交換
- 永続ページトークンの取得
- トークン期限切れ時の自動更新
"""

import json
import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv, set_key

load_dotenv()

APP_ID = "4273207802923040"
APP_SECRET = "4a282acb0427f226637cef997ab08129"
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
TOKEN_INFO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "token_info.json")


def check_token_valid() -> bool:
    """現在のアクセストークンが有効か確認する。"""
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    account_id = os.getenv("INSTAGRAM_ACCOUNT_ID")

    if not token or not account_id:
        return False

    try:
        r = requests.get(
            f"https://graph.facebook.com/v21.0/{account_id}",
            params={"fields": "id", "access_token": token},
            timeout=10,
        )
        data = r.json()
        return "error" not in data
    except Exception:
        return False


def get_token_expiry() -> dict:
    """トークンのデバッグ情報（有効期限など）を取得する。"""
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    if not token:
        return {}

    try:
        r = requests.get(
            "https://graph.facebook.com/debug_token",
            params={
                "input_token": token,
                "access_token": f"{APP_ID}|{APP_SECRET}",
            },
            timeout=10,
        )
        return r.json().get("data", {})
    except Exception:
        return {}


def save_token_info(user_token: str, page_token: str, account_id: str) -> None:
    """トークン情報をJSONファイルに保存する。"""
    info = {
        "user_token": user_token,
        "page_token": page_token,
        "account_id": account_id,
        "last_updated": datetime.now().isoformat(),
    }
    with open(TOKEN_INFO_PATH, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)


def load_token_info() -> dict:
    """保存済みのトークン情報を読み込む。"""
    if not os.path.exists(TOKEN_INFO_PATH):
        return {}
    with open(TOKEN_INFO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def refresh_user_token(current_user_token: str) -> str | None:
    """
    長期ユーザートークンを新しい長期トークンに交換する。
    有効期限内であれば新しい60日間トークンが取得できる。
    """
    try:
        r = requests.get(
            "https://graph.facebook.com/v21.0/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": APP_ID,
                "client_secret": APP_SECRET,
                "fb_exchange_token": current_user_token,
            },
            timeout=10,
        )
        data = r.json()
        return data.get("access_token")
    except Exception:
        return None


def get_page_token(user_token: str) -> tuple[str, str] | None:
    """
    ユーザートークンからページトークンとInstagram Account IDを取得する。
    長期ユーザートークンから取得したページトークンは無期限。
    """
    try:
        # ページ一覧を取得
        r = requests.get(
            "https://graph.facebook.com/v21.0/me/accounts",
            params={"access_token": user_token},
            timeout=10,
        )
        pages = r.json()

        if "data" not in pages or len(pages["data"]) == 0:
            return None

        page = pages["data"][0]
        page_id = page["id"]
        page_token = page["access_token"]

        # Instagram Account ID を取得
        r2 = requests.get(
            f"https://graph.facebook.com/v21.0/{page_id}",
            params={
                "fields": "instagram_business_account",
                "access_token": user_token,
            },
            timeout=10,
        )
        ig_data = r2.json()
        ig_id = ig_data.get("instagram_business_account", {}).get("id")

        if ig_id:
            return page_token, ig_id
        return None
    except Exception:
        return None


def update_env(token: str, account_id: str) -> None:
    """.env ファイルのトークンを更新する。"""
    set_key(ENV_PATH, "INSTAGRAM_ACCESS_TOKEN", token)
    set_key(ENV_PATH, "INSTAGRAM_ACCOUNT_ID", account_id)
    # 環境変数も即時更新
    os.environ["INSTAGRAM_ACCESS_TOKEN"] = token
    os.environ["INSTAGRAM_ACCOUNT_ID"] = account_id
    print(f"[トークン管理] .env を更新しました")


def auto_refresh() -> bool:
    """
    トークンの自動更新を試みる。
    1. 現在のトークンが有効か確認
    2. 無効なら保存済みユーザートークンで更新を試行
    3. ユーザートークンを新しい長期トークンに交換
    4. ページトークン（無期限）を再取得
    5. .env を自動更新

    Returns:
        True: トークンが有効（更新含む）
        False: 更新失敗、手動対応が必要
    """
    # まず現在のトークンが有効か確認
    if check_token_valid():
        print("[トークン管理] トークンは有効です")

        # ユーザートークンの予防的更新を試みる
        info = load_token_info()
        user_token = info.get("user_token")
        if user_token:
            new_user_token = refresh_user_token(user_token)
            if new_user_token and new_user_token != user_token:
                result = get_page_token(new_user_token)
                if result:
                    page_token, account_id = result
                    update_env(page_token, account_id)
                    save_token_info(new_user_token, page_token, account_id)
                    print("[トークン管理] トークンを予防的に更新しました")
        return True

    print("[トークン管理] トークンが無効です。自動更新を試みます...")

    # 保存済みのユーザートークンで更新を試行
    info = load_token_info()
    user_token = info.get("user_token")

    if not user_token:
        print("[トークン管理] ユーザートークンが保存されていません")
        return False

    # ユーザートークンを更新
    new_user_token = refresh_user_token(user_token)
    if not new_user_token:
        print("[トークン管理] ユーザートークンの更新に失敗しました")
        return False

    # ページトークンを再取得
    result = get_page_token(new_user_token)
    if not result:
        print("[トークン管理] ページトークンの取得に失敗しました")
        return False

    page_token, account_id = result
    update_env(page_token, account_id)
    save_token_info(new_user_token, page_token, account_id)
    print("[トークン管理] トークンを自動更新しました！")
    return True
