# gesture_event.py v2.5
"""
フックイベントのデータクラス定義と、
InputDriver コールバック群（キューに積むだけの薄いレイヤー）。

v2.4 → v2.5 変更:
  - カーソル移動禁止のRDP対応コードを削除。[SPEC-RDP-CURSOR-BLOCK-UNAVAILABLE] 参照。
    - __init__ から input_driver 引数を削除。
    - set_input_driver() を削除。
    - update() から set_block_cursor() 呼び出しを削除。
    - on_mouse_move_filter のドキュメントから SetCursorPos 言及を削除。

v2.3 → v2.4 変更:
  - RDP環境でのカーソル移動ブロック対応（v2.5 で削除）。

v2.2 → v2.3 変更:
  - toggle_hotkey_vks を廃止。
    enabled=False 時はホットキーVKに限らず全入力を素通りさせるシンプルな実装に変更。

v2.1 → v2.2 変更:
  - ホットキー（主電源トグル）の伝播制御をこのレイヤーで判定するよう変更。
  - update() に enabled 引数を追加。

v2.0 → v2.1 変更:
  - [SPEC-HOOK-BLOCK-CURSOR] 仕様書v2.6対応。
    update() の hooked 引数の意味を変更。

v1.0 → v2.0 変更:
  - バージョン番号のみ更新。ロジック変更なし。

フックコールバックがやること:
  - on_mouse_move_filter : _block_cursor フラグを見て即時返却（キューに積まない）
  - それ以外             : イベントをキューに積んで即返却

即時返却が必要な情報は GestureCore から都度 update() で通知される:
  - block_cursor  : カーソル移動を禁止するか [SPEC-HOOK-BLOCK-CURSOR]
  - trigger_vks   : 常時ブロックするVK集合
  - block_keys    : 現セッションでブロックするジェスチャキーVK集合
  - block_scroll_v: 垂直スクロールをブロックするか
  - block_scroll_h: 水平スクロールをブロックするか
  - enabled       : ジェスチャが有効かどうか（主電源）
"""

from __future__ import annotations

import queue
from dataclasses import dataclass


# ===========================================================================
# イベントデータクラス
# ===========================================================================

@dataclass
class KeyEvent:
    vk: int
    pressed: bool

@dataclass
class MouseButtonEvent:
    vk: int
    pressed: bool

@dataclass
class ScrollEvent:
    delta: int
    horizontal: bool

@dataclass
class MoveEvent:
    dx: int
    dy: int

GestureEvent = KeyEvent | MouseButtonEvent | ScrollEvent | MoveEvent


# ===========================================================================
# フックコールバック群
# ===========================================================================

class GestureEventHandler:
    """
    InputDriver のコールバックを受け取り、キューに積む薄いレイヤー。
    on_mouse_move_filter のみ即時返却（キューに積まない）。

    GestureCore から update() で都度フック状態を受け取る。
    """

    def __init__(self, event_queue: queue.Queue):
        self._queue = event_queue

        self._block_cursor   = False
        self._trigger_vks:   frozenset = frozenset()
        self._block_keys:    frozenset = frozenset()
        self._block_scroll_v = False
        self._block_scroll_h = False
        self._enabled        = True

    def update(self,
               block_cursor: bool,
               trigger_vks: frozenset,
               block_keys: frozenset,
               block_scroll_v: bool,
               block_scroll_h: bool,
               enabled: bool = True) -> None:
        """GestureCore からフック状態の変化を通知される。"""
        self._block_cursor   = block_cursor
        self._trigger_vks    = trigger_vks
        self._block_keys     = block_keys
        self._block_scroll_v = block_scroll_v
        self._block_scroll_h = block_scroll_h
        self._enabled        = enabled

    # ------------------------------------------------------------------ #
    # InputDriver コールバック
    # ------------------------------------------------------------------ #

    def on_mouse_move_filter(self, x: int, y: int) -> bool:
        """
        WM_MOUSEMOVE フック。即時返却が必要なためキューに積まない。
        [SPEC-HOOK-BLOCK-CURSOR]
        """
        if self._block_cursor:
            return False
        return True

    def on_key(self, vk: int, pressed: bool) -> bool:
        """[SPEC-HOOK-BLOCK-TRIGGER-KEY][SPEC-HOOK-BLOCK-GESTURE-KEY]"""
        self._queue.put(KeyEvent(vk, pressed))
        if not self._enabled:
            return True
        if vk in self._trigger_vks:
            return False   # [SPEC-HOOK-BLOCK-TRIGGER-KEY]
        if vk in self._block_keys:
            return False   # [SPEC-HOOK-BLOCK-GESTURE-KEY]
        return True        # [SPEC-HOOK-NO-MATCH-PASSTHROUGH]

    def on_mouse_button(self, vk: int, pressed: bool) -> bool:
        """[SPEC-HOOK-BLOCK-TRIGGER-KEY][SPEC-HOOK-BLOCK-GESTURE-KEY]"""
        self._queue.put(MouseButtonEvent(vk, pressed))
        if not self._enabled:
            return True
        if vk in self._trigger_vks:
            return False
        if vk in self._block_keys:
            return False
        return True

    def on_mouse_scroll(self, delta: int, horizontal: bool) -> bool:
        """[SPEC-HOOK-BLOCK-GESTURE-KEY]"""
        self._queue.put(ScrollEvent(delta, horizontal))
        if horizontal and self._block_scroll_h:
            return False
        if not horizontal and self._block_scroll_v:
            return False
        return True

    def on_mouse_move(self, dx: int, dy: int) -> None:
        """Raw Input 相対移動量。伝播制御なし。"""
        self._queue.put(MoveEvent(dx, dy))
