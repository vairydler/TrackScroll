# gesture_config.py v2.2
"""
設定ファイル。ジェスチャテーブルおよびシステムパラメータを提供する。

v2.1 → v2.2 変更:
  - パッケージ構成対応。
    `from gesture_action` → `from core.gesture_action`
    `from gesture_builder` → `from core.gesture_builder`
    `from vk_codes` → `from drivers.vk_codes`

v1.1 → v2.0 変更:
  - 仕様書2.2対応。エントリを3動作方式（ダウン/アップ/リピート）に更新 [SPEC-ACTION-THREE-WAY]
  - ↓/↑ 押しっぱなし記法のサンプルを追加 [SPEC-ACTION-STRING-NOTATION]
  - get_flick_time() を get_delay_time() にリネーム（仕様書「猶予時間」に合わせる）
    ※ 後方互換のため get_flick_time() はエイリアスとして残す

v2.0 → v2.1 変更:
  - get_toggle_hotkey() を追加。
    ジェスチャの有効/無効をトグルするホットキーを frozenset[int] で返す。
    None を返すとホットキー無効。複数キーの同時押しにも対応。

[SPEC-CONFIG-FILE]
現時点ではPythonコード上に直接記述し、特定の関数の戻り値として返す形式とする。
将来的にはJSON設定ファイルからの読み込みへ移行できるよう、各取得関数のインターフェースを維持すること。
"""

from __future__ import annotations

from core.gesture_action import GestureRecord
from core.gesture_builder import GKey, record, noop
from drivers.vk_codes import VK


# ===========================================================================
# システムパラメータ取得関数  [SPEC-CONFIG-FILE]
# ===========================================================================

def get_default_move_threshold() -> float:
    """移動方向判定しきい値デフォルト（px）。[SPEC-MOVE-THRESHOLD]"""
    return 30.0


def get_jitter_threshold() -> float:
    """手ブレ補正しきい値（px）。[SPEC-REPEAT-CLEAR-ON-MOVE]"""
    return 5.0


def get_repeat_interval() -> float:
    """リピート発火間隔（秒）。全ジェスチャ共通。[SPEC-REPEAT-INTERVAL]"""
    return 0.04


def get_delay_time() -> float:
    """猶予時間（秒）。トリガ自体へのダウン動作発行を遅延させる時間。[SPEC-TRIGGER-ACTION-FLICK-TIME]"""
    return 0.3


def get_flick_time() -> float:
    """後方互換エイリアス。get_delay_time() と同値。"""
    return get_delay_time()


def get_toggle_hotkey() -> frozenset[int] | None:
    """
    ジェスチャの有効/無効をトグルするホットキー。
    frozenset[int] で VK コードの組み合わせを返す。複数キー同時押し対応。
    None を返すとホットキー無効。

    例:
        return frozenset({VK.F14})              # F14 単独
        return frozenset({VK.F13, VK.F14})      # F13+F14 同時押し
        return None                             # ホットキー無効
    """
    return frozenset({VK.N6, VK.N8})

# ===========================================================================
# ジェスチャテーブル取得関数  [SPEC-CONFIG-FILE]
# ===========================================================================

def get_gesture_table() -> list[GestureRecord]:
    """
    ジェスチャテーブルを返す。
    [SPEC-CONFIG-FILE] 将来的にはJSONファイルからの読み込みへ移行予定。
    """
    try:
        ret = [
            _rec_scrlButton(),
            _rec_LeftButton(),
            _rec_RightButton(),
            _rec_LeftRightButton(),
            _rec_scrlLeftButton(),
            _rec_scrlRightButton(),
            _rec_scrlLeftRightButton(),
            
#            _rec_num7Button(),
#            _rec_num8Button(),
#            _rec_num9Button(),
#            _rec_num89Button(),
            
            _rec_xButton(),
            _rec_cButton(),
            _rec_vButton(),
            _rec_xcButton(),
            _rec_xvButton(),
            _rec_cvButton(),
        ]
        print("config正常")

        return ret
    except Exception as e:
        print("【エラーをキャッチしました】")
        print(f"発生したエラー内容: {e}")

# ===========================================================================
# REC-01  右ボタン単独
# ===========================================================================
# ジェスチャデータ仕様トレース:
#   移動上下左右 [SPEC-MOVE-THRESHOLD][SPEC-MOVE-RESET]
#   スクロール上下 [SPEC-GKEY-SINGLE]
#   X1/X2 マウスボタン [SPEC-GKEY-SINGLE][SPEC-REPEAT-DISABLED]
#   トリガ自体（フリック/リピート）[SPEC-TRIGGER-ACTION-ASSIGN]
#                                  [SPEC-TRIGGER-ACTION-DELAY]
#                                  [SPEC-TRIGGER-ACTION-PUSHONLY]
# ===========================================================================
def _rec_scrlButton() -> GestureRecord:
    return record((VK.SCROLL), entries=[
    ])

def _rec_LeftButton() -> GestureRecord:
    return record((VK.LEFT), entries=[
        ("", "↓Left", "↑Left", "↓Left", 2),

        (GKey.MOVE_UP,    "^r", 0),
        (GKey.MOVE_DOWN,  "^w", 0),
        (GKey.MOVE_LEFT,  "!Left", 0),
        (GKey.MOVE_RIGHT, "!Right", 0),
        
        (GKey.SCROLL_UP,  "^PgUp", 0),
        (GKey.SCROLL_DOWN,"^PgDn", 0),
    ],threshold=100,move_cooldown=1)

def _rec_RightButton() -> GestureRecord:
    return record((VK.RIGHT), entries=[
        ("", "↓Right", "↑Right", "↓Right", 2),

        (GKey.MOVE_UP,    "Up", 0),
        (GKey.MOVE_DOWN,  "Down", 0),
        (GKey.MOVE_LEFT,  "Left", 0),
        (GKey.MOVE_RIGHT, "Right", 0),
    ],threshold=100)

def _rec_LeftRightButton() -> GestureRecord:
    return record((VK.RIGHT,VK.LEFT), entries=[
        (GKey.MOVE_UP,    "WheelUp", 0),
        (GKey.MOVE_DOWN,  "WheelDown", 0),
        (GKey.MOVE_LEFT,  "WheelLeft", 0),
        (GKey.MOVE_RIGHT, "WheelRight", 0),
    ],threshold=50)

def _rec_scrlLeftButton() -> GestureRecord:
    return record((VK.SCROLL,VK.LEFT), entries=[
        ("", "↓RButton", "↑RButton", noop, 1.0),
    ],threshold=100,move_cooldown=0.2)

def _rec_scrlRightButton() -> GestureRecord:
    return record((VK.SCROLL,VK.RIGHT), entries=[
        ("", "↓LButton", "↑LButton", noop, 1.0),
    ],threshold=100,move_cooldown=0.2)

def _rec_scrlLeftRightButton() -> GestureRecord:
    return record((VK.SCROLL,VK.LEFT,VK.RIGHT), entries=[
    ],threshold=100,move_cooldown=0.2)

def _rec_num7Button() -> GestureRecord:
    return record((VK.NUMPAD7), entries=[
        (GKey.MOVE_UP,    "^r", 0),
        (GKey.MOVE_DOWN,  "^w", 0),
        (GKey.MOVE_LEFT,  "!Left", 0),
        (GKey.MOVE_RIGHT, "!Right", 0),
        
        (GKey.SCROLL_UP,  "^PgUp", 0),
        (GKey.SCROLL_DOWN,"^PgDn", 0),
    ],threshold=100,move_cooldown=1)

def _rec_num8Button() -> GestureRecord:
    return record((VK.NUMPAD8), entries=[
        ("", "↓RButton", "↑RButton", noop, 0.5),
    ],threshold=100,move_cooldown=0.2)

def _rec_num9Button() -> GestureRecord:
    return record((VK.NUMPAD9), entries=[
        ("", "↓LButton", "↑LButton", noop, 0.5),
    ],threshold=100,move_cooldown=0.2)

def _rec_num89Button() -> GestureRecord:
    return record((VK.NUMPAD8,VK.NUMPAD9), entries=[
        (GKey.MOVE_UP,    "WheelUp", 0),
        (GKey.MOVE_DOWN,  "WheelDown", 0),
        (GKey.MOVE_LEFT,  "WheelLeft", 0),
        (GKey.MOVE_RIGHT, "WheelRight", 0),
    ],threshold=50)


def _rec_xButton() -> GestureRecord:
    return record((VK.X), entries=[
        ("", "↓x", "↑x", "↓x", 0.7),

        (GKey.MOVE_LEFT,  "BackSpace", 0),
        (GKey.MOVE_RIGHT, "Delete", 0),
        
        (GKey.SCROLL_UP,  "^z", 0),
        (GKey.SCROLL_DOWN,"^y", 0),
    ],threshold=100,move_cooldown=0.3)

def _rec_cButton() -> GestureRecord:
    return record((VK.C), entries=[
        ("", "↓c", "↑c", "↓c", 0.7),

        (GKey.MOVE_UP,    "WheelUp", 0),
        (GKey.MOVE_DOWN,  "WheelDown", 0),
        (GKey.MOVE_LEFT,  "WheelLeft", 0),
        (GKey.MOVE_RIGHT, "WheelRight", 0),

        (GKey.SCROLL_UP,  "^WheelUp", 0),
        (GKey.SCROLL_DOWN,"^WheelDown", 0),
    ],threshold=50)

def _rec_vButton() -> GestureRecord:
    return record((VK.V), entries=[
        ("", "↓v", "↑v", "↓v", 0.7),

        (GKey.MOVE_UP,    "Up", 0),
        (GKey.MOVE_DOWN,  "Down", 0),
        (GKey.MOVE_LEFT,  "Left", 0),
        (GKey.MOVE_RIGHT, "Right", 0),
    ],threshold=100)

def _rec_xcButton() -> GestureRecord:
    return record((VK.X,VK.C), entries=[
        ("", "↓RButton", "↑RButton", noop, 0.5),
    ],threshold=50)

def _rec_xvButton() -> GestureRecord:
    return record((VK.X,VK.V), entries=[
        ("", "↓LButton", "↑LButton", noop, 0.5),
    ],threshold=50)

def _rec_cvButton() -> GestureRecord:
    return record((VK.C,VK.V), entries=[
        (GKey.MOVE_UP,    "^r", 0),
        (GKey.MOVE_DOWN,  "^w", 0),
        (GKey.MOVE_LEFT,  "!Left", 0),
        (GKey.MOVE_RIGHT, "!Right", 0),
        
        (GKey.SCROLL_UP,  "^PgUp", 0),
        (GKey.SCROLL_DOWN,"^PgDn", 0),
    ],threshold=100,move_cooldown=1)
