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
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

from modules.token_manager import auto_refresh
from modules.ai_image_generator import generate_ai_image, generate_reel_images, generate_slideshow_video
from modules.uploader import upload_image, upload_video
from modules.insta_poster import (
    post_to_instagram,
    post_carousel_to_instagram,
    post_reel_to_instagram,
    post_story_to_instagram,
)
from modules.hashtags import replace_hashtags

# 自動アンフォロー（ローカル専用、GitHub Actionsでは不要）
try:
    from modules.unfollower import unfollow_non_followers
    UNFOLLOW_AVAILABLE = True
except ImportError:
    UNFOLLOW_AVAILABLE = False

# 楽天API（実商品投稿用）
try:
    from modules.rakuten_api import pick_random_product, generate_caption as rakuten_caption
    RAKUTEN_AVAILABLE = True
except Exception:
    RAKUTEN_AVAILABLE = False

# 投稿分析モジュール
from modules.analytics import analyze_posts

# Amazon API（アフィリエイト連携）
try:
    from modules.amazon_api import (
        pick_random_product as amazon_pick_product,
        generate_caption as amazon_caption,
        generate_affiliate_link,
        _is_available as amazon_is_available,
    )
    AMAZON_AVAILABLE = amazon_is_available()
except Exception:
    AMAZON_AVAILABLE = False

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
# 高級ブランドインスパイアのデザイン。ランダムで1つ選ばれます。
POSTS = [
    # === トップス - ハイブランドインスパイア ===
    {
        "prompt": "Luxury product photo of a black oversized hoodie with bold diagonal white stripes crossing the front and industrial yellow caution tape-style belt strap hanging from the waist, raw cut asymmetric hem, heavyweight 500gsm cotton, large arrow graphic print on back in white, laid flat on matte black marble surface, dramatic directional studio lighting, high fashion streetwear campaign, 8K",
        "caption": "Diagonal Arrow Oversized Hoodie\nダイアゴナルアロー オーバーサイズパーカー\n\nIndustrial tape detail. Arrow print. 500gsm weight.\nインダストリアルテープと矢印プリントの融合。\nWhere the street meets the runway.\n\n#fashion #ファッション #hoodie #oversized #avantgarde #パーカー #ストリート #モード #highfashion #お洒落さんと繋がりたい",
    },
    {
        "prompt": "High-end product photo of a deconstructed oversized blazer in black with exposed white basting stitches running along seams, four-stitch white thread detail on back, no buttons, raw edge lapels, slightly shrunken left sleeve revealing the lining, draped over clear acrylic mannequin against grey concrete wall, avant-garde fashion house editorial lighting, 8K",
        "caption": "Deconstructed Four-Stitch Blazer\nデコンストラクト フォーステッチブレザー\n\nExposed basting. Raw lapels. Intentionally unfinished.\nあえて未完成に仕上げた脱構築の美学。\nThe art of imperfection.\n\n#fashion #ファッション #blazer #deconstructed #avantgarde #ブレザー #脱構築 #モード #highfashion #デザイン",
    },
    {
        "prompt": "Luxury product photo of a black oversized distressed hoodie with multiple intentional rips and holes across the front, faded logo print barely visible underneath layers of distressing, extremely dropped shoulders hitting mid-arm, extra long sleeves with thumbholes, heavyweight washed cotton with vintage feel, laid flat on industrial concrete floor, harsh overhead light creating deep shadows in the rips, luxury grunge aesthetic, 8K",
        "caption": "Destroyed Luxury Hoodie\nデストロイド ラグジュアリーパーカー\n\nIntentional rips. Faded prints. Washed-out luxury.\nダメージ加工に隠されたラグジュアリー。\nBeautifully broken.\n\n#fashion #ファッション #destroyed #hoodie #luxury #ダメージ #パーカー #グランジ #highfashion #hype",
    },
    {
        "prompt": "Premium product photo of an oversized pitch black long sleeve t-shirt with draped cowl neckline, elongated body reaching mid-thigh, asymmetric raw hem cut at a dramatic angle, double layered front panel creating depth, matte jersey fabric with subtle ribbed texture, displayed on jet black mannequin against pure black background with single harsh side light, dark avant-garde fashion, 8K",
        "caption": "Draped Cowl Long Tee\nドレープカウル ロングT\n\nAsymmetric hem. Cowl neck. Layered panels.\n異素材レイヤードの立体ドレープ。\nDarkness as a design language.\n\n#fashion #ファッション #darkfashion #drape #avantgarde #ドレープ #モード #黒 #darkwear #デザイン",
    },
    {
        "prompt": "Stunning product photo of a cream white oversized knit sweater with visible intrecciato-style woven texture across the entire body, thick chunky yarn showing each weave intersection clearly, ribbed mock neck, dropped shoulders, laid on warm beige linen surface, soft golden window light, quiet luxury Italian craftsmanship aesthetic, 8K",
        "caption": "Intrecciato Weave Knit\nイントレチャート ウィーブニット\n\nSignature woven texture. Chunky yarn. Quiet luxury.\n編み込みテクスチャーが主役の贅沢ニット。\nCraftsmanship you can see and feel.\n\n#fashion #ファッション #knit #woven #quietluxury #ニット #編み込み #イタリア #craftsmanship #上品",
    },
    {
        "prompt": "High-end product photo of a black technical nylon re-nylon shirt jacket with pointed collar, concealed snap button front, triangular enamel logo badge on chest pocket, lightweight crinkled recycled nylon fabric with slight sheen, displayed on minimalist chrome hanger against white gallery wall, clean modernist studio lighting, Italian technical luxury aesthetic, 8K",
        "caption": "Re-Nylon Technical Shirt\nリナイロン テクニカルシャツ\n\nRecycled nylon. Triangle badge. Technical luxury.\nリサイクルナイロンの光沢と三角ロゴの存在感。\nSustainability meets sophistication.\n\n#fashion #ファッション #nylon #technical #luxury #ナイロン #テクニカル #サステナブル #イタリア #モード",
    },
    {
        "prompt": "Luxury product photo of a double-layered sheer organza shirt in black with solid black tank underneath visible through translucent fabric, oversized boxy fit, mother of pearl buttons, French cuffs, delicate fabric catching light showing weave pattern, hung on black velvet hanger against smoky grey backdrop, moody editorial lighting, haute couture ready-to-wear aesthetic, 8K",
        "caption": "Sheer Organza Layered Shirt\nシアーオーガンザ レイヤードシャツ\n\nTranslucent organza over solid tank. Pearl buttons.\n透けるオーガンザが生む奥行き。\nRevealing without revealing.\n\n#fashion #ファッション #sheer #organza #layered #シアー #オーガンザ #レイヤード #モード #hautecouture",
    },
    {
        "prompt": "Premium product photo of an oversized grey marl hoodie with the entire front printed with a large trompe-l'oeil photorealistic tuxedo jacket design including lapels, pocket square, and boutonniere, heavyweight cotton fleece, regular kangaroo pocket hidden within the print, laid flat on polished marble, bright clean studio lighting, conceptual fashion brand campaign, 8K",
        "caption": "Trompe L'oeil Tuxedo Hoodie\nトロンプルイユ タキシードパーカー\n\nPhotorealistic tuxedo print on a hoodie. Formal meets casual.\nだまし絵タキシードをパーカーに。\nBlack tie? More like black hoodie.\n\n#fashion #ファッション #trompeoeil #tuxedo #hoodie #トロンプルイユ #パーカー #コンセプト #ユニーク #hype",
    },
    # === ボトムス - ハイブランドインスパイア ===
    {
        "prompt": "Luxury product photo of extremely oversized wide-leg jeans in washed medium blue denim with exaggerated 40-inch leg opening, high waist with double button, heavy 14oz rigid denim with raw selvedge hem dragging on floor, industrial metal rivets, draped over chrome pipe rack casting dramatic shadows, runway denim editorial lighting, 8K",
        "caption": "Ultra Wide-Leg Runway Denim\nウルトラワイドレッグ ランウェイデニム\n\nExtreme 40-inch leg opening. Raw selvedge. Heavy rigid denim.\n40インチの圧巻フレア。ランウェイから街へ。\nDenim taken to the absolute extreme.\n\n#fashion #ファッション #widelegdenim #runway #selvedge #ワイドデニム #ランウェイ #デニム #モード #avantgarde",
    },
    {
        "prompt": "High-end product photo of tailored black wool trousers with integrated leather belt that wraps and buckles at the front, sharp pressed crease, slightly cropped ankle length, slant pockets with leather trim, premium Italian virgin wool with visible diagonal twill weave, hung on gold hanger against cream backdrop, soft diffused studio lighting, quiet luxury tailoring aesthetic, 8K",
        "caption": "Integrated Belt Wool Trousers\nインテグレーテッドベルト ウールトラウザー\n\nBuilt-in leather belt. Italian virgin wool. Sharp crease.\n一体型レザーベルトのミニマル美。\nTailoring that speaks for itself.\n\n#fashion #ファッション #trousers #tailored #wool #テーラード #トラウザー #quietluxury #イタリア #ミニマル",
    },
    {
        "prompt": "Stunning product photo of black track pants with tuxedo-style satin side stripe running from waist to ankle, elasticated waist with drawcord, tapered slim fit, technical jersey fabric with four-way stretch, subtle tonal logo embroidery on thigh, laid flat on polished black surface with patent leather shoes beside, luxury athleisure editorial, 8K",
        "caption": "Satin Stripe Tuxedo Track Pants\nサテンストライプ タキシードトラックパンツ\n\nTuxedo satin stripe on tech jersey. Formal x athletic.\nタキシードのサテンラインをトラックパンツに。\nRed carpet from the waist down.\n\n#fashion #ファッション #trackpants #satin #tuxedo #トラックパンツ #サテン #アスレジャー #luxurysport #モード",
    },
    {
        "prompt": "Luxury product photo of sky blue leather trousers in butter-soft lambskin, straight relaxed fit, high waist with wide waistband, tonal stitching throughout, visible grain texture of premium leather, displayed draped over brutalist concrete bench, cool blue-toned studio lighting, Italian luxury leather goods campaign, macro detail of leather grain visible, 8K",
        "caption": "Lambskin Leather Trousers\nラムスキン レザートラウザー\n\nButter-soft lambskin. Sky blue. Tonal stitching.\nバターのように柔らかいラムスキン。\nLuxury you can touch through the screen.\n\n#fashion #ファッション #leather #lambskin #trousers #レザー #ラムスキン #トラウザー #luxury #イタリア",
    },
    {
        "prompt": "Premium product photo of black nylon parachute cargo pants with multiple oversized 3D pockets protruding from thighs and calves, adjustable toggle drawstring at hem and knees, technical waterproof coating visible as slight sheen, heavy duty metal zipper details, styled on dark metal grid surface, harsh industrial lighting, functional luxury techwear aesthetic, 8K",
        "caption": "3D Pocket Technical Cargo\n3Dポケット テクニカルカーゴ\n\nOversized 3D pockets. Toggle adjustable. Waterproof nylon.\n立体ポケットが生む圧倒的な存在感。\nUtility elevated to art.\n\n#fashion #ファッション #cargo #techwear #3Dpocket #カーゴパンツ #テックウェア #機能美 #luxury #モード",
    },
    # === シューズ - ハイブランドインスパイア ===
    {
        "prompt": "Luxury sneaker product photo of chunky platform sneakers in triple white leather with exaggerated 4-inch sculpted sole, multiple layered panels with perforations, oversized tongue with embossed logo, visible air unit in heel, placed on white marble pedestal with dramatic under-lighting showing sole architecture, luxury sneaker campaign, close-up 45 degree angle, 8K",
        "caption": "Sculpted Platform Sneakers\nスカルプテッド プラットフォームスニーカー\n\nExaggerated 4-inch sole. Sculpted architecture. Triple white.\n4インチの彫刻的ソール。存在感の塊。\nWalking on art.\n\n#fashion #ファッション #platformsneakers #chunky #luxury #厚底 #スニーカー #プラットフォーム #hype #highfashion",
    },
    {
        "prompt": "High-end product photo of split-toe tabi boots in black calfskin leather, distinctive divided toe design, cylindrical block heel, back zip closure, smooth leather with subtle natural creases, placed on polished dark wood surface with single dramatic spotlight from above, avant-garde Japanese fashion house aesthetic, 8K",
        "caption": "Tabi Split-Toe Boots\nタビ スプリットトゥブーツ\n\nIconic split-toe silhouette. Calfskin leather. Block heel.\n足袋の伝統を現代ファッションに昇華。\nThe shoe that changed fashion.\n\n#fashion #ファッション #tabi #boots #splittoe #タビブーツ #足袋 #avantgarde #Japanese #モード",
    },
    {
        "prompt": "Stunning product photo of sock-style speed runner sneakers in all black knit upper that extends to mid-calf, seamless one-piece construction, bold white oversized logo text on outer side, chunky clear rubber sole with aggressive tread pattern, displayed on reflective black surface showing sole detail, luxury sportswear campaign lighting, 8K",
        "caption": "Speed Knit Sock Runners\nスピードニット ソックランナー\n\nSeamless knit upper. Bold logo. Clear chunky sole.\nシームレスニットの未来的フォルム。\nSpeed has a new shape.\n\n#fashion #ファッション #sockrunner #speedtrainer #knit #ソックスニーカー #ニット #ランナー #luxury #hype",
    },
    {
        "prompt": "Premium product photo of oversized chunky sole derby shoes in polished black leather with exaggerated 3-inch commando rubber lug sole, round toe, contrast yellow welt stitching, metal eyelet lacing, placed on rough hewn wooden block with dramatic side lighting showing sole thickness and leather shine, British luxury meets punk aesthetic, 8K",
        "caption": "Mega Sole Derby Shoes\nメガソール ダービーシューズ\n\nPolished leather. 3-inch lug sole. Yellow welt.\n極厚ラグソールにイエローウェルトの存在感。\nClassic shoes, extreme soles.\n\n#fashion #ファッション #derby #lugsole #polished #ダービー #厚底 #ブリティッシュ #パンク #革靴",
    },
    {
        "prompt": "Luxury product photo of minimalist white leather slide sandals with chunky padded quilted strap across the top, signature intrecciato-style woven leather texture on strap, molded rubber footbed, thick platform sole, displayed on white marble slab with soft shadow, warm clean studio lighting, Italian resort luxury aesthetic, macro detail showing weave pattern, 8K",
        "caption": "Woven Leather Platform Slides\nウーブンレザー プラットフォームスライド\n\nIntrecciato weave strap. Padded quilted leather. Chunky sole.\n編み込みレザーのラグジュアリーサンダル。\nPool to dinner. Effortlessly.\n\n#fashion #ファッション #slides #woven #leather #スライド #サンダル #レザー #イタリア #quietluxury",
    },
    # === アウター - ハイブランドインスパイア ===
    {
        "prompt": "Luxury product photo of an oversized cocoon-shaped puffer jacket in matte black with exaggerated volume, high neck covering chin, no visible logo, minimalist design with hidden snap closure, premium matte nylon shell with ultra-lightweight down fill, displayed on faceless mannequin against pure white background, clean bright studio lighting emphasizing the sculptural silhouette, luxury outerwear campaign, 8K",
        "caption": "Cocoon Sculpted Puffer\nコクーン スカルプテッドパファー\n\nExaggerated volume. No logo. Pure silhouette.\n究極のミニマル。ロゴなし、シルエットで語る。\nVolume is the new luxury.\n\n#fashion #ファッション #puffer #cocoon #minimalist #パファー #コクーン #ミニマル #シルエット #quietluxury",
    },
    {
        "prompt": "High-end product photo of a black hybrid coat combining trench coat top with padded puffer bottom section, contrasting materials of gabardine and quilted nylon meeting at waist with visible zipper separation, belt at waist, oversized proportions, hung on sleek metal coat stand against dark grey backdrop, moody directional studio lighting, Japanese avant-garde hybrid fashion editorial, 8K",
        "caption": "Hybrid Trench-Puffer Coat\nハイブリッド トレンチパファーコート\n\nTrench top. Puffer bottom. Two worlds merged.\nトレンチとパファーの異素材ハイブリッド。\nWhy choose when you can have both?\n\n#fashion #ファッション #hybrid #trench #puffer #ハイブリッド #トレンチ #パファー #avantgarde #Japanese",
    },
    {
        "prompt": "Stunning product photo of a long black leather trench coat in supple calfskin, double-breasted with oversized horn buttons, wide pointed lapels, matching leather belt with silver hardware, full length reaching ankle, slight A-line silhouette, displayed on tall mannequin against industrial concrete wall, cinematic lighting creating long shadow, luxury leather goods campaign, 8K",
        "caption": "Calfskin Leather Trench\nカーフスキン レザートレンチ\n\nFull-length calfskin. Horn buttons. Silver hardware.\nカーフスキンの贅沢ロングトレンチ。\nThe ultimate power coat.\n\n#fashion #ファッション #leathertrench #calfskin #luxury #レザートレンチ #カーフスキン #高級 #パワー #モード",
    },
    {
        "prompt": "Premium product photo of an oversized wool-blend bomber jacket in camel with contrast black ribbed collar, cuffs and hem, signature oblique jacquard pattern woven into the fabric visible at certain angles, two-way gold zipper, slash pockets with leather trim, displayed on wooden torso form against warm neutral backdrop, editorial golden hour lighting, French luxury house aesthetic, 8K",
        "caption": "Oblique Jacquard Bomber\nオブリーク ジャカードボンバー\n\nHidden jacquard pattern. Wool-blend. Gold hardware.\n光の角度で浮かぶジャカード織り。\nSubtlety is the ultimate sophistication.\n\n#fashion #ファッション #bomber #jacquard #wool #ボンバー #ジャカード #キャメル #luxury #フレンチ",
    },
    {
        "prompt": "Luxury product photo of a reversible padded vest in sage green quilted nylon on side A and compass-patch arm badge with black shell on side B, stand collar with chin guard, internal jersey lining visible at armhole, heavy duty double zip front, placed on outdoor wooden fence post with autumn forest background blurred, adventure meets luxury editorial lighting, 8K",
        "caption": "Compass Badge Reversible Vest\nコンパスバッジ リバーシブルベスト\n\nReversible. Compass patch. Quilted nylon.\nコンパスバッジの機能美を2WAYで。\nOne vest, two identities.\n\n#fashion #ファッション #vest #reversible #compass #ベスト #リバーシブル #アウトドア #機能美 #luxury",
    },
    # === バッグ - ハイブランドインスパイア ===
    {
        "prompt": "Luxury product photo of a structured mini crossbody bag in black calfskin leather with signature woven intrecciato texture covering entire surface, gold-tone metal knot closure, adjustable thin leather shoulder strap, displayed on white marble pedestal with single warm spotlight from above creating soft shadow, Italian luxury leather goods campaign, extreme macro detail of weave visible, 8K",
        "caption": "Intrecciato Mini Crossbody\nイントレチャート ミニクロスボディ\n\nHand-woven calfskin. Knot closure. Italian craft.\n職人の手編みが生む唯一無二のテクスチャー。\nThe bag that defines quiet luxury.\n\n#fashion #ファッション #intrecciato #crossbody #leather #イントレチャート #バッグ #レザー #職人技 #quietluxury",
    },
    {
        "prompt": "High-end product photo of a black nylon backpack with reinforced triangular metal logo plate on front flap, padded adjustable straps, multiple compartments with smooth silver zippers, re-nylon recycled material with slight sheen, displayed against clean white background with dramatic side lighting showing the triangular plate catching light, Italian minimalist luxury accessory campaign, 8K",
        "caption": "Triangle Logo Nylon Backpack\nトライアングルロゴ ナイロンバックパック\n\nTriangle plate. Re-nylon. Multiple compartments.\nトライアングルプレートのアイコニックな存在感。\nMinimal design, maximum impact.\n\n#fashion #ファッション #backpack #nylon #triangle #バックパック #ナイロン #ミニマル #luxury #イタリア",
    },
    {
        "prompt": "Stunning product photo of a large soft leather tote bag in smooth butter cream calfskin with no visible logos or hardware, magnetic closure hidden under the fold, unstructured slouchy shape that drapes naturally, clean unlined interior visible, placed casually on cream linen sofa in sunlit room, warm natural afternoon light, whisper-quiet luxury aesthetic, extreme leather texture detail, 8K",
        "caption": "Unstructured Leather Tote\nアンストラクチャード レザートート\n\nNo logos. No hardware. Pure leather.\nロゴもハードウェアもない、究極の引き算。\nLuxury doesn't need to announce itself.\n\n#fashion #ファッション #tote #leather #nologo #トート #レザー #ノーロゴ #quietluxury #ミニマル",
    },
    {
        "prompt": "Premium product photo of a small structured saddle bag in cognac calfskin leather with large antique brass CD-style monogram buckle on front flap, adjustable canvas and leather shoulder strap with embroidered pattern, hand-stitched edges visible, placed on dark wood table with vintage books and dried flowers, warm romantic editorial lighting, French luxury heritage aesthetic, 8K",
        "caption": "Monogram Buckle Saddle Bag\nモノグラムバックル サドルバッグ\n\nAntique brass buckle. Hand-stitched. Heritage canvas strap.\nアンティーク真鍮バックルの風格。\nHeritage reimagined.\n\n#fashion #ファッション #saddlebag #monogram #heritage #サドルバッグ #モノグラム #ヘリテージ #フレンチ #luxury",
    },
    # === アクセサリー - ハイブランドインスパイア ===
    {
        "prompt": "Luxury product photo of oversized cat-eye sunglasses in glossy black acetate with thick bold frame, gold metal interlocking logo detail on temple arms, gradient grey lenses, displayed on white marble with gold chain necklace and lipstick beside it, warm glamorous studio lighting, Italian luxury eyewear campaign, extreme detail on hinge mechanism visible, 8K",
        "caption": "Bold Cat-Eye Sunglasses\nボールドキャットアイ サングラス\n\nOversized cat-eye. Gold temple detail. Gradient lens.\nゴールドロゴが輝くキャットアイフレーム。\nIconic frames. Iconic energy.\n\n#fashion #ファッション #cateye #sunglasses #bold #キャットアイ #サングラス #ゴールド #luxury #アイウェア",
    },
    {
        "prompt": "High-end product photo of a silk twill square scarf in vibrant orange and blue with intricate equestrian horse and carriage print, hand-rolled edges visible, displayed partially draped showing both the print detail and the silk texture catching light, placed on cream leather surface, warm studio lighting, French luxury heritage maison campaign, 8K",
        "caption": "Equestrian Print Silk Scarf\nエケストリアンプリント シルクスカーフ\n\nHand-rolled silk twill. Equestrian motif. Heritage print.\n馬車モチーフの手巻きシルク。\nOne scarf, infinite ways to style.\n\n#fashion #ファッション #silkscarf #equestrian #heritage #シルクスカーフ #エケストリアン #フレンチ #luxury #上品",
    },
    {
        "prompt": "Stunning product photo of heavy sterling silver gothic cross pendant necklace on thick curb chain, cross decorated with floral scroll engravings and small garnet stones at each point, darkened oxidized patina on silver, displayed on black velvet cushion with dramatic single spotlight, luxury gothic jewelry campaign, extreme macro detail of engravings, 8K",
        "caption": "Gothic Scroll Cross Pendant\nゴシックスクロール クロスペンダント\n\nSterling silver. Floral scroll. Garnet accents.\n彫刻とガーネットが輝くゴシッククロス。\nFaith, fashion, and edge.\n\n#fashion #ファッション #gothic #cross #silver #ゴシック #クロス #シルバー #ペンダント #jewelry",
    },
    {
        "prompt": "Premium product photo of a wide leather belt in glossy black patent leather with oversized ornate gold baroque-style double-letter logo buckle, belt width approximately 4cm, polished gold hardware throughout, displayed coiled on black glass surface with dramatic studio lighting catching the buckle reflection, Italian luxury accessories campaign, 8K",
        "caption": "Baroque Logo Leather Belt\nバロックロゴ レザーベルト\n\nOversized baroque buckle. Patent leather. Gold hardware.\n大振りバロックバックルの圧倒的存在感。\nThe buckle that stops traffic.\n\n#fashion #ファッション #belt #baroque #logo #ベルト #バロック #ゴールド #パテント #luxury",
    },
    {
        "prompt": "Luxury product photo of a pair of black leather gloves in butter-soft lambskin with quilted diamond pattern on back of hand and smooth palm, cashmere lining visible at wrist opening, small gold logo snap button at wrist, displayed on dark grey slate surface with single red rose beside, moody romantic editorial lighting, French luxury accessories campaign, 8K",
        "caption": "Quilted Lambskin Gloves\nキルティング ラムスキングローブ\n\nDiamond quilt. Cashmere lined. Lambskin leather.\nカシミヤライニングとラムスキンの贅沢。\nLuxury at your fingertips.\n\n#fashion #ファッション #gloves #quilted #lambskin #グローブ #キルティング #ラムスキン #カシミヤ #luxury",
    },
    # === ジュエリー - ハイブランドインスパイア ===
    {
        "prompt": "High-end product photo of a chunky gold-tone chain bracelet with large medusa-style medallion charm dangling from it, polished high-shine finish, heavy substantial weight visible, toggle clasp closure, displayed on black obsidian stone with water droplets, dramatic spotlight creating golden reflections, Italian luxury jewelry campaign, extreme macro detail, 8K",
        "caption": "Medallion Chain Bracelet\nメダリオン チェーンブレスレット\n\nMedusa medallion. Chunky gold chain. Toggle clasp.\n重厚感あるメダリオンチェーン。\nPower on your wrist.\n\n#fashion #ファッション #medallion #bracelet #gold #メダリオン #ブレスレット #ゴールド #チェーン #luxury",
    },
    {
        "prompt": "Stunning product photo of minimalist gold vermeil ring set of three stackable thin bands, one plain polished, one with tiny pave-set cubic zirconia stones, one twisted rope texture, displayed on a small ceramic dish against soft pink backdrop, warm diffused studio lighting showing the sparkle of stones, Scandinavian minimalist jewelry aesthetic, 8K",
        "caption": "Stackable Gold Ring Set\nスタッカブル ゴールドリングセット\n\nThree textures. Gold vermeil. Everyday elegance.\nポリッシュ、パヴェ、ロープの3テクスチャー。\nStack, mix, express yourself.\n\n#fashion #ファッション #rings #stackable #gold #リング #重ね付け #ゴールド #ミニマル #everyday",
    },
    {
        "prompt": "Premium product photo of oversized hoop earrings in brushed gold with subtle hammered texture, 5cm diameter, lightweight hollow construction, displayed hanging from thin gold rod against deep navy velvet background, warm golden studio lighting catching the hammered texture details, luxury artisan jewelry campaign, 8K",
        "caption": "Hammered Gold Hoops\nハンマード ゴールドフープ\n\nOversized 5cm hoops. Hammered texture. Brushed gold.\nハンマー加工のゴールドフープイヤリング。\nThe earrings that frame your face.\n\n#fashion #ファッション #hoops #gold #hammered #フープ #ゴールド #イヤリング #artisan #luxury",
    },
    # === トップス - 追加 ===
    {
        "prompt": "Luxury product photo of a cropped boxy varsity jacket in cream wool with black leather sleeves, oversized chenille letter patch on chest, striped ribbed collar and cuffs, brass snap buttons, displayed on black metal hanger against gymnasium locker backdrop, warm nostalgic editorial lighting, American prep meets luxury streetwear, 8K",
        "caption": "Varsity Leather Sleeve Jacket\nバーシティ レザースリーブジャケット\n\nChenille patch. Leather sleeves. Brass snaps.\nレザースリーブのヴァーシティジャケット。\nCampus royalty.\n\n#fashion #ファッション #varsity #leather #preppy #バーシティ #レザー #アメカジ #highfashion #ストリート",
    },
    {
        "prompt": "High-end product photo of a black mesh layered long sleeve top, sheer technical mesh outer layer over solid ribbed tank, visible double-layer construction, thumbhole cuffs, slim elongated fit, displayed on glass mannequin against smoke grey background, dramatic backlit studio lighting showing mesh transparency, dark avant-garde aesthetic, 8K",
        "caption": "Mesh Layered Long Sleeve\nメッシュレイヤード ロングスリーブ\n\nSheer mesh over ribbed tank. Double layer. Thumbholes.\n透けるメッシュが生む奥行きと陰影。\nLayered darkness.\n\n#fashion #ファッション #mesh #layered #darkfashion #メッシュ #レイヤード #黒 #avantgarde #モード",
    },
    {
        "prompt": "Premium product photo of a boxy cropped cable knit cardigan in sage green with oversized mother of pearl buttons, deep V-neck, chunky twisted cable pattern across front and sleeves, slightly fuzzy mohair blend texture, displayed flat on natural linen surface with dried eucalyptus stems, warm soft natural light, Scandinavian cozy luxury aesthetic, 8K",
        "caption": "Cable Knit Mohair Cardigan\nケーブルニット モヘアカーディガン\n\nChunky cable knit. Mohair blend. Pearl buttons.\nモヘアブレンドの上質ケーブルニット。\nCozy never looked this good.\n\n#fashion #ファッション #cardigan #cableknit #mohair #カーディガン #ニット #モヘア #北欧 #quietluxury",
    },
    {
        "prompt": "Luxury product photo of an oversized striped rugby polo in navy and forest green with thick horizontal stripes, white rubber collar, embroidered crest on chest, heavy washed cotton with vintage fade, dropped shoulders, displayed casually draped over leather armchair, warm afternoon golden light, British heritage sport luxury, 8K",
        "caption": "Heritage Striped Rugby Polo\nヘリテージストライプ ラグビーポロ\n\nThick stripes. Rubber collar. Embroidered crest.\nヴィンテージフェードのラグビーポロ。\nOld school, new rules.\n\n#fashion #ファッション #rugby #polo #heritage #ラグビー #ポロ #ブリティッシュ #ヴィンテージ #preppy",
    },
    {
        "prompt": "High-end product photo of a sleeveless oversized denim vest in raw indigo selvedge with exposed white warp threads, raw frayed armholes, oversized chest pockets with copper rivets, back panel featuring large distressed paintbrush stroke print in white, displayed on industrial pipe rack, harsh overhead studio lighting emphasizing raw denim texture, workwear meets art, 8K",
        "caption": "Raw Selvedge Denim Vest\nロウセルビッジ デニムベスト\n\nRaw indigo. Exposed threads. Paint stroke print.\n生デニムのラフさとアートの融合。\nWorkwear elevated to gallery level.\n\n#fashion #ファッション #denim #vest #selvedge #デニム #ベスト #セルビッジ #ワークウェア #アート",
    },
    # === ボトムス - 追加 ===
    {
        "prompt": "Luxury product photo of black pleated wide-leg trousers with sharp knife pleats running from waist to hem, high waist with double pleat front, pressed crease visible, lightweight tropical wool, ankle length showing socks, hung on slim gold hanger against white wall, clean minimalist editorial lighting, Japanese tailoring precision aesthetic, 8K",
        "caption": "Knife Pleat Wide Trousers\nナイフプリーツ ワイドトラウザー\n\nSharp knife pleats. Tropical wool. Japanese precision.\n鋭いプリーツが生む完璧なドレープ。\nEvery pleat tells a story.\n\n#fashion #ファッション #pleats #widepants #tailored #プリーツ #ワイドパンツ #テーラード #ミニマル #Japanese",
    },
    {
        "prompt": "Premium product photo of gradient-dyed jogger pants transitioning from deep black at waist to charcoal grey at knees to light ash at ankles, tapered slim fit, zip pockets with matte black hardware, ribbed cuffs, premium French terry interior visible at rolled hem, displayed on dark marble surface, moody gradient studio lighting matching the garment transition, luxury athleisure campaign, 8K",
        "caption": "Gradient Dip-Dye Joggers\nグラデーション ディップダイジョガー\n\nBlack to ash gradient. French terry. Zip pockets.\n黒からアッシュへのグラデーション。\nFade into style.\n\n#fashion #ファッション #joggers #gradient #dipdye #ジョガー #グラデーション #アスレジャー #luxury #モード",
    },
    {
        "prompt": "High-end product photo of dark olive military cargo shorts with multiple flap pockets on thighs and sides, heavy cotton ripstop fabric, adjustable drawstring at hem, antique brass hardware and D-ring attachments, relaxed fit hitting just above knee, displayed on weathered wooden crate with compass and vintage map, adventure editorial warm lighting, utility luxury aesthetic, 8K",
        "caption": "Military Ripstop Cargo Shorts\nミリタリーリップストップ カーゴショーツ\n\nRipstop cotton. Brass hardware. D-ring details.\nミリタリーディテールの機能派ショーツ。\nBuilt for adventure, styled for the city.\n\n#fashion #ファッション #cargo #military #shorts #カーゴ #ミリタリー #ショーツ #utility #adventure",
    },
    {
        "prompt": "Stunning product photo of white linen drawstring pants with relaxed wide silhouette, natural texture visible in weave, side seam pockets, elastic waist with braided cotton drawstring, slightly sheer quality showing relaxed drape, displayed on sun-bleached driftwood at beach setting with ocean blur, golden hour warm light, Mediterranean resort luxury, 8K",
        "caption": "Linen Drawstring Wide Pants\nリネンドローストリング ワイドパンツ\n\nPure linen. Braided drawstring. Mediterranean ease.\n地中海の風を纏うリネンパンツ。\nSummer in a silhouette.\n\n#fashion #ファッション #linen #widepants #resort #リネン #ワイドパンツ #リゾート #地中海 #夏",
    },
    {
        "prompt": "Luxury product photo of pinstripe suit trousers in charcoal grey with fine white chalk pinstripe, flat front with extended tab waistband, side adjusters instead of belt loops, full break at hem, premium Super 120s wool, displayed on tailor's wooden pressing board with scissors and measuring tape, warm workshop lighting, Savile Row bespoke tailoring aesthetic, 8K",
        "caption": "Chalk Pinstripe Suit Trousers\nチョークピンストライプ スーツトラウザー\n\nSuper 120s wool. Side adjusters. Full break hem.\nサヴィルロウ仕込みのピンストライプ。\nThe trouser that means business.\n\n#fashion #ファッション #pinstripe #suit #bespoke #ピンストライプ #スーツ #テーラード #savilerow #紳士",
    },
    # === シューズ - 追加 ===
    {
        "prompt": "Premium product photo of minimalist white leather Chelsea boots with elastic side panels, rounded toe, stacked natural leather sole with slight heel, clean unadorned design with only a subtle embossed logo on inner sole, butter-soft calfskin, displayed on white terrazzo surface with morning light casting long shadow, quiet luxury footwear campaign, 8K",
        "caption": "Minimalist Chelsea Boots\nミニマリスト チェルシーブーツ\n\nCalfskin leather. Stacked sole. No excess.\n引き算の美学、カーフスキンチェルシー。\nLess is literally more.\n\n#fashion #ファッション #chelseaboots #minimalist #calfskin #チェルシーブーツ #ミニマル #レザー #quietluxury #靴",
    },
    {
        "prompt": "High-end product photo of retro-style chunky running sneakers with multicolor panel design in cream, forest green, and burgundy suede and mesh combination, oversized N or wavy logo on side, thick gum rubber outsole with visible cushioning unit, vintage worn-in look with slightly yellowed midsole, displayed on old wooden gym bench, warm nostalgic afternoon light, heritage sportswear revival, 8K",
        "caption": "Retro Heritage Runners\nレトロヘリテージ ランナー\n\nMulticolor suede. Gum sole. Vintage spirit.\nスエード×メッシュのレトロランナー。\nThe past runs forward.\n\n#fashion #ファッション #retro #runners #vintage #レトロ #スニーカー #ヴィンテージ #heritage #gumsole",
    },
    {
        "prompt": "Luxury product photo of sleek black patent leather pointed-toe ankle boots with stiletto heel, mirror-like shine reflecting studio lights, inside zip closure, elegant almond toe shape, 8cm heel, displayed on black glass pedestal with dramatic single spotlight creating sharp reflections, luxury evening footwear campaign, 8K",
        "caption": "Patent Stiletto Ankle Boots\nパテント スティレットアンクルブーツ\n\nMirror patent leather. 8cm stiletto. Sharp silhouette.\n鏡面パテントのスティレットブーツ。\nEvery step commands attention.\n\n#fashion #ファッション #stiletto #patent #ankleboots #スティレット #パテント #ブーツ #luxury #シャープ",
    },
    {
        "prompt": "Stunning product photo of woven leather huarache sandals in tan brown, intricate hand-woven leather strips forming the upper, open back with adjustable buckle strap, cushioned leather insole, low natural leather heel, placed on terracotta tiles with succulent plant nearby, warm Mexican summer light, artisan craftsman heritage aesthetic, 8K",
        "caption": "Hand-Woven Huarache Sandals\nハンドウーブン ウアラチサンダル\n\nHand-woven leather. Artisan craft. Mexican heritage.\n職人が手編みするレザーサンダル。\nEvery weave tells a story.\n\n#fashion #ファッション #huarache #woven #sandals #ウアラチ #サンダル #職人 #handmade #ヘリテージ",
    },
    {
        "prompt": "Premium product photo of futuristic metallic silver high-top sneakers with holographic panels that shift between silver and iridescent purple, exaggerated padded tongue, chunky translucent sole with LED-style clear material, reflective 3M lace loops, displayed on mirror surface with neon blue and purple light reflections, cyberpunk luxury sneaker campaign, 8K",
        "caption": "Holographic High-Top Sneakers\nホログラフィック ハイトップスニーカー\n\nIridescent panels. Clear sole. Futuristic design.\n光で色が変わるホログラフィックスニーカー。\nThe future is on your feet.\n\n#fashion #ファッション #holographic #hightop #futuristic #ホログラフィック #ハイトップ #未来的 #sneakers #hype",
    },
    # === アウター - 追加 ===
    {
        "prompt": "Luxury product photo of an oversized shearling aviator jacket in rich cognac brown with thick cream curly shearling lining visible at collar, cuffs and hem, heavy-duty antique brass front zipper, buckle straps at waist, soft grained leather exterior, displayed on vintage wooden propeller stand, warm golden hangar lighting, aviation heritage luxury, 8K",
        "caption": "Shearling Aviator Jacket\nシアリング アビエイタージャケット\n\nGenuine shearling. Cognac leather. Brass hardware.\nカーリーシアリングの贅沢アビエイター。\nReady for takeoff.\n\n#fashion #ファッション #shearling #aviator #leather #シアリング #アビエイター #レザー #ヴィンテージ #luxury",
    },
    {
        "prompt": "High-end product photo of a tailored double-breasted overcoat in camel cashmere wool blend, peak lapels, six button front with horn buttons, chest welt pocket, flap hip pockets, back vent, reaching just below knee, perfect drape showing fabric weight and quality, displayed on dark wood coat stand in library setting with leather-bound books, warm intellectual editorial lighting, British gentleman luxury, 8K",
        "caption": "Cashmere Double-Breasted Overcoat\nカシミヤ ダブルブレストオーバーコート\n\nCamel cashmere blend. Peak lapels. Horn buttons.\nカシミヤブレンドの極上オーバーコート。\nThe coat that defines elegance.\n\n#fashion #ファッション #overcoat #cashmere #doublebreasted #オーバーコート #カシミヤ #紳士 #ブリティッシュ #上品",
    },
    {
        "prompt": "Stunning product photo of a transparent clear PVC raincoat with glossy finish, oversized silhouette, white cotton lining visible at seams, snap button front closure, attached hood, reaching mid-calf, displayed on mannequin against rainy window backdrop with water droplets, cool blue-grey studio lighting, futuristic meets utilitarian fashion, 8K",
        "caption": "Clear PVC Rain Coat\nクリアPVC レインコート\n\nTransparent PVC. Oversized fit. Weather-ready fashion.\n透明PVCで魅せるファッションレインコート。\nNothing to hide.\n\n#fashion #ファッション #pvc #raincoat #transparent #レインコート #クリア #透明 #futuristic #モード",
    },
    {
        "prompt": "Premium product photo of a military-inspired field jacket in washed olive green cotton with four large front cargo pockets, shoulder epaulets, concealed zip and button front, adjustable drawstring waist, brass snap collar closure, displayed on barbed wire fence in open field setting with golden sunset behind, rugged adventure editorial lighting, military heritage meets fashion, 8K",
        "caption": "M-65 Field Jacket\nM-65 フィールドジャケット\n\nFour-pocket design. Olive cotton. Military heritage.\n本格ミリタリーフィールドジャケット。\nBattle-tested, street-approved.\n\n#fashion #ファッション #fieldjacket #m65 #military #フィールドジャケット #ミリタリー #オリーブ #heritage #メンズ",
    },
    {
        "prompt": "Luxury product photo of a cropped black leather biker jacket with asymmetric front zip, silver stud embellishments on lapels and pocket flaps, quilted panel on elbows and shoulders, slim tailored fit, heavy silver YKK zippers throughout, displayed on chrome motorcycle handlebar, dramatic harsh side lighting creating deep shadows, rock and roll luxury aesthetic, 8K",
        "caption": "Studded Leather Biker Jacket\nスタッズレザー バイカージャケット\n\nAsymmetric zip. Silver studs. Quilted panels.\nスタッズが輝くライダースジャケット。\nRebel with impeccable taste.\n\n#fashion #ファッション #biker #leather #studs #ライダース #レザー #スタッズ #ロック #バイカー",
    },
    # === バッグ - 追加 ===
    {
        "prompt": "High-end product photo of a structured bucket bag in smooth black leather with drawstring closure and adjustable crossbody strap, gold-tone metal logo ring detail at drawstring, suede interior lining visible, cylindrical shape holding form perfectly, displayed on white marble shelf with single orchid stem, warm elegant studio lighting, modern luxury accessories campaign, 8K",
        "caption": "Leather Bucket Bag\nレザーバケットバッグ\n\nSmooth calfskin. Drawstring closure. Gold ring detail.\n美しいフォルムのバケットバッグ。\nStructure meets simplicity.\n\n#fashion #ファッション #bucketbag #leather #gold #バケットバッグ #レザー #ゴールド #モダン #luxury",
    },
    {
        "prompt": "Stunning product photo of an oversized canvas tote bag in natural beige heavy-weight canvas with bold black screen-printed typographic logo across the front, reinforced leather bottom panel in dark brown, thick cotton rope handles, interior zip pocket, casual unstructured shape, displayed on cafe table with espresso cup nearby, warm morning light through window, elevated everyday carry aesthetic, 8K",
        "caption": "Logo Canvas Utility Tote\nロゴキャンバス ユーティリティトート\n\nHeavy canvas. Leather base. Bold typography.\nヘビーキャンバスのデイリートート。\nThe tote that carries everything, including style.\n\n#fashion #ファッション #canvastote #logo #utility #キャンバストート #ロゴ #デイリー #カジュアル #おしゃれ",
    },
    {
        "prompt": "Premium product photo of a compact camera bag in burgundy grained leather with front flap, antique gold turn-lock closure, detachable chain and leather shoulder strap, boxy structured shape, interior card slots visible with flap open, displayed on dark velvet surface with vintage film camera beside it, warm moody editorial lighting, French luxury maison aesthetic, 8K",
        "caption": "Grained Leather Camera Bag\nグレインレザー カメラバッグ\n\nTurn-lock closure. Chain strap. Compact design.\nアンティークゴールドのターンロック。\nSmall bag, big statement.\n\n#fashion #ファッション #camerabag #leather #burgundy #カメラバッグ #レザー #チェーン #フレンチ #luxury",
    },
    {
        "prompt": "Luxury product photo of a black technical nylon belt bag with clean angular design, waterproof matte finish, hidden magnetic front pocket, adjustable woven webbing strap with metal buckle, subtle embossed logo on front, slim low-profile shape, displayed on polished concrete surface with sunglasses nearby, clean modern urban lighting, minimal techno-luxury everyday carry, 8K",
        "caption": "Technical Nylon Belt Bag\nテクニカルナイロン ベルトバッグ\n\nWaterproof nylon. Magnetic pocket. Angular design.\n都市生活のためのテクニカルベルトバッグ。\nHands-free, worry-free.\n\n#fashion #ファッション #beltbag #technical #nylon #ベルトバッグ #ナイロン #テクニカル #ミニマル #urban",
    },
    {
        "prompt": "High-end product photo of a woven raffia clutch bag in natural straw color with leather trim in tan, fold-over magnetic closure, interior leather lining, handcrafted irregular weave pattern showing artisan quality, oversized enough for essentials, displayed on whitewashed wooden table with seashells and dried palm frond, bright warm beach sunset light, Mediterranean summer luxury, 8K",
        "caption": "Raffia Fold-Over Clutch\nラフィア フォールドオーバークラッチ\n\nHandwoven raffia. Leather trim. Summer essential.\n手編みラフィアのサマークラッチ。\nSummer in your hands.\n\n#fashion #ファッション #raffia #clutch #summer #ラフィア #クラッチ #サマー #ハンドメイド #リゾート",
    },
    # === アクセサリー - 追加 ===
    {
        "prompt": "Luxury product photo of a cashmere beanie in heather grey with ribbed turn-up cuff, small leather logo tag stitched on cuff, ultra-soft lightweight knit visible in texture, slightly slouchy fit, displayed on polished black stone sphere against snowy window backdrop, cool winter editorial lighting, Nordic luxury knitwear aesthetic, 8K",
        "caption": "Cashmere Ribbed Beanie\nカシミヤリブ ビーニー\n\nPure cashmere. Leather tag. Featherweight warmth.\n極上カシミヤのライトウェイトビーニー。\nLuxury you can feel on your head.\n\n#fashion #ファッション #beanie #cashmere #winter #ビーニー #カシミヤ #冬 #ニット帽 #北欧",
    },
    {
        "prompt": "Premium product photo of aviator sunglasses with gold metal frame, gradient green lenses, thin temple arms with tortoiseshell acetate tips, double bridge design, displayed on folded leather pilot jacket, warm golden afternoon light creating lens reflections, classic American aviation heritage luxury, extreme detail on bridge mechanism, 8K",
        "caption": "Aviator Gradient Sunglasses\nアビエイター グラデーションサングラス\n\nGold frame. Green gradient lens. Double bridge.\nゴールドフレームのクラシックアビエイター。\nThe original cool.\n\n#fashion #ファッション #aviator #sunglasses #gold #アビエイター #サングラス #ゴールド #クラシック #heritage",
    },
    {
        "prompt": "Stunning product photo of a wide-brim fedora hat in black wool felt with grosgrain ribbon band and small metal logo pin, structured crown with center crease, displayed on ceramic head form against dark textured wall, moody directional studio lighting creating dramatic shadow of brim, luxury millinery campaign, Italian artisan craft, 8K",
        "caption": "Wool Felt Fedora\nウールフェルト フェドラ\n\nBlack wool felt. Grosgrain band. Center crease.\nクラシックフェドラの完璧なシルエット。\nThe hat that makes the outfit.\n\n#fashion #ファッション #fedora #hat #woolfelt #フェドラ #帽子 #クラシック #イタリア #紳士",
    },
    {
        "prompt": "High-end product photo of a sterling silver watch with minimalist white dial, thin applied hour markers, dauphine hands, ultra-thin 7mm case, dark navy blue alligator leather strap with butterfly deployant clasp, displayed on midnight blue velvet watch cushion, clean precise studio lighting showing dial detail, Swiss haute horlogerie aesthetic, 8K",
        "caption": "Ultra-Thin Dress Watch\nウルトラシン ドレスウォッチ\n\nMinimalist dial. 7mm thin case. Alligator strap.\n7mmの薄さに宿る美意識。\nTime, refined.\n\n#fashion #ファッション #watch #minimalist #ultrathin #腕時計 #ミニマル #ドレスウォッチ #Swiss #上品",
    },
    {
        "prompt": "Premium product photo of black leather card holder wallet with embossed crocodile texture, matte finish, four card slots and center bill compartment, slim profile under 5mm thick, subtle blind-stamped logo on corner, displayed on dark marble surface with business cards peeking out, clean executive studio lighting, luxury leather goods essentials campaign, 8K",
        "caption": "Croc-Embossed Card Holder\nクロコエンボス カードホルダー\n\nEmbossed croc leather. Ultra-slim 5mm. Four slots.\n5mmの極薄クロコエンボスカードホルダー。\nMinimalism in your pocket.\n\n#fashion #ファッション #cardholder #crocodile #leather #カードホルダー #クロコ #レザー #ミニマル #紳士",
    },
    # === ジュエリー - 追加 ===
    {
        "prompt": "Luxury product photo of a chunky Cuban link chain necklace in polished sterling silver, 12mm width, heavy substantial weight with each link clearly defined, lobster clasp closure, 50cm length, displayed draped over black obsidian crystal on dark surface with dramatic single spot light creating sharp silver reflections, hip-hop luxury jewelry campaign, 8K",
        "caption": "Cuban Link Chain Necklace\nキューバンリンク チェーンネックレス\n\nSterling silver. 12mm width. Heavy links.\n重厚な存在感のキューバンリンクチェーン。\nWeight that commands respect.\n\n#fashion #ファッション #cubanlink #chain #silver #キューバンリンク #チェーン #シルバー #ヒップホップ #jewelry",
    },
    {
        "prompt": "High-end product photo of a minimalist open cuff bangle bracelet in brushed 18k gold vermeil, tapered ends, smooth interior, subtle asymmetric gap opening, 6mm width, displayed on pale pink quartz stone against soft white background, delicate warm studio lighting showing the brushed gold texture, Scandinavian minimalist luxury jewelry, 8K",
        "caption": "Open Cuff Gold Bangle\nオープンカフ ゴールドバングル\n\nBrushed gold vermeil. Tapered ends. Open cuff.\nブラッシュ加工の上品なオープンバングル。\nElegant restraint.\n\n#fashion #ファッション #bangle #gold #cuff #バングル #ゴールド #カフ #ミニマル #Scandinavian",
    },
    {
        "prompt": "Stunning product photo of mismatched asymmetric earrings, left ear featuring long thin silver chain with small crescent moon pendant, right ear featuring shorter chain with star pendant, both in oxidized sterling silver with matte finish, displayed on dark blue velvet ear display stand, moody celestial-themed studio lighting with tiny light spots like stars, luxury artisan celestial jewelry, 8K",
        "caption": "Celestial Mismatched Earrings\nセレスティアル ミスマッチイヤリング\n\nMoon and star pendants. Oxidized silver. Asymmetric design.\n月と星のアシンメトリーイヤリング。\nWear the universe.\n\n#fashion #ファッション #celestial #earrings #mismatched #セレスティアル #イヤリング #月 #星 #シルバー",
    },
    {
        "prompt": "Premium product photo of a thick signet ring in polished gold-tone stainless steel with flat oval face featuring engraved compass rose design, heavy substantial construction, slight dome on sides, displayed on antique nautical map with brass compass nearby, warm amber editorial lighting, maritime heritage luxury accessories, 8K",
        "caption": "Compass Rose Signet Ring\nコンパスローズ シグネットリング\n\nEngraved compass. Gold-tone steel. Heavy weight.\n羅針盤を刻んだシグネットリング。\nFind your direction.\n\n#fashion #ファッション #signetring #compass #gold #シグネット #リング #コンパス #マリン #heritage",
    },
    {
        "prompt": "Luxury product photo of layered necklace set featuring three separate chains worn together: a 40cm thin box chain, a 45cm figaro chain with small padlock pendant, and a 50cm rope chain, all in sterling silver, displayed on slender neck form bust against matte charcoal background, clean directional studio lighting showing chain texture differences, modern luxury layering jewelry campaign, 8K",
        "caption": "Layered Silver Chain Set\nレイヤード シルバーチェーンセット\n\nThree chains. Three textures. Padlock accent.\n3本のチェーンで作るレイヤードスタイル。\nMore is more.\n\n#fashion #ファッション #layered #chains #silver #レイヤード #チェーン #シルバー #padlock #ネックレス",
    },
]

# --- モデル着用 全身コーディネート投稿 ---
OUTFIT_POSTS = [
    # === ストリート×モード ===
    {
        "gender": "male",
        "prompt": "Full body fashion editorial photo of a handsome 25-year-old Western male model with defined jawline, light stubble, and intense green eyes walking on a Tokyo street at dusk, wearing an oversized black deconstructed blazer over a white graphic tee, black wide-leg pleated trousers with sharp crease, chunky platform derby shoes, carrying a woven leather crossbody bag, confident stride, shot from slightly low angle, neon signs reflected on wet pavement, moody cinematic lighting, Japanese street fashion editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Tokyo After Dark\n東京アフターダーク\n\n🖤 Deconstructed blazer × Wide pleats × Platform derbys\n脱構築ブレザーにワイドプリーツの黒コーデ。\nThe city is your runway.\n\nBlazer: Oversized deconstructed\nTee: White graphic\nPants: Wide-leg pleats\nShoes: Platform derby\nBag: Woven crossbody\n\n#fashion #ootd #コーデ #全身コーデ #ストリート #モード #東京 #メンズファッション #darkfashion #styling",
    },
    {
        "gender": "female",
        "prompt": "Full body fashion photo of a stunning 25-year-old Western female model with sculpted cheekbones, flowing hair, and captivating blue eyes posing under neon lights in Shibuya crossing at night, wearing a cropped metallic silver puffer jacket with holographic panels over a neon green mesh crop top, high-waisted black vinyl flare pants with reflective piping down the sides, chunky platform combat boots with neon orange laces, oversized futuristic visor sunglasses, multiple chunky acrylic chain necklaces in pink and green, cyberpunk inspired bold pose, neon city lights reflecting off vinyl and metallic surfaces, vibrant Tokyo nightlife fashion editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Neon Shibuya Nights\nネオン渋谷ナイツ\n\n💚 Holographic puffer × Vinyl flares × Neon mesh\nホログラフィック×ビニール×ネオンの未来コーデ。\nThe future is bright. Literally.\n\nJacket: Silver holographic puffer\nTop: Neon green mesh crop\nPants: Black vinyl flares\nBoots: Platform combat\nAccessory: Acrylic chain necklaces\n\n#fashion #ootd #コーデ #渋谷 #ネオン #サイバーパンク #レディース #cyberpunk #neon #styling",
    },
    {
        "gender": "male",
        "prompt": "Full body street style photo of a handsome 25-year-old Western male model with defined jawline, light stubble, and intense green eyes leaning against a concrete wall, wearing a black oversized hoodie with diagonal arrow print layered under a long black leather trench coat, black distressed skinny jeans, triple white chunky platform sneakers, silver Cuban link chain necklace visible, hands in pockets, edgy confident expression, harsh side lighting creating dramatic shadows, urban streetwear editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Shadow Walker\nシャドウウォーカー\n\n⚫ Leather trench × Arrow hoodie × Chunky sneakers\nレザートレンチの下に矢印パーカーのレイヤード。\nLayers of darkness.\n\nCoat: Black leather trench\nHoodie: Arrow print oversized\nJeans: Black distressed\nShoes: Triple white platform\nChain: Silver Cuban link\n\n#fashion #ootd #コーデ #ストリート #レザー #レイヤード #黒コーデ #メンズ #darkstyle #streetwear",
    },
    {
        "gender": "female",
        "prompt": "Full body fashion editorial of a stunning 25-year-old Western female model with sculpted cheekbones, flowing hair, and captivating blue eyes striking a pose on a neon-lit rooftop, wearing a bold flame print oversized satin bomber jacket in red orange and yellow over a black latex corset top, acid wash ripped baggy jeans with heavy chain belt, towering clear platform boots showing neon socks, oversized hoop earrings with flame charms, fire-red box braids, fierce expression with one hand raised, dramatic red and orange stage lighting from below, Y2K meets avant-garde fire editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Flame Girl\nフレイムガール\n\n🔥 Flame bomber × Latex corset × Clear platforms\n炎プリントボンバー×ラテックス×クリアブーツ。\nSet the trend on fire.\n\nJacket: Flame satin bomber\nTop: Black latex corset\nJeans: Acid wash ripped baggy\nBoots: Clear platform\nBelt: Heavy chain\nEarrings: Flame hoop\n\n#fashion #ootd #コーデ #Y2K #炎 #ラテックス #レディース #flamefashion #avantgarde #styling",
    },
    {
        "gender": "male",
        "prompt": "Full body photo of a handsome 25-year-old Western male model with defined jawline, light stubble, and intense green eyes standing on a rooftop at sunset, wearing a sage green quilted reversible vest over a black technical nylon shirt, dark olive military cargo shorts, retro heritage running sneakers in cream and forest green, aviator gradient sunglasses, black nylon belt bag across chest, athletic relaxed pose, warm golden sunset backlighting, outdoor urban adventure style, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Urban Explorer\nアーバンエクスプローラー\n\n🌿 Quilted vest × Cargo shorts × Retro runners\nベストとカーゴの機能派アウトドアMIX。\nCity to trail, no outfit change needed.\n\nVest: Sage reversible quilted\nShirt: Black tech nylon\nShorts: Olive cargo\nShoes: Retro heritage runners\nBag: Black belt bag\n\n#fashion #ootd #コーデ #アウトドア #ミリタリー #メンズ #機能美 #techwear #adventure #styling",
    },
    # === ダーク×アバンギャルド ===
    {
        "gender": "male",
        "prompt": "Full body editorial photo of a striking 25-year-old androgynous Western model with angular bone structure and piercing grey eyes standing in a dimly lit gallery space, wearing head-to-toe black: draped cowl neck long tee reaching mid-thigh, black pleated wide-leg trousers, split-toe tabi boots, gothic scroll cross pendant on silver chain, black leather gloves, minimalist and dark silhouette against white gallery wall, single harsh spotlight from above, dark avant-garde fashion editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Gallery Noir\nギャラリーノワール\n\n🖤 All-black: Cowl drape × Wide pleats × Tabi boots\n全身黒のアバンギャルドスタイリング。\nDarkness is a language.\n\nTop: Draped cowl long tee\nPants: Black wide pleats\nBoots: Split-toe tabi\nJewelry: Gothic cross pendant\nGloves: Black lambskin\n\n#fashion #ootd #コーデ #黒コーデ #avantgarde #tabi #darkfashion #モード #allblack #styling",
    },
    {
        "gender": "female",
        "prompt": "Full body fashion photo of a stunning 25-year-old Western female model with sculpted cheekbones, flowing hair, and captivating blue eyes posing in front of a graffiti wall, wearing a cropped varsity jacket with cream wool body and black leather sleeves over a black mesh layered long sleeve top, ultra wide-leg washed denim jeans with raw selvedge hem dragging slightly, holographic high-top sneakers, mismatched celestial earrings, bold confident pose with one hand on hip, vibrant urban energy, colorful street art backdrop, bright daylight, street style photography, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Street Art Energy\nストリートアート エナジー\n\n🎨 Varsity jacket × Mesh layer × Ultra wide denim\nバーシティ×メッシュのレイヤード×ワイドデニム。\nBe the art.\n\nJacket: Varsity leather sleeve\nInner: Black mesh layered\nDenim: Ultra wide raw selvedge\nShoes: Holographic high-tops\nEarrings: Celestial mismatched\n\n#fashion #ootd #コーデ #ストリート #デニム #バーシティ #レディース #streetstyle #colorful #styling",
    },
    {
        "gender": "male",
        "prompt": "Full body fashion editorial of a handsome 25-year-old Western male model with defined jawline, light stubble, and intense green eyes sitting on marble steps of a luxury hotel entrance, wearing a grey marl trompe-l'oeil tuxedo hoodie with pinstripe suit trousers in charcoal, minimalist white Chelsea boots, ultra-thin dress watch visible on wrist, croc-embossed card holder casually held, legs crossed elegantly, warm afternoon sunlight, luxury casual contradiction editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Formal Illusion\nフォーマルイリュージョン\n\n🎭 Tuxedo hoodie × Pinstripe trousers × Chelsea boots\nだまし絵タキシードパーカーにピンストライプ。\nFormally informal.\n\nHoodie: Trompe-l'oeil tuxedo\nTrousers: Charcoal pinstripe\nBoots: White Chelsea\nWatch: Ultra-thin dress\nWallet: Croc card holder\n\n#fashion #ootd #コーデ #ミックス #カジュアル #フォーマル #メンズ #unique #smartcasual #styling",
    },
    {
        "gender": "female",
        "prompt": "Full body photo of a stunning 25-year-old Western female model with sculpted cheekbones, flowing hair, and captivating blue eyes standing at a minimalist cafe counter, wearing an oversized striped rugby polo in navy and forest green with white collar, high-waisted black knife pleat wide trousers, patent stiletto ankle boots, quilted lambskin crossbody bag in black, cashmere beanie in heather grey, holding a coffee cup, natural relaxed smile, warm morning cafe light through large windows, effortless preppy luxury, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Cafe Morning Prep\nカフェモーニング プレッピー\n\n☕ Rugby polo × Knife pleats × Patent boots\nラグビーポロ×ナイフプリーツの知的コーデ。\nPreppy with an edge.\n\nPolo: Navy/green rugby stripe\nPants: Black knife pleat wide\nBoots: Patent stiletto\nBag: Quilted lambskin\nHat: Cashmere beanie\n\n#fashion #ootd #コーデ #プレッピー #カフェ #レディース #preppy #smartcasual #morning #styling",
    },
    {
        "gender": "male",
        "prompt": "Full body fashion photo of a handsome 25-year-old Western male model with defined jawline, light stubble, and intense green eyes walking through an autumn park with fallen leaves, wearing a shearling aviator jacket in cognac brown, black cable knit mohair cardigan underneath, gradient dip-dye joggers fading from black to ash, hand-woven tan huarache sandals with socks, compass rose signet ring visible, wool felt fedora in black, warm amber autumn sunlight filtering through trees, heritage meets modern street style, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Autumn Heritage Walk\nオータム ヘリテージウォーク\n\n🍂 Shearling aviator × Cable knit × Gradient joggers\nシアリングアビエイターの秋レイヤード。\nLayers for the season.\n\nJacket: Cognac shearling aviator\nKnit: Cable mohair cardigan\nPants: Gradient dip-dye joggers\nShoes: Woven huarache\nHat: Black wool fedora\nRing: Compass signet\n\n#fashion #ootd #コーデ #秋コーデ #レイヤード #ヘリテージ #メンズ #autumn #vintage #styling",
    },
    # === 派手×インパクト ===
    {
        "gender": "female",
        "prompt": "Full body fashion photo of a stunning 25-year-old Western female model with sculpted cheekbones, flowing hair, and captivating blue eyes walking confidently through a crowded Harajuku street, wearing a bold all-over graffiti-printed oversized denim jacket covered in neon spray paint patterns over a hot pink ribbed bodysuit, patchwork mixed-media wide leg jeans with contrasting denim panels and exposed orange stitching, chunky triple-sole rainbow platform sneakers, stacked colorful acrylic bangles on both wrists, bucket hat covered in pins and patches, energetic stride, bright sunny day, explosive Harajuku kawaii street fashion, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Harajuku Explosion\n原宿エクスプロージョン\n\n🌈 Graffiti denim × Pink bodysuit × Rainbow platforms\nグラフィティデニム×ピンクボディスーツの原宿全開コーデ。\nColor is my language.\n\nJacket: Graffiti spray paint denim\nTop: Hot pink bodysuit\nJeans: Patchwork mixed-media\nShoes: Rainbow triple-sole platforms\nAccessory: Stacked acrylic bangles\nHat: Pin-covered bucket hat\n\n#fashion #ootd #コーデ #原宿 #グラフィティ #カラフル #レディース #harajuku #kawaii #styling",
    },
    {
        "gender": "male",
        "prompt": "Full body editorial photo of a handsome 25-year-old Western male model with defined jawline, light stubble, and intense green eyes standing in front of a luxury car showroom window, wearing a camel oblique jacquard bomber jacket, white sheer organza layered shirt underneath, tailored black wool trousers with integrated leather belt, polished black mega sole derby shoes, open gold cuff bangle on wrist, hands casually at sides, warm evening showroom lighting reflecting off glass, French luxury casual editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Showroom After Hours\nショールーム アフターアワーズ\n\n✨ Jacquard bomber × Organza shirt × Mega sole derbys\nジャカードボンバー×透けるシャツの大人コーデ。\nEvening elegance.\n\nJacket: Oblique jacquard bomber\nShirt: Sheer organza layered\nPants: Integrated belt wool\nShoes: Mega sole derby\nBangle: Gold open cuff\n\n#fashion #ootd #コーデ #フレンチ #ジャカード #大人コーデ #メンズ #luxury #evening #styling",
    },
    {
        "gender": "female",
        "prompt": "Full body fashion photo of a stunning 25-year-old Western female model with sculpted cheekbones, flowing hair, and captivating blue eyes on a beach boardwalk at sunset, wearing a transparent clear PVC raincoat over a black ribbed tank top and white linen drawstring wide pants, woven raffia fold-over clutch in hand, hand-woven huarache sandals in tan, hammered gold hoop earrings, wind blowing hair, golden sunset creating silhouette effect through the clear coat, resort meets avant-garde summer editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Transparent Summer\nトランスペアレント サマー\n\n🌊 Clear PVC coat × Linen wide × Raffia clutch\n透明レインコートを夏のビーチで。\nNothing to hide, everything to show.\n\nCoat: Clear PVC raincoat\nTop: Black ribbed tank\nPants: White linen wide\nShoes: Woven huarache\nBag: Raffia clutch\nEarrings: Hammered gold hoops\n\n#fashion #ootd #コーデ #夏コーデ #ビーチ #PVC #レディース #summer #avantgarde #styling",
    },
    {
        "gender": "male",
        "prompt": "Full body photo of a handsome 25-year-old Western male model with defined jawline, light stubble, and intense green eyes leaning against a brick wall in Harajuku, wearing a destroyed luxury hoodie with intentional rips and faded print, black 3D pocket technical cargo pants with toggle hem, speed knit sock runner sneakers in all black, medallion chain bracelet on wrist, technical nylon belt bag worn crossbody, hood up with earbuds in, casual urban posture, overcast soft daylight, Tokyo Harajuku street fashion documentary style, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Harajuku Utility\n原宿ユーティリティ\n\n🔧 Destroyed hoodie × 3D cargo × Sock runners\nダメージパーカー×立体カーゴのストリートコーデ。\nFunctional destruction.\n\nHoodie: Destroyed luxury\nPants: 3D pocket tech cargo\nShoes: Speed knit sock runners\nBag: Tech nylon belt bag\nBracelet: Medallion chain\n\n#fashion #ootd #コーデ #原宿 #ストリート #テックウェア #メンズ #harajuku #techwear #styling",
    },
    {
        "gender": "female",
        "prompt": "Full body fashion editorial of a stunning 25-year-old Western female model with sculpted cheekbones, flowing hair, and captivating blue eyes sitting on a velvet sofa in a luxury apartment, wearing a double-layered sheer black organza shirt over black tank, sky blue lambskin leather trousers, patent stiletto ankle boots, layered silver chain necklace set with padlock pendant, burgundy grained leather camera bag on shoulder, legs crossed elegantly, moody warm interior lighting with table lamp glow, evening luxury at home editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Evening In\nイブニングイン\n\n🕯️ Organza shirt × Lambskin pants × Patent boots\nシアーオーガンザ×レザーパンツの夜コーデ。\nStaying in never looked this good.\n\nShirt: Sheer organza layered\nPants: Sky blue lambskin\nBoots: Patent stiletto\nBag: Burgundy camera bag\nNecklace: Silver layered chains\n\n#fashion #ootd #コーデ #大人コーデ #レザー #シアー #レディース #evening #luxury #styling",
    },
    # === スポーツ×ラグジュアリー ===
    {
        "gender": "male",
        "prompt": "Full body fashion photo of a handsome 25-year-old Western male model with defined jawline, light stubble, and intense green eyes jogging through a park in early morning mist, wearing a black cocoon sculpted puffer jacket unzipped, satin stripe tuxedo track pants, retro heritage runners in cream burgundy and forest green, cashmere ribbed beanie in heather grey, stackable gold ring set visible on hand, airpods in ears, dynamic motion captured mid-stride, misty soft morning light, luxury athleisure lifestyle editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Morning Run Luxe\nモーニングラン ラグジュアリー\n\n🏃 Cocoon puffer × Tuxedo tracks × Retro runners\nコクーンパファー×タキシードトラックの朝ランコーデ。\nEven your warm-up deserves style.\n\nJacket: Black cocoon puffer\nPants: Satin stripe tuxedo tracks\nShoes: Retro heritage runners\nHat: Cashmere beanie\nRings: Gold stackable set\n\n#fashion #ootd #コーデ #アスレジャー #ランニング #パファー #メンズ #athleisure #morning #styling",
    },
    {
        "gender": "female",
        "prompt": "Full body fashion photo of a stunning 25-year-old Western female model with sculpted cheekbones, flowing hair, and captivating blue eyes posing dramatically in a chrome-decorated warehouse, wearing a metallic chrome silver trench coat with mirror-finish panels, underneath a bold graphic print turtleneck in electric blue and black geometric patterns, high-waisted wide-leg leather pants in deep burgundy with exposed silver zippers, towering chrome platform ankle boots, oversized geometric sculptural earrings in silver, statement chrome clutch bag shaped like a crescent moon, powerful wide stance, harsh industrial spotlights creating reflections on all metallic surfaces, futuristic high fashion editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Chrome Dimension\nクロームディメンション\n\n🪞 Chrome trench × Geometric print × Mirror platforms\nクローム×幾何学プリント×メタリックの近未来コーデ。\nReflect the future.\n\nCoat: Chrome mirror trench\nTop: Geometric turtleneck\nPants: Burgundy leather wide\nBoots: Chrome platform\nBag: Crescent moon clutch\nEarrings: Sculptural silver\n\n#fashion #ootd #コーデ #クローム #メタリック #近未来 #レディース #chrome #futuristic #styling",
    },
    {
        "gender": "male",
        "prompt": "Full body fashion photo of a handsome 25-year-old Western male model with defined jawline, light stubble, and intense green eyes at a train station platform, wearing a hybrid trench-puffer coat in black with gabardine top and quilted bottom, black mesh layered long sleeve underneath, gradient dip-dye joggers from black to charcoal, futuristic metallic silver high-top sneakers with holographic panels, technical nylon belt bag, looking down at phone, overhead fluorescent station lighting mixed with golden sunset through platform windows, Japanese urban commuter fashion, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Platform Style\nプラットフォームスタイル\n\n🚉 Hybrid trench × Gradient joggers × Holographic sneakers\nハイブリッドコート×ホログラフィックスニーカー。\nCommute in the future.\n\nCoat: Hybrid trench-puffer\nInner: Black mesh layered\nPants: Gradient dip-dye joggers\nShoes: Holographic high-tops\nBag: Technical belt bag\n\n#fashion #ootd #コーデ #未来的 #ハイブリッド #メンズ #通勤 #futuristic #techwear #styling",
    },
    {
        "gender": "female",
        "prompt": "Full body editorial photo of a stunning 25-year-old Western female model with sculpted cheekbones, flowing hair, and captivating blue eyes walking down a cobblestone street in Paris, wearing a studded black leather biker jacket, equestrian print silk scarf tied at neck, high-waisted charcoal pinstripe trousers, polished mega sole derby shoes, monogram buckle saddle bag in cognac leather, aviator gradient sunglasses, confident Parisian stride, warm afternoon light casting long shadows on stone, French rock chic editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Parisian Rock Chic\nパリジャン ロックシック\n\n🗼 Biker jacket × Silk scarf × Pinstripe trousers\nライダース×シルクスカーフのパリスタイル。\nRock meets refinement.\n\nJacket: Studded leather biker\nScarf: Equestrian silk twill\nPants: Charcoal pinstripe\nShoes: Mega sole derby\nBag: Monogram saddle bag\n\n#fashion #ootd #コーデ #パリ #ロック #ライダース #レディース #parisian #rockchic #styling",
    },
    {
        "gender": "male",
        "prompt": "Full body fashion photo of a handsome 25-year-old Western male model with defined jawline, light stubble, and intense green eyes standing on a rooftop pool deck, wearing an M-65 military field jacket in olive green open over bare chest, white linen drawstring wide pants, woven leather platform slides, gold Cuban link chain necklace, compass badge reversible vest tied around waist, aviator sunglasses, relaxed resort pose with drink in hand, bright blue sky and cityscape behind, rooftop pool party luxury lifestyle, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Rooftop Season\nルーフトップシーズン\n\n🏊 Military field jacket × Linen wide × Platform slides\nM-65ジャケット×リネンのリゾートコーデ。\nPool deck commander.\n\nJacket: Olive M-65 field\nPants: White linen drawstring\nShoes: Woven platform slides\nChain: Gold Cuban link\nSunglasses: Aviator gradient\n\n#fashion #ootd #コーデ #リゾート #ミリタリー #プール #メンズ #rooftop #summer #styling",
    },
    # === 高級ブランド風 斬新デザイン ===
    {
        "gender": "male",
        "prompt": "Full body high fashion editorial photo of a handsome 25-year-old Western male model with defined jawline, light stubble, and intense green eyes standing in an empty white concrete brutalist space, wearing an extremely oversized sculptural black cocoon coat reaching below knees with exaggerated dropped shoulders and raw-edge hems, underneath a deconstructed black hoodie with exposed internal seams worn inside-out, ultra wide-leg draped trousers pooling over chunky square-toe platform boots with exaggerated sole height of 10cm, small structured geometric crossbody bag in matte black, hood up, powerful minimalist stance, harsh single overhead spotlight creating dramatic shadow, dark avant-garde luxury runway editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Sculptural Void\nスカルプチュラル ヴォイド\n\n🖤 Cocoon coat × Inside-out hoodie × Platform boots\n彫刻のようなコクーンコートの圧倒的シルエット。\nArchitecture you wear.\n\nCoat: Oversized sculptural cocoon\nHoodie: Deconstructed inside-out\nPants: Ultra wide draped\nBoots: 10cm platform square-toe\nBag: Geometric crossbody\n\n#fashion #ootd #コーデ #ハイファッション #アバンギャルド #モード #メンズ #avantgarde #darkfashion #runway",
    },
    {
        "gender": "female",
        "prompt": "Full body fashion editorial of a stunning 25-year-old Western female model with sculpted cheekbones, flowing hair, and captivating blue eyes posing in an art gallery with white walls, wearing a dramatic asymmetric deconstructed blazer in black with one shoulder padded extremely high and the other side draped loose revealing a white architectural corset top underneath, paired with an ultra-long floor-length black wool skirt with irregular raw-cut hem at different heights, split-toe leather boots, oversized woven intrecciato leather clutch in bottega green, statement geometric silver ear cuff, intense editorial pose, museum lighting with clean directional spots, conceptual luxury fashion campaign, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Asymmetric Architecture\nアシンメトリック アーキテクチャー\n\n🏛️ Deconstructed blazer × Corset × Floor-length skirt\n肩の高低差が生むドラマティックなシルエット。\nFashion is sculpture.\n\nBlazer: Asymmetric deconstructed\nTop: Architectural corset\nSkirt: Raw-cut floor-length\nBoots: Split-toe leather\nBag: Woven intrecciato clutch\n\n#fashion #ootd #コーデ #ハイファッション #脱構築 #アシンメトリー #レディース #deconstructed #couture #styling",
    },
    {
        "gender": "male",
        "prompt": "Full body fashion photo of a handsome 25-year-old Western male model with defined jawline, light stubble, and intense green eyes walking through a rain-wet Tokyo alley at night, wearing a long black leather trench coat with extreme oversized proportions reaching ankles, sleeves extending past hands, worn over a black ribbed knit turtleneck bodysuit, baggy distressed black cargo pants with hanging straps and excessive hardware, knee-high black leather riding boots with silver buckles, multiple layered silver chains and a single gothic cross pendant, dark sunglasses at night, menacing confident stride, neon reflections on wet pavement, neo-gothic luxury streetwear editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Neo Gothic Tokyo\nネオゴシック 東京\n\n⛓️ Oversized leather trench × Cargo × Riding boots\nオーバーサイズレザーの漆黒コーデ。\nDarkness has never looked this luxurious.\n\nCoat: Oversized leather trench\nTop: Ribbed turtleneck\nPants: Distressed cargo\nBoots: Knee-high riding\nJewelry: Gothic cross chains\n\n#fashion #ootd #コーデ #ゴシック #レザー #東京 #メンズ #gothic #darkfashion #luxury",
    },
    {
        "gender": "female",
        "prompt": "Full body editorial photo of a stunning 25-year-old Western female model with sculpted cheekbones, flowing hair, and captivating blue eyes in a minimalist white studio, wearing a groundbreaking outfit: a structured oversized blazer in electric cobalt blue with sharp architectural shoulders and nipped waist creating an extreme hourglass power silhouette, underneath absolutely nothing but a black silk bralette, paired with matching cobalt blue tailored bermuda shorts hitting just above knee, bare legs, pointed-toe stiletto mules in nude, tiny structured micro bag in matching cobalt on gold chain, slicked-back wet-look hair, fierce power pose, clean bright studio lighting with blue color gel accents, luxury power dressing editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Cobalt Power\nコバルトパワー\n\n💙 Power blazer × Bermuda × Micro bag\nコバルトブルーのパワーショルダースーツ。\nColor is confidence.\n\nBlazer: Cobalt architectural shoulder\nTop: Black silk bralette\nShorts: Matching bermuda\nShoes: Nude stiletto mules\nBag: Cobalt micro bag\n\n#fashion #ootd #コーデ #パワースーツ #コバルト #ハイファッション #レディース #powerdressing #couture #styling",
    },
    {
        "gender": "male",
        "prompt": "Full body fashion editorial of a handsome 25-year-old Western male model with defined jawline, light stubble, and intense green eyes standing against a raw concrete wall, wearing a revolutionary layered look: a sleeveless long vest in heavy raw denim with frayed edges reaching mid-calf over a crisp white oversized dress shirt with extreme balloon sleeves, tucked into high-waisted wide pleated trousers in cream with a thick leather harness belt, chunky derby shoes with transparent clear rubber sole showing internal mechanism, round wire-frame sunglasses, single pearl earring, intellectual avant-garde pose with one hand adjusting glasses, warm golden hour side lighting, Japanese intellectual luxury editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Intellectual Raw\nインテレクチュアル ロウ\n\n🧠 Raw denim vest × Balloon shirt × Clear sole derbys\nロウデニム×バルーンシャツの知的レイヤード。\nThink different. Dress different.\n\nVest: Raw denim sleeveless long\nShirt: Balloon sleeve oversized\nPants: Cream wide pleats\nShoes: Clear sole derby\nAccessory: Pearl earring\n\n#fashion #ootd #コーデ #インテリ #デニム #アバンギャルド #メンズ #intellectual #rawdenim #styling",
    },
    {
        "gender": "female",
        "prompt": "Full body fashion photo of a stunning 25-year-old Western female model with sculpted cheekbones, flowing hair, and captivating blue eyes posing dramatically on marble stairs, wearing a head-turning outfit: a cropped leather jacket covered entirely in silver metal spike studs and crystal embellishments catching light everywhere, over a flowing sheer black organza maxi dress with visible black underwear silhouette, the dress trailing on steps, combat boots with chrome silver toe caps, multiple punk silver chain necklaces layered, dark dramatic smokey eye makeup, rebellious luxury pose sitting on stairs, dramatic chiaroscuro lighting with hard shadows, punk couture luxury editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Punk Couture\nパンク クチュール\n\n🔩 Studded leather × Sheer maxi × Chrome combat boots\nスタッズ×シアーの究極パンククチュール。\nDestruction is creation.\n\nJacket: Crystal studded leather\nDress: Sheer organza maxi\nBoots: Chrome toe combat\nJewelry: Layered punk chains\n\n#fashion #ootd #コーデ #パンク #クチュール #スタッズ #レディース #punk #couture #styling",
    },
    {
        "gender": "male",
        "prompt": "Full body fashion editorial of a handsome 25-year-old Western male model with defined jawline, light stubble, and intense green eyes in a stark white void studio, wearing an all-white monochromatic luxury outfit: oversized white double-breasted suit jacket with peaked lapels worn over a white turtleneck, white wide-leg tailored trousers with sharp crease, white chunky sole loafers, white leather belt bag worn across chest, white-framed angular sunglasses, all pieces in slightly different shades and textures of white creating tonal depth, minimal confident pose, pure white studio with soft diffused lighting creating subtle shadows showing texture differences, quiet luxury monochrome editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Total White\nトータルホワイト\n\n🤍 White suit × White turtleneck × White loafers\n全身ホワイトのトーナルグラデーション。\nEvery shade of white tells a story.\n\nJacket: Double-breasted peaked lapel\nKnit: White turtleneck\nPants: Wide-leg tailored\nShoes: Chunky sole loafers\nBag: White belt bag\n\n#fashion #ootd #コーデ #オールホワイト #モノクロ #ラグジュアリー #メンズ #totalwhite #quietluxury #styling",
    },
    {
        "gender": "female",
        "prompt": "Full body fashion editorial of a stunning 25-year-old Western female model with sculpted cheekbones, flowing hair, and captivating blue eyes walking through a futuristic mirrored corridor, wearing cutting-edge fashion: an oversized deconstructed trench coat in khaki with the back panel completely removed showing the internal construction and floating belt, over a tight black technical bodysuit with visible seam lines, one leg in a black leather thigh-high boot and the other in a white chunky sneaker creating deliberate asymmetry, carrying a large soft leather hobo bag in caramel, hair half-shaved half-long flowing, confident avant-garde walk, cool fluorescent corridor lighting with mirror reflections multiplying the silhouette, boundary-breaking luxury fashion editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Deconstructed Reality\nデコンストラクト リアリティ\n\n✂️ Open-back trench × Mismatched shoes × Tech bodysuit\n背面解体トレンチ×左右非対称シューズ。\nBreak the rules. Make new ones.\n\nCoat: Deconstructed open-back trench\nBodysuit: Black technical\nLeft foot: Thigh-high boot\nRight foot: White chunky sneaker\nBag: Caramel hobo\n\n#fashion #ootd #コーデ #脱構築 #アシンメトリー #前衛的 #レディース #deconstructed #avantgarde #styling",
    },
    {
        "gender": "male",
        "prompt": "Full body fashion photo of a handsome 25-year-old Western male model with defined jawline, light stubble, and intense green eyes leaning against a vintage European sports car, wearing ultra-luxury casual: a butter-soft unstructured blazer in rich chocolate brown suede with no lining visible at rolled cuffs, over a fine-gauge cream cashmere crew neck sweater, perfectly fitted dark olive chinos with no belt, sockless tan suede driving loafers, gold Cartier-style tank watch on wrist, tortoiseshell sunglasses pushed up on head, effortless old money confidence, warm Mediterranean golden hour light, Italian Riviera luxury lifestyle editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Riviera Money\nリヴィエラ マネー\n\n🏎️ Suede blazer × Cashmere × Driving loafers\nスエード×カシミヤのオールドマネースタイル。\nTrue luxury whispers.\n\nBlazer: Chocolate suede unstructured\nKnit: Cream cashmere crew\nPants: Olive chinos\nShoes: Tan suede loafers\nWatch: Gold tank\n\n#fashion #ootd #コーデ #オールドマネー #イタリア #カシミヤ #メンズ #oldmoney #quietluxury #riviera",
    },
    {
        "gender": "female",
        "prompt": "Full body editorial photo of a stunning 25-year-old Western female model with sculpted cheekbones, flowing hair, and captivating blue eyes posing in an industrial warehouse space, wearing a show-stopping outfit: an enormous voluminous puffer coat in highlighter neon yellow that engulfs her upper body like a wearable cloud, unzipped to reveal a skin-tight black catsuit underneath, paired with over-the-knee pointed-toe boots in glossy black patent leather, tiny structured box bag in matching neon yellow with gold chain handle, bold red lip, dramatic pose emerging from the puffer volume, harsh industrial lighting with yellow color cast from the coat reflecting on walls, avant-garde luxury streetwear campaign, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Neon Cloud\nネオンクラウド\n\n💛 Volume puffer × Catsuit × Patent boots\n蛍光イエローのクラウドパファーで包まれて。\nBe impossible to ignore.\n\nCoat: Neon yellow mega puffer\nBodysuit: Black catsuit\nBoots: Patent over-the-knee\nBag: Neon yellow box bag\n\n#fashion #ootd #コーデ #ネオン #パファー #ハイファッション #レディース #neon #puffer #statement",
    },
    {
        "gender": "male",
        "prompt": "Full body fashion editorial of a handsome 25-year-old Western male model with defined jawline, light stubble, and intense green eyes standing in a dimly lit concrete parking garage, wearing dark luxury: a matte black technical fabric bomber jacket with hidden magnetic closures and no visible hardware creating an impossibly clean silhouette, over a black mock neck in compression fabric, slim black coated denim jeans with waxed finish giving leather-like sheen, sleek black pointed Chelsea boots with hidden elastic in matching black, black leather card holder in hand, no visible logos anywhere on entire outfit, stealth wealth aesthetic, dramatic parking garage fluorescent mixed with car headlight beams, ultra-minimal dark luxury editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Stealth Mode\nステルスモード\n\n🖤 Tech bomber × Coated denim × Clean Chelsea\n一切のロゴなし、全身マットブラック。\nThe loudest statement is silence.\n\nBomber: Magnetic closure tech\nTop: Compression mock neck\nJeans: Waxed coated denim\nBoots: Sleek pointed Chelsea\n\n#fashion #ootd #コーデ #ステルスウェルス #ノーロゴ #ブラック #メンズ #stealthwealth #allblack #minimal",
    },
    {
        "gender": "female",
        "prompt": "Full body fashion photo of a stunning 25-year-old Western female model with sculpted cheekbones, flowing hair, and captivating blue eyes in a luxury hotel lobby with marble floors, wearing a daring luxury look: an oversized men's tuxedo jacket in midnight blue velvet worn as a dress with nothing underneath, belted at waist with a thick gold chain belt, bare legs, strappy gold metallic sandal heels, vintage-style gold cuff bracelet, small velvet evening bag in matching midnight blue, tousled effortless hair, confident stride through lobby, warm ambient hotel chandelier lighting creating velvet sheen, after-party luxury chic editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "After Hours Velvet\nアフターアワーズ ベルベット\n\n🌙 Velvet tuxedo as dress × Gold chain belt × Strappy heels\nベルベットタキシードをドレスとして。\nWho needs a dress when you have a tuxedo?\n\nJacket/Dress: Midnight blue velvet tuxedo\nBelt: Gold chain\nShoes: Gold strappy heels\nBag: Velvet evening clutch\nBracelet: Gold cuff\n\n#fashion #ootd #コーデ #ベルベット #タキシード #ゴールド #レディース #velvet #afterhours #styling",
    },
    {
        "gender": "male",
        "prompt": "Full body fashion editorial of a handsome 25-year-old Western male model with defined jawline, light stubble, and intense green eyes standing on a bridge overlooking a river at twilight, wearing boundary-pushing luxury: a hand-painted one-of-a-kind leather jacket with abstract expressionist brushstrokes in red blue and white over the entire black leather surface, paired with simple straight-leg black wool trousers, black leather double monk strap shoes, plain white crew neck tee underneath, the jacket being the sole statement piece, confident hands in trouser pockets pose, beautiful blue hour twilight sky with city lights beginning to glow, wearable art luxury editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Wearable Art\nウェアラブル アート\n\n🎨 Hand-painted leather × Simple trousers × Monk straps\n世界に一つの手描きレザージャケット。\nYour jacket is the gallery.\n\nJacket: Hand-painted leather\nTee: White crew neck\nPants: Black straight-leg wool\nShoes: Double monk strap\n\n#fashion #ootd #コーデ #アート #ペイント #レザー #メンズ #wearableart #handpainted #oneofone",
    },
    {
        "gender": "female",
        "prompt": "Full body editorial photo of a stunning 25-year-old Western female model with sculpted cheekbones, flowing hair, and captivating blue eyes on a rooftop at sunset, wearing luxury layering mastery: a long flowing sheer silk organza coat in pale blush pink worn open and billowing in the wind, over a structured black leather bustier corset top and high-waisted black cigarette pants, pointed-toe black kitten heel slingbacks, delicate gold layered necklaces including a pendant with single diamond, small structured black leather top-handle bag, wind catching the organza coat creating ethereal movement, dramatic golden sunset backlighting creating silhouette through sheer fabric, romantic luxury haute couture editorial, ultra photorealistic, shot on Canon EOS R5 85mm f1.4, sharp focus, detailed skin texture, natural skin pores visible, 8K RAW",
        "caption": "Ethereal Blush\nエーテリアル ブラッシュ\n\n🌸 Sheer organza coat × Leather bustier × Cigarette pants\nシアーオーガンザが風に舞うエーテリアルコーデ。\nHardness and softness in perfect balance.\n\nCoat: Blush silk organza\nTop: Black leather bustier\nPants: Black cigarette\nShoes: Kitten heel slingbacks\nBag: Structured top-handle\n\n#fashion #ootd #コーデ #シアー #オーガンザ #クチュール #レディース #ethereal #hautecouture #styling",
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


def add_cta(caption: str, category: str = "") -> str:
    """キャプションのハッシュタグ最適化 + CTA + アフィリエイト誘導を追加する。"""
    optimized = replace_hashtags(caption, category)
    cta = random.choice(CTAS)
    return optimized + cta + AFFILIATE_CTA


def auto_story(image_url: str) -> None:
    """投稿と同じ画像をストーリーにもシェアする（失敗してもメイン投稿に影響しない）。"""
    try:
        logging.info("[ストーリー] 自動ストーリー投稿中...")
        story_id = post_story_to_instagram(image_url)
        logging.info(f"[ストーリー] 完了! Story ID: {story_id}")
    except Exception as e:
        logging.warning(f"[ストーリー] 失敗（メイン投稿は成功）: {e}")


# --- カルーセル用アングルバリエーション ---
ANGLE_SUFFIXES = [
    ", close-up macro detail shot showing fabric texture and stitching, 8K",
    ", styled overhead flat lay with complementary accessories around it, lifestyle photography, 8K",
    ", side angle view showing silhouette and proportions, clean white background, lookbook style, 8K",
]

# --- コーデ用アングルバリエーション ---
OUTFIT_ANGLE_SUFFIXES = [
    ", close-up detail shot of upper body showing layering and accessories, portrait crop, 8K",
    ", full body from behind showing back details and silhouette, same setting, 8K",
    ", lower body focus showing pants shoes and bag details, 8K",
]


def post_ai_image():
    """AI生成画像をカルーセル投稿する。"""
    temp_image = os.path.join(os.path.dirname(__file__), "temp_image.jpg")

    try:
        idx, post = pick_unused_post(POSTS)
        prompt = post["prompt"]
        caption = add_cta(post["caption"])
        logging.info(f"[AI投稿] プロンプト: {prompt[:80]}...")

        image_urls = []

        # メイン画像
        logging.info("AI画像を生成中... (1/3 メイン)")
        generate_ai_image(prompt, temp_image)
        image_urls.append(upload_image(temp_image))

        # アングル違い画像 2枚
        for i, suffix in enumerate(random.sample(ANGLE_SUFFIXES, 2)):
            angle_prompt = prompt.rsplit(", 8K", 1)[0] + suffix
            logging.info(f"AI画像を生成中... ({i+2}/3 アングル)")
            generate_ai_image(angle_prompt, temp_image)
            image_urls.append(upload_image(temp_image))

        # カルーセル投稿
        post_id = post_carousel_to_instagram(image_urls, caption)
        logging.info(f"[AI投稿] 完了! Post ID: {post_id}")

        # ストーリーにもシェア（メイン画像を使用）
        auto_story(image_urls[0])
        return True

    finally:
        if os.path.exists(temp_image):
            os.remove(temp_image)


def post_ai_reel():
    """AI生成画像からスライドショー動画を作成してリール投稿する。"""
    base_dir = os.path.dirname(__file__)
    temp_video = os.path.join(base_dir, "temp_reel.mp4")
    reel_images = []

    try:
        idx, post = pick_unused_post(POSTS)
        prompt = post["prompt"]
        caption = add_cta(post["caption"])
        logging.info(f"[リール投稿] プロンプト: {prompt[:80]}...")

        # リール用縦長画像を4枚生成
        reel_images = generate_reel_images(prompt, output_dir=base_dir, num_images=4)

        # スライドショー動画生成（各3秒 = 合計12秒）
        generate_slideshow_video(reel_images, temp_video, duration_per_image=3.0)

        # 動画アップロード
        video_url = upload_video(temp_video)

        # カバー画像（1枚目を使用）
        cover_url = upload_image(reel_images[0])

        # リール投稿
        post_id = post_reel_to_instagram(video_url, caption, cover_url=cover_url)
        logging.info(f"[リール投稿] 完了! Post ID: {post_id}")

        # ストーリーにもカバー画像をシェア
        auto_story(cover_url)
        return True

    finally:
        # 一時ファイル削除
        if os.path.exists(temp_video):
            os.remove(temp_video)
        for img in reel_images:
            if os.path.exists(img):
                os.remove(img)


def post_amazon_product():
    """Amazon商品を取得して投稿する。"""
    product = amazon_pick_product()
    if not product:
        logging.warning("[Amazon] 商品が見つからず、楽天にフォールバック")
        return post_real_product()

    caption = add_cta(amazon_caption(product), category="product")
    logging.info(f"[Amazon] {product['name'][:50]}...")

    image_url = product["image_url"]
    post_id = post_to_instagram(image_url, caption)
    logging.info(f"[Amazon] 完了! Post ID: {post_id}")

    # ストーリーにもシェア
    auto_story(image_url)
    return True


def post_real_product():
    """楽天APIから実商品を取得してカルーセル投稿する。"""
    product = pick_random_product()
    if not product:
        logging.warning("[実商品] 商品が見つからず、AI投稿にフォールバック")
        return post_ai_image()

    caption = add_cta(rakuten_caption(product), category="product")
    logging.info(f"[実商品] {product['name'][:50]}...")
    logging.info(f"[実商品] ¥{product['price']:,}")

    # 商品画像をカルーセル投稿（複数画像があれば最大3枚）
    image_urls = product.get("all_images", [product["image_url"]])[:3]

    # 画像が1枚しかない場合は通常投稿
    if len(image_urls) == 1:
        post_id = post_to_instagram(image_urls[0], caption)
    else:
        post_id = post_carousel_to_instagram(image_urls, caption)

    logging.info(f"[実商品] 完了! Post ID: {post_id}")

    # ストーリーにもシェア（1枚目の画像を使用）
    auto_story(image_urls[0] if isinstance(image_urls, list) else product["image_url"])
    return True


# --- 投稿モード管理 ---
MODE_PATH = os.path.join(os.path.dirname(__file__), "post_mode.json")


def post_outfit_image():
    """モデル着用の全身コーデ画像をカルーセル投稿する。"""
    temp_image = os.path.join(os.path.dirname(__file__), "temp_image.jpg")

    try:
        idx, post = pick_unused_outfit(OUTFIT_POSTS)
        prompt = post["prompt"]
        caption = add_cta(post["caption"], category="outfit")
        logging.info(f"[コーデ投稿] プロンプト: {prompt[:80]}...")

        image_urls = []

        # メイン画像（全身）
        logging.info("AI画像を生成中... (1/3 メイン全身)")
        generate_ai_image(prompt, temp_image)
        image_urls.append(upload_image(temp_image))

        # アングル違い画像 2枚
        for i, suffix in enumerate(random.sample(OUTFIT_ANGLE_SUFFIXES, 2)):
            angle_prompt = prompt.rsplit(", 8K", 1)[0] + suffix
            logging.info(f"AI画像を生成中... ({i+2}/3 アングル)")
            generate_ai_image(angle_prompt, temp_image)
            image_urls.append(upload_image(temp_image))

        # カルーセル投稿
        post_id = post_carousel_to_instagram(image_urls, caption)
        logging.info(f"[コーデ投稿] 完了! Post ID: {post_id}")

        # ストーリーにもシェア（メイン画像を使用）
        auto_story(image_urls[0])
        return True

    finally:
        if os.path.exists(temp_image):
            os.remove(temp_image)


# --- コーデ用の投稿履歴管理（POSTS とは別管理）---
OUTFIT_HISTORY_PATH = os.path.join(os.path.dirname(__file__), "outfit_history.json")


def load_outfit_history() -> dict:
    default = {"posted_indices": [], "last_gender": None}
    if os.path.exists(OUTFIT_HISTORY_PATH):
        with open(OUTFIT_HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 古い形式（リスト）の場合は辞書形式にマイグレーション
            if isinstance(data, list):
                return {"posted_indices": data, "last_gender": None}
            return data
    return default


def save_outfit_history(history: dict) -> None:
    with open(OUTFIT_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f)


def pick_unused_outfit(posts: list[dict]) -> tuple[int, dict]:
    history_data = load_outfit_history()
    posted_indices = history_data["posted_indices"]
    last_gender = history_data.get("last_gender")

    all_indices = list(range(len(posts)))
    # まだ投稿していないインデックス
    available_indices = [i for i in all_indices if i not in posted_indices]

    if not available_indices:
        logging.info("全コーデ投稿済み → 履歴リセット")
        posted_indices = []
        available_indices = all_indices

    # 男女交互ロジック
    target_gender = "female" if last_gender == "male" else "male"
    
    # ターゲット性別の投稿候補を探す
    candidates = [i for i in available_indices if posts[i].get("gender") == target_gender]

    if not candidates:
        # ターゲット性別がない場合（例：片方だけ全部終わった）、残りの性別から選ぶ
        logging.info(f"{target_gender} の候補切れ → 残りから選択")
        candidates = available_indices
    
    idx = random.choice(candidates)
    post = posts[idx]
    
    # 履歴更新
    posted_indices.append(idx)
    save_outfit_history({"posted_indices": posted_indices, "last_gender": post.get("gender")})
    
    logging.info(f"コーデ選択: #{idx+1} ({post.get('gender')}) (残り: {len(available_indices)-1}件)")
    return idx, post


def get_next_mode() -> str:
    """次の投稿モードを取得する（コーデ投稿メイン）。"""
    # コーデ投稿を中心に、たまに商品・リールを挟む
    # 6回中4回がコーデ、1回が商品、1回がリール
    MODE_ROTATION = ["outfit", "outfit", "product", "outfit", "outfit", "reel"]

    if os.path.exists(MODE_PATH):
        with open(MODE_PATH, "r") as f:
            data = json.load(f)
            last_mode = data.get("last_mode", "reel")
    else:
        last_mode = "reel"

    try:
        current_idx = MODE_ROTATION.index(last_mode)
        next_mode = MODE_ROTATION[(current_idx + 1) % len(MODE_ROTATION)]
    except ValueError:
        next_mode = "outfit"

    with open(MODE_PATH, "w") as f:
        json.dump({"last_mode": next_mode}, f)

    return next_mode


def auto_post():
    """完全自動で1投稿を行う（AI画像 → 実商品 → リールのローテーション）。"""
    logging.info("=" * 40)
    logging.info("自動投稿を開始します")

    try:
        # Step 0: トークン確認＆自動更新
        logging.info("トークンを確認中...")
        if not auto_refresh():
            logging.error("トークンが無効です。python get_token.py を実行してください。")
            return False

        # Step 1: 投稿モード決定
        if RAKUTEN_AVAILABLE:
            mode = get_next_mode()
        else:
            # 楽天API使えなければ ai と reel を交互に
            if os.path.exists(MODE_PATH):
                with open(MODE_PATH, "r") as f:
                    last = json.load(f).get("last_mode", "reel")
                mode = "reel" if last == "ai" else "ai"
            else:
                mode = "ai"
            with open(MODE_PATH, "w") as f:
                json.dump({"last_mode": mode}, f)

        logging.info(f"投稿モード: {mode}")

        # Step 2: 投稿実行
        if mode == "product":
            result = post_real_product()
        elif mode == "reel":
            result = post_ai_reel()
        elif mode == "amazon":
            result = post_amazon_product()
        elif mode == "outfit":
            result = post_outfit_image()
        else:
            result = post_ai_image()

        # Step 3: 投稿分析（5投稿ごとに実行）
        if result:
            try:
                history = load_history()
                if len(history) % 5 == 0:
                    logging.info("[分析] 定期分析を実行中...")
                    analyze_posts()
            except Exception as e:
                logging.warning(f"[分析] 分析エラー（投稿は成功）: {e}")

        # Step 4: 自動アンフォロー（安全のため毎回実行、ただし内部で制限あり）
        # .env にユーザー名/パスワードがない場合はスキップされます
        if UNFOLLOW_AVAILABLE:
            try:
                unfollow_non_followers(max_unfollows=10)  # 1回あたり最大10人
            except Exception as e:
                logging.warning(f"[Unfollow] エラー（投稿は成功）: {e}")

        return result

    except Exception as e:
        logging.error(f"エラー発生: {e}")
        return False


if __name__ == "__main__":
    success = auto_post()
    sys.exit(0 if success else 1)
