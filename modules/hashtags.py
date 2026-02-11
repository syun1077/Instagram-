"""
ハッシュタグ最適化モジュール
カテゴリ別に人気・中規模・ニッチタグを混合して最大リーチを狙う。
Instagram推奨: 3〜5個が最適、最大30個まで。
"""

import random

# --- カテゴリ別ハッシュタグプール ---
# 各カテゴリに大(100万+), 中(10万〜100万), 小(1万〜10万)を用意
HASHTAG_POOLS = {
    "tops": {
        "large": ["#fashion", "#ootd", "#style", "#mensfashion", "#streetwear", "#ファッション"],
        "medium": ["#hoodie", "#streetstyle", "#koreanfashion", "#メンズファッション", "#パーカー", "#モード"],
        "small": ["#oversizedhoodie", "#avantgardefashion", "#darkfashion", "#韓国ファッション", "#ストリートコーデ", "#オーバーサイズ"],
    },
    "bottoms": {
        "large": ["#fashion", "#ootd", "#style", "#mensfashion", "#denim", "#ファッション"],
        "medium": ["#widelegpants", "#streetstyle", "#cargopants", "#メンズファッション", "#デニム", "#ワイドパンツ"],
        "small": ["#widelegdenim", "#techwear", "#cargostyle", "#カーゴパンツ", "#テックウェア", "#ボトムス"],
    },
    "shoes": {
        "large": ["#fashion", "#sneakers", "#shoes", "#kicks", "#style", "#ファッション"],
        "medium": ["#platformshoes", "#boots", "#sneakerhead", "#スニーカー", "#ブーツ", "#厚底"],
        "small": ["#tabiboots", "#chunkyshoes", "#sockrunner", "#タビブーツ", "#ダービーシューズ", "#厚底スニーカー"],
    },
    "outerwear": {
        "large": ["#fashion", "#ootd", "#style", "#jacket", "#mensfashion", "#ファッション"],
        "medium": ["#pufferjacket", "#trenchcoat", "#outerwear", "#パファー", "#トレンチ", "#アウター"],
        "small": ["#hybridcoat", "#cocoonpuffer", "#avantgardecoat", "#ボンバージャケット", "#モードアウター", "#コクーン"],
    },
    "bags": {
        "large": ["#fashion", "#bag", "#style", "#luxury", "#accessories", "#ファッション"],
        "medium": ["#crossbodybag", "#leatherbag", "#totebag", "#バッグ", "#レザー", "#クロスボディ"],
        "small": ["#intrecciato", "#quietluxury", "#minimalbag", "#イントレチャート", "#ミニマルバッグ", "#職人技"],
    },
    "accessories": {
        "large": ["#fashion", "#accessories", "#style", "#jewelry", "#ootd", "#ファッション"],
        "medium": ["#sunglasses", "#scarf", "#belt", "#サングラス", "#スカーフ", "#アクセサリー"],
        "small": ["#silkscarf", "#gothicjewelry", "#luxuryaccessories", "#シルクスカーフ", "#ゴシック", "#ラグジュアリー"],
    },
    "jewelry": {
        "large": ["#fashion", "#jewelry", "#gold", "#accessories", "#style", "#ファッション"],
        "medium": ["#bracelet", "#rings", "#earrings", "#ジュエリー", "#ゴールド", "#リング"],
        "small": ["#stackablerings", "#goldvermeil", "#artisanjewelry", "#重ね付け", "#ハンドメイドジュエリー", "#ゴールドリング"],
    },
    "product": {
        "large": ["#fashion", "#ootd", "#shopping", "#style", "#mensfashion", "#ファッション"],
        "medium": ["#おすすめ", "#メンズファッション", "#コーデ", "#お洒落さんと繋がりたい", "#トレンド", "#韓国ファッション"],
        "small": ["#プチプラコーデ", "#楽天購入品", "#今日のコーデ", "#メンズコーデ", "#ファッション好き", "#着回しコーデ"],
    },
}

# 常に含めるブランディングタグ
BRAND_TAGS = ["#fashionpicks", "#dailyfashion"]

# エンゲージメントブーストタグ（時々追加）
ENGAGEMENT_TAGS = [
    "#お洒落さんと繋がりたい",
    "#ファッション好きな人と繋がりたい",
    "#服好きな人と繋がりたい",
    "#コーデ好き",
]


def detect_category(caption: str) -> str:
    """キャプションからカテゴリを推定する。"""
    caption_lower = caption.lower()

    category_keywords = {
        "tops": ["hoodie", "パーカー", "shirt", "シャツ", "tee", "knit", "ニット", "sweater", "organza"],
        "bottoms": ["pants", "パンツ", "denim", "デニム", "trousers", "トラウザー", "cargo", "カーゴ"],
        "shoes": ["sneaker", "スニーカー", "boot", "ブーツ", "shoe", "シューズ", "slide", "サンダル", "tabi", "タビ"],
        "outerwear": ["jacket", "ジャケット", "coat", "コート", "puffer", "パファー", "bomber", "ボンバー", "vest", "ベスト", "trench", "トレンチ"],
        "bags": ["bag", "バッグ", "tote", "トート", "crossbody", "クロスボディ", "backpack", "バックパック"],
        "accessories": ["sunglasses", "サングラス", "scarf", "スカーフ", "belt", "ベルト", "gloves", "グローブ"],
        "jewelry": ["ring", "リング", "bracelet", "ブレスレット", "earring", "イヤリング", "pendant", "ペンダント", "necklace", "ネックレス", "chain", "チェーン"],
    }

    for category, keywords in category_keywords.items():
        if any(kw in caption_lower for kw in keywords):
            return category

    return "tops"  # デフォルト


def generate_hashtags(caption: str, category: str = "", max_tags: int = 20) -> str:
    """
    最適化されたハッシュタグセットを生成する。

    構成比:
    - 大 (100万+投稿): 3個 → 発見タブ入りのチャンス
    - 中 (10万〜100万): 5個 → 競争率適度
    - 小 (1万〜10万): 5個 → 上位表示されやすい
    - エンゲージメント: 2個 → 日本語圏のつながり
    - ブランド: 2個 → 固定タグ
    """
    if not category:
        category = detect_category(caption)

    pool = HASHTAG_POOLS.get(category, HASHTAG_POOLS["tops"])

    large = random.sample(pool["large"], min(3, len(pool["large"])))
    medium = random.sample(pool["medium"], min(5, len(pool["medium"])))
    small = random.sample(pool["small"], min(5, len(pool["small"])))
    engage = random.sample(ENGAGEMENT_TAGS, min(2, len(ENGAGEMENT_TAGS)))

    all_tags = large + medium + small + engage + BRAND_TAGS

    # 重複除去（順序維持）
    seen = set()
    unique_tags = []
    for tag in all_tags:
        if tag not in seen:
            seen.add(tag)
            unique_tags.append(tag)

    # 最大数に制限
    final_tags = unique_tags[:max_tags]
    random.shuffle(final_tags)

    return " ".join(final_tags)


def replace_hashtags(caption: str, category: str = "") -> str:
    """キャプション内の既存ハッシュタグを最適化されたものに置き換える。"""
    # 既存のハッシュタグ部分を除去
    lines = caption.split("\n")
    clean_lines = []
    for line in lines:
        # ハッシュタグだけの行を除外
        stripped = line.strip()
        if stripped and all(word.startswith("#") for word in stripped.split() if word):
            continue
        clean_lines.append(line)

    clean_caption = "\n".join(clean_lines).rstrip()
    new_tags = generate_hashtags(caption, category)

    return f"{clean_caption}\n\n{new_tags}"
