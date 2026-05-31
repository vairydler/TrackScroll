# gesture_builder.py v2.3
"""
ジェスチャテーブル簡易ビルダー。

v2.2 → v2.3 変更:
  - パッケージ構成対応。
    `from gesture_action` → `from core.gesture_action`

v2.1 → v2.2 変更:
  - noop() 関数を追加。
    リピートタイマを有効にしつつ動作不要な場合に使用する。

v2.0 → v2.1 変更:
  - record() に move_cooldown 引数を追加 [SPEC-MOVE-COOLDOWN]
  - GestureData の3動作方式に合わせてエントリ形式を変更 [SPEC-ACTION-THREE-WAY]
  - エントリのタプル形式:
      (ジェスチャキー, ダウン, リピート開始時間)                          ← ダウンのみ（後方互換）
      (ジェスチャキー, ダウン, アップ, リピート開始時間)                   ← ダウン＋アップ
      (ジェスチャキー, ダウン, アップ, リピート動作, リピート開始時間)     ← フル指定
  - アップ/リピートは None 省略可

使用例:
    from gesture_builder import GKey, record
    from vk_codes import VK

    rec = record(VK.RBUTTON, entries=[
        # ダウンのみ（旧形式と互換）
        (GKey.MOVE_UP,   "BrowserForward", 0.5),
        # ダウン＋アップ（Shiftを押し続ける例）
        (VK.XBUTTON1,    "↓Shift", "↑Shift", 0.0),
        # ダウン＋アップ＋リピート
        (GKey.MOVE_UP,   "Tab", None, "Tab", 0.3),
        # 空欄=トリガ自体 [SPEC-TRIGGER-ACTION-ASSIGN]
        ("",             _right_click_func, 1.0),
    ])

エントリのキー部分の型と解釈:
    GKey.*    → 移動方向・スクロール方向のジェスチャキー
    int (VK値)→ マウスボタンまたはキーボードキーのジェスチャキー
    "" / None → 空欄ジェスチャキー（トリガ自体への動作）[SPEC-TRIGGER-ACTION-ASSIGN]

エントリのアクション部分の型と解釈:
    str           → GestureAction.parse() で解釈（AHK風文字列記法）[SPEC-ACTION-STRING-NOTATION]
    callable      → GestureAction.function() で登録
    GestureAction → そのまま使用
    None          → 動作なし
"""

from __future__ import annotations

from enum import Enum
from typing import Union

from core.gesture_action import (
    GestureAction, GestureData, GestureKey, GestureRecord,
)

_MOUSE_BUTTON_VKS = {0x01, 0x02, 0x04, 0x05, 0x06}


# ===========================================================================
# ユーティリティ
# ===========================================================================

def noop() -> None:
    """
    何もしない関数。リピートタイマを有効にしつつ動作不要な場合に使用する。

    使用例:
        # 1秒後にダウンを発行し、以降は何もしない（リピートタイマだけ維持）
        ("", "↓RButton", "↑RButton", noop, 1.0)

    Note:
        関数オブジェクトとして渡すため、noop と書く（noop() と呼び出さない）。
    """
    pass


# ===========================================================================
# ジェスチャキー種別 Enum
# ===========================================================================

class GKey(str, Enum):
    """
    ジェスチャキー種別の文字列 Enum。
    移動方向・スクロール方向のジェスチャキーを表す。
    """
    MOVE_UP      = "move_up"
    MOVE_DOWN    = "move_down"
    MOVE_LEFT    = "move_left"
    MOVE_RIGHT   = "move_right"
    SCROLL_UP    = "scroll_up"
    SCROLL_DOWN  = "scroll_down"
    SCROLL_LEFT  = "scroll_left"
    SCROLL_RIGHT = "scroll_right"


GKeyType    = Union[GKey, int, str, None]
ActionType  = Union[str, GestureAction, callable, None]

# エントリのタプル型（可変長）
# (key, down, repeat_start)
# (key, down, up, repeat_start)
# (key, down, up, repeat, repeat_start)
EntryType = tuple


# ===========================================================================
# ビルダー関数
# ===========================================================================

def record(
    trigger: Union[int, tuple[int, ...]],
    entries: list[EntryType],
    threshold: float | None = None,
    move_cooldown: float | None = None,
) -> GestureRecord:
    """
    GestureRecord を簡易記法で生成する。

    Parameters
    ----------
    trigger       : int または int のタプル。VK.* の値を指定する。
    entries       : エントリのリスト。各エントリは以下のいずれかの形式:
                      (key, down, repeat_start)
                      (key, down, up, repeat_start)
                      (key, down, up, repeat, repeat_start)
    threshold     : 移動方向判定しきい値（px）。None でシステムデフォルト使用。
    move_cooldown : 移動クールダウン時間（秒）。None または 0.0 で無効。[SPEC-MOVE-COOLDOWN]
    """
    if isinstance(trigger, int):
        trigger_set = frozenset({trigger})
    else:
        trigger_set = frozenset(trigger)

    gesture_data = [_build_data(entry) for entry in entries]

    return GestureRecord(
        trigger=trigger_set,
        gesture_data=gesture_data,
        threshold=threshold,
        move_cooldown=move_cooldown,
    )


def _build_data(entry: EntryType) -> GestureData:
    """
    エントリのタプルから GestureData を生成する。

    形式:
      3要素: (key, down, repeat_start)
      4要素: (key, down, up, repeat_start)
      5要素: (key, down, up, repeat, repeat_start)
    """
    n = len(entry)
    if n == 3:
        gkey_raw, down_raw, repeat_start = entry
        up_raw     = None
        repeat_raw = None
    elif n == 4:
        gkey_raw, down_raw, up_raw, repeat_start = entry
        repeat_raw = None
    elif n == 5:
        gkey_raw, down_raw, up_raw, repeat_raw, repeat_start = entry
    else:
        raise ValueError(f"エントリのタプル長が不正です（3〜5要素）: {entry!r}")

    gesture_key = _resolve_gesture_key(gkey_raw)
    down_action   = _resolve_action(down_raw)
    up_action     = _resolve_action(up_raw)
    repeat_action = _resolve_action(repeat_raw)

    return GestureData(
        gesture_key=gesture_key,
        down_action=down_action,
        up_action=up_action,
        repeat_action=repeat_action,
        repeat_start=repeat_start,
    )


def _resolve_gesture_key(gkey_raw: GKeyType) -> GestureKey:
    """
    エントリのキー部分を GestureKey に変換する。
    """
    if gkey_raw is None or gkey_raw == "":
        return GestureKey.trigger()

    if isinstance(gkey_raw, GKey):
        val = gkey_raw.value
        if val.startswith("move_"):
            return GestureKey.move(val[len("move_"):])
        if val.startswith("scroll_"):
            return GestureKey.scroll(val[len("scroll_"):])
        raise ValueError(f"未知の GKey 値: {gkey_raw!r}")

    if isinstance(gkey_raw, int):
        if gkey_raw in _MOUSE_BUTTON_VKS:
            return GestureKey.mouse_button(gkey_raw)
        return GestureKey.key(gkey_raw)

    raise TypeError(f"ジェスチャキーに使用できない型: {type(gkey_raw).__name__!r} ({gkey_raw!r})")


def _resolve_action(action_raw: ActionType) -> "GestureAction | None":
    """
    エントリのアクション部分を GestureAction に変換する。None はそのまま返す。
    """
    if action_raw is None:
        return None
    if isinstance(action_raw, str):
        return GestureAction.parse(action_raw)
    if isinstance(action_raw, GestureAction):
        return action_raw
    if callable(action_raw):
        return GestureAction.function(action_raw)
    raise TypeError(f"アクションに使用できない型: {type(action_raw).__name__!r}")
