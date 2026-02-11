"""
Instagram Graph API のアクセストークンを取得するヘルパースクリプト
トークン情報を自動保存し、期限切れ時の自動更新に対応。
"""
import requests
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from modules.token_manager import save_token_info, update_env

APP_ID = "4273207802923040"
APP_SECRET = "4a282acb0427f226637cef997ab08129"
REDIRECT_URI = "http://localhost:5555/callback"
SCOPES = "instagram_basic,instagram_content_publish,pages_read_engagement,pages_show_list"

auth_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("認証成功！このページを閉じてターミナルに戻ってください。".encode("utf-8"))
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            error = params.get("error_description", ["不明なエラー"])[0]
            self.wfile.write(f"エラー: {error}".encode("utf-8"))

    def log_message(self, format, *args):
        pass


def main():
    global auth_code

    print("=" * 50)
    print("  Instagram トークン取得ツール")
    print("=" * 50)
    print()

    # ローカルサーバーを起動
    server = HTTPServer(("localhost", 5555), CallbackHandler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()

    # ブラウザで認証URLを開く
    auth_url = (
        f"https://www.facebook.com/v21.0/dialog/oauth"
        f"?client_id={APP_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&response_type=code"
        f"&scope={SCOPES}"
        f"&auth_type=rerequest"
    )

    print("ブラウザで認証ページを開きます...")
    print("Facebookにログインして「続行」を押してください。\n")
    webbrowser.open(auth_url)

    thread.join(timeout=120)
    server.server_close()

    if not auth_code:
        print("エラー: 認証コードを取得できませんでした。")
        return

    print("認証コード取得成功！")

    # codeをアクセストークンに交換
    print("\nアクセストークンに交換中...")
    r = requests.get("https://graph.facebook.com/v21.0/oauth/access_token", params={
        "client_id": APP_ID,
        "redirect_uri": REDIRECT_URI,
        "client_secret": APP_SECRET,
        "code": auth_code,
    })
    data = r.json()

    if "access_token" not in data:
        print(f"エラー: {data}")
        return

    short_token = data["access_token"]
    print("短期トークン取得成功！")

    # 長期トークンに交換
    print("長期トークンに交換中...")
    r = requests.get("https://graph.facebook.com/v21.0/oauth/access_token", params={
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "fb_exchange_token": short_token,
    })
    data = r.json()

    if "access_token" not in data:
        print(f"エラー: {data}")
        return

    long_token = data["access_token"]
    print("長期トークン取得成功！（60日間有効）")

    # ページ一覧を取得
    print("\nFacebookページを検索中...")
    r = requests.get("https://graph.facebook.com/v21.0/me/accounts", params={
        "access_token": long_token,
    })
    pages = r.json()

    if "data" not in pages or len(pages["data"]) == 0:
        print("Facebookページが見つかりません。")
        return

    page = pages["data"][0]
    page_id = page["id"]
    page_token = page.get("access_token", long_token)
    print(f"ページ発見: {page.get('name')} (ID: {page_id})")

    # Instagram Account ID を取得
    print("Instagram Account ID を検索中...")
    r = requests.get(f"https://graph.facebook.com/v21.0/{page_id}", params={
        "fields": "instagram_business_account",
        "access_token": long_token,
    })
    ig_data = r.json()
    ig_id = ig_data.get("instagram_business_account", {}).get("id")

    if not ig_id:
        print("Instagram Account ID を取得できませんでした。")
        return

    # .env に自動書き込み + token_info.json に保存
    update_env(page_token, ig_id)
    save_token_info(long_token, page_token, ig_id)

    print()
    print("=" * 50)
    print("  セットアップ完了！")
    print("  .env にトークンを自動保存しました。")
    print("  トークン更新用の情報も保存済みです。")
    print("=" * 50)
    print()
    print(f"INSTAGRAM_ACCESS_TOKEN={page_token}")
    print(f"INSTAGRAM_ACCOUNT_ID={ig_id}")
    print()


if __name__ == "__main__":
    main()
