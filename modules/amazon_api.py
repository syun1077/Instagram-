"""
Amazonアフィリエイト連携モジュール
Amazon PA-API 5.0を使用して商品を検索し、アフィリエイトリンク付きキャプションを生成する。
PA-APIが利用できない場合はAmazonアソシエイトリンクを直接生成する。
"""

import os
import random
import hashlib
import hmac
import json
from datetime import datetime, timezone
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv()

# Amazon PA-API 5.0 エンドポイント（日本）
PAAPI_HOST = "webservices.amazon.co.jp"
PAAPI_ENDPOINT = f"https://{PAAPI_HOST}/paapi5/searchitems"

# ファッションカテゴリのASIN検索キーワード
FASHION_KEYWORDS = [
    "メンズ パーカー ストリート",
    "メンズ デニム ワイド",
    "レディース ニット オーバーサイズ",
    "スニーカー 厚底",
    "レザーバッグ ミニマル",
    "メンズ テーラードジャケット",
    "アクセサリー ゴールド チェーン",
    "メンズ カーゴパンツ",
    "レディース トレンチコート",
    "シルバー リング メンズ",
    "メンズ ブーツ レザー",
    "レディース サングラス",
]


def _get_credentials() -> tuple[str, str, str]:
    """Amazon PA-API認証情報を取得する。"""
    access_key = os.getenv("AMAZON_ACCESS_KEY", "")
    secret_key = os.getenv("AMAZON_SECRET_KEY", "")
    partner_tag = os.getenv("AMAZON_PARTNER_TAG", "")
    return access_key, secret_key, partner_tag


def _is_available() -> bool:
    """PA-API認証情報が設定されているか確認する。"""
    access_key, secret_key, partner_tag = _get_credentials()
    return bool(access_key and secret_key and partner_tag)


def _sign(key: bytes, msg: str) -> bytes:
    """HMAC-SHA256署名を生成する。"""
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _get_signature_key(key: str, date_stamp: str, region: str, service: str) -> bytes:
    """AWS Signature V4の署名キーを生成する。"""
    k_date = _sign(("AWS4" + key).encode("utf-8"), date_stamp)
    k_region = _sign(k_date, region)
    k_service = _sign(k_region, service)
    k_signing = _sign(k_service, "aws4_request")
    return k_signing


def search_products(keyword: str = "", max_results: int = 5) -> list[dict]:
    """
    Amazon PA-API 5.0で商品を検索する。

    Args:
        keyword: 検索キーワード（空の場合ランダム選択）
        max_results: 最大取得件数

    Returns:
        商品情報のリスト
    """
    access_key, secret_key, partner_tag = _get_credentials()

    if not all([access_key, secret_key, partner_tag]):
        print("[Amazon] PA-API認証情報が未設定です")
        return []

    if not keyword:
        keyword = random.choice(FASHION_KEYWORDS)

    payload = {
        "Keywords": keyword,
        "SearchIndex": "Fashion",
        "ItemCount": max_results,
        "PartnerTag": partner_tag,
        "PartnerType": "Associates",
        "Marketplace": "www.amazon.co.jp",
        "Resources": [
            "Images.Primary.Large",
            "ItemInfo.Title",
            "Offers.Listings.Price",
            "ItemInfo.Features",
        ],
    }

    # AWS Signature V4
    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    region = "us-west-2"
    service = "ProductAdvertisingAPI"

    payload_json = json.dumps(payload)
    headers = {
        "content-type": "application/json; charset=utf-8",
        "content-encoding": "amz-1.0",
        "host": PAAPI_HOST,
        "x-amz-date": amz_date,
        "x-amz-target": "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems",
    }

    # Canonical request
    canonical_uri = "/paapi5/searchitems"
    canonical_querystring = ""
    signed_headers = "content-encoding;content-type;host;x-amz-date;x-amz-target"
    payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

    canonical_headers = (
        f"content-encoding:{headers['content-encoding']}\n"
        f"content-type:{headers['content-type']}\n"
        f"host:{headers['host']}\n"
        f"x-amz-date:{headers['x-amz-date']}\n"
        f"x-amz-target:{headers['x-amz-target']}\n"
    )

    canonical_request = (
        f"POST\n{canonical_uri}\n{canonical_querystring}\n"
        f"{canonical_headers}\n{signed_headers}\n{payload_hash}"
    )

    # String to sign
    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = (
        f"{algorithm}\n{amz_date}\n{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )

    # Signature
    signing_key = _get_signature_key(secret_key, date_stamp, region, service)
    signature = hmac.new(
        signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    # Authorization header
    authorization = (
        f"{algorithm} Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    headers["Authorization"] = authorization

    print(f"[Amazon] 商品検索中: {keyword}")
    try:
        response = requests.post(PAAPI_ENDPOINT, headers=headers, data=payload_json, timeout=30)
        data = response.json()
    except Exception as e:
        print(f"[Amazon] APIリクエストエラー: {e}")
        return []

    if "Errors" in data:
        print(f"[Amazon] APIエラー: {data['Errors'][0].get('Message', '不明')}")
        return []

    items = data.get("SearchResult", {}).get("Items", [])
    products = []
    for item in items:
        title = item.get("ItemInfo", {}).get("Title", {}).get("DisplayValue", "")
        image_url = (
            item.get("Images", {}).get("Primary", {}).get("Large", {}).get("URL", "")
        )
        price_info = (
            item.get("Offers", {})
            .get("Listings", [{}])[0]
            .get("Price", {})
        )
        price = price_info.get("Amount", 0)
        price_display = price_info.get("DisplayAmount", "")
        detail_url = item.get("DetailPageURL", "")

        if title and image_url:
            products.append({
                "name": title,
                "image_url": image_url,
                "price": int(price) if price else 0,
                "price_display": price_display,
                "url": detail_url,
                "asin": item.get("ASIN", ""),
            })

    print(f"[Amazon] {len(products)}件の商品を取得")
    return products


def generate_affiliate_link(asin: str = "", keyword: str = "") -> str:
    """
    Amazonアソシエイトリンクを生成する。
    PA-APIが使えなくても、パートナータグさえあれば直接リンクを生成できる。

    Args:
        asin: 商品ASIN（指定時はその商品へのリンク）
        keyword: 検索キーワード（ASIN未指定時は検索結果ページへのリンク）

    Returns:
        アフィリエイトリンクURL
    """
    _, _, partner_tag = _get_credentials()
    if not partner_tag:
        return ""

    if asin:
        return f"https://www.amazon.co.jp/dp/{asin}?tag={partner_tag}"
    elif keyword:
        encoded = quote(keyword)
        return f"https://www.amazon.co.jp/s?k={encoded}&tag={partner_tag}"
    return ""


def generate_caption(product: dict) -> str:
    """Amazon商品のキャプションを生成する。"""
    name = product["name"]
    price_display = product.get("price_display", "")
    url = product.get("url", "")

    caption = f"{name}\n\n"
    if price_display:
        caption += f"Price: {price_display}\n"
    caption += "\nAmazonで購入可能\nAvailable on Amazon\n"

    return caption


def pick_random_product() -> dict | None:
    """ランダムなファッション商品を1つ取得する。"""
    keyword = random.choice(FASHION_KEYWORDS)
    products = search_products(keyword, max_results=5)
    if products:
        return random.choice(products)
    return None
