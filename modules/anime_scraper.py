"""
アニメ画像スクレイパーモジュール
Wallhaven APIから進撃の巨人・呪術廻戦・ワンピースのアニメ壁紙を取得する。
"""

import random
import requests
import os
import logging
from PIL import Image

ANIME_SERIES = {
    "進撃の巨人": {
        "query": "attack on titan",
        "hashtags": [
            "#進撃の巨人", "#AttackOnTitan", "#SNK", "#ShingekiNoKyojin",
            "#エレン", "#ErenYeager", "#ミカサ", "#MikasaAckerman",
            "#リヴァイ", "#LeviFanart", "#アルミン", "#調査兵団",
            "#aot", "#aotfanart", "#aotedit", "#attackontitanfanart",
            "#anime", "#animeart", "#animefanart", "#animeartwork",
            "#manga", "#mangaart", "#otaku", "#weeb",
            "#japaneseanimation", "#日本アニメ", "#アニメ", "#アニメイラスト",
            "#animewallpaper", "#animeedit", "#animecharacter",
        ],
        "title": "進撃の巨人",
        "title_en": "Attack on Titan",
        "desc_en": [
            "The walls couldn't contain the story. 🗡️",
            "Freedom is worth fighting for. ⚔️",
            "Beyond the walls lies the truth. 🌊",
            "The rumbling has begun. 🔥",
            "Every scar tells a story. 💥",
        ],
    },
    "呪術廻戦": {
        "query": "jujutsu kaisen",
        "hashtags": [
            "#呪術廻戦", "#JujutsuKaisen", "#JJK", "#JJKfanart",
            "#五条悟", "#GojoSatoru", "#虎杖悠仁", "#ItadoriYuji",
            "#伏黒恵", "#MegumiFushiguro", "#野薔薇", "#NobaraKugisaki",
            "#sukuna", "#ryomensukuna", "#gojo", "#jjkedit",
            "#jjkfanart", "#jujutsukaisen0", "#jujutsukaisenfanart",
            "#anime", "#animeart", "#animefanart", "#animeartwork",
            "#manga", "#mangaart", "#otaku", "#weeb",
            "#japaneseanimation", "#日本アニメ", "#アニメ", "#アニメイラスト",
            "#animewallpaper", "#animeedit",
        ],
        "title": "呪術廻戦",
        "title_en": "Jujutsu Kaisen",
        "desc_en": [
            "Cursed energy never looked this good. 💜",
            "Gojo would approve of this. 👁️",
            "The strongest — no cap. 🔵",
            "Cursed techniques on full display. ⚡",
            "Domain Expansion: your feed. 🌀",
        ],
    },
    "ワンピース": {
        "query": "one piece anime",
        "hashtags": [
            "#ワンピース", "#OnePiece", "#OnePieceFanart",
            "#ルフィ", "#MonkeyDLuffy", "#ゾロ", "#RoronoaZoro",
            "#サンジ", "#VinsmokeSanji", "#ナミ", "#海賊王",
            "#麦わら海賊団", "#StrawHatPirates", "#luffy", "#zoro",
            "#onepieceedit", "#onepiecemanga", "#onepieceart",
            "#gear5", "#gear5luffy", "#mugiwara",
            "#anime", "#animeart", "#animefanart", "#animeartwork",
            "#manga", "#mangaart", "#otaku", "#weeb",
            "#japaneseanimation", "#日本アニメ", "#アニメ", "#アニメイラスト",
            "#animewallpaper", "#animeedit",
        ],
        "title": "ワンピース",
        "title_en": "One Piece",
        "desc_en": [
            "I'm gonna be King of the Pirates! 🏴‍☠️",
            "The Grand Line never looked this epic. 🌊",
            "Nakama forever. ❤️‍🔥",
            "Finding the One Piece, one post at a time. ⚓",
            "The will of D. lives on. 🔥",
        ],
    },
    "マーベル": {
        "query": "marvel comics",
        "hashtags": [
            "#Marvel", "#MarvelComics", "#MCU", "#MarvelUniverse",
            "#SpiderMan", "#IronMan", "#Thor", "#CaptainAmerica",
            "#BlackPanther", "#WandaMaximoff", "#Avengers", "#Xmen",
            "#Deadpool", "#Wolverine", "#MarvelArt", "#MarvelFanart",
            "#superhero", "#superheroes", "#comicart", "#comicbook",
            "#marvelstudios", "#marvelfan", "#marvelheroes", "#avengersart",
            "#animation", "#digitalart", "#fanart", "#characterdesign",
            "#illustration", "#artofinstagram",
        ],
        "title": "マーベル",
        "title_en": "Marvel",
        "desc_en": [
            "With great power comes great responsibility. 🕷️",
            "Avengers, assemble! ⚡",
            "The universe's mightiest heroes. 🦸",
            "I am Iron Man. 🔴🟡",
            "Wakanda Forever. 🖤",
        ],
    },
    "DC": {
        "query": "dc comics batman superman",
        "hashtags": [
            "#DC", "#DCComics", "#DCEU", "#DCUniverse",
            "#Batman", "#Superman", "#WonderWoman", "#TheFlash",
            "#Joker", "#AquaMan", "#GreenLantern", "#Cyborg",
            "#JusticeLeague", "#DarkKnight", "#DCFanart", "#DCFan",
            "#superhero", "#superheroes", "#comicart", "#comicbook",
            "#dcart", "#dcheroes", "#batman_fans", "#supermanfan",
            "#animation", "#digitalart", "#fanart", "#characterdesign",
            "#illustration", "#artofinstagram",
        ],
        "title": "DC",
        "title_en": "DC Comics",
        "desc_en": [
            "I am the night. 🦇",
            "In brightest day, in blackest night. 💚",
            "It's not who I am underneath, but what I do that defines me. 🦇",
            "You will believe a man can fly. 🔴💙",
            "Justice will be served. ⚡",
        ],
    },
    "鬼滅の刃": {
        "query": "demon slayer kimetsu no yaiba",
        "hashtags": [
            "#鬼滅の刃", "#DemonSlayer", "#KimetsuNoYaiba", "#DemonSlayerFanart",
            "#炭治郎", "#TanjiroKamado", "#禰豆子", "#NezukoKamado",
            "#善逸", "#ZenItsu", "#伊之助", "#InosukeHashibira",
            "#柱", "#Hashira", "#鬼", "#muzan",
            "#demonslayeredit", "#demonslayerart", "#kny", "#knyedit",
            "#anime", "#animeart", "#animefanart", "#animeartwork",
            "#manga", "#mangaart", "#otaku", "#weeb",
            "#japaneseanimation", "#アニメ",
        ],
        "title": "鬼滅の刃",
        "title_en": "Demon Slayer",
        "desc_en": [
            "I will slay every demon. 🔥💧",
            "Total Concentration Breathing. 🌊",
            "The bond between siblings is unbreakable. 🌸",
            "Thunder Breathing: First Form! ⚡",
            "Nezuko is always protecting. 🌸",
        ],
    },
    "ナルト": {
        "query": "naruto shippuden anime",
        "hashtags": [
            "#NARUTO", "#ナルト", "#NarutoShippuden", "#NarutoFanart",
            "#うずまきナルト", "#NarutoUzumaki", "#サスケ", "#SasukeUchiga",
            "#カカシ", "#KakashiHatake", "#Itachi", "#ItachiUchiga",
            "#boruto", "#sharingan", "#rasengan", "#chidori",
            "#narutoedit", "#narutofan", "#narutoart", "#narutocommunity",
            "#anime", "#animeart", "#animefanart", "#animeartwork",
            "#manga", "#mangaart", "#otaku", "#weeb",
            "#japaneseanimation", "#アニメ",
        ],
        "title": "NARUTO",
        "title_en": "Naruto",
        "desc_en": [
            "Believe it! Dattebayo! 🍥",
            "I never go back on my word. That's my nindo! 🔥",
            "The Will of Fire burns eternal. 🌀",
            "From dead last to Hokage. 💪",
            "Itachi... I will avenge you. 👁️",
        ],
    },
    "ドラゴンボール": {
        "query": "dragon ball z goku",
        "hashtags": [
            "#DragonBall", "#ドラゴンボール", "#DragonBallZ", "#DBZ",
            "#Goku", "#悟空", "#Vegeta", "#ベジータ",
            "#SuperSaiyan", "#超サイヤ人", "#DragonBallSuper", "#DBS",
            "#Gohan", "#Piccolo", "#Frieza", "#CellGames",
            "#dbzfanart", "#dbzedit", "#dragonballfanart", "#dragonballart",
            "#anime", "#animeart", "#animefanart", "#animeartwork",
            "#manga", "#mangaart", "#otaku", "#weeb",
            "#japaneseanimation", "#アニメ",
        ],
        "title": "ドラゴンボール",
        "title_en": "Dragon Ball Z",
        "desc_en": [
            "It's over 9000!!! 💥",
            "The Prince of all Saiyans. 👑",
            "Kamehameha! 🌊⚡",
            "This isn't even my final form. 🔱",
            "Super Saiyan God. 🔴✨",
        ],
    },
}

WALLHAVEN_API = "https://wallhaven.cc/api/v1/search"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
}


def _fetch_wallpapers(query: str, page: int = 1) -> list[dict]:
    """Wallhaven APIからアニメ壁紙リストを取得する。"""
    params = {
        "q": query,
        "categories": "010",   # anime only
        "purity": "100",       # SFW only
        "atleast": "1080x1080",
        "sorting": "random",
        "page": page,
    }
    response = requests.get(WALLHAVEN_API, params=params, headers=_HEADERS, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data.get("data", [])


def download_anime_images(series_name: str, output_dir: str, count: int = 5) -> list[str]:
    """
    アニメ画像をダウンロードしてローカルパスのリストを返す。

    Args:
        series_name: ANIME_SERIESのキー（例: "進撃の巨人"）
        output_dir: 保存先ディレクトリ
        count: 取得枚数

    Returns:
        ダウンロードした画像のローカルパスリスト
    """
    series = ANIME_SERIES[series_name]
    query = series["query"]

    # まずランダムソートで取得
    posts = _fetch_wallpapers(query, page=1)

    if not posts:
        raise RuntimeError(f"Wallhaven: {series_name} の画像が見つかりませんでした")

    # jpg/png のみフィルタ
    valid_posts = [
        p for p in posts
        if p.get("path", "").lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    random.shuffle(valid_posts)

    downloaded = []
    for i, post in enumerate(valid_posts):
        if len(downloaded) >= count:
            break

        file_url = post["path"]
        local_path = os.path.join(output_dir, f"anime_temp_{i}.jpg")

        try:
            resp = requests.get(file_url, headers=_HEADERS, timeout=60)
            resp.raise_for_status()

            # 一時保存してJPEGに変換（PNGでもInstagramに対応させる）
            raw_path = local_path + ".raw"
            with open(raw_path, "wb") as f:
                f.write(resp.content)

            if os.path.getsize(raw_path) < 10_000:
                os.remove(raw_path)
                logging.warning(f"[アニメスクレイパー] ファイルサイズ不足でスキップ: {file_url}")
                continue

            # PIL でJPEG変換（透過PNG対応）
            with Image.open(raw_path) as img:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(local_path, "JPEG", quality=90)
            os.remove(raw_path)

            downloaded.append(local_path)
            logging.info(f"[アニメスクレイパー] ダウンロード完了 ({len(downloaded)}/{count}): {file_url}")

        except Exception as e:
            logging.warning(f"[アニメスクレイパー] ダウンロード失敗: {e}")
            for p in (local_path, local_path + ".raw"):
                if os.path.exists(p):
                    os.remove(p)

    if not downloaded:
        raise RuntimeError(f"[アニメスクレイパー] {series_name} の画像ダウンロードに全て失敗しました")

    return downloaded


def generate_anime_caption(series_name: str) -> str:
    """アニメ投稿用キャプションを生成する（日英バイリンガル）。"""
    series = ANIME_SERIES[series_name]
    hashtags = " ".join(series["hashtags"])
    title = series["title"]
    title_en = series["title_en"]
    desc_en = random.choice(series["desc_en"])

    templates = [
        (
            f"✨ {title} / {title_en} ✨\n\n"
            f"{desc_en}\n\n"
            f"{title}の名シーン集をお届け！\nSwipe to see all the best artwork!\n\n"
            f"{hashtags}"
        ),
        (
            f"🔥 {title_en} 🔥\n\n"
            f"{desc_en}\n\n"
            f"最高のアートワークをまとめました！\nDouble tap if you love {title_en}! ❤️\n\n"
            f"{hashtags}"
        ),
        (
            f"💫 {title} Best Artwork 💫\n\n"
            f"{desc_en}\n\n"
            f"Save this for your wallpaper collection!\n壁紙にぜひ保存してね！🖼️\n\n"
            f"{hashtags}"
        ),
        (
            f"🎌 {title_en} Fan Gallery 🎌\n\n"
            f"{desc_en}\n\n"
            f"Which one is your favorite? Comment below!\nどれが一番好き？コメントで教えて！\n\n"
            f"{hashtags}"
        ),
        (
            f"⚡ {title} アート特集 ⚡\n\n"
            f"{desc_en}\n\n"
            f"Follow for daily anime content!\n毎日アニメ投稿中 → フォローしてね！\n\n"
            f"{hashtags}"
        ),
    ]

    return random.choice(templates)


def pick_random_series() -> str:
    """ランダムにシリーズを選択する。"""
    return random.choice(list(ANIME_SERIES.keys()))
