"""
自動アンフォロー機能のセットアップスクリプト
Instagramのユーザー名とパスワードを .env に保存し、
テストログインを行ってセッションファイルを作成します。
"""

import os
import sys
from getpass import getpass
from modules.token_manager import update_env
from modules.unfollower import login_to_instagram

def main():
    print("=" * 50)
    print("  Instagram 自動アンフォロー設定")
    print("=" * 50)
    print("この機能を使用するには、Instagramのユーザー名とパスワードが必要です。")
    print("情報はローカルの .env ファイルにのみ保存され、外部には送信されません。")
    print()

    username = input("Instagram ユーザー名: ").strip()
    if not username:
        print("ユーザー名が入力されませんでした。中止します。")
        return

    password = getpass("Instagram パスワード (表示されません): ").strip()
    if not password:
        print("パスワードが入力されませんでした。中止します。")
        return

    print("\n設定を保存中...")
    
    # .envファイルの内容を更新
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    
    # 既存の読み込み
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    env_vars[key] = value
    
    # 新しい値で更新
    env_vars["INSTAGRAM_USERNAME"] = username
    env_vars["INSTAGRAM_PASSWORD"] = password
    
    # 書き込み
    with open(env_path, "w", encoding="utf-8") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
            
    # 環境変数にも反映（現在のプロセス用）
    os.environ["INSTAGRAM_USERNAME"] = username
    os.environ["INSTAGRAM_PASSWORD"] = password
    
    print(".env に保存しました。")
    print("\n接続テスト（ログイン）を行っています...")
    print("※ 初回は二段階認証のコードを求められる場合があります。")
    print("   その場合は、ターミナルにコードを入力してください。")
    print()

    try:
        # ログイン試行（これにより session.json が作成される）
        cl = login_to_instagram()
        print("\n[成功] ログインに成功しました！")
        print("セッション情報が保存されたため、次回からは自動的にログインされます。")
        
    except Exception as e:
        print(f"\n[エラー] ログインに失敗しました: {e}")
        print("パスワードが間違っているか、二段階認証が必要な可能性があります。")
        print("再度実行するか、Instagramアプリで不審なログインの通知が来ていないか確認してください。")

if __name__ == "__main__":
    main()
