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
    # === トップス ===
    {
        "prompt": "Aesthetic product photo of an oversized sage green hoodie with small embroidered bear logo on chest, heavyweight cotton, laid flat on clean white surface, soft natural window light from left side, minimal styling with dried eucalyptus branch, premium streetwear brand aesthetic, product photography, 8K",
        "caption": "Sage Green Bear Hoodie\nくすみグリーンのベアロゴパーカー\n\nHeavyweight cotton. Oversized fit. Tiny bear detail.\n肉厚コットンにさりげないクマ刺繍。\nThe hoodie you'll live in.\n\n#fashion #ファッション #hoodie #sagegreen #streetwear #パーカー #トップス #大学生コーデ #デザイン #お洒落さんと繋がりたい",
    },
    {
        "prompt": "Beautiful flat lay product photo of a cream white cable knit sweater with chunky texture, neatly folded on light wooden table, a cup of coffee and old book beside it, warm cozy morning light, autumn aesthetic, lifestyle product photography, 8K",
        "caption": "Chunky Cable Knit\nざっくりケーブルニット\n\nThick cable knit texture you can feel through the screen.\n触りたくなるざっくり編み。\nMade for cozy mornings.\n\n#fashion #ファッション #knit #cableknit #sweater #ニット #秋冬 #トップス #cozy #warmstyle",
    },
    {
        "prompt": "Stylish product photo of a black oversized graphic tee with minimalist white line art design of a city skyline on back, premium heavy cotton, hanging on a matte black clothes hanger against raw concrete wall, moody side lighting, streetwear brand campaign, 8K",
        "caption": "City Skyline Back Print Tee\nシティスカイラインのバックプリントT\n\nMinimalist line art on heavyweight cotton.\n背中で語るミニマルデザイン。\nSimple front, statement back.\n\n#fashion #ファッション #tshirt #graphic #streetwear #Tシャツ #バックプリント #トップス #デザイン #cool",
    },
    {
        "prompt": "Aesthetic product photo of a lavender cropped cardigan with pearl buttons, delicate knit texture, styled on white linen fabric with small wildflowers scattered around, soft dreamy window light, feminine fashion brand aesthetic, 8K",
        "caption": "Lavender Pearl Cardigan\nラベンダーのパールボタンカーデ\n\nSoft knit, pearl buttons, perfect cropped length.\nパールボタンが上品なアクセント。\nA cardigan that feels like spring.\n\n#fashion #ファッション #cardigan #lavender #pearl #カーディガン #春服 #トップス #cute #girly",
    },
    {
        "prompt": "Clean product photo of a navy and white striped long sleeve Breton top, classic French style, neatly folded on marble surface with a beret and sunglasses beside it, bright clean lighting, timeless fashion aesthetic, 8K",
        "caption": "Classic Breton Stripe\n定番ボーダーロンT\n\nThe French classic that never goes out of style.\n何年経っても色褪せないボーダー。\nTimeless for a reason.\n\n#fashion #ファッション #breton #stripes #french #ボーダー #ロンT #トップス #classic #定番",
    },
    {
        "prompt": "Aesthetic product photo of a dusty pink oversized sweatshirt with small white heart embroidery on left chest, soft brushed fleece inside, laid on white bedsheets with morning sunlight streaming through sheer curtains, cozy lifestyle photography, 8K",
        "caption": "Heart Embroidery Sweatshirt\nハート刺繍のスウェット\n\nTiny heart, big comfort. Brushed fleece inside.\n小さなハートがさりげなく可愛い。\nYour new favorite comfort piece.\n\n#fashion #ファッション #sweatshirt #heart #pink #スウェット #刺繍 #トップス #cute #お洒落さんと繋がりたい",
    },
    # === パンツ / ボトムス ===
    {
        "prompt": "Stylish product photo of dark olive cargo pants with clean tapered silhouette, multiple utility pockets with matte black snaps, laid flat on dark wooden floor with white sneakers placed beside them, overhead flat lay view, modern streetwear aesthetic, 8K",
        "caption": "Tapered Cargo Pants\nテーパードカーゴパンツ\n\nClean tapered fit with functional pockets.\nすっきりシルエットで大人なカーゴ。\nNot your dad's cargo pants.\n\n#fashion #ファッション #cargo #pants #streetwear #カーゴパンツ #ボトムス #メンズ #デザイン #cool",
    },
    {
        "prompt": "Beautiful product photo of light wash wide leg jeans with natural fading and subtle distressing, draped over a vintage wooden chair, sunlit room with white walls, relaxed California aesthetic, denim brand campaign photography, 8K",
        "caption": "Wide Leg Vintage Wash Denim\nワイドレッグのヴィンテージウォッシュ\n\nNatural fading that looks like years of wear.\n絶妙な色落ちが最高にかっこいい。\nDenim that tells a story.\n\n#fashion #ファッション #denim #jeans #wideleg #デニム #ジーンズ #ボトムス #vintage #style",
    },
    {
        "prompt": "Aesthetic product photo of cream white high-waisted pleated wide pants, flowing lightweight fabric, hanging on a gold clothes hanger against soft beige wall, gentle breeze effect on fabric, elegant minimal styling, 8K",
        "caption": "Pleated Wide Pants\nプリーツワイドパンツ\n\nFlowing fabric with a perfect pleated drape.\nふわっと揺れるプリーツが美しい。\nElegance in every step.\n\n#fashion #ファッション #widepants #pleated #cream #ワイドパンツ #プリーツ #ボトムス #elegant #きれいめ",
    },
    {
        "prompt": "Product photo of black tapered jogger pants with clean minimal design, subtle ribbed cuffs, premium fabric texture visible, neatly folded on white marble surface next to a sleek water bottle and earbuds, modern lifestyle flat lay, 8K",
        "caption": "Minimal Black Joggers\nミニマルブラックジョガー\n\nClean lines, premium fabric, zero logos.\nロゴなしの潔いミニマルデザイン。\nFrom gym to cafe, no problem.\n\n#fashion #ファッション #joggers #minimal #black #ジョガーパンツ #ボトムス #ミニマル #デザイン #streetwear",
    },
    {
        "prompt": "Stylish product photo of a brown plaid mini skirt with gold button detail on front, A-line silhouette, styled flat on cream knit blanket with autumn leaves and a coffee cup, warm golden afternoon light, preppy fashion aesthetic, 8K",
        "caption": "Plaid Mini Skirt\nチェック柄ミニスカート\n\nGold buttons and classic plaid. Autumn essential.\nゴールドボタンがポイントの秋カラー。\nPreppy never looked this good.\n\n#fashion #ファッション #plaid #skirt #autumn #チェック #スカート #ボトムス #preppy #秋服",
    },
    # === シューズ ===
    {
        "prompt": "Premium product photo of brand new white leather low-top sneakers with clean stitching and minimal design, placed on polished concrete floor, soft directional studio lighting creating gentle shadows, sneaker brand campaign style, close-up showing material texture, 8K",
        "caption": "Clean White Leather Sneakers\nクリーンな白レザースニーカー\n\nPure white leather. No logos. Just clean design.\n真っ白なレザーの美しさ。\nThe only white sneakers you need.\n\n#fashion #ファッション #sneakers #white #leather #白スニーカー #スニーカー #シューズ #minimal #kicks",
    },
    {
        "prompt": "Aesthetic product photo of brown suede Chelsea boots with elastic side panels, placed on weathered wooden surface with dried autumn leaves scattered around, warm side lighting, British heritage brand aesthetic, showing suede texture detail, 8K",
        "caption": "Suede Chelsea Boots\nスエードチェルシーブーツ\n\nRich brown suede with a timeless silhouette.\n深みのあるスエードが上品。\nOne pair, endless outfits.\n\n#fashion #ファッション #chelseaboots #suede #brown #チェルシーブーツ #ブーツ #シューズ #autumn #classic",
    },
    {
        "prompt": "Stylish product photo of chunky white platform sneakers with thick rubber sole, placed on pink background, overhead angle showing the sole design, trendy Y2K inspired aesthetic, clean bright studio lighting, 8K",
        "caption": "Chunky Platform Sneakers\nチャンキー厚底スニーカー\n\nBold sole. Big statement. Light as air.\n存在感のある厚底で脚長効果。\nWalk taller, feel bolder.\n\n#fashion #ファッション #platform #sneakers #chunky #厚底 #スニーカー #シューズ #トレンド #cute",
    },
    {
        "prompt": "Beautiful product photo of tan leather strappy sandals with gold buckle details, placed on white sand with a seashell beside them, warm golden sunset light, summer resort fashion aesthetic, 8K",
        "caption": "Gold Buckle Sandals\nゴールドバックルサンダル\n\nTan leather meets gold hardware. Summer luxury.\nゴールド金具がリゾート感。\nYour feet deserve these.\n\n#fashion #ファッション #sandals #leather #summer #サンダル #シューズ #ゴールド #リゾート #夏",
    },
    # === アウター ===
    {
        "prompt": "Premium product photo of a beige oversized trench coat with classic double-breasted design, belt detail, hung on a wooden coat stand in a minimalist white room, soft morning light from large window, luxury outerwear brand aesthetic, fabric texture visible, 8K",
        "caption": "Classic Trench Coat\nクラシックトレンチコート\n\nTimeless double-breasted design in perfect beige.\n完璧なベージュの永遠の定番。\nThe coat that goes with everything.\n\n#fashion #ファッション #trenchcoat #beige #classic #トレンチ #アウター #コート #定番 #お洒落さんと繋がりたい",
    },
    {
        "prompt": "Stylish product photo of a navy MA-1 bomber jacket with orange lining visible at collar, matte nylon fabric, laid flat on industrial metal surface, overhead angle, moody directional lighting, streetwear brand aesthetic, 8K",
        "caption": "Navy MA-1 Bomber\nネイビーMA-1ボンバー\n\nClassic MA-1 with signature orange lining.\nオレンジ裏地がチラ見えするのがたまらない。\nStreet classic, forever.\n\n#fashion #ファッション #MA1 #bomber #navy #ボンバージャケット #アウター #ストリート #cool #定番",
    },
    {
        "prompt": "Aesthetic product photo of a cropped cream puffer jacket with matte finish, soft puffy texture, hanging on a clear acrylic hanger against pale blue wall, bright winter daylight, cute and cozy outerwear aesthetic, 8K",
        "caption": "Cropped Cream Puffer\nクロップドクリームパファー\n\nShort length keeps the silhouette balanced and cute.\nショート丈で可愛く防寒。\nStay warm without the bulk.\n\n#fashion #ファッション #puffer #cream #cropped #ダウン #アウター #冬服 #cute #防寒",
    },
    {
        "prompt": "Product photo of a black leather biker jacket with silver hardware and asymmetric zip, displayed on a matte black mannequin torso against dark grey background, dramatic side lighting highlighting leather texture, rock fashion aesthetic, 8K",
        "caption": "Leather Biker Jacket\nレザーバイカージャケット\n\nAsymmetric zip, silver hardware, rebel energy.\n斜めジップにシルバー金具。永遠のかっこよさ。\nOne jacket to rule them all.\n\n#fashion #ファッション #leather #bikerjacket #black #レザー #ジャケット #アウター #cool #rock",
    },
    # === アクセサリー ===
    {
        "prompt": "Elegant jewelry flat lay of layered gold chain necklaces in three different lengths and styles on white marble surface, soft warm window light, close-up showing chain texture and clasp details, minimal luxury aesthetic, 8K",
        "caption": "Layered Gold Chains\nレイヤードゴールドチェーン\n\nThree chains, three lengths, one perfect stack.\n重ね付けで一気にこなれ感。\nLayer up, level up.\n\n#fashion #ファッション #goldchain #necklace #layered #ゴールド #ネックレス #アクセサリー #jewelry #お洒落さんと繋がりたい",
    },
    {
        "prompt": "Aesthetic product photo of a minimalist silver watch with white dial and mesh band, placed on dark slate surface with soft reflection, clean studio lighting, close-up macro showing watch face detail, Scandinavian design aesthetic, 8K",
        "caption": "Minimal Silver Watch\nミニマルシルバーウォッチ\n\nClean dial, mesh band, Scandinavian simplicity.\n無駄のないデザインが逆に映える。\nTime looks good on you.\n\n#fashion #ファッション #watch #silver #minimal #腕時計 #シルバー #アクセサリー #ミニマル #デザイン",
    },
    {
        "prompt": "Cute flat lay photo of hair accessories set including pearl hair clips, velvet scrunchies in dusty rose and sage, and a tortoiseshell claw clip, arranged on soft pink fabric, dreamy soft lighting, aesthetic accessory photography, 8K",
        "caption": "Hair Accessory Set\nヘアアクセサリーコレクション\n\nPearl clips, velvet scrunchies, tortoiseshell claw.\nパール、ベルベット、べっ甲。全部欲しい。\nSmall details, big impact.\n\n#fashion #ファッション #hairaccessories #pearl #scrunchie #ヘアアクセ #アクセサリー #パール #cute #お洒落",
    },
    {
        "prompt": "Stylish product photo of a canvas tote bag in natural beige with a small minimalist logo print, sitting on a wooden cafe table next to a latte and a book, warm afternoon light, everyday carry lifestyle aesthetic, 8K",
        "caption": "Everyday Canvas Tote\nデイリーキャンバストート\n\nSimple canvas, endless possibilities.\nシンプルだからこそ毎日使える。\nThe bag that goes everywhere.\n\n#fashion #ファッション #totebag #canvas #minimal #トートバッグ #バッグ #アクセサリー #デイリー #シンプル",
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
