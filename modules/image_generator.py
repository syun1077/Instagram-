"""
画像生成モジュール
テキストからInstagram用の正方形画像(1080x1080)を自動生成する。
"""

from PIL import Image, ImageDraw, ImageFont
import textwrap
import os

# 画像設定
IMAGE_SIZE = (1080, 1080)
BACKGROUND_COLOR = (245, 245, 220)  # パステルベージュ
TEXT_COLOR = (45, 45, 45)           # ダークグレー
PADDING = 80                        # 画像端からの余白


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """利用可能なフォントを取得する。"""
    # Windows日本語フォント候補
    font_candidates = [
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
        "C:/Windows/Fonts/YuGothM.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for font_path in font_candidates:
        if os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)
    # どれも見つからなければデフォルト
    return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.Draw) -> list[str]:
    """テキストを画像幅に収まるよう自動折り返しする。"""
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        # 1文字ずつ追加して幅を測定
        current_line = ""
        for char in paragraph:
            test_line = current_line + char
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] > max_width:
                if current_line:
                    lines.append(current_line)
                current_line = char
            else:
                current_line = test_line
        if current_line:
            lines.append(current_line)
    return lines


def _calculate_font_size(text: str, draw: ImageDraw.Draw) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """テキスト量に応じてフォントサイズを自動調整する。"""
    max_width = IMAGE_SIZE[0] - PADDING * 2
    max_height = IMAGE_SIZE[1] - PADDING * 2

    # 大きいサイズから試して収まるものを選ぶ
    for size in range(64, 20, -2):
        font = _get_font(size)
        lines = _wrap_text(text, font, max_width, draw)
        line_height = size * 1.5
        total_height = len(lines) * line_height
        if total_height <= max_height:
            return font, lines

    # 最小サイズでも収まらない場合は切り詰め
    font = _get_font(22)
    lines = _wrap_text(text, font, max_width, draw)
    max_lines = int(max_height / (22 * 1.5))
    if len(lines) > max_lines:
        lines = lines[:max_lines - 1] + [lines[max_lines - 1] + "..."]
    return font, lines


def generate_image(text: str, output_path: str = "temp_image.jpg") -> str:
    """
    テキストからInstagram用の画像を生成する。

    Args:
        text: 投稿テキスト
        output_path: 出力ファイルパス

    Returns:
        保存した画像のファイルパス
    """
    img = Image.new("RGB", IMAGE_SIZE, BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)

    # 装飾: 上下にアクセントライン
    accent_color = (180, 140, 100)
    draw.rectangle([(PADDING, 40), (IMAGE_SIZE[0] - PADDING, 44)], fill=accent_color)
    draw.rectangle([(PADDING, IMAGE_SIZE[1] - 44), (IMAGE_SIZE[0] - PADDING, IMAGE_SIZE[1] - 40)], fill=accent_color)

    # テキスト描画
    font, lines = _calculate_font_size(text, draw)
    font_size = font.size if hasattr(font, "size") else 22
    line_height = font_size * 1.5
    total_text_height = len(lines) * line_height

    # 垂直中央揃え
    y_start = (IMAGE_SIZE[1] - total_text_height) / 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        # 水平中央揃え
        x = (IMAGE_SIZE[0] - text_width) / 2
        y = y_start + i * line_height
        draw.text((x, y), line, fill=TEXT_COLOR, font=font)

    img.save(output_path, "JPEG", quality=95)
    print(f"[画像生成] 保存完了: {output_path}")
    return output_path
