"""
自動アンフォローモジュール

instagrapiを使用して、フォロワー以外のユーザー（片思いフォロー）を自動的にアンフォローする。
アカウントの安全のため、1回の実行でのアンフォロー数は制限され、ランダムな待機時間を設けている。
"""

import os
import time
import random
import logging
import json
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
from dotenv import load_dotenv

load_dotenv()

# セッションファイルのパス
SESSION_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "session.json")
# ホワイトリスト（アンフォローしないユーザーIDのリスト）
WHITELIST_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "whitelist.json")

def load_whitelist() -> list[str]:
    """ホワイトリストを読み込む。"""
    if os.path.exists(WHITELIST_FILE):
        try:
            with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def login_to_instagram() -> Client:
    """
    Instagramにログインし、クライアントインスタンスを返す。
    セッションファイルがある場合はそれを使用し、なければ新規ログインして保存する。
    """
    cl = Client()
    
    username = os.getenv("INSTAGRAM_USERNAME")
    password = os.getenv("INSTAGRAM_PASSWORD")
    
    if not username or not password:
        raise ValueError("INSTAGRAM_USERNAME または INSTAGRAM_PASSWORD が .env に設定されていません。")

    # セッションの読み込み
    if os.path.exists(SESSION_FILE):
        try:
            logging.info("[Unfollow] セッションを読み込み中...")
            cl.load_settings(SESSION_FILE)
            cl.login(username, password) # セッション有効確認も含めてログイン
            logging.info("[Unfollow] セッションログイン成功")
            return cl
        except Exception as e:
            logging.warning(f"[Unfollow] セッションログイン失敗: {e}")
            # 失敗したらセッションファイルを削除して再試行
            pass

    # 新規ログイン
    logging.info("[Unfollow] 新規ログインを試行中...")
    try:
        cl.login(username, password)
        logging.info("[Unfollow] ログイン成功")
        # セッション保存
        cl.dump_settings(SESSION_FILE)
        logging.info("[Unfollow] セッションを保存しました")
    except Exception as e:
        # 二段階認証などが必要な場合のハンドリングは基本実装ではスキップ（エラーログのみ）
        logging.error(f"[Unfollow] ログインエラー: {e}")
        raise

    return cl

def unfollow_non_followers(max_unfollows: int = 10):
    """
    フォローバックされていないユーザーをアンフォローする。
    
    Args:
        max_unfollows: 1回の実行でアンフォローする最大人数
    """
    logging.info("=" * 40)
    logging.info("[Unfollow] 自動アンフォロー処理を開始")
    
    try:
        cl = login_to_instagram()
    except Exception as e:
        logging.error(f"[Unfollow] ログインできないため中止します: {e}")
        return

    try:
        # 自分のID取得
        user_id = cl.user_id
        logging.info(f"[Unfollow] ユーザーID: {user_id}")
        
        # フォロワーとフォロー中を取得
        # 注意: 数が多いと時間がかかります
        logging.info("[Unfollow] フォロワー・フォローリストを取得中...")
        followers = cl.user_followers(user_id).keys()
        following = cl.user_following(user_id).keys()
        
        logging.info(f"[Unfollow] フｫロワー: {len(followers)}人, フォロー中: {len(following)}人")
        
        # 片思いユーザー（フォローしているが、フォローされていない）
        non_followers = [uid for uid in following if uid not in followers]
        logging.info(f"[Unfollow] 片思いユーザー: {len(non_followers)}人")
        
        # ホワイトリスト除外
        whitelist = load_whitelist()
        targets = [uid for uid in non_followers if str(uid) not in whitelist]
        
        if not targets:
            logging.info("[Unfollow] アンフォロー対象がいません。")
            return

        # アンフォロー実行
        # ランダムにシャッフルして、いつも同じ人から始まらないようにする（オプション）
        random.shuffle(targets)
        
        count = 0
        for uid in targets:
            if count >= max_unfollows:
                break
                
            try:
                # ユーザー詳細取得（ログ出力用）- API制限節約のためIDのみでも可だが、名前があったほうが安心
                user_info = cl.user_info(uid)
                username = user_info.username
                
                logging.info(f"[Unfollow] アンフォロー実行中: {username} ({count+1}/{max_unfollows})")
                
                cl.user_unfollow(uid)
                count += 1
                
                # 安全のための待機時間（30〜60秒）
                wait_time = random.uniform(30, 60)
                logging.info(f"[Unfollow] 待機中... ({int(wait_time)}秒)")
                time.sleep(wait_time)
                
            except Exception as e:
                logging.error(f"[Unfollow] エラー ({uid}): {e}")
                time.sleep(60) # エラー時も少し待つ
        
        logging.info(f"[Unfollow] 完了: {count}人をアンフォローしました。")

    except Exception as e:
        logging.error(f"[Unfollow] 予期せぬエラー: {e}")

if __name__ == "__main__":
    # テスト実行用
    # 実際には username/password が .env に設定されている必要があります
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    unfollow_non_followers(max_unfollows=2) # テストなので少なめに
