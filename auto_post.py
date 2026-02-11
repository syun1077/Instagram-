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
    # === 可愛い動物 ===
    {
        "prompt": "Ultra realistic photograph of a fluffy white kitten with bright blue eyes sitting on a windowsill, soft morning light, bokeh background, shot on Canon EOS R5, 85mm lens, f/1.4",
        "caption": "窓辺の天使 🐱\n\n#cat #kitten #cute #fluffy #catlover #catoftheday #kawaii #animal #pet #photography",
    },
    {
        "prompt": "Adorable golden retriever puppy running through a field of wildflowers at golden hour, motion blur, professional wildlife photography, National Geographic style",
        "caption": "お花畑を駆け回るゴールデン 🐕🌼\n\n#goldenretriever #puppy #dog #dogsofinstagram #cute #nature #goldenhour #pet #doglovers",
    },
    {
        "prompt": "Baby red panda sleeping on a tree branch in a misty forest, incredibly cute face, soft natural lighting, wildlife photography, 4K ultra detailed",
        "caption": "おやすみレッサーパンダ 🐾\n\n#redpanda #cute #animal #wildlife #sleeping #nature #adorable #kawaii #animalphotography",
    },
    {
        "prompt": "Two baby rabbits cuddling together in a garden surrounded by daisies, soft pastel colors, dreamy atmosphere, shallow depth of field, professional photo",
        "caption": "仲良しうさぎ 🐰🌸\n\n#rabbit #bunny #cute #animals #garden #flowers #adorable #pet #kawaii #bunnylove",
    },
    {
        "prompt": "Majestic white owl with piercing golden eyes perched on a snowy branch, winter forest background, magical atmosphere, National Geographic award winning photo",
        "caption": "雪の森のフクロウ 🦉❄️\n\n#owl #wildlife #nature #winter #snow #majestic #bird #animal #photography #beautiful",
    },
    {
        "prompt": "Cute baby fox kit peeking out from behind a tree in an enchanted autumn forest, golden leaves falling, warm sunlight filtering through trees, 8K photo",
        "caption": "秋の森のキツネの赤ちゃん 🦊🍂\n\n#fox #babyfox #autumn #nature #wildlife #cute #forest #animal #fall #adorable",
    },
    {
        "prompt": "Three kittens of different colors (orange, black, white) sitting in a row on a rustic wooden bench, looking at camera, studio quality lighting",
        "caption": "三兄弟 🧡🖤🤍\n\n#cats #kittens #cute #trio #catlife #catsofinstagram #adorable #kawaii #pet #catlovers",
    },
    {
        "prompt": "Baby elephant playing in water, splashing with its trunk, joyful expression, African savanna sunset background, cinematic photography, golden hour light",
        "caption": "水遊びが大好きな子ゾウ 🐘💦\n\n#elephant #babyelephant #wildlife #africa #nature #cute #animal #safari #photography",
    },
    # === 美しい風景 ===
    {
        "prompt": "Breathtaking aerial view of turquoise ocean meeting white sand beach, Maldives, crystal clear water, coral reef visible from above, drone photography, 8K",
        "caption": "地上の楽園 🏝️\n\n#maldives #ocean #beach #paradise #travel #blue #nature #beautiful #tropical #景色",
    },
    {
        "prompt": "Mount Fuji at sunrise with perfect reflection in Lake Kawaguchi, cherry blossoms in foreground, pink sky, ultra sharp landscape photography",
        "caption": "富士山と桜の絶景 🗻🌸\n\n#mtfuji #fujisan #japan #cherryblossoms #sunrise #landscape #beautiful #日本 #富士山 #桜",
    },
    {
        "prompt": "Northern lights aurora borealis dancing over a perfectly still lake in Iceland, green and purple lights reflecting in water, starry sky, long exposure photography",
        "caption": "オーロラの魔法 ✨🌌\n\n#aurora #northernlights #iceland #nature #nightsky #stars #beautiful #landscape #travel #magical",
    },
    {
        "prompt": "Enchanted bamboo forest path in Kyoto Japan with soft morning mist, sunbeams filtering through, peaceful zen atmosphere, fine art photography",
        "caption": "京都の竹林 🎋\n\n#kyoto #bamboo #japan #zen #peaceful #nature #forest #japanese #beautiful #京都",
    },
    {
        "prompt": "Stunning pink and orange sunset over Santorini Greece, white buildings with blue domes, Mediterranean sea, professional travel photography",
        "caption": "サントリーニの夕日 🇬🇷🌅\n\n#santorini #greece #sunset #travel #beautiful #mediterranean #architecture #europe #景色",
    },
    {
        "prompt": "Magical wisteria tunnel in full bloom, cascading purple flowers creating a fairy tale pathway, soft dreamy light, Ashikaga Flower Park Japan",
        "caption": "藤のトンネル 💜\n\n#wisteria #flowers #japan #purple #beautiful #nature #garden #magical #藤 #花",
    },
    # === 美しいアート ===
    {
        "prompt": "Ethereal woman made of glowing cherry blossom petals dissolving into wind, digital art, fantasy, soft pink and white, magical particles, 8K ultra detailed",
        "caption": "桜の精霊 🌸✨\n\n#digitalart #fantasy #cherryblossoms #art #beautiful #ethereal #magical #artwork #illustration",
    },
    {
        "prompt": "Underwater photograph of a sea turtle swimming through a beam of sunlight in crystal clear blue ocean, tropical fish around, National Geographic style",
        "caption": "光の中を泳ぐウミガメ 🐢🌊\n\n#seaturtle #ocean #underwater #nature #marine #beautiful #wildlife #photography #sea #blue",
    },
    {
        "prompt": "Cozy rainy day window view of a beautiful Japanese garden, raindrops on glass, warm indoor lighting, cup of matcha tea on windowsill, aesthetic photography",
        "caption": "雨の日の静けさ 🌧️🍵\n\n#rainy #cozy #japan #matcha #aesthetic #peaceful #rain #日本庭園 #雨 #お茶",
    },
    {
        "prompt": "Magnificent whale breaching out of ocean at sunset, water droplets frozen in air, dramatic golden sky, award winning wildlife photography",
        "caption": "夕日とクジラのジャンプ 🐋🌅\n\n#whale #ocean #sunset #wildlife #nature #amazing #photography #sea #beautiful #animal",
    },
    {
        "prompt": "Field of sunflowers stretching to the horizon under a bright blue sky with fluffy white clouds, summer vibes, vibrant colors, professional landscape photo",
        "caption": "ひまわり畑 🌻☀️\n\n#sunflower #summer #nature #flowers #sky #beautiful #yellow #landscape #ひまわり #夏",
    },
    {
        "prompt": "Adorable calico cat wearing a tiny scarf sitting in front of a fireplace on a snowy winter evening, cozy warm atmosphere, soft lighting, detailed fur texture",
        "caption": "暖炉前の冬猫 🐱🧣\n\n#cat #winter #cozy #fireplace #cute #catlife #warm #catsofinstagram #kawaii #冬",
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
