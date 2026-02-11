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
    # === トップス / シャツ / ジャケット ===
    {
        "prompt": "Fashion editorial photo of an oversized cream white knit sweater on a wooden hanger, minimalist beige studio background, soft natural lighting, Vogue magazine style, product photography, 8K ultra detailed",
        "caption": "ふわふわニットで冬を暖かく\n\nオーバーサイズのクリームホワイトニット。\nシンプルだけど存在感のある一枚。\n\n#fashion #knit #sweater #winter #ootd #ファッション #ニット #冬コーデ #シンプルコーデ #お洒落さんと繋がりたい",
    },
    {
        "prompt": "Stunning fashion photograph of a tailored black leather jacket with silver zippers, hanging on a vintage coat rack, moody studio lighting with dramatic shadows, high fashion editorial, shot on Hasselblad",
        "caption": "永遠の定番、レザージャケット\n\nどんなスタイルにもハマる万能アイテム。\n一着あるだけでコーデが締まる。\n\n#fashion #leatherjacket #black #レザージャケット #ファッション #メンズファッション #ストリート #cool #style #outfit",
    },
    {
        "prompt": "Professional fashion photo of a pastel pink linen shirt with rolled up sleeves, laid flat on white marble surface with dried flowers and sunglasses, top view flat lay, bright airy aesthetic, product photography",
        "caption": "春の定番リネンシャツ\n\nパステルピンクで柔らかい印象に。\n一枚でもレイヤードでも使える。\n\n#fashion #linen #shirt #spring #pastel #ファッション #リネンシャツ #春コーデ #ピンク #大人カジュアル",
    },
    {
        "prompt": "Editorial fashion photo of a vintage denim jacket with custom patches and embroidery, worn by a mannequin, urban street background with graffiti wall, golden hour lighting, streetwear photography",
        "caption": "ヴィンテージデニムの味わい\n\nパッチワークと刺繍で唯一無二の一着。\nストリートスタイルの主役に。\n\n#fashion #denim #vintage #streetwear #デニム #ヴィンテージ #ストリートファッション #古着 #ootd #コーデ",
    },
    # === パンツ / ボトムス ===
    {
        "prompt": "High fashion product photo of perfectly pressed wide leg beige trousers draped elegantly on a minimalist white chair, soft studio lighting, clean aesthetic, luxury fashion brand style, 8K",
        "caption": "ワイドパンツで作る大人の余裕\n\nベージュのワイドレッグトラウザー。\nきれいめにもカジュアルにも。\n\n#fashion #widepants #beige #trousers #ファッション #ワイドパンツ #ベージュ #大人コーデ #きれいめ #パンツスタイル",
    },
    {
        "prompt": "Stylish fashion photograph of dark indigo raw selvedge denim jeans, perfectly folded showing the red selvedge line, on a rustic wooden surface, warm moody lighting, premium denim brand aesthetic",
        "caption": "こだわりのセルビッジデニム\n\nインディゴの深い色味と赤耳。\n育てる楽しみがあるジーンズ。\n\n#fashion #denim #jeans #selvedge #ファッション #デニム #ジーンズ #セルビッジ #メンズ #こだわり",
    },
    {
        "prompt": "Fashion editorial of olive green cargo pants with multiple pockets, styled on a model mannequin with white sneakers, urban concrete background, street style photography, natural lighting",
        "caption": "カーゴパンツでミリタリーMIX\n\nオリーブグリーンのカーゴパンツ。\n機能性とスタイルの両立。\n\n#fashion #cargo #pants #military #ファッション #カーゴパンツ #ミリタリー #ストリート #メンズファッション #コーデ",
    },
    # === シューズ ===
    {
        "prompt": "Luxury product photography of pristine white leather sneakers on a reflective surface, minimalist studio, soft gradient background, premium shoe brand campaign style, ultra sharp detail, 8K",
        "caption": "白スニーカーは究極のベーシック\n\nどんなコーデにも合う清潔感。\n一足は持っておきたいマストアイテム。\n\n#fashion #sneakers #white #shoes #ファッション #スニーカー #白スニーカー #シューズ #足元倶楽部 #靴",
    },
    {
        "prompt": "Editorial photograph of brown suede Chelsea boots on autumn leaves, warm golden light, shallow depth of field, British fashion style, luxury footwear campaign, shot on medium format camera",
        "caption": "チェルシーブーツで大人の足元\n\nブラウンスエードが秋の雰囲気にぴったり。\nシンプルなのに品がある。\n\n#fashion #boots #chelsea #suede #ファッション #ブーツ #チェルシーブーツ #秋コーデ #足元 #メンズシューズ",
    },
    {
        "prompt": "High-end fashion photo of sleek black loafers with gold hardware detail, placed on dark marble surface with dramatic side lighting, luxury brand aesthetic, product photography, 8K detail",
        "caption": "ローファーで品格をプラス\n\nゴールドのアクセントが上品。\nカジュアルにもフォーマルにも。\n\n#fashion #loafers #shoes #luxury #ファッション #ローファー #革靴 #シューズ #大人コーデ #上品",
    },
    # === アクセサリー ===
    {
        "prompt": "Luxury still life photograph of a minimalist silver watch with black dial on a dark slate surface, soft rim lighting, jewelry product photography, close-up macro detail, premium brand aesthetic",
        "caption": "シンプルな腕時計が映えるコーデ\n\nミニマルなシルバーウォッチ。\nさりげないけど確実に格上げ。\n\n#fashion #watch #silver #minimal #ファッション #腕時計 #アクセサリー #シルバー #ミニマル #お洒落",
    },
    {
        "prompt": "Aesthetic flat lay of gold chain necklaces and rings on cream linen fabric, soft morning light from window, warm tones, jewelry photography, Instagram aesthetic, delicate details",
        "caption": "ゴールドアクセで華やかに\n\nチェーンネックレスとリングの重ね付け。\nコーデのアクセントに。\n\n#fashion #jewelry #gold #accessories #ファッション #アクセサリー #ゴールド #ネックレス #リング #ジュエリー",
    },
    {
        "prompt": "Fashion product photo of stylish black rectangular sunglasses on white marble with palm leaf shadow, summer vibes, luxury accessory campaign, clean bright lighting, 8K",
        "caption": "サングラスで一気にこなれ感\n\nブラックフレームのスクエアタイプ。\n夏のマストアイテム。\n\n#fashion #sunglasses #summer #style #ファッション #サングラス #夏 #アクセサリー #お洒落さんと繋がりたい #コーデ",
    },
    # === マフラー / スカーフ ===
    {
        "prompt": "Cozy fashion photo of a chunky knit camel colored scarf draped elegantly on a coat hanger with a wool overcoat, warm studio lighting, autumn winter fashion editorial, texture detail",
        "caption": "キャメルマフラーで温もりコーデ\n\nチャンキーニットの存在感。\n巻き方で印象が変わる。\n\n#fashion #scarf #camel #winter #ファッション #マフラー #キャメル #冬コーデ #ニット #防寒お洒落",
    },
    {
        "prompt": "Elegant product photo of a silk patterned scarf in navy and burgundy, artfully draped on light grey surface, luxury fashion brand aesthetic, soft diffused lighting, 8K detail",
        "caption": "シルクスカーフで上品さを\n\nネイビー×バーガンディの配色。\n首元に巻いてもバッグに結んでも。\n\n#fashion #silk #scarf #elegant #ファッション #スカーフ #シルク #上品 #大人ファッション #コーデ",
    },
    # === 帽子 ===
    {
        "prompt": "Stylish fashion photo of a classic black fedora hat on a wooden hat stand, moody dramatic lighting with warm tones, vintage atmosphere, editorial hat photography, sharp detail",
        "caption": "フェドラハットで大人の遊び心\n\nブラックフェドラで一気にこなれ感。\nシンプルコーデのアクセントに。\n\n#fashion #hat #fedora #style #ファッション #帽子 #フェドラ #大人コーデ #お洒落 #ハット",
    },
    {
        "prompt": "Aesthetic photo of a cream colored bucket hat and beige tote bag on sandy beach background, summer fashion lifestyle, bright natural lighting, resort style, clean composition",
        "caption": "バケットハットで夏スタイル\n\nクリーム色で爽やかに。\nビーチにも街にもハマる。\n\n#fashion #buckethat #summer #beach #ファッション #バケットハット #夏コーデ #帽子 #リゾート #カジュアル",
    },
    # === コーディネート全身 ===
    {
        "prompt": "Full body fashion editorial of a complete minimalist outfit on mannequin: white t-shirt, beige chino pants, white sneakers, silver watch, urban rooftop background at golden hour, Vogue style photography",
        "caption": "シンプルイズベスト\n\n白T × ベージュチノ × 白スニーカー。\nミニマルだけど計算されたコーデ。\n\n#fashion #minimal #ootd #coordinate #ファッション #ミニマル #コーディネート #シンプルコーデ #メンズコーデ #今日のコーデ",
    },
    {
        "prompt": "Stunning fashion photograph of an all-black outfit: turtleneck, tailored trousers, leather Chelsea boots, laid out neatly on white surface, overhead flat lay view, luxury menswear editorial",
        "caption": "オールブラックの美学\n\nタートルネック × テーラードパンツ × チェルシーブーツ。\n黒で統一すると一気に洗練される。\n\n#fashion #allblack #black #monochrome #ファッション #オールブラック #黒コーデ #モノトーン #大人コーデ #メンズ",
    },
    {
        "prompt": "Street style fashion photo of layered outfit: grey hoodie under camel overcoat, dark jeans, white sneakers, on urban city sidewalk, candid street photography style, autumn atmosphere",
        "caption": "レイヤードで作る秋のストリート\n\nパーカー × コートの鉄板レイヤード。\nカジュアルときれいめのバランス。\n\n#fashion #layered #streetstyle #autumn #ファッション #レイヤード #秋コーデ #ストリート #重ね着 #コーデ",
    },
    {
        "prompt": "Summer fashion flat lay of complete outfit: navy linen shirt, white shorts, brown leather sandals, straw hat, sunglasses, on light wooden surface, bright airy aesthetic, vacation style",
        "caption": "夏の大人リゾートスタイル\n\nリネンシャツ × ショートパンツで爽やかに。\n休日のリラックスコーデ。\n\n#fashion #summer #resort #linen #ファッション #夏コーデ #リゾート #リネン #大人カジュアル #休日コーデ",
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
