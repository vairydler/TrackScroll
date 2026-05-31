# main.py v3.2
"""
マウスジェスチャドライバ エントリポイント。

v3.1 → v3.2 変更:
  - パッケージ構成対応。
    `from app_core`       → `from app.app_core`
    `from app_messages`   → `from app.app_messages`
    `from console_app`    → `from app.console_app`
    `from gesture_service` → `from app.gesture_service`

v2.0 → v3.0 変更（工程6）:
  - AppCore / GestureService / ConsoleApp ベースのアーキテクチャに移行。
  - ConfigProvider / GestureApp クラスを削除（gesture_service.py へ移管済み）。
  - argparse による起動モード切り替え（--console / --gui）を追加。
  - SIGINT ハンドラをコンソール版専用に変更。
    AppCore.post() 経由で APP_QUIT をポスト（sender="__main__"）。
  - AppCore.run() に処理を委譲（ブロッキング）。

v3.0 → v3.1 変更:
  - AppCore.run() はブロッキングのため、GESTURE_START を run() 前に post() しても
    メッセージループが始まるまで処理されない問題を修正。
  - run() の直前に別スレッドで GESTURE_START をポストするよう変更。
    スレッドは daemon=True のため終了時の待機不要。

起動引数:
    python main.py [--console | --gui]
      --console : コンソール版で起動（デフォルト）
      --gui     : タスクトレイGUI版で起動（TrayApp / 工程9で実装）
"""

import argparse
import signal
import sys
import threading

from app.app_core import AppCore
from app.app_messages import msg_app_quit, msg_gesture_start
from app.console_app import ConsoleApp
from app.gesture_service import GestureService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="マウスジェスチャドライバ"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--console",
        dest="mode",
        action="store_const",
        const="console",
        help="コンソール版で起動（デフォルト）",
    )
    group.add_argument(
        "--gui",
        dest="mode",
        action="store_const",
        const="gui",
        help="タスクトレイGUI版で起動",
    )
    parser.set_defaults(mode="console")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    app_core = AppCore()
    gesture_service = GestureService()
    app_core.add_task(gesture_service, "GestureService")

    if args.mode == "console":
        ui_task = ConsoleApp()
        app_core.add_task(ui_task, "ConsoleApp")

        # コンソール版のみ SIGINT ハンドラを設定。
        # AppCore.post() 経由で APP_QUIT をポストし、正常終了シーケンスを踏む。
        # sender="__main__" はどのタスク名とも被らないため全タスクにブロードキャストされる。
        def _on_sigint(sig, frame):
            app_core.post(msg_app_quit())

        signal.signal(signal.SIGINT, _on_sigint)

        print("[main] コンソール版で起動します。Ctrl+C で終了します。")

    elif args.mode == "gui":
        # TrayApp は工程9で実装予定
        print("[main] GUI版（TrayApp）は工程9で実装予定です。", file=sys.stderr)
        sys.exit(1)

    # run() はブロッキングのため、GESTURE_START を別スレッドでポストする。
    # メッセージループ開始後に処理されることが保証される。
    threading.Thread(
        target=lambda: app_core.post(msg_gesture_start()),
        daemon=True,
    ).start()

    # 登録順に start() → メッセージループ → 逆順に stop()
    app_core.run()


if __name__ == "__main__":
    main()
