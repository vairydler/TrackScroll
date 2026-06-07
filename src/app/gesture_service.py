# gesture_service.py v1.5.1
"""
ジェスチャ機能の外部向けファサード。

GestureCore / GestureEventHandler / InputDriver / OutputDriver を内包し、
AppTask インターフェースを通じて AppCore から制御される。

v1.5 → v1.5.1 変更:
  - SPEC-TOGGLE-HOTKEY-NOTIFY タグを _on_toggle() および load() 呼び出し部に追記。

v1.4 → v1.5 変更:
  - gesture_config を config/ パッケージに移動したことに伴い import を変更。
    `import gesture_config` → `import config.gesture_config`

v1.3 → v1.4 変更:
  - パッケージ構成対応。
    `import gesture_config`  → `import gesture_config`（ルート直下のため変更なし）
    `from app_core`          → `from app.app_core`
    `from app_messages`      → `from app.app_messages`
    `from gesture_core`      → `from core.gesture_core`
    `from gesture_event`     → `from core.gesture_event`
    `from input_driver`      → `from drivers.input_driver`
    `from output_driver`     → `from drivers.output_driver`

v1.2 → v1.3 変更:
  - __init__ から post_to_core 引数を削除。
    AppCore.add_task() → set_post_to_core() 経由で受け取る形に変更。

v1.1 → v1.2 変更:
  - _build_and_load() で core.load() に on_toggle コールバックを渡すよう変更。
  - _on_toggle() を追加。ホットキートグル時に GESTURE_TOGGLED をポストする。

v1.2 → v1.3 変更:
  - _ConfigProvider クラスを削除。
    gesture_config モジュールを GestureCore に直接渡すよう変更。
    薄いラッパーに過ぎず、追加関数の追従漏れを招くだけのため廃止。

受け付けるコマンド:
    GESTURE_START          : ジェスチャを起動する
    GESTURE_STOP           : ジェスチャを停止する
    GESTURE_RELOAD_CONFIG  : 設定を再読み込みして再起動する

送出するコマンド（AppCore.post 経由）:
    GESTURE_CONFLICT_WARNING   : 競合警告 [SPEC-CONFLICT-DETECT]
    GESTURE_INVALID_UP_WARNING : 不正アップ動作警告 [SPEC-INVALID-UP-DETECT]
    GESTURE_ERROR              : 回復不能なエラー
    GESTURE_TOGGLED            : ホットキーによる有効/無効切り替え通知
"""

from __future__ import annotations

import queue
import threading

import config.gesture_config as _config_module
from app.app_core import AppTask
from app.app_messages import AppMessage, Command
from core.gesture_core import GestureCore
from core.gesture_event import GestureEventHandler
from drivers.input_driver import InputDriver
from drivers.output_driver import OutputDriver


# ===========================================================================
# GestureService
# ===========================================================================

class GestureService(AppTask):
    """
    ジェスチャ機能を AppTask としてカプセル化したファサード。

    AppCore から post_message() でコマンドを受け取り、
    内部キューで非ブロッキングに処理する。

    [SPEC-SELF-EVENT-FILTER]
    OutputDriver と InputDriver に同一の識別子を設定し、
    自己送出イベントがフックコールバックで無視されることを保証する。
    """

    def __init__(self):
        super().__init__()
        self._msg_queue: queue.Queue[AppMessage] = queue.Queue()
        self._worker_thread: threading.Thread | None = None
        self._running = False

        self._od:     OutputDriver | None = None
        self._driver: InputDriver  | None = None
        self._core:   GestureCore  | None = None
        self._started = False

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
            target=self._worker_loop, daemon=True, name="GestureService-worker"
        )
        self._worker_thread.start()

    def stop(self) -> None:
        """ジェスチャを停止し、ワーカースレッドを終了する。"""
        self._running = False
        self._msg_queue.put(AppMessage(Command.GESTURE_STOP))
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

            try:
                self._handle(msg)
            except Exception as e:
                self._post_to_core(
                    AppMessage(Command.GESTURE_ERROR, str(e))
                )

    def _handle(self, msg: AppMessage) -> None:
        if msg.command == Command.GESTURE_START:
            self._do_start()
        elif msg.command == Command.GESTURE_STOP:
            self._do_stop()
        elif msg.command == Command.GESTURE_RELOAD_CONFIG:
            self._do_reload()

    # ------------------------------------------------------------------ #
    # 起動 / 停止 / リロード
    # ------------------------------------------------------------------ #

    def _do_start(self) -> None:
        if self._started:
            return
        self._build_and_load()
        self._started = True

    def _do_stop(self) -> None:
        if not self._started:
            return
        if self._driver is not None:
            self._driver.stop()
        if self._core is not None:
            self._core.stop()
        self._driver  = None
        self._core    = None
        self._od      = None
        self._started = False

    def _do_reload(self) -> None:
        self._do_stop()
        self._do_start()

    def _build_and_load(self) -> None:
        """
        OutputDriver / InputDriver / GestureCore / GestureEventHandler を
        生成・接続してジェスチャを開始する。
        [SPEC-SELF-EVENT-FILTER]
        """
        od      = OutputDriver()
        eq: queue.Queue = queue.Queue()
        handler = GestureEventHandler(eq)
        core    = GestureCore(
            config      = _config_module,
            od          = od,
            handler     = handler,
            event_queue = eq,
        )
        driver = InputDriver(
            on_key               = handler.on_key,
            on_mouse_button      = handler.on_mouse_button,
            on_mouse_scroll      = handler.on_mouse_scroll,
            on_mouse_move        = handler.on_mouse_move,
            on_mouse_move_filter = handler.on_mouse_move_filter,
        )

        # [SPEC-SELF-EVENT-FILTER] 両ドライバの識別子を一致させる
        extra_info = od._extra_info
        driver.set_extra_info(extra_info)

        # 警告・トグルコールバックを設定して load [SPEC-TOGGLE-HOTKEY-NOTIFY]
        core.load(on_warning=self._on_warning, on_toggle=self._on_toggle)
        driver.start()

        self._od     = od
        self._core   = core
        self._driver = driver

    def _on_warning(self, kind: str, messages: list[str]) -> None:
        """
        GestureCore.load() から警告を受け取り、メインキューにポストする。
        [SPEC-CONFLICT-DETECT][SPEC-INVALID-UP-DETECT]
        """
        if kind == "conflict":
            self._post_to_core(
                AppMessage(Command.GESTURE_CONFLICT_WARNING, messages)
            )
        elif kind == "invalid_up":
            self._post_to_core(
                AppMessage(Command.GESTURE_INVALID_UP_WARNING, messages)
            )

    def _on_toggle(self, enabled: bool) -> None:
        """
        [SPEC-TOGGLE-HOTKEY-NOTIFY]
        GestureCore からホットキートグルを受け取り、GESTURE_TOGGLED をポストする。
        """
        self._post_to_core(
            AppMessage(Command.GESTURE_TOGGLED, enabled)
        )
