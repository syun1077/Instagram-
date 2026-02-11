"""
Instagram Insights 分析モジュール
投稿のパフォーマンスを取得・分析する。
"""

import requests
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
INSIGHTS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "insights_data.json")


def _get_credentials() -> tuple[str, str]:
    access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    account_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
    if not access_token or not account_id:
        raise ValueError("認証情報が設定されていません。")
    return access_token, account_id


def get_post_insights(post_id: str) -> dict:
    """投稿のインサイト（いいね、コメント、リーチ、保存数）を取得する。"""
    access_token, _ = _get_credentials()

    # 基本メトリクス（likes, comments）
    url = f"{GRAPH_API_BASE}/{post_id}"
    params = {
        "fields": "like_count,comments_count,timestamp,caption",
        "access_token": access_token,
    }
    response = requests.get(url, params=params, timeout=30)
    data = response.json()

    if "error" in data:
        print(f"[Insights] エラー: {data['error'].get('message')}")
        return {}

    result = {
        "post_id": post_id,
        "likes": data.get("like_count", 0),
        "comments": data.get("comments_count", 0),
        "timestamp": data.get("timestamp", ""),
        "caption_preview": (data.get("caption") or "")[:60],
    }

    # 詳細インサイト（リーチ、保存など）
    insights_url = f"{GRAPH_API_BASE}/{post_id}/insights"
    insights_params = {
        "metric": "impressions,reach,saved",
        "access_token": access_token,
    }
    insights_resp = requests.get(insights_url, params=insights_params, timeout=30)
    insights_data = insights_resp.json()

    if "data" in insights_data:
        for metric in insights_data["data"]:
            name = metric.get("name", "")
            value = metric.get("values", [{}])[0].get("value", 0)
            result[name] = value

    return result


def get_recent_posts(limit: int = 25) -> list[str]:
    """最近の投稿IDを取得する。"""
    access_token, account_id = _get_credentials()
    url = f"{GRAPH_API_BASE}/{account_id}/media"
    params = {
        "limit": limit,
        "access_token": access_token,
    }
    response = requests.get(url, params=params, timeout=30)
    data = response.json()

    if "error" in data:
        print(f"[Insights] エラー: {data['error'].get('message')}")
        return []

    return [item["id"] for item in data.get("data", [])]


def analyze_all_posts() -> list[dict]:
    """全投稿のインサイトを取得して分析結果を返す。"""
    print("[Insights] 最近の投稿を取得中...")
    post_ids = get_recent_posts()
    print(f"[Insights] {len(post_ids)}件の投稿を分析中...")

    results = []
    for i, pid in enumerate(post_ids):
        print(f"[Insights] 分析中... ({i+1}/{len(post_ids)})")
        insight = get_post_insights(pid)
        if insight:
            results.append(insight)

    # エンゲージメント率でソート
    results.sort(
        key=lambda x: x.get("likes", 0) + x.get("saved", 0) * 3,
        reverse=True,
    )

    # ファイルに保存
    output = {
        "analyzed_at": datetime.now().isoformat(),
        "total_posts": len(results),
        "posts": results,
    }
    with open(INSIGHTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[Insights] 分析結果を保存: {INSIGHTS_PATH}")

    return results


def print_report() -> None:
    """分析レポートを表示する。"""
    results = analyze_all_posts()

    if not results:
        print("分析できる投稿がありません。")
        return

    print("\n" + "=" * 60)
    print("  Instagram Insights レポート")
    print("=" * 60)

    total_likes = sum(r.get("likes", 0) for r in results)
    total_saves = sum(r.get("saved", 0) for r in results)
    total_reach = sum(r.get("reach", 0) for r in results)

    print(f"\n  投稿数: {len(results)}")
    print(f"  総いいね: {total_likes}")
    print(f"  総保存数: {total_saves}")
    print(f"  総リーチ: {total_reach}")
    print(f"  平均いいね/投稿: {total_likes / len(results):.1f}")

    print("\n--- トップ5投稿 (エンゲージメント順) ---")
    for i, r in enumerate(results[:5], 1):
        print(f"\n  #{i}: {r.get('caption_preview', 'N/A')}")
        print(f"      ❤️ {r.get('likes', 0)} | 💬 {r.get('comments', 0)} | 💾 {r.get('saved', 0)} | 👁️ {r.get('reach', 0)}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    print_report()
