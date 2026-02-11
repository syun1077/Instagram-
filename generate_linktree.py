"""
アフィリエイトリンクページ生成スクリプト
プロフィールに貼るリンク先HTMLを生成する。
楽天・Amazon検索URLを自動生成。
"""

import urllib.parse

# --- アフィリエイトID（ここに自分のIDを設定） ---
RAKUTEN_AFFILIATE_ID = "50ea7249.f430e39c.50ea724a.973b1974"
AMAZON_ASSOCIATE_TAG = "107704-22"

# --- おすすめアイテムキーワード ---
ITEMS = [
    {"name": "Oversized Hoodie / オーバーサイズパーカー", "keywords": "オーバーサイズ パーカー メンズ 韓国"},
    {"name": "Deconstructed Blazer / デコンストラクトブレザー", "keywords": "モード ブレザー メンズ オーバーサイズ"},
    {"name": "Leather Trench / レザートレンチコート", "keywords": "レザー トレンチコート メンズ"},
    {"name": "Wide-Leg Denim / ワイドデニム", "keywords": "ワイドパンツ デニム メンズ"},
    {"name": "Technical Cargo / テクニカルカーゴ", "keywords": "テックウェア カーゴパンツ メンズ"},
    {"name": "Platform Sneakers / 厚底スニーカー", "keywords": "厚底 スニーカー メンズ 韓国"},
    {"name": "Tabi Boots / タビブーツ", "keywords": "足袋ブーツ メンズ"},
    {"name": "Woven Leather Bag / 編み込みレザーバッグ", "keywords": "イントレチャート バッグ レザー"},
    {"name": "Silver Chain / シルバーチェーン", "keywords": "シルバー925 チェーンネックレス メンズ"},
    {"name": "Gothic Cross / ゴシッククロス", "keywords": "ゴシック クロス ペンダント シルバー"},
    {"name": "Puffer Jacket / パファージャケット", "keywords": "パファージャケット メンズ オーバーサイズ"},
    {"name": "Gold Ring Set / ゴールドリングセット", "keywords": "メンズ リング ゴールド セット"},
]


def generate_rakuten_url(keywords: str) -> str:
    encoded = urllib.parse.quote(keywords)
    base = f"https://search.rakuten.co.jp/search/mall/{encoded}/"
    if RAKUTEN_AFFILIATE_ID:
        return f"https://hb.afl.rakuten.co.jp/hgc/{RAKUTEN_AFFILIATE_ID}/?pc={urllib.parse.quote(base)}"
    return base


def generate_amazon_url(keywords: str) -> str:
    encoded = urllib.parse.quote(keywords)
    base = f"https://www.amazon.co.jp/s?k={encoded}"
    if AMAZON_ASSOCIATE_TAG:
        return f"{base}&tag={AMAZON_ASSOCIATE_TAG}"
    return base


def generate_html() -> str:
    html = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fashion Picks</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0a0a0a; color: #fff;
            min-height: 100vh; padding: 20px;
        }
        .container { max-width: 480px; margin: 0 auto; }
        h1 {
            text-align: center; font-size: 1.5rem;
            margin-bottom: 8px; letter-spacing: 2px;
        }
        .subtitle {
            text-align: center; color: #888;
            font-size: 0.85rem; margin-bottom: 24px;
        }
        .item {
            background: #1a1a1a; border-radius: 12px;
            padding: 16px; margin-bottom: 12px;
        }
        .item-name {
            font-weight: 600; font-size: 0.95rem;
            margin-bottom: 10px;
        }
        .links { display: flex; gap: 8px; }
        .links a {
            flex: 1; text-align: center; padding: 10px;
            border-radius: 8px; text-decoration: none;
            font-size: 0.85rem; font-weight: 600;
        }
        .rakuten { background: #bf0000; color: #fff; }
        .amazon { background: #ff9900; color: #000; }
        .footer {
            text-align: center; color: #555;
            font-size: 0.75rem; margin-top: 24px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>FASHION PICKS</h1>
        <p class="subtitle">Tap to find similar items / タップして類似アイテムを探す</p>
"""

    for item in ITEMS:
        rakuten_url = generate_rakuten_url(item["keywords"])
        amazon_url = generate_amazon_url(item["keywords"])
        html += f"""
        <div class="item">
            <div class="item-name">{item["name"]}</div>
            <div class="links">
                <a href="{rakuten_url}" target="_blank" class="rakuten">楽天で探す</a>
                <a href="{amazon_url}" target="_blank" class="amazon">Amazonで探す</a>
            </div>
        </div>
"""

    html += """
        <p class="footer">Updated daily / 毎日更新中</p>
    </div>
</body>
</html>
"""
    return html


if __name__ == "__main__":
    html = generate_html()
    output_path = "linktree.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"リンクページ生成完了: {output_path}")
    print("このHTMLをGitHub PagesやNetlifyでホスティングし、")
    print("Instagramプロフィールのリンクに設定してください。")
