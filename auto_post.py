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
    # === トップス - ストリート / スポーツMIX ===
    {
        "prompt": "Luxury brand product photo of a black oversized hoodie with bold white three-stripe detail running down both sleeves, large embossed trefoil-style logo on chest, premium heavyweight 450gsm cotton fleece, kangaroo pocket with hidden zip, laid flat on matte black surface with dramatic studio lighting, high-end sportswear campaign aesthetic, extreme fabric texture detail visible, 8K",
        "caption": "Three-Stripe Oversized Hoodie\nスリーストライプ オーバーサイズパーカー\n\n450gsm heavyweight fleece. Bold stripe detail on sleeves.\n肉厚フリースにスリーストライプが映える。\nStreet meets luxury.\n\n#fashion #ファッション #hoodie #streetwear #stripes #パーカー #ストリート #トレンド #hype #お洒落さんと繋がりたい",
    },
    {
        "prompt": "Premium product photo of a vintage-washed burgundy track jacket with white contrast piping along sleeves and collar, retro zip-up design with stand collar, embroidered crest logo on left chest, laid on weathered leather surface, warm editorial lighting, 90s revival sportswear aesthetic, fabric texture visible, 8K",
        "caption": "Retro Track Jacket\nレトロトラックジャケット\n\nVintage wash with contrast piping. 90s vibes reborn.\nバーガンディの色落ち感がたまらない。\nThe 90s called, we kept the jacket.\n\n#fashion #ファッション #trackjacket #retro #90s #トラックジャケット #ヴィンテージ #トレンド #streetwear #cool",
    },
    {
        "prompt": "High-end product photo of a forest green oversized crewneck sweatshirt with large tonal puff-print logo across chest, ribbed cuffs and hem, premium brushed fleece interior visible at neckline, displayed on clear acrylic stand against concrete wall, moody directional lighting, luxury streetwear brand campaign, 8K",
        "caption": "Puff Print Logo Crewneck\nパフプリントロゴ クルーネック\n\nTonal puff-print logo on forest green fleece.\n立体パフプリントの存在感。\nLogo game, elevated.\n\n#fashion #ファッション #crewneck #logo #streetwear #スウェット #ロゴ #トレンド #hype #デザイン",
    },
    {
        "prompt": "Stunning product photo of a cream and black color-block varsity jacket with genuine leather sleeves, chenille letter patch on chest, snap button front, striped ribbed collar cuffs and hem, hung on vintage wooden hanger against dark wall, warm dramatic lighting showing leather grain texture, American prep meets streetwear, 8K",
        "caption": "Varsity Letterman Jacket\nバーシティ レターマンジャケット\n\nLeather sleeves x chenille patch. Campus icon.\n本革スリーブにシェニールパッチ。\nVarsity style never gets old.\n\n#fashion #ファッション #varsity #letterman #jacket #バーシティ #アメカジ #トレンド #streetwear #cool",
    },
    {
        "prompt": "Luxury product photo of a mesh-panel black jersey top with geometric cutout pattern on shoulders and back, sporty number 07 print in reflective silver, slim athletic fit, displayed flat on glossy white surface with dramatic overhead studio lighting showing mesh detail, athleisure fashion campaign, 8K",
        "caption": "Mesh Detail Jersey Top\nメッシュディテール ジャージトップ\n\nGeometric mesh panels. Reflective number print.\nスポーティなメッシュ切り替えデザイン。\nAthleisure, but make it fashion.\n\n#fashion #ファッション #jersey #mesh #athleisure #ジャージ #メッシュ #スポーツMIX #トレンド #デザイン",
    },
    {
        "prompt": "Premium product photo of an oversized tie-dye gradient hoodie fading from deep indigo to sky blue to white, heavy cotton french terry fabric, raw edge hem detail, dropped shoulders, laid flat on white marble surface, bright clean studio lighting, modern streetwear brand lookbook, 8K",
        "caption": "Gradient Tie-Dye Hoodie\nグラデーション タイダイパーカー\n\nIndigo to sky blue hand-dyed gradient.\nインディゴからスカイブルーへの美しいグラデ。\nEvery piece is one of a kind.\n\n#fashion #ファッション #tiedye #gradient #hoodie #タイダイ #パーカー #グラデーション #ストリート #unique",
    },
    # === ボトムス - トレンド ===
    {
        "prompt": "High-end product photo of black side-stripe track pants with white double-stripe detail from waist to ankle, tapered fit with zip ankle cuffs, elastic waistband with internal drawcord, technical woven fabric with slight sheen, laid flat on polished concrete floor with retro sneakers beside them, sportswear brand campaign lighting, 8K",
        "caption": "Double-Stripe Track Pants\nダブルストライプ トラックパンツ\n\nSide stripes. Zip ankles. Clean taper.\nサイドラインとジップアンクルでスポーティに。\nFrom track to street.\n\n#fashion #ファッション #trackpants #stripes #sportswear #トラックパンツ #ストリート #トレンド #テーパード #cool",
    },
    {
        "prompt": "Luxury product photo of stone wash baggy cargo jeans with oversized flap pockets on thighs, heavy denim fabric with visible selvedge detail, contrast orange stitching throughout, draped over industrial metal pipe rack, harsh directional lighting creating strong shadows, raw denim brand campaign aesthetic, 8K",
        "caption": "Baggy Cargo Denim\nバギーカーゴデニム\n\nOversized flap pockets. Contrast stitching. Raw edge.\nフラップポケットとオレンジステッチの存在感。\nDenim with an attitude.\n\n#fashion #ファッション #cargo #denim #baggy #カーゴデニム #バギー #デニム #ストリート #hype",
    },
    {
        "prompt": "Stunning product photo of olive green parachute pants with elastic toggle hem, multiple cargo pockets with velcro closures, lightweight nylon ripstop fabric with slight crinkle texture, styled on matte white surface with tactical belt coiled beside them, clean bright studio lighting, gorpcore fashion trend, 8K",
        "caption": "Parachute Cargo Pants\nパラシュートカーゴパンツ\n\nToggle hem. Ripstop nylon. Gorpcore essential.\nトグルヘムでシルエット自在。\nThe pants everyone is wearing right now.\n\n#fashion #ファッション #parachutepants #gorpcore #cargo #パラシュートパンツ #ゴープコア #トレンド #ストリート #2025",
    },
    {
        "prompt": "Premium product photo of cream colored wide-leg pleated trousers with sharp center crease, high waist design with double button closure, luxury wool-blend fabric with visible herringbone weave pattern, hung on gold clothes hanger against warm beige linen backdrop, soft golden lighting, quiet luxury fashion aesthetic, 8K",
        "caption": "Herringbone Wide Trousers\nヘリンボーン ワイドトラウザー\n\nSharp crease. Herringbone weave. Quiet luxury.\nヘリンボーン織りのセンタープレス。\nUnderstated elegance speaks volumes.\n\n#fashion #ファッション #trousers #herringbone #quietluxury #トラウザー #ワイドパンツ #きれいめ #上品 #トレンド",
    },
    {
        "prompt": "High-end product photo of a black satin midi skirt with high slit on left side, invisible zip closure, liquid-like fabric sheen catching studio light, draped over clear acrylic chair against dark background, dramatic moody side lighting, minimalist luxury brand aesthetic, 8K",
        "caption": "Satin Slit Midi Skirt\nサテンスリット ミディスカート\n\nLiquid satin with a daring high slit.\n光沢サテンの大胆スリット。\nDay to night in one piece.\n\n#fashion #ファッション #satin #midi #skirt #サテン #スカート #ミディ #モード #トレンド",
    },
    # === シューズ - ハイプ ===
    {
        "prompt": "Premium sneaker product photo of retro running shoes in grey suede and mesh upper with three side stripes in white, chunky gum rubber outsole, vintage-style tongue label, placed on reflective dark surface with dramatic rim lighting showing material details, sneaker campaign style, close-up from 45 degree angle, 8K",
        "caption": "Retro Runner - Grey Suede\nレトロランナー グレースエード\n\nSuede and mesh upper. Gum sole. Classic lines.\nスエード×メッシュにガムソール。\nThe retro runner making a comeback.\n\n#fashion #ファッション #sneakers #retrorunner #suede #スニーカー #レトロ #ガムソール #kicks #トレンド",
    },
    {
        "prompt": "Luxury sneaker photo of chunky basketball-inspired high-tops in white leather with perforated toe box, padded high collar, oversized tongue with bold branding tab, thick sculpted midsole with visible air cushion, displayed on glass shelf with dramatic under-lighting, premium sneaker brand campaign, 8K",
        "caption": "Chunky Basketball High-Tops\nチャンキー バスケットハイトップ\n\nPadded collar. Air cushion sole. Court to street.\nボリュームソールにパッド入りカラー。\nBig shoes, bigger statement.\n\n#fashion #ファッション #hightops #basketball #chunky #ハイトップ #スニーカー #バッシュ #hype #kicks",
    },
    {
        "prompt": "Stunning product photo of black and white panda dunk low-top sneakers, smooth leather upper with contrasting color blocking, flat rubber sole, clean stitching detail visible, placed on raw concrete block with harsh studio lighting from above, hype sneaker release photography, 8K",
        "caption": "Panda Colorblock Lows\nパンダカラーブロック ローカット\n\nBlack and white leather. Clean. Iconic.\n白×黒のカラーブロック。永遠の定番。\nThe pair that goes with literally everything.\n\n#fashion #ファッション #sneakers #panda #colorblock #ローカット #スニーカー #モノトーン #定番 #hype",
    },
    {
        "prompt": "Premium product photo of beige suede hiking boots with chunky vibram-style lug sole, padded ankle collar, metal D-ring lace eyelets, GORE-TEX style waterproof tag detail, placed on moss-covered rock with fern leaves, outdoor adventure meets fashion, warm natural lighting, gorpcore aesthetic, 8K",
        "caption": "Lug Sole Hiking Boots\nラグソール ハイキングブーツ\n\nChunky lug sole. Waterproof. Trail to city.\n本格アウトドア仕様を街で履く。\nGorpcore at its finest.\n\n#fashion #ファッション #hikingboots #gorpcore #outdoor #ハイキングブーツ #アウトドア #ゴープコア #boots #トレンド",
    },
    # === アウター - ブランド風 ===
    {
        "prompt": "Luxury product photo of a black puffer jacket with matte nylon shell and all-over debossed monogram pattern, oversized fit, high funnel neck with hidden hood, two-way zip front, displayed on matte black mannequin torso against dark charcoal background, dramatic studio lighting catching the debossed texture, luxury streetwear brand campaign, 8K",
        "caption": "Monogram Debossed Puffer\nモノグラム デボスドパファー\n\nAll-over debossed monogram on matte nylon.\n型押しモノグラムの贅沢ディテール。\nLuxury you can feel in the dark.\n\n#fashion #ファッション #puffer #monogram #luxury #パファー #モノグラム #アウター #hype #ストリート",
    },
    {
        "prompt": "High-end product photo of an oversized cream shearling-lined denim jacket with raw frayed edges, exposed shearling at collar lapels and cuffs, vintage brass button closures, heavy 14oz selvedge denim, hung on industrial pipe rack against exposed brick wall, warm golden lighting, premium denim brand aesthetic, 8K",
        "caption": "Shearling Denim Jacket\nシアリング デニムジャケット\n\nShearling collar x raw selvedge denim. Rugged luxury.\nボア襟とセルビッジデニムの重厚感。\nWinter essential with attitude.\n\n#fashion #ファッション #denim #shearling #selvedge #ボアデニム #デニムジャケット #アウター #vintage #cool",
    },
    {
        "prompt": "Stunning product photo of a forest green waterproof windbreaker with reflective 3M tape accent strips, packable hood with toggle adjustment, half-zip pullover design with large kangaroo pocket, technical ripstop fabric, laid flat on dark surface showing reflective detail with flash photography effect, techwear outdoor brand campaign, 8K",
        "caption": "3M Reflective Windbreaker\n3Mリフレクティブ ウィンドブレーカー\n\nReflective tape glows in the dark. Packable hood.\n暗闇で光るリフレクティブテープ。\nBe seen. Stay dry. Look good.\n\n#fashion #ファッション #windbreaker #reflective #techwear #ウィンドブレーカー #リフレクティブ #アウトドア #テックウェア #機能美",
    },
    {
        "prompt": "Premium product photo of a camel wool-cashmere blend overcoat with peak lapel, double-breasted six button front, structured shoulders, full length reaching below knee, displayed on wooden coat stand in a marble-floored minimalist room, soft directional window light, Italian luxury tailoring aesthetic, fabric weave texture visible, 8K",
        "caption": "Cashmere Blend Overcoat\nカシミヤブレンド オーバーコート\n\nWool-cashmere blend. Peak lapel. Italian craft.\nカシミヤ混の極上タッチ。\nThe coat that makes the outfit.\n\n#fashion #ファッション #overcoat #cashmere #camel #オーバーコート #カシミヤ #キャメル #quietluxury #上品",
    },
    # === アクセサリー - トレンド ===
    {
        "prompt": "Luxury product photo of a crossbody mini bag in black quilted leather with gold chain strap and turn-lock closure, diamond quilting pattern with visible stitching, placed on white marble surface with gold jewelry scattered around, warm studio lighting catching the chain links, designer bag campaign aesthetic, macro detail, 8K",
        "caption": "Quilted Chain Crossbody\nキルティング チェーンクロスボディ\n\nDiamond quilt. Gold chain. Turn-lock closure.\nゴールドチェーン×キルティングの高級感。\nSmall bag, big energy.\n\n#fashion #ファッション #crossbody #quilted #goldchain #キルティング #バッグ #チェーンバッグ #トレンド #お洒落さんと繋がりたい",
    },
    {
        "prompt": "Premium product photo of a stainless steel chunky chain bracelet and matching Cuban link necklace set in silver finish, heavy substantial weight visible, displayed on dark slate stone surface with water droplets, dramatic close-up macro showing individual link detail and clasp mechanism, luxury jewelry campaign, 8K",
        "caption": "Cuban Link Chain Set\nキューバンリンク チェーンセット\n\nHeavy stainless steel. Cuban link. Silver finish.\nずっしりとしたキューバンリンクの存在感。\nStack the wrist, drip the neck.\n\n#fashion #ファッション #cubanlink #chain #silver #キューバンリンク #チェーン #アクセサリー #jewelry #hype",
    },
    {
        "prompt": "Aesthetic product photo of rectangular sport sunglasses with shield lens in gradient smoke, wraparound frame in matte black with subtle logo on temple arm, displayed on reflective chrome surface, clean studio lighting showing lens gradient detail, Y2K sport eyewear revival trend, 8K",
        "caption": "Shield Sport Sunglasses\nシールドスポーツサングラス\n\nWraparound shield lens. Y2K sport revival.\nY2Kリバイバルのシールドレンズ。\nThe future is retro.\n\n#fashion #ファッション #sunglasses #shield #Y2K #サングラス #スポーツ #Y2Kファッション #アクセサリー #トレンド",
    },
    {
        "prompt": "Stunning product photo of a structured bucket hat in premium black nylon with embroidered logo on front panel, metal eyelet vents on sides, adjustable internal drawstring, placed on white pedestal with harsh top-down studio lighting creating dramatic shadow, streetwear accessory campaign, 8K",
        "caption": "Nylon Bucket Hat\nナイロンバケットハット\n\nStructured nylon. Embroidered logo. Metal eyelets.\nメタルアイレットがアクセント。\nThe bucket hat that means business.\n\n#fashion #ファッション #buckethat #nylon #streetwear #バケハ #バケットハット #帽子 #ストリート #hype",
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
