"""
Windowsタスクスケジューラに自動投稿タスクを登録するスクリプト。
毎日指定時刻にauto_post.pyを自動実行する。
"""

import subprocess
import sys
import os


def setup_task(hour: int = 12, minute: int = 0):
    """
    タスクスケジューラに自動投稿タスクを登録する。

    Args:
        hour: 実行時刻（時）
        minute: 実行時刻（分）
    """
    python_path = sys.executable
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_post.py")
    working_dir = os.path.dirname(os.path.abspath(__file__))
    task_name = "InstagramAutoPost"
    time_str = f"{hour:02d}:{minute:02d}"

    # 既存タスクを削除（あれば）
    subprocess.run(
        ["schtasks", "/delete", "/tn", task_name, "/f"],
        capture_output=True,
    )

    # 新しいタスクを作成
    result = subprocess.run(
        [
            "schtasks", "/create",
            "/tn", task_name,
            "/tr", f'"{python_path}" "{script_path}"',
            "/sc", "daily",
            "/st", time_str,
            "/rl", "HIGHEST",
            "/f",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"タスク登録完了！")
        print(f"  タスク名: {task_name}")
        print(f"  実行時刻: 毎日 {time_str}")
        print(f"  スクリプト: {script_path}")
        print(f"\nログは auto_post.log に記録されます。")
    else:
        print(f"タスク登録に失敗しました: {result.stderr}")


def remove_task():
    """タスクスケジューラから自動投稿タスクを削除する。"""
    result = subprocess.run(
        ["schtasks", "/delete", "/tn", "InstagramAutoPost", "/f"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("自動投稿タスクを削除しました。")
    else:
        print(f"削除に失敗しました: {result.stderr}")


def main():
    print("=" * 50)
    print("  Instagram 自動投稿スケジューラ設定")
    print("=" * 50)
    print()
    print("操作を選択してください:")
    print("  1. 自動投稿を設定する")
    print("  2. 自動投稿を停止する（タスク削除）")
    print()

    choice = input("選択 [1/2]: ").strip()

    if choice == "1":
        print()
        time_input = input("毎日何時に投稿しますか？ (例: 12:00): ").strip()
        try:
            parts = time_input.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except (ValueError, IndexError):
            print("無効な時刻です。12:00 で設定します。")
            hour, minute = 12, 0

        setup_task(hour, minute)

    elif choice == "2":
        remove_task()
    else:
        print("無効な選択です。")


if __name__ == "__main__":
    main()
