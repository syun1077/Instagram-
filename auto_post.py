"""
Instagram 完全自動投稿スクリプト
人間の操作なしで、AI画像を生成してInstagramに自動投稿する。
Windowsタスクスケジューラから呼び出して使用。
"""

import os
import sys
import random
import logging
from datetime import datetime

# ログ設定
LOG_PATH = os.path.join(os.path.dirname(__file__), "auto_post.log")
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)

from modules.token_manager import auto_refresh
from modules.ai_image_generator import generate_ai_image
from modules.uploader import upload_image
from modules.insta_poster import post_to_instagram

# --- 自動投稿用のプロンプト＆キャプション一覧 ---
# ここに好きなだけ追加してください。ランダムで1つ選ばれます。
POSTS = [
    {
        "prompt": "A serene Japanese garden with cherry blossoms at golden hour, cinematic lighting",
        "caption": "日本の美しい庭園 🌸\n#japan #garden #cherryblossoms #beautiful #nature #photography",
    },
    {
        "prompt": "Cyberpunk Tokyo city at night with neon lights and rain reflections",
        "caption": "ネオン輝く夜の東京 🌃\n#tokyo #cyberpunk #neon #nightlife #cityscape #japan",
    },
    {
        "prompt": "Cute cat sitting in a cozy coffee shop with warm lighting and latte art",
        "caption": "カフェでくつろぐ猫 ☕🐱\n#cat #coffeeshop #cozy #cute #cafe #catlovers",
    },
    {
        "prompt": "Beautiful ocean sunset with dramatic clouds and golden light reflecting on water",
        "caption": "黄金に輝く海のサンセット 🌅\n#sunset #ocean #golden #beautiful #nature #sea",
    },
    {
        "prompt": "Minimalist workspace flat lay with laptop, coffee, and plants, aesthetic photography",
        "caption": "理想のワークスペース 💻\n#workspace #minimal #aesthetic #flatlay #productivity",
    },
    {
        "prompt": "Fantasy landscape with floating islands, waterfalls and magical aurora in the sky",
        "caption": "幻想的な風景 ✨\n#fantasy #landscape #magical #aurora #art #dreamlike",
    },
    {
        "prompt": "Aesthetic food photography of colorful sushi platter on wooden table, top view",
        "caption": "美しい寿司アート 🍣\n#sushi #foodphotography #japanese #aesthetic #foodie",
    },
    {
        "prompt": "Modern glass architecture building reflecting sunset sky, wide angle photography",
        "caption": "モダン建築と夕焼け 🏙️\n#architecture #modern #sunset #building #design",
    },
    {
        "prompt": "Dreamy lavender field at sunset in Provence France, soft purple haze",
        "caption": "ラベンダー畑の夢のような景色 💜\n#lavender #provence #purple #nature #dreamy",
    },
    {
        "prompt": "Cute golden retriever puppy playing in autumn leaves, warm sunlight",
        "caption": "秋を楽しむゴールデンレトリバー 🍂🐕\n#dog #goldenretriever #autumn #puppy #cute",
    },
]


def auto_post():
    """完全自動で1投稿を行う。"""
    logging.info("=" * 40)
    logging.info("自動投稿を開始します")

    temp_image = os.path.join(os.path.dirname(__file__), "temp_image.jpg")

    try:
        # Step 0: トークン確認＆自動更新
        logging.info("トークンを確認中...")
        if not auto_refresh():
            logging.error("トークンが無効です。python get_token.py を実行してください。")
            return False

        # Step 1: ランダムにプロンプトを選択
        post = random.choice(POSTS)
        prompt = post["prompt"]
        caption = post["caption"]
        logging.info(f"プロンプト: {prompt}")
        logging.info(f"キャプション: {caption[:50]}...")

        # Step 2: AI画像生成
        logging.info("AI画像を生成中...")
        generate_ai_image(prompt, temp_image)
        logging.info("画像生成完了")

        # Step 3: 画像アップロード
        logging.info("画像をアップロード中...")
        image_url = upload_image(temp_image)
        logging.info(f"アップロード完了: {image_url}")

        # Step 4: Instagram投稿
        logging.info("Instagramに投稿中...")
        post_id = post_to_instagram(image_url, caption)
        logging.info(f"投稿完了! Post ID: {post_id}")

        return True

    except Exception as e:
        logging.error(f"エラー発生: {e}")
        return False

    finally:
        if os.path.exists(temp_image):
            os.remove(temp_image)
            logging.info("一時ファイルを削除しました")


if __name__ == "__main__":
    success = auto_post()
    sys.exit(0 if success else 1)
