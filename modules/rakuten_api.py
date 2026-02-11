"""
楽天商品検索APIモジュール
実際の商品画像・価格・アフィリエイトURLを取得する。
楽天アフィリエイトID取得: https://affiliate.rakuten.co.jp/
楽天API登録: https://webservice.rakuten.co.jp/
"""

import requests
import os
import random
from dotenv import load_dotenv

load_dotenv()

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20220601"


def _get_credentials() -> tuple[str, str]:
    """楽天API認証情報を取得する。"""
    app_id = os.getenv("RAKUTEN_APP_ID")
    access_key = os.getenv("RAKUTEN_ACCESS_KEY", "")
    if not app_id:
        raise ValueError(
            "RAKUTEN_APP_ID が .env に設定されていません。\n"
            "https://webservice.rakuten.co.jp/ で無料取得できます。"
        )
    return app_id, access_key


def search_products(
    keyword: str,
    genre_id: str = "",
    hits: int = 10,
    sort: str = "-reviewCount",
    min_price: int = 0,
    max_price: int = 0,
) -> list[dict]:
    """
    楽天市場から商品を検索する。

    Args:
        keyword: 検索キーワード
        genre_id: ジャンルID（ファッション: 100371）
        hits: 取得件数（最大30）
        sort: ソート順（-reviewCount, -reviewAverage, +itemPrice, -itemPrice）
        min_price: 最低価格
        max_price: 最高価格

    Returns:
        商品情報のリスト
    """
    app_id, access_key = _get_credentials()
    affiliate_id = os.getenv("RAKUTEN_AFFILIATE_ID", "")

    params = {
        "applicationId": app_id,
        "keyword": keyword,
        "hits": hits,
        "sort": sort,
        "imageFlag": 1,
        "format": "json",
    }

    if access_key:
        params["accessKey"] = access_key
    if affiliate_id:
        params["affiliateId"] = affiliate_id
    if genre_id:
        params["genreId"] = genre_id
    if min_price > 0:
        params["minPrice"] = min_price
    if max_price > 0:
        params["maxPrice"] = max_price

    headers = {
        "Origin": "https://github.com",
        "Referer": "https://github.com/",
    }

    response = requests.get(RAKUTEN_API_URL, params=params, headers=headers, timeout=30)
    data = response.json()

    if "error" in data:
        raise RuntimeError(f"楽天API エラー: {data['error']}")
    if "errors" in data:
        raise RuntimeError(f"楽天API エラー: {data['errors']}")

    items = data.get("Items", [])
    results = []

    for item_wrapper in items:
        item = item_wrapper.get("Item", {})
        images = item.get("mediumImageUrls", [])
        if not images:
            continue

        # 画像URLを高画質版に変換（128x128 → 実サイズ）
        image_url = images[0].get("imageUrl", "")
        image_url = image_url.replace("?_ex=128x128", "?_ex=500x500")

        # アフィリエイトURLがあればそちらを使う
        product_url = item.get("affiliateUrl") or item.get("itemUrl", "")

        results.append({
            "name": item.get("itemName", ""),
            "price": item.get("itemPrice", 0),
            "image_url": image_url,
            "product_url": product_url,
            "shop": item.get("shopName", ""),
            "review_avg": item.get("reviewAverage", 0),
            "review_count": item.get("reviewCount", 0),
            "all_images": [
                img.get("imageUrl", "").replace("?_ex=128x128", "?_ex=500x500")
                for img in images
            ],
        })

    return results


# --- ファッションカテゴリ別の検索キーワード ---
FASHION_SEARCHES = [
    {"keyword": "オーバーサイズ パーカー メンズ 韓国", "category": "Tops"},
    {"keyword": "デニムジャケット メンズ ヴィンテージ", "category": "Outerwear"},
    {"keyword": "ワイドパンツ メンズ ストリート", "category": "Bottoms"},
    {"keyword": "厚底 スニーカー メンズ 韓国", "category": "Shoes"},
    {"keyword": "レザー ショルダーバッグ メンズ", "category": "Bags"},
    {"keyword": "シルバー チェーンネックレス メンズ", "category": "Accessories"},
    {"keyword": "テックウェア カーゴパンツ", "category": "Bottoms"},
    {"keyword": "MA-1 ボンバージャケット メンズ", "category": "Outerwear"},
    {"keyword": "ニット セーター メンズ モード", "category": "Tops"},
    {"keyword": "トラックジャケット レトロ", "category": "Outerwear"},
    {"keyword": "バケットハット ストリート", "category": "Accessories"},
    {"keyword": "チェストバッグ メンズ ストリート", "category": "Bags"},
    {"keyword": "リング メンズ シルバー925", "category": "Accessories"},
    {"keyword": "サングラス メンズ スポーツ", "category": "Accessories"},
    {"keyword": "コンバットブーツ 厚底", "category": "Shoes"},
    {"keyword": "パファージャケット メンズ", "category": "Outerwear"},
    {"keyword": "スウェット クルーネック ビッグシルエット", "category": "Tops"},
    {"keyword": "カーゴパンツ メンズ ミリタリー", "category": "Bottoms"},
    {"keyword": "レザーベルト メンズ ブランド", "category": "Accessories"},
    {"keyword": "ダービーシューズ 厚底 メンズ", "category": "Shoes"},
]


def pick_random_product() -> dict | None:
    """
    ランダムなカテゴリから人気商品を1つ選んで返す。

    Returns:
        商品情報 or None
    """
    search = random.choice(FASHION_SEARCHES)
    print(f"[楽天API] 検索: {search['keyword']}")

    try:
        products = search_products(
            keyword=search["keyword"],
            hits=10,
            sort="-reviewCount",
            min_price=2000,
            max_price=30000,
        )
    except Exception as e:
        print(f"[楽天API] 検索エラー: {e}")
        return None

    if not products:
        print("[楽天API] 商品が見つかりませんでした")
        return None

    # レビュー数上位5件からランダムに選択
    top_products = products[:5]
    product = random.choice(top_products)
    product["category"] = search["category"]
    product["search_keyword"] = search["keyword"]

    print(f"[楽天API] 選択: {product['name'][:50]}...")
    print(f"[楽天API] 価格: {product['price']:,}円")
    print(f"[楽天API] レビュー: {product['review_avg']}/5.0 ({product['review_count']}件)")

    return product


def generate_caption(product: dict) -> str:
    """商品情報からInstagramキャプションを生成する。"""
    name = product["name"]
    # 商品名が長すぎる場合は短縮
    if len(name) > 60:
        name = name[:57] + "..."

    price = product["price"]
    shop = product["shop"]
    review = product["review_avg"]
    category = product.get("category", "Fashion")

    caption = (
        f"{name}\n\n"
        f"¥{price:,} tax included\n"
        f"⭐ {review}/5.0 rating\n"
        f"🏪 {shop}\n\n"
        f"Real item, real quality.\n"
        f"本物のアイテム、本物のクオリティ。\n\n"
        f"#fashion #ファッション #{category.lower()} #ootd "
        f"#お洒落さんと繋がりたい #コーデ #メンズファッション "
        f"#トレンド #shopping #おすすめ"
    )

    return caption


if __name__ == "__main__":
    product = pick_random_product()
    if product:
        print(f"\n商品名: {product['name']}")
        print(f"価格: ¥{product['price']:,}")
        print(f"画像: {product['image_url']}")
        print(f"URL: {product['product_url']}")
        print(f"\n--- キャプション ---")
        print(generate_caption(product))
