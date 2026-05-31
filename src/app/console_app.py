# console_app.py v1.3
"""
コンソール版UIタスク。

AppTask インターフェースを実装し、UI系コマンドを標準出力に出力する。
TrayApp と差し替え可能な存在として、コンソール環境での動作確認に使用する。

v1.2 → v1.3 変更:
  - パッケージ構成対応。
    `from app_core`     → `from app.app_core`
    `from app_messages` → `from app.app_messages`

v1.1 → v1.2 変更:
  - __init__ から post_to_core 引数を削除。
    AppCore.add_task() → set_post_to_core() 経由で受け取る形に変更。
  - _handle() から APP_QUIT の処理を削除。
    APP_QUIT は AppCore が処理するため各タスクでの処理は不要。

v1.1 → v1.2 変更:
  - GESTURE_TOGGLED コマンドを受け取り、有効/無効状態をコンソール出力するよう追加。

受け付けるコマンド:
    UI_SHOW_WARNING  : 標準出力に警告テキストを出力
    UI_UPDATE_STATUS : 標準出力に状態テキストを出力
    UI_NOTIFY        : 標準出力に通知テキストを出力
    GESTURE_TOGGLED  : ジェスチャ有効/無効状態をコンソール出力
"""

from __future__ import annotations

import queue
import threading

from app.app_core import AppTask
from app.app_messages import AppMessage, Command, StatusParams


class ConsoleApp(AppTask):
    """
    コンソール版UIタスク。
    UI系コマンドを標準出力へ出力する。
    """

    def __init__(self):
        super().__init__()
        self._msg_queue: queue.Queue[AppMessage] = queue.Queue()
        self._worker_thread: threading.Thread | None = None
        self._running = False

    # ------------------------------------------------------------------ #
    # AppTask インターフェース
    # ------------------------------------------------------------------ #

    def post_message(self, msg: AppMessage) -> None:
        """AppCore からメッセージを受け取る唯一の入口。非ブロッキング。"""
        self._msg_queue.put(msg)

    def start(self) -> None:
        """ワーカースレッドを起動する。"""
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop, daemon=True, name="ConsoleApp-worker"
        )
        self._worker_thread.start()

    def stop(self) -> None:
        """ワーカースレッドを終了する。"""
        self._running = False
        if self._worker_thread is not None:
            self._worker_thread.join(timeout=3.0)

    # ------------------------------------------------------------------ #
    # ワーカーループ
    # ------------------------------------------------------------------ #

    def _worker_loop(self) -> None:
        while self._running:
            try:
                msg = self._msg_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            self._handle(msg)

    def _handle(self, msg: AppMessage) -> None:
        if msg.command == Command.UI_SHOW_WARNING:
            print(f"[WARNING] {msg.params}")
        elif msg.command == Command.UI_UPDATE_STATUS:
            params: StatusParams = msg.params
            print(f"[STATUS] {params.status.name}: {params.message}")
        elif msg.command == Command.UI_NOTIFY:
            print(f"[NOTIFY] {msg.params}")
        elif msg.command == Command.GESTURE_TOGGLED:
            state = "有効" if msg.params else "無効"
            print(f"[GESTURE] ジェスチャ {state}")
