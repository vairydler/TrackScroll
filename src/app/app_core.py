# app_core.py v1.3
"""
タスク共通インターフェース定義 および AppCore 実装。

v1.2 → v1.3 変更:
  - パッケージ構成対応。
    `from app_messages` → `from app.app_messages`

v1.1 → v1.2 変更:
  - AppCore.post() パブリックメソッドを追加。
    タスク外部（main.py 等）から任意の sender 名でメッセージをポストできる。

v1.1 → v1.2 変更:
  - _post() を削除。post() に一本化。
    add_task() の partial も post() を参照するよう変更。
"""

from __future__ import annotations

import queue
from abc import ABC, abstractmethod
from functools import partial
from typing import Callable

from app.app_messages import AppMessage, Command


# ===========================================================================
# AppTask（共通インターフェース）
# ===========================================================================

class AppTask(ABC):
    """全タスクが実装する共通インターフェース。"""

    def __init__(self):
        self._post_to_core: Callable[[AppMessage], None] | None = None

    def set_post_to_core(self, fn: Callable[[AppMessage], None]) -> None:
        """
        AppCore.add_task() から呼ばれる。
        sender 名がバインド済みの post 関数を受け取る。
        各タスクは self._post_to_core(msg) で AppCore キューへ積む。
        """
        self._post_to_core = fn

    @abstractmethod
    def post_message(self, msg: AppMessage) -> None:
        """AppCore からメッセージを受け取る唯一の入口。非ブロッキング。"""
        ...

    @abstractmethod
    def start(self) -> None:
        """タスクを起動する。"""
        ...

    @abstractmethod
    def stop(self) -> None:
        """タスクを停止する。"""
        ...


# ===========================================================================
# AppCore
# ===========================================================================

class AppCore:
    """
    メインスレッドで動作するメッセージルーター。

    役割:
      - タスクの登録・名前管理（add_task）
      - メインメッセージキューの読み出しと全タスクへのブロードキャスト
      - APP_QUIT 受信によるシャットダウン（登録逆順で stop）
      - APP_ERROR 受信のログ出力
      - ループ検出フェールセーフ

    使い方:
        core = AppCore()
        core.add_task(gesture_service, "GestureService")
        core.add_task(console_app, "ConsoleApp")
        core.run()  # 内部で start() → メッセージループ → stop()
    """

    _POLL_TIMEOUT      = 0.1   # キューポーリング間隔（秒）
    _LOOP_DETECT_LIMIT = 20    # 同一 sender+command の連続回数でループ検出

    def __init__(self):
        self._queue: queue.Queue[tuple[str, AppMessage]] = queue.Queue()
        self._tasks: list[tuple[str, AppTask]] = []
        self._running = False

    # ------------------------------------------------------------------ #
    # タスク登録
    # ------------------------------------------------------------------ #

    def add_task(self, task: AppTask, name: str) -> None:
        """
        タスクを登録し、sender 名をバインドした post 関数を set_post_to_core() に渡す。
        名前の重複はエラーとする。
        run() 呼び出し前に登録すること。
        """
        if any(n == name for n, _ in self._tasks):
            raise ValueError(f"タスク名が競合しています: {name!r}")
        self._tasks.append((name, task))
        task.set_post_to_core(partial(self.post, sender=name))

    # ------------------------------------------------------------------ #
    # ポスト口
    # ------------------------------------------------------------------ #

    def post(self, msg: AppMessage, sender: str = "__main__") -> None:
        """
        タスク外部（main.py 等）からメッセージをポストするパブリック口。
        sender はブロードキャスト除外に使われるだけなので、
        登録済みタスク名と被らなければ任意の文字列でよい。
        非ブロッキング。
        """
        self._queue.put((sender, msg))

    # ------------------------------------------------------------------ #
    # メインループ（ブロッキング）
    # ------------------------------------------------------------------ #

    def run(self) -> None:
        """
        全タスクを登録順に start() してからメッセージループに入る。
        APP_QUIT を受信すると全タスクを逆順に stop() して返る。
        main.py から呼ぶ。
        """
        self._running = True

        for _, task in self._tasks:
            task.start()

        try:
            self._message_loop()
        finally:
            self._shutdown()

    def _message_loop(self) -> None:
        """メッセージループ本体。ループ検出フェールセーフを含む。"""
        loop_last_command: Command | None = None
        loop_count = 0

        while self._running:
            try:
                sender, msg = self._queue.get(timeout=self._POLL_TIMEOUT)
            except queue.Empty:
                # アイドル状態: ループカウントをリセット
                loop_last_command = None
                loop_count = 0
                continue

            # ループ検出 [フェールセーフ]
            if msg.command == loop_last_command:
                loop_count += 1
                if loop_count >= self._LOOP_DETECT_LIMIT:
                    print(
                        f"[FATAL] メッセージループを検出しました。"
                        f"command={msg.command}。強制終了します。"
                    )
                    self._running = False
                    return
            else:
                loop_last_command = msg.command
                loop_count = 1

            self._handle(sender, msg)

    # ------------------------------------------------------------------ #
    # メッセージ処理
    # ------------------------------------------------------------------ #

    def _handle(self, sender: str, msg: AppMessage) -> None:
        """
        APP_QUIT / APP_ERROR は AppCore が直接処理する。
        その他は全タスクにブロードキャスト。
        """
        if msg.command == Command.APP_QUIT:
            print("[AppCore] APP_QUIT を受信しました。終了します。")
            self._running = False
            self._broadcast(sender, msg)
            return

        if msg.command == Command.APP_ERROR:
            print(f"[AppCore] APP_ERROR: {msg.params}")
            self._broadcast(sender, msg)
            return

        self._broadcast(sender, msg)

    def _broadcast(self, sender: str, msg: AppMessage) -> None:
        """
        送信元を除く全登録タスクの post_message() を呼ぶ。
        送信元に同じメッセージが戻ることによる無限ループを防ぐ。
        NOTE: 購読方式へ移行するときはこのメソッドのみ差し替える。
        """
        for name, task in self._tasks:
            if name == sender:
                continue  # 送信元には返さない
            task.post_message(msg)

    # ------------------------------------------------------------------ #
    # シャットダウン
    # ------------------------------------------------------------------ #

    def _shutdown(self) -> None:
        """登録逆順でタスクを stop() する。"""
        print("[AppCore] タスクを停止しています...")
        for _, task in reversed(self._tasks):
            try:
                task.stop()
            except Exception as e:
                print(f"[AppCore] タスク停止中にエラー: {e}")
        print("[AppCore] 全タスク停止完了。")
