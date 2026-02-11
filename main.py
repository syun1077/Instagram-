"""
Instagram 自動投稿Bot - メインスクリプト
テキストを入力するだけで、画像生成 → Imgurアップロード → Instagram投稿を全自動で行う。
モード選択: テキスト画像 or AI画像
"""

import os
import sys
from modules.image_generator import generate_image
from modules.ai_image_generator import generate_ai_image, show_prompt_examples
from modules.uploader import upload_image
from modules.insta_poster import post_to_instagram
from modules.token_manager import auto_refresh


def cleanup(image_path: str) -> None:
    """一時画像ファイルを削除する。"""
    if os.path.exists(image_path):
        os.remove(image_path)
        print(f"[クリーンアップ] 一時ファイル削除: {image_path}")


def main() -> None:
    print("=" * 50)
    print("  Instagram 自動投稿Bot")
    print("=" * 50)
    print()

    # --- トークン自動チェック＆更新 ---
    print("トークンを確認中...")
    if not auto_refresh():
        print("\n[エラー] トークンが無効です。")
        print("以下のコマンドでトークンを再取得してください:")
        print("  python get_token.py")
        sys.exit(1)
    print()

    # --- モード選択 ---
    print("投稿モードを選択してください:")
    print("  1. AI画像生成（プロンプトからAI画像を作成）")
    print("  2. テキスト画像（文字を画像にして投稿）")
    print()
    mode = input("モード [1/2] (デフォルト: 1): ").strip()
    if mode not in ("1", "2"):
        mode = "1"

    temp_image = "temp_image.jpg"

    try:
        if mode == "1":
            # --- AI画像モード ---
            show_prompt_examples()
            prompt = input("画像生成プロンプトを入力（英語推奨）: ").strip()
            if not prompt:
                print("プロンプトが入力されませんでした。終了します。")
                sys.exit(1)

            print()
            caption = input("キャプション（Instagram上の投稿文）を入力: ").strip()
            if not caption:
                caption = prompt

            # Step 1: AI画像生成
            print("\n--- Step 1: AI画像生成 ---")
            generate_ai_image(prompt, temp_image)

        else:
            # --- テキスト画像モード ---
            print("投稿テキストを入力してください（複数行OK、空行で入力終了）:")
            lines = []
            while True:
                try:
                    line = input()
                except EOFError:
                    break
                if line == "":
                    break
                lines.append(line)

            if not lines:
                print("テキストが入力されませんでした。終了します。")
                sys.exit(1)

            post_text = "\n".join(lines)
            print(f"\n[入力テキスト]\n{post_text}\n")

            caption_input = input("キャプション [Enter で投稿テキストと同じにする]: ").strip()
            caption = caption_input if caption_input else post_text

            # Step 1: テキスト画像生成
            print("\n--- Step 1: 画像生成 ---")
            generate_image(post_text, temp_image)

        # Step 2: Imgurにアップロード
        print("\n--- Step 2: 画像アップロード ---")
        image_url = upload_image(temp_image)

        # Step 3: Instagramに投稿
        print("\n--- Step 3: Instagram投稿 ---")
        post_id = post_to_instagram(image_url, caption)

        print("\n" + "=" * 50)
        print("  投稿が完了しました!")
        print(f"  Post ID: {post_id}")
        print("=" * 50)

    except (ValueError, FileNotFoundError) as e:
        print(f"\n[設定エラー] {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"\n[実行エラー] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n処理を中断しました。")
        sys.exit(0)
    finally:
        cleanup(temp_image)


if __name__ == "__main__":
    main()
