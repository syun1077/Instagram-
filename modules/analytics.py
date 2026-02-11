"""
投稿分析・自動改善モジュール
Instagram Graph APIのインサイトを使用して投稿パフォーマンスを分析し、
次回の投稿戦略を自動最適化する。
"""

import os
import json
import logging
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
ANALYTICS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "analytics_data.json")


def _get_credentials() -> tuple[str, str]:
    access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    account_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
    return access_token, account_id


def load_analytics() -> dict:
    """分析データを読み込む。"""
    if os.path.exists(ANALYTICS_PATH):
        with open(ANALYTICS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"posts": [], "best_categories": {}, "best_hours": {}, "insights": {}}


def save_analytics(data: dict) -> None:
    """分析データを保存する。"""
    with open(ANALYTICS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_recent_media(limit: int = 25) -> list[dict]:
    """最近の投稿一覧を取得する。"""
    access_token, account_id = _get_credentials()
    if not access_token or not account_id:
        return []

    url = f"{GRAPH_API_BASE}/{account_id}/media"
    params = {
        "fields": "id,caption,timestamp,media_type,like_count,comments_count,permalink",
        "limit": limit,
        "access_token": access_token,
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        return data.get("data", [])
    except Exception as e:
        logging.warning(f"[分析] メディア取得エラー: {e}")
        return []


def fetch_media_insights(media_id: str) -> dict:
    """個別投稿のインサイトを取得する。"""
    access_token, _ = _get_credentials()

    url = f"{GRAPH_API_BASE}/{media_id}/insights"
    params = {
        "metric": "impressions,reach,engagement,saved",
        "access_token": access_token,
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        insights = {}
        for item in data.get("data", []):
            insights[item["name"]] = item["values"][0]["value"]
        return insights
    except Exception as e:
        logging.warning(f"[分析] インサイト取得エラー ({media_id}): {e}")
        return {}


def fetch_account_insights() -> dict:
    """アカウント全体のインサイトを取得する。"""
    access_token, account_id = _get_credentials()
    if not access_token or not account_id:
        return {}

    url = f"{GRAPH_API_BASE}/{account_id}/insights"
    params = {
        "metric": "impressions,reach,follower_count,profile_views",
        "period": "day",
        "access_token": access_token,
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        insights = {}
        for item in data.get("data", []):
            values = item.get("values", [])
            if values:
                insights[item["name"]] = values[-1]["value"]
        return insights
    except Exception as e:
        logging.warning(f"[分析] アカウントインサイト取得エラー: {e}")
        return {}


def analyze_posts() -> dict:
    """
    最近の投稿を分析してパフォーマンスレポートを生成する。

    Returns:
        分析結果のdict
    """
    logging.info("[分析] 投稿分析を開始...")
    media_list = fetch_recent_media(25)
    if not media_list:
        logging.warning("[分析] 投稿データなし")
        return {}

    analytics = load_analytics()
    post_scores = []

    for media in media_list:
        media_id = media["id"]
        likes = media.get("like_count", 0)
        comments = media.get("comments_count", 0)
        timestamp = media.get("timestamp", "")
        media_type = media.get("media_type", "")
        caption = media.get("caption", "")

        # インサイト取得
        insights = fetch_media_insights(media_id)

        # エンゲージメントスコア計算
        impressions = insights.get("impressions", 0)
        reach = insights.get("reach", 0)
        saved = insights.get("saved", 0)

        # スコア = (いいね*1 + コメント*3 + 保存*5) / リーチ * 100
        engagement_score = 0
        if reach > 0:
            engagement_score = (likes + comments * 3 + saved * 5) / reach * 100

        # 投稿時間を抽出
        hour = ""
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                # UTCをJSTに変換（+9時間）
                jst_hour = (dt.hour + 9) % 24
                hour = str(jst_hour)
            except Exception:
                pass

        # カテゴリ推定
        category = _detect_post_category(caption)

        post_data = {
            "id": media_id,
            "likes": likes,
            "comments": comments,
            "saved": saved,
            "impressions": impressions,
            "reach": reach,
            "engagement_score": round(engagement_score, 2),
            "media_type": media_type,
            "category": category,
            "hour": hour,
            "timestamp": timestamp,
        }
        post_scores.append(post_data)

    # カテゴリ別パフォーマンス
    category_scores = {}
    for post in post_scores:
        cat = post["category"]
        if cat not in category_scores:
            category_scores[cat] = []
        category_scores[cat].append(post["engagement_score"])

    best_categories = {}
    for cat, scores in category_scores.items():
        avg = sum(scores) / len(scores) if scores else 0
        best_categories[cat] = round(avg, 2)

    # 時間帯別パフォーマンス
    hour_scores = {}
    for post in post_scores:
        h = post["hour"]
        if h:
            if h not in hour_scores:
                hour_scores[h] = []
            hour_scores[h].append(post["engagement_score"])

    best_hours = {}
    for h, scores in hour_scores.items():
        avg = sum(scores) / len(scores) if scores else 0
        best_hours[h] = round(avg, 2)

    # メディアタイプ別パフォーマンス
    type_scores = {}
    for post in post_scores:
        mt = post["media_type"]
        if mt not in type_scores:
            type_scores[mt] = []
        type_scores[mt].append(post["engagement_score"])

    best_types = {}
    for mt, scores in type_scores.items():
        avg = sum(scores) / len(scores) if scores else 0
        best_types[mt] = round(avg, 2)

    # 分析結果を保存
    analytics["posts"] = post_scores
    analytics["best_categories"] = best_categories
    analytics["best_hours"] = best_hours
    analytics["best_types"] = best_types
    analytics["last_analyzed"] = datetime.now().isoformat()

    # 改善提案を生成
    analytics["insights"] = _generate_insights(best_categories, best_hours, best_types, post_scores)

    save_analytics(analytics)

    logging.info(f"[分析] 分析完了: {len(post_scores)}件の投稿を分析")
    logging.info(f"[分析] ベストカテゴリ: {best_categories}")
    logging.info(f"[分析] ベスト時間帯(JST): {best_hours}")
    logging.info(f"[分析] メディアタイプ別: {best_types}")

    return analytics


def _detect_post_category(caption: str) -> str:
    """キャプションから投稿カテゴリを推定する。"""
    caption_lower = caption.lower()
    categories = {
        "tops": ["hoodie", "tee", "shirt", "knit", "sweater", "blazer", "パーカー", "シャツ", "ニット"],
        "bottoms": ["jeans", "denim", "trousers", "pants", "cargo", "デニム", "パンツ", "トラウザー"],
        "shoes": ["sneaker", "boot", "derby", "slide", "runner", "スニーカー", "ブーツ", "サンダル"],
        "outerwear": ["puffer", "coat", "trench", "bomber", "vest", "パファー", "コート", "トレンチ"],
        "bags": ["bag", "tote", "backpack", "crossbody", "バッグ", "トート"],
        "accessories": ["sunglasses", "scarf", "belt", "gloves", "サングラス", "スカーフ", "ベルト"],
        "jewelry": ["bracelet", "ring", "earring", "pendant", "hoop", "ブレスレット", "リング", "ピアス"],
        "product": ["rakuten", "amazon", "購入"],
    }

    for cat, keywords in categories.items():
        if any(kw in caption_lower for kw in keywords):
            return cat
    return "other"


def _generate_insights(
    best_categories: dict,
    best_hours: dict,
    best_types: dict,
    post_scores: list[dict],
) -> dict:
    """分析結果から改善提案を生成する。"""
    insights = {}

    # ベストカテゴリ
    if best_categories:
        sorted_cats = sorted(best_categories.items(), key=lambda x: x[1], reverse=True)
        insights["top_category"] = sorted_cats[0][0]
        insights["worst_category"] = sorted_cats[-1][0]
        insights["category_recommendation"] = (
            f"{sorted_cats[0][0]}カテゴリのエンゲージメントが最も高い "
            f"(スコア: {sorted_cats[0][1]}%)。"
            f"{sorted_cats[0][0]}の投稿頻度を増やすことを推奨。"
        )

    # ベスト投稿時間
    if best_hours:
        sorted_hours = sorted(best_hours.items(), key=lambda x: x[1], reverse=True)
        insights["best_posting_hour"] = sorted_hours[0][0]
        insights["hour_recommendation"] = (
            f"JST {sorted_hours[0][0]}時台の投稿が最もエンゲージメントが高い "
            f"(スコア: {sorted_hours[0][1]}%)。"
        )

    # メディアタイプ
    if best_types:
        sorted_types = sorted(best_types.items(), key=lambda x: x[1], reverse=True)
        insights["best_media_type"] = sorted_types[0][0]
        insights["type_recommendation"] = (
            f"{sorted_types[0][0]}タイプの投稿が最もパフォーマンスが高い。"
        )

    # 全体的なエンゲージメント率
    if post_scores:
        avg_engagement = sum(p["engagement_score"] for p in post_scores) / len(post_scores)
        insights["avg_engagement"] = round(avg_engagement, 2)
        top_post = max(post_scores, key=lambda x: x["engagement_score"])
        insights["top_post_id"] = top_post["id"]
        insights["top_post_score"] = top_post["engagement_score"]

    return insights


def get_optimal_category() -> str:
    """
    分析データから最適なカテゴリを取得する。
    auto_post.pyから呼ばれ、投稿カテゴリの選択に使用。
    """
    analytics = load_analytics()
    top_cat = analytics.get("insights", {}).get("top_category", "")
    return top_cat


def get_optimal_posting_hour() -> int | None:
    """分析データから最適な投稿時間を取得する。"""
    analytics = load_analytics()
    best_hour = analytics.get("insights", {}).get("best_posting_hour", "")
    if best_hour:
        try:
            return int(best_hour)
        except ValueError:
            pass
    return None
