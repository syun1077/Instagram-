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
    # === メンズ - アウター ===
    {
        "prompt": "Fashion photo of a young handsome Japanese male model with short black hair and clean face, wearing an oversized beige trench coat over a white hoodie and black skinny jeans, white sneakers, walking through a trendy Tokyo street with cherry blossom trees, natural daylight, street photography, 8K",
        "caption": "Trench Coat x Hoodie\nトレンチ×パーカーの王道レイヤード\n\nThe classic layered look for spring.\nベージュトレンチにホワイトパーカーを合わせて。\nEffortlessly cool.\n\n#fashion #ファッション #trenchcoat #hoodie #layered #spring #メンズコーデ #大学生コーデ #ootd #お洒落さんと繋がりたい",
    },
    {
        "prompt": "Fashion photo of a young handsome Japanese male model with short black hair and clean face, wearing a navy MA-1 bomber jacket over a grey crewneck sweatshirt, khaki chino pants, white leather sneakers, standing in front of a modern concrete building, overcast sky, street style photography, 8K",
        "caption": "MA-1 Bomber Style\nMA-1で作るストリートカジュアル\n\nNavy bomber jacket keeps it simple and sharp.\nグレースウェット×カーキチノでバランス良く。\nA look that works anywhere.\n\n#fashion #ファッション #MA1 #bomber #streetstyle #casual #メンズコーデ #大学生コーデ #ootd #シンプルコーデ",
    },
    {
        "prompt": "Fashion photo of a young handsome Japanese male model with short black hair and clean face, wearing a black leather biker jacket over a white crew neck tee, dark wash slim jeans, black Chelsea boots, leaning against a brick wall in an urban alley, golden hour lighting, editorial photography, 8K",
        "caption": "Leather Jacket Essential\nレザージャケットは永遠の相棒\n\nBlack leather x white tee. Timeless combo.\nシンプルな白T合わせが一番かっこいい。\nEvery guy needs this in their closet.\n\n#fashion #ファッション #leatherjacket #レザー #blackandwhite #メンズコーデ #大学生コーデ #ootd #cool #style",
    },
    # === レディース - アウター ===
    {
        "prompt": "Fashion photo of a young beautiful Japanese female model with medium length dark brown hair, wearing a soft camel oversized knit cardigan over a white lace camisole, light blue high waisted jeans, beige loafers, walking through a sunlit park with autumn leaves, warm golden light, fashion photography, 8K",
        "caption": "Camel Cardigan for Autumn\nキャメルカーデで秋のゆるコーデ\n\nOversized camel knit over delicate white lace.\nゆるっとニットで大人っぽく。\nCozy and chic.\n\n#fashion #ファッション #cardigan #camel #autumn #秋コーデ #レディースコーデ #大学生コーデ #ootd #お洒落さんと繋がりたい",
    },
    {
        "prompt": "Fashion photo of a young beautiful Japanese female model with medium length dark brown hair, wearing a cropped cream white puffer jacket, light grey knit dress underneath, white chunky sneakers, holding a coffee cup, standing outside a minimalist cafe with large glass windows, bright winter day, street style photography, 8K",
        "caption": "Cropped Puffer x Knit Dress\nショートダウン×ニットワンピ\n\nCream puffer keeps the silhouette cute and warm.\nショート丈ダウンでバランスよく。\nWinter layering done right.\n\n#fashion #ファッション #pufferjacket #knitdress #winter #冬コーデ #レディースコーデ #大学生コーデ #ootd #cute",
    },
    {
        "prompt": "Fashion photo of a young beautiful Japanese female model with medium length dark brown hair, wearing a classic beige double-breasted blazer over a black turtleneck, dark grey tailored pants, black pointed flats, walking through a modern office lobby with marble floors, natural window light, fashion editorial, 8K",
        "caption": "Blazer for Smart Casual\nブレザーできれいめカジュアル\n\nBeige blazer x black turtleneck. Clean and polished.\nかっちりしすぎないのがポイント。\nDress smart, feel confident.\n\n#fashion #ファッション #blazer #smartcasual #きれいめ #レディースコーデ #大学生コーデ #ootd #office #style",
    },
    # === メンズ - トップス ===
    {
        "prompt": "Fashion photo of a young handsome Japanese male model with short black hair and clean face, wearing a striped navy and white oversized long sleeve tee, beige wide leg pants, white canvas sneakers, sitting on steps of a university campus with green lawn, bright sunny day, casual photography, 8K",
        "caption": "Striped Tee x Wide Pants\nボーダーT×ワイドパンツの定番\n\nNavy stripes keep it classic and clean.\nゆるっとワイドパンツでリラックス感。\nCampus style staple.\n\n#fashion #ファッション #stripes #widepants #casual #キャンパスコーデ #メンズコーデ #大学生コーデ #ootd #relaxed",
    },
    {
        "prompt": "Fashion photo of a young handsome Japanese male model with short black hair and clean face, wearing a sage green oversized hoodie, black jogger pants, chunky white sneakers, walking through a neon-lit shopping street at night, urban night photography, 8K",
        "caption": "Sage Green Hoodie\nセージグリーンのゆるパーカー\n\nThis green hits different at night.\nくすみグリーンで差をつける。\nSimple but never boring.\n\n#fashion #ファッション #hoodie #sagegreen #streetstyle #パーカー #メンズコーデ #大学生コーデ #ootd #nightout",
    },
    # === レディース - トップス ===
    {
        "prompt": "Fashion photo of a young beautiful Japanese female model with medium length dark brown hair, wearing a cream white cable knit sweater, brown plaid mini skirt, brown knee high boots, standing in front of a cozy bookshop with warm interior lighting, autumn afternoon, fashion photography, 8K",
        "caption": "Cable Knit x Plaid Skirt\nケーブルニット×チェックスカート\n\nWarm cable knit meets cute plaid.\n秋の定番コーデ、本屋さん巡りの日。\nBookish and beautiful.\n\n#fashion #ファッション #cableknit #plaid #autumn #秋コーデ #レディースコーデ #大学生コーデ #ootd #cozy",
    },
    {
        "prompt": "Fashion photo of a young beautiful Japanese female model with medium length dark brown hair, wearing a lavender oversized sweatshirt with small embroidered flower on chest, white pleated midi skirt, white platform sneakers, sitting on a bench in a flower garden, soft spring light, dreamy photography, 8K",
        "caption": "Lavender Sweatshirt\nラベンダースウェットで春気分\n\nSoft lavender with a tiny flower detail.\nさりげない刺繍がポイント。\nSpring mood in one outfit.\n\n#fashion #ファッション #lavender #sweatshirt #spring #春コーデ #レディースコーデ #大学生コーデ #ootd #pastel",
    },
    # === メンズ - パンツ / 全身 ===
    {
        "prompt": "Fashion photo of a young handsome Japanese male model with short black hair and clean face, wearing a plain white oversized tee tucked into dark olive cargo pants, black high top sneakers, silver chain necklace, standing on a rooftop with city skyline behind, sunset golden hour, fashion photography, 8K",
        "caption": "Cargo Pants on the Rooftop\nカーゴパンツで都会のサンセット\n\nWhite tee x olive cargo. Keep it easy.\nシンプルに着るのが今っぽい。\nSunset vibes, city style.\n\n#fashion #ファッション #cargo #cargopants #sunset #カーゴパンツ #メンズコーデ #大学生コーデ #ootd #streetwear",
    },
    {
        "prompt": "Fashion photo of a young handsome Japanese male model with short black hair and clean face, wearing a denim-on-denim outfit with light wash oversized denim jacket and darker wash straight jeans, white tee underneath, retro sunglasses on head, standing at a coastal pier with ocean background, bright summer day, 8K",
        "caption": "Denim on Denim\nデニム×デニムの夏スタイル\n\nDouble denim done right by the sea.\n濃淡を変えるのがコツ。\nSummer vibes only.\n\n#fashion #ファッション #denim #doubledenim #summer #デニム #夏コーデ #メンズコーデ #大学生コーデ #ootd",
    },
    # === レディース - ボトムス / 全身 ===
    {
        "prompt": "Fashion photo of a young beautiful Japanese female model with medium length dark brown hair, wearing a fitted black ribbed top, high waisted cream wide leg trousers, gold hoop earrings, small black crossbody bag, walking through a European style cobblestone street with outdoor cafes, afternoon sun, street style photography, 8K",
        "caption": "Black Top x Cream Wide Pants\n黒リブ×クリームワイドの大人バランス\n\nSimple black and cream. Always elegant.\nモノトーンにゴールドアクセで抜け感。\nEffortless elegance.\n\n#fashion #ファッション #widepants #monochrome #elegant #大人コーデ #レディースコーデ #大学生コーデ #ootd #chic",
    },
    {
        "prompt": "Fashion photo of a young beautiful Japanese female model with medium length dark brown hair, wearing a light blue denim overall dress over a white puff sleeve blouse, white canvas sneakers, holding a straw basket bag, standing in a sunflower field, bright summer day, cheerful photography, 8K",
        "caption": "Denim Overall in Sunflowers\nデニムオーバーオールでひまわり畑へ\n\nDenim overalls x puff sleeves for summer.\nブラウス合わせで大人可愛く。\nSummer adventure outfit.\n\n#fashion #ファッション #overalls #denim #summer #ひまわり #夏コーデ #レディースコーデ #大学生コーデ #ootd",
    },
    # === メンズ - シューズ / アクセサリー ===
    {
        "prompt": "Fashion photo of a young handsome Japanese male model with short black hair and clean face, wearing a black oversized graphic tee, grey sweatpants, brand new white leather low-top sneakers, silver watch, sitting on a skatepark bench with graffiti wall behind, afternoon light, street photography, 8K",
        "caption": "Fresh White Kicks\n白スニーカーは正義\n\nClean white sneakers make any fit look better.\n新品の白スニーカーはテンション上がる。\nFresh kicks, fresh start.\n\n#fashion #ファッション #whitesneakers #sneakers #streetwear #白スニーカー #メンズコーデ #大学生コーデ #ootd #kicks",
    },
    {
        "prompt": "Fashion photo of a young handsome Japanese male model with short black hair and clean face, wearing a navy knit polo shirt, beige tailored shorts, brown leather sandals, woven bracelet, walking on a wooden boardwalk near the beach, ocean breeze, summer evening light, resort photography, 8K",
        "caption": "Summer Resort Casual\n夏のリゾートカジュアル\n\nKnit polo x tailored shorts by the sea.\nニットポロでキレイめな海コーデ。\nVacation mode: ON.\n\n#fashion #ファッション #resort #summer #knitpolo #リゾート #夏コーデ #メンズコーデ #大学生コーデ #ootd",
    },
    # === レディース - シューズ / アクセサリー ===
    {
        "prompt": "Fashion photo of a young beautiful Japanese female model with medium length dark brown hair, wearing a white off-shoulder blouse, light wash straight jeans, strappy tan leather sandals, layered gold necklaces, straw hat in hand, walking along a seaside promenade at sunset, warm golden light, summer photography, 8K",
        "caption": "Golden Hour Seaside Look\nゴールデンアワーの海沿いコーデ\n\nWhite off-shoulder x gold layers. Summer perfection.\n夕日に映えるゴールドアクセ。\nChasing sunsets in style.\n\n#fashion #ファッション #goldenhour #seaside #summer #夏コーデ #レディースコーデ #大学生コーデ #ootd #sunset",
    },
    {
        "prompt": "Fashion photo of a young beautiful Japanese female model with medium length dark brown hair, wearing a fitted black turtleneck, camel wool coat, dark blue straight jeans, brown suede ankle boots, small brown leather bag, walking through a tree-lined avenue with fallen leaves, crisp autumn light, editorial photography, 8K",
        "caption": "Camel Coat x Black Turtleneck\nキャメルコート×黒タートル\n\nTimeless camel coat for the perfect autumn walk.\n秋の並木道にキャメルコートが映える。\nClassic never goes out of style.\n\n#fashion #ファッション #camelcoat #turtleneck #autumn #秋コーデ #レディースコーデ #大学生コーデ #ootd #classic",
    },
    # === メンズ - きれいめ ===
    {
        "prompt": "Fashion photo of a young handsome Japanese male model with short black hair and clean face, wearing a white oxford button-down shirt with sleeves rolled up, navy chino pants, brown leather loafers, minimal silver watch, standing in a bright art gallery with white walls, clean natural lighting, smart casual photography, 8K",
        "caption": "Smart Casual at the Gallery\n美術館デートのスマートカジュアル\n\nWhite oxford x navy chinos. Clean and sharp.\nシャツの袖まくりでこなれ感を。\nArt meets style.\n\n#fashion #ファッション #smartcasual #oxford #shirt #きれいめ #メンズコーデ #大学生コーデ #ootd #dateoutfit",
    },
    {
        "prompt": "Fashion photo of a young handsome Japanese male model with short black hair and clean face, wearing a charcoal grey oversized knit sweater, black tapered pants, white minimalist sneakers, tote bag on shoulder, walking past a modern glass building in the rain with umbrella, rainy city aesthetic, street photography, 8K",
        "caption": "Rainy Day Grey Knit\n雨の日のグレーニット\n\nCharcoal knit keeps you warm and stylish in the rain.\n雨の街に溶け込むグレートーン。\nBad weather, good style.\n\n#fashion #ファッション #knit #grey #rainyday #雨の日コーデ #メンズコーデ #大学生コーデ #ootd #mood",
    },
    # === レディース - きれいめ ===
    {
        "prompt": "Fashion photo of a young beautiful Japanese female model with medium length dark brown hair, wearing a soft pink satin slip dress layered over a white tee, white canvas sneakers, small pearl earrings, sitting at an outdoor cafe terrace with potted plants, soft afternoon light, lifestyle photography, 8K",
        "caption": "Slip Dress x Tee Layering\nスリップドレス×Tシャツの抜け感コーデ\n\nPink satin slip over a casual white tee.\nドレスをカジュアルダウンするのが今っぽい。\nDressy and casual at once.\n\n#fashion #ファッション #slipdress #layering #pink #カフェコーデ #レディースコーデ #大学生コーデ #ootd #trendy",
    },
    {
        "prompt": "Fashion photo of a young beautiful Japanese female model with medium length dark brown hair, wearing a mint green oversized shirt jacket over a white crop tank top, beige linen wide pants, white mules, small gold hoop earrings, browsing at an outdoor weekend market with colorful stalls, bright sunny day, lifestyle photography, 8K",
        "caption": "Mint Shirt Jacket at the Market\nミントシャツジャケットで休日マーケットへ\n\nMint green shacket for a relaxed weekend vibe.\nリネンパンツ合わせで爽やかに。\nWeekend mood, market finds.\n\n#fashion #ファッション #shacket #mint #weekend #休日コーデ #レディースコーデ #大学生コーデ #ootd #linen",
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
