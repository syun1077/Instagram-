"""
Instagram 完全自動投稿スクリプト
人間の操作なしで、AI画像を生成してInstagramに自動投稿する。
Windowsタスクスケジューラから呼び出して使用。
"""

import os
import sys
import json
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
from modules.insta_poster import post_to_instagram, post_carousel_to_instagram

# --- 投稿履歴管理（重複防止） ---
HISTORY_PATH = os.path.join(os.path.dirname(__file__), "post_history.json")


def load_history() -> list[int]:
    """投稿済みインデックスのリストを読み込む。"""
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_history(history: list[int]) -> None:
    """投稿済みインデックスのリストを保存する。"""
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f)


def pick_unused_post(posts: list[dict]) -> tuple[int, dict]:
    """未投稿のアイテムをランダムに選ぶ。全部投稿済みならリセット。"""
    history = load_history()
    all_indices = list(range(len(posts)))
    available = [i for i in all_indices if i not in history]

    if not available:
        logging.info("全アイテム投稿済み → 履歴リセット")
        history = []
        available = all_indices

    idx = random.choice(available)
    history.append(idx)
    save_history(history)
    logging.info(f"選択: #{idx+1}/{len(posts)} (残り{len(available)-1}件)")
    return idx, posts[idx]


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
    # === クセ強め - トップス ===
    {
        "prompt": "High-end product photo of a distressed acid wash denim shirt with bleach splatter effect, raw cut hem, oversized boxy fit, mismatched vintage-style buttons in brass and silver, heavy 12oz denim, laid flat on rusted metal surface, harsh overhead lighting creating strong contrast, punk-meets-luxury aesthetic, 8K",
        "caption": "Acid Wash Bleach Denim Shirt\nアシッドウォッシュ ブリーチデニムシャツ\n\nBleach splatter. Raw hem. Mismatched buttons.\n漂白加工とミスマッチボタンの無骨さ。\nPerfectly imperfect.\n\n#fashion #ファッション #acidwash #denim #distressed #アシッドウォッシュ #デニムシャツ #グランジ #punk #トレンド",
    },
    {
        "prompt": "Luxury product photo of a black oversized half-zip fleece pullover with contrasting neon orange zipper and zipper pull tab, sherpa texture visible, boxy cropped length hitting at waist, embroidered coordinates text on back in white, displayed on industrial chain-link backdrop, harsh flash photography, techwear gorpcore brand aesthetic, 8K",
        "caption": "Neon Zip Sherpa Pullover\nネオンジップ シェルパプルオーバー\n\nSherpa fleece x neon orange zip. Unexpected combo.\nネオンオレンジのジップがアクセント。\nOutdoor tech, city attitude.\n\n#fashion #ファッション #sherpa #fleece #neonzip #シェルパ #フリース #ゴープコア #techwear #クセ強",
    },
    {
        "prompt": "Premium product photo of a cream oversized rugby polo shirt with bold navy and maroon horizontal stripes across chest, white rubber collar, embroidered crest patch, heavyweight cotton pique fabric, draped over vintage gymnasium pommel horse, warm nostalgic lighting, preppy sport revival aesthetic, 8K",
        "caption": "Vintage Rugby Polo\nヴィンテージ ラグビーポロ\n\nBold stripes. Rubber collar. Old-school rugby energy.\nラバーカラーにボールドストライプ。\nPreppy with an edge.\n\n#fashion #ファッション #rugby #polo #preppy #ラグビーシャツ #ポロ #ヴィンテージ #スポーツMIX #クセ強",
    },
    {
        "prompt": "Stunning product photo of an oversized black mesh football jersey with glossy vinyl number 99 in chrome silver on front and back, contrast white piping at shoulders, vented mesh side panels, displayed floating against pure black background with single spotlight from above, sports luxe editorial, 8K",
        "caption": "Chrome 99 Mesh Jersey\nクローム99 メッシュジャージ\n\nVinyl chrome numbers on full mesh. Sports luxe.\n光沢クロームナンバーが主役。\nJersey culture, elevated.\n\n#fashion #ファッション #jersey #mesh #chrome #ジャージ #メッシュ #スポーツ #blokecore #hype",
    },
    {
        "prompt": "High-end product photo of a washed olive military field jacket with hand-painted abstract art splashes in white and red across the back panel, distressed brass snap buttons, multiple flap pockets, faded cotton twill fabric, hung on rusty nail against raw plywood wall, gritty editorial lighting, art-meets-military fashion, 8K",
        "caption": "Hand-Painted Military Jacket\nハンドペイント ミリタリージャケット\n\nHand-painted art on vintage military cotton.\n一点物のハンドペイントアート。\nWearable art with a military soul.\n\n#fashion #ファッション #military #handpainted #art #ミリタリー #ハンドペイント #一点物 #アート #クセ強",
    },
    # === クセ強め - ボトムス ===
    {
        "prompt": "Luxury product photo of reconstructed patchwork denim jeans made from multiple different wash shades of denim sewn together in irregular panels, exposed raw seams with orange contrast stitching, wide straight leg fit, laid flat on butcher paper surface, bright overhead studio lighting, avant-garde denim brand aesthetic, 8K",
        "caption": "Patchwork Reconstructed Denim\nパッチワーク リコンストラクトデニム\n\nMultiple washes. Raw seams. One-of-a-kind panels.\n異なるウォッシュを再構築した唯一無二のデニム。\nDenim, deconstructed.\n\n#fashion #ファッション #patchwork #denim #reconstructed #パッチワーク #デニム #リメイク #アート #unique",
    },
    {
        "prompt": "Premium product photo of black technical jogger pants with detachable cargo pocket pouches connected by carabiner clips, adjustable velcro ankle straps, waterproof ripstop nylon fabric with taped seams visible, multiple d-ring attachment points, styled on metal grid surface with tactical accessories, techwear utility brand campaign, 8K",
        "caption": "Modular Cargo Joggers\nモジュラーカーゴジョガー\n\nDetachable pouches. Carabiner clips. Full utility.\n着脱式ポーチとカラビナの機能美。\nCustomize your carry.\n\n#fashion #ファッション #techwear #modular #cargo #テックウェア #モジュラー #カーゴ #utility #機能美",
    },
    {
        "prompt": "Stunning product photo of cream corduroy flared pants with exaggerated wide flare from knee, high waist with oversized tortoiseshell belt buckle, thick 8-wale corduroy with visible texture ridges, hung on wooden pants hanger against terracotta wall, warm golden afternoon light, 70s revival fashion trend, 8K",
        "caption": "Corduroy Mega Flares\nコーデュロイ メガフレア\n\nExaggerated flare. Thick corduroy. 70s reborn.\n膝下から大胆に広がるメガフレア。\nThe 70s are back, and louder.\n\n#fashion #ファッション #corduroy #flare #70s #コーデュロイ #フレアパンツ #レトロ #ヴィンテージ #クセ強",
    },
    # === クセ強め - シューズ ===
    {
        "prompt": "High-end sneaker product photo of deconstructed chunky trail runners with exposed foam midsole in neon green, translucent mesh upper showing internal structure, mismatched lace colors in orange and purple, aggressive lug outsole, placed on cracked earth surface with dramatic side lighting, experimental sneaker design campaign, 8K",
        "caption": "Deconstructed Trail Runners\nデコンストラクト トレイルランナー\n\nExposed foam. Translucent mesh. Mismatched laces.\n内部構造が透けるトランスルーセントメッシュ。\nSneakers that break the rules.\n\n#fashion #ファッション #trailrunner #deconstructed #sneakers #トレイル #スニーカー #実験的 #デザイン #hype",
    },
    {
        "prompt": "Premium product photo of glossy black patent leather combat boots with chunky platform sole, silver metal toe cap detail, oversized silver buckle straps wrapping around ankle, yellow contrast welt stitching, placed on wet reflective black surface with water droplets, dramatic moody lighting, punk-luxury boot campaign, 8K",
        "caption": "Platform Combat Boots\nプラットフォーム コンバットブーツ\n\nPatent leather. Metal toe cap. Buckle straps.\nメタルトゥキャップにバックルストラップ。\nHeavy boots, heavy statement.\n\n#fashion #ファッション #combatboots #platform #patent #コンバットブーツ #厚底 #パンク #boots #クセ強",
    },
    {
        "prompt": "Luxury sneaker photo of retro basketball mid-tops in sail white aged leather with vintage yellowed sole, perforated toe box, ankle strap with metal snap closure, distressed scuff marks intentionally applied, placed on aged newspaper pages, warm vintage film photography aesthetic, archive sneaker revival, 8K",
        "caption": "Vintage Aged Basketball Mids\nヴィンテージエイジド バスケットミッド\n\nPre-aged leather. Yellowed sole. Worn-in character.\n経年変化を再現したエイジド加工。\nBorn vintage.\n\n#fashion #ファッション #vintage #basketball #aged #ヴィンテージ #バッシュ #エイジド #レトロ #archive",
    },
    # === クセ強め - アウター ===
    {
        "prompt": "Stunning product photo of an oversized black tactical vest with multiple molle webbing attachment points, padded shoulders, high collar with velcro name tape area, multiple zip and snap cargo pockets in different sizes, heavy duty YKK zippers, displayed on mannequin torso against urban concrete backdrop, harsh directional lighting, military tactical fashion campaign, 8K",
        "caption": "Tactical MOLLE Vest\nタクティカル モールベスト\n\nMOLLE webbing. Multiple pockets. Mission ready.\nモールシステムで拡張自在。\nStreet tactical. No missions required.\n\n#fashion #ファッション #tactical #vest #molle #タクティカル #ベスト #ミリタリー #techwear #クセ強",
    },
    {
        "prompt": "High-end product photo of a reversible bomber jacket, side A in black satin with embroidered Japanese souvenir jacket style tiger and dragon artwork in gold thread, side B in plain quilted olive nylon, displayed showing both sides simultaneously partially folded, dramatic studio lighting on dark background, sukajan revival fashion, 8K",
        "caption": "Reversible Sukajan Bomber\nリバーシブル スカジャン\n\nEmbroidered tiger x dragon. Satin x quilted nylon.\n虎と龍の刺繍が圧巻のスカジャン。\nTwo jackets in one. Flip the script.\n\n#fashion #ファッション #sukajan #スカジャン #embroidered #bomber #刺繍 #リバーシブル #和柄 #hype",
    },
    {
        "prompt": "Premium product photo of a deconstructed trench coat in beige with asymmetric hem, one sleeve in original trench fabric and other sleeve in contrasting black nylon, exposed internal seam construction, raw edge details, oversized exaggerated collar, hung on minimalist metal rack against white gallery wall, avant-garde fashion editorial lighting, 8K",
        "caption": "Deconstructed Asymmetric Trench\nデコンストラクト アシンメトリートレンチ\n\nMixed fabrics. Asymmetric hem. Exposed seams.\n左右非対称に再構築されたトレンチ。\nClassic, destroyed, rebuilt.\n\n#fashion #ファッション #deconstructed #trench #asymmetric #アシンメトリー #トレンチ #モード #avantgarde #クセ強",
    },
    # === クセ強め - アクセサリー ===
    {
        "prompt": "Luxury product photo of an oversized industrial chain necklace in brushed gunmetal finish with large padlock pendant, heavy linked chain with visible welding texture, displayed on raw concrete slab with metal shavings scattered around, dramatic harsh studio lighting, industrial punk jewelry campaign, macro detail, 8K",
        "caption": "Padlock Chain Necklace\nパドロック チェーンネックレス\n\nGunmetal chain. Padlock pendant. Industrial weight.\nガンメタルの重厚チェーンに南京錠。\nLock it down.\n\n#fashion #ファッション #padlock #chain #industrial #南京錠 #チェーン #アクセサリー #パンク #クセ強",
    },
    {
        "prompt": "Premium product photo of a crossbody chest rig bag in black cordura nylon with reflective piping, multiple front zip compartments, adjustable quick-release buckle straps, molle-style webbing on sides, displayed on dark surface with tactical accessories around it, flash photography showing reflective detail, urban utility accessory campaign, 8K",
        "caption": "Tactical Chest Rig Bag\nタクティカル チェストリグバッグ\n\nCordura nylon. Quick-release buckle. Reflective piping.\nクイックリリースバックルで着脱簡単。\nHands free, style on lock.\n\n#fashion #ファッション #chestrig #tactical #cordura #チェストバッグ #タクティカル #utility #テックウェア #hype",
    },
    {
        "prompt": "Stunning product photo of oversized wraparound visor sunglasses with gradient mirror lens shifting from blue to purple, futuristic one-piece shield design, thin titanium arms, displayed on chrome mannequin head against pure white background, clean studio lighting showing lens color shift, futuristic eyewear campaign, 8K",
        "caption": "Mirror Shield Visor\nミラーシールド バイザー\n\nGradient mirror lens. Blue to purple shift.\nブルーからパープルに変化するミラーレンズ。\nFuture-proof eyewear.\n\n#fashion #ファッション #visor #mirror #futuristic #バイザー #ミラーレンズ #サングラス #未来 #クセ強",
    },
]

# --- CTA（コールトゥアクション）テンプレート ---
CTAS = [
    "\n\n💾 Save this for your next outfit inspo!\nこのコーデ保存しておいて！",
    "\n\n🔥 Would you rock this? Comment below!\nこれ着る？コメントで教えて！",
    "\n\n👆 Double tap if this is your style!\nいいねで教えて、あなたのスタイル！",
    "\n\n📲 Share with someone who'd love this!\n好きそうな友達にシェアしてね！",
    "\n\n💬 Rate this 1-10 in the comments!\n10点満点で何点？コメントしてね！",
    "\n\n🛒 Link in bio for similar items!\nプロフィールのリンクから類似アイテムをチェック！",
    "\n\n👀 Follow for daily fashion drops!\nフォローして毎日の新作をチェック！",
    "\n\n🔖 Bookmark this for later!\nあとで見返せるように保存しておこう！",
]

# --- アフィリエイトリンク誘導テンプレート ---
AFFILIATE_CTA = (
    "\n\n🔗 Similar items → Link in bio!"
    "\n似たアイテムはプロフィールのリンクから🛒"
)


def add_cta(caption: str) -> str:
    """キャプションの末尾にランダムCTA + アフィリエイト誘導を追加する。"""
    cta = random.choice(CTAS)
    return caption + cta + AFFILIATE_CTA


# --- カルーセル用アングルバリエーション ---
ANGLE_SUFFIXES = [
    ", close-up macro detail shot showing fabric texture and stitching, 8K",
    ", styled overhead flat lay with complementary accessories around it, lifestyle photography, 8K",
    ", side angle view showing silhouette and proportions, clean white background, lookbook style, 8K",
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

        # Step 1: 未投稿のアイテムを選択（重複防止）
        idx, post = pick_unused_post(POSTS)
        prompt = post["prompt"]
        caption = add_cta(post["caption"])
        logging.info(f"プロンプト: {prompt}")
        logging.info(f"キャプション: {caption[:50]}...")

        # Step 2: AI画像生成（メイン + アングル違い2枚 = 計3枚）
        image_urls = []

        # メイン画像
        logging.info("AI画像を生成中... (1/3 メイン)")
        generate_ai_image(prompt, temp_image)
        logging.info("メイン画像生成完了")
        image_url = upload_image(temp_image)
        image_urls.append(image_url)
        logging.info(f"アップロード完了: {image_url}")

        # アングル違い画像 2枚
        for i, suffix in enumerate(random.sample(ANGLE_SUFFIXES, 2)):
            angle_prompt = prompt.rsplit(", 8K", 1)[0] + suffix
            logging.info(f"AI画像を生成中... ({i+2}/3 アングル)")
            generate_ai_image(angle_prompt, temp_image)
            url = upload_image(temp_image)
            image_urls.append(url)
            logging.info(f"アップロード完了: {url}")

        # Step 3: カルーセル投稿
        logging.info(f"Instagramにカルーセル投稿中... ({len(image_urls)}枚)")
        post_id = post_carousel_to_instagram(image_urls, caption)
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
