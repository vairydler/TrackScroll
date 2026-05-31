# gesture_action.py v2.1
"""
ジェスチャキー定義・ジェスチャ動作定義・AHK風文字列パーサ。

v2.0 → v2.1 変更:
  - GestureRecord に move_cooldown フィールドを追加 [SPEC-MOVE-COOLDOWN]
  - GestureData をダウン/アップ/リピートの3動作方式に変更 [SPEC-ACTION-THREE-WAY]
  - AHK文字列記法に ↓/↑ プレフィックス（押しっぱなし記法）を追加 [SPEC-ACTION-STRING-NOTATION]
  - ActionKind に KEY_SEQUENCE（複数キーの同時down/up）を追加
  - GestureData.action を廃止し down_action / up_action / repeat_action に分割

[SPEC-ACTION-STRING-NOTATION] AHK風文字列記法によるキー/ボタン/スクロール登録
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, ClassVar, Optional, Union
import re

# ---------------------------------------------------------------------------
# ジェスチャキー種別
# ---------------------------------------------------------------------------

class GestureKeyKind:
    """ジェスチャキーの種類定数。[SPEC-GKEY-SINGLE]"""
    MOVE_UP    = "move_up"
    MOVE_DOWN  = "move_down"
    MOVE_LEFT  = "move_left"
    MOVE_RIGHT = "move_right"
    MOUSE_BTN  = "mouse_btn"
    SCROLL_UP       = "scroll_up"
    SCROLL_DOWN     = "scroll_down"
    SCROLL_LEFT     = "scroll_left"
    SCROLL_RIGHT    = "scroll_right"
    KEY        = "key"
    TRIGGER    = "trigger"   # 空欄ジェスチャキー [SPEC-TRIGGER-ACTION-ASSIGN]

    # アップ動作を持てないジェスチャキー種別
    NO_UP_KINDS = frozenset({
        MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT,
        SCROLL_UP, SCROLL_DOWN, SCROLL_LEFT, SCROLL_RIGHT,
    })


@dataclass(frozen=True)
class GestureKey:
    """
    ジェスチャキーを表す不変オブジェクト。
    [SPEC-GKEY-SINGLE] 1データにつき1入力のみ。
    """
    kind: str
    vk: int = 0

    @staticmethod
    def move(direction: str) -> "GestureKey":
        return GestureKey(kind=f"move_{direction}")

    @staticmethod
    def mouse_button(vk: int) -> "GestureKey":
        return GestureKey(kind=GestureKeyKind.MOUSE_BTN, vk=vk)

    @staticmethod
    def scroll(direction: str) -> "GestureKey":
        return GestureKey(kind=f"scroll_{direction}")

    @staticmethod
    def key(vk: int) -> "GestureKey":
        return GestureKey(kind=GestureKeyKind.KEY, vk=vk)

    @staticmethod
    def trigger() -> "GestureKey":
        """空欄ジェスチャキー [SPEC-TRIGGER-ACTION-ASSIGN]"""
        return GestureKey(kind=GestureKeyKind.TRIGGER)

    def has_up(self) -> bool:
        """アップ動作を持てる種別かどうか。"""
        return self.kind not in GestureKeyKind.NO_UP_KINDS

    def __repr__(self) -> str:
        if self.kind in (GestureKeyKind.MOUSE_BTN, GestureKeyKind.KEY):
            return f"GestureKey({self.kind}, vk=0x{self.vk:02X})"
        return f"GestureKey({self.kind})"


# ---------------------------------------------------------------------------
# ジェスチャ動作種別
# ---------------------------------------------------------------------------

class ActionKind:
    """ジェスチャ動作の種類定数。"""
    KEY_PRESS    = "key_press"    # 押下→離上
    KEY_DOWN     = "key_down"     # 押下のみ
    KEY_UP       = "key_up"       # 離上のみ
    KEY_SEQUENCE = "key_sequence" # 複数キーの同時 down/up（↓+Ctrl 等）
    MOUSE_CLICK  = "mouse_click"
    MOUSE_DOWN   = "mouse_down"
    MOUSE_UP     = "mouse_up"
    SCROLL       = "scroll"
    FUNCTION     = "function"


@dataclass
class GestureAction:
    """
    ジェスチャ動作を表すオブジェクト。
    [SPEC-ACTION-STRING-NOTATION] 文字列記法から parse() で生成可能。

    KEY_SEQUENCE の場合:
      - vk_list: ダウン順のVKリスト（アップは逆順で発行する）
      - is_down: True=key_down の連鎖, False=key_up の連鎖
    """
    kind: str
    vk: int = 0
    modifiers: list = field(default_factory=list)
    delta: int = 0
    horizontal: bool = False
    func: Optional[Callable] = None
    # KEY_SEQUENCE 用
    vk_list: list = field(default_factory=list)
    is_down: bool = True   # True=down 連鎖, False=up 連鎖

    # ---- ファクトリ ----

    @staticmethod
    def key_press(vk: int, modifiers: list[int] | None = None) -> "GestureAction":
        return GestureAction(kind=ActionKind.KEY_PRESS, vk=vk,
                             modifiers=modifiers or [])

    @staticmethod
    def key_down(vk: int) -> "GestureAction":
        return GestureAction(kind=ActionKind.KEY_DOWN, vk=vk)

    @staticmethod
    def key_up(vk: int) -> "GestureAction":
        return GestureAction(kind=ActionKind.KEY_UP, vk=vk)

    @staticmethod
    def key_sequence(vk_list: list[int], is_down: bool) -> "GestureAction":
        """
        複数キーの down または up 連鎖。
        ↓+Ctrl → key_sequence([0xA0, 0xA2], is_down=True)
        ↑+Ctrl → key_sequence([0xA0, 0xA2], is_down=False)
        [SPEC-ACTION-STRING-NOTATION]
        """
        return GestureAction(kind=ActionKind.KEY_SEQUENCE,
                             vk_list=list(vk_list), is_down=is_down)

    @staticmethod
    def mouse_click(vk: int) -> "GestureAction":
        return GestureAction(kind=ActionKind.MOUSE_CLICK, vk=vk)

    @staticmethod
    def mouse_down(vk: int) -> "GestureAction":
        return GestureAction(kind=ActionKind.MOUSE_DOWN, vk=vk)

    @staticmethod
    def mouse_up(vk: int) -> "GestureAction":
        return GestureAction(kind=ActionKind.MOUSE_UP, vk=vk)

    @staticmethod
    def scroll(delta: int, horizontal: bool = False) -> "GestureAction":
        return GestureAction(kind=ActionKind.SCROLL, delta=delta,
                             horizontal=horizontal)

    @staticmethod
    def function(func: Callable) -> "GestureAction":
        return GestureAction(kind=ActionKind.FUNCTION, func=func)

    # ---- AHK風文字列パーサ [SPEC-ACTION-STRING-NOTATION] ----

    _SPECIAL_KEYS: ClassVar[dict[str, Optional[int]]] = {
        "LButton": 0x01, "RButton": 0x02, "MButton": 0x04,
        "XButton1": 0x05, "XButton2": 0x06,
        "WheelUp": None, "WheelDown": None,
        "WheelLeft": None, "WheelRight": None,
        "BackSpace": 0x08, "Tab": 0x09, "Enter": 0x0D,
        "Escape": 0x1B, "Space": 0x20,
        "PgUp": 0x21, "PgDn": 0x22, "End": 0x23, "Home": 0x24,
        "Left": 0x25, "Up": 0x26, "Right": 0x27, "Down": 0x28,
        "PrintScreen": 0x2C, "Insert": 0x2D, "Delete": 0x2E,
        "F1":  0x70, "F2":  0x71, "F3":  0x72, "F4":  0x73,
        "F5":  0x74, "F6":  0x75, "F7":  0x76, "F8":  0x77,
        "F9":  0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
        "LWin": 0x5B, "RWin": 0x5C, "Apps": 0x5D,
        "NumLock": 0x90, "ScrollLock": 0x91, "CapsLock": 0x14,
        "LShift": 0xA0, "RShift": 0xA1, "LCtrl": 0xA2, "RCtrl": 0xA3,
        "LAlt": 0xA4, "RAlt": 0xA5,
        "VolMute": 0xAD, "VolDown": 0xAE, "VolUp": 0xAF,
        "MediaNext": 0xB0, "MediaPrev": 0xB1,
        "MediaStop": 0xB2, "MediaPlay": 0xB3,
        "BrowserBack": 0xA6, "BrowserForward": 0xA7,
        "Shift": 0xA0, "Ctrl": 0xA2, "Alt": 0xA4, "Win": 0x5B,
    }

    _MOD_MAP: ClassVar[dict[str, int]] = {
        "!": 0xA4,  # LAlt
        "^": 0xA2,  # LCtrl
        "#": 0x5B,  # LWin
        "+": 0xA0,  # LShift
    }

    _WHEEL_MAP: ClassVar[dict[str, tuple[int, bool]]] = {
        "WheelUp":    ( 120, False),
        "WheelDown":  (-120, False),
        "WheelLeft":  (-120, True),
        "WheelRight": ( 120, True),
    }

    @staticmethod
    def parse(notation: str) -> "GestureAction":
        """
        AHK風文字列からGestureActionを生成する。
        [SPEC-ACTION-STRING-NOTATION]

        通常記法:
            "^z"        → Ctrl+Z (key_press)
            "!^#C"      → Alt+Ctrl+Win+C
            "LButton"   → 左クリック (mouse_click)
            "WheelUp"   → 垂直スクロール上 (scroll +120)

        押しっぱなし記法:
            "↓Alt"      → key_down(Alt)
            "↑Alt"      → key_up(Alt)
            "↓+Ctrl"    → key_sequence([Shift, Ctrl], is_down=True)
            "↑+Ctrl"    → key_sequence([Shift, Ctrl], is_down=False)
        """
        s = notation.strip()
        if not s:
            raise ValueError("空の記法は parse できません。GestureKey.trigger() を使用してください。")

        # ↓/↑ プレフィックス（押しっぱなし記法）[SPEC-ACTION-STRING-NOTATION]
        if s.startswith("↓") or s.startswith("↑"):
            is_down = s.startswith("↓")
            rest = s[1:]  # 矢印1文字（U+2193/U+2191）を除去
            return GestureAction._parse_hold(rest, is_down)

        # 通常記法
        return GestureAction._parse_normal(s)

    @staticmethod
    def _parse_hold(s: str, is_down: bool) -> "GestureAction":
        """
        ↓/↑ プレフィックス除去後の文字列をパースする。
        [SPEC-ACTION-STRING-NOTATION]

        キー:
            "Alt"    → key_down(0xA4) / key_up(0xA4)
            "+Ctrl"  → key_sequence([Shift, Ctrl], is_down=True)
                       key_sequence([Shift, Ctrl], is_down=False) ← _execute_action が逆順発行
        マウスボタン（モディファイヤあり可）:
            "^LButton" → Ctrl down → LButton down (is_down=True)
                         LButton up → Ctrl up    (is_down=False, 逆順)
        ホイール:
            ↓/↑ との組み合わせは押下状態を持たないためエラー。
        """
        # モディファイヤ記号を収集
        mods: list[int] = []
        i = 0
        while i < len(s) and s[i] in GestureAction._MOD_MAP:
            mods.append(GestureAction._MOD_MAP[s[i]])
            i += 1
        key_str = s[i:]

        # ホイールは ↓/↑ と組み合わせ不可 [SPEC-ACTION-STRING-NOTATION]
        if key_str in GestureAction._WHEEL_MAP:
            raise ValueError(
                f"ホイールは ↓/↑ 記法と組み合わせできません: "
                f"{'↓' if is_down else '↑'}{s!r}"
            )

        # マウスボタン（モディファイヤあり可）
        mouse_vks = {
            "LButton": 0x01, "RButton": 0x02, "MButton": 0x04,
            "XButton1": 0x05, "XButton2": 0x06,
        }
        if key_str in mouse_vks:
            btn_vk = mouse_vks[key_str]
            if not mods:
                # モディファイヤなし: 単純な mouse_down / mouse_up
                if is_down:
                    return GestureAction.mouse_down(btn_vk)
                else:
                    return GestureAction.mouse_up(btn_vk)
            else:
                # モディファイヤあり: key_sequence で mods を down/up し、
                # ボタン操作は別途 MOUSE_DOWN/MOUSE_UP を組み合わせる必要があるが、
                # GestureAction は単一動作のため KEY_SEQUENCE + MOUSE_* を
                # 合成した専用 kind を使う代わりに、
                # modifiers フィールドを持つ MOUSE_DOWN / MOUSE_UP として表現する。
                if is_down:
                    return GestureAction(kind=ActionKind.MOUSE_DOWN,
                                         vk=btn_vk, modifiers=mods)
                else:
                    return GestureAction(kind=ActionKind.MOUSE_UP,
                                         vk=btn_vk, modifiers=mods)

        # キー名解決（通常キー・特殊キー）
        vk = GestureAction._resolve_vk(key_str)
        vk_list = mods + [vk]

        if len(vk_list) == 1:
            if is_down:
                return GestureAction.key_down(vk_list[0])
            else:
                return GestureAction.key_up(vk_list[0])
        else:
            return GestureAction.key_sequence(vk_list, is_down=is_down)

    @staticmethod
    def _parse_normal(s: str) -> "GestureAction":
        """
        モディファイヤ＋キー名の通常記法をパースして key_press / mouse_click / scroll を返す。

        モディファイヤ＋ホイール:
            "^WheelUp" → Ctrl down → WheelUp → Ctrl up
        モディファイヤ＋マウスボタン:
            "^LButton" → Ctrl down → LButton click → Ctrl up
        """
        # モディファイヤ収集
        mods: list[int] = []
        i = 0
        while i < len(s) and s[i] in GestureAction._MOD_MAP:
            mods.append(GestureAction._MOD_MAP[s[i]])
            i += 1
        key_str = s[i:]

        # ホイール（モディファイヤあり可）
        if key_str in GestureAction._WHEEL_MAP:
            delta, horizontal = GestureAction._WHEEL_MAP[key_str]
            return GestureAction(kind=ActionKind.SCROLL, delta=delta,
                                 horizontal=horizontal, modifiers=mods)

        # マウスボタン（モディファイヤあり可）
        mouse_vks = {
            "LButton": 0x01, "RButton": 0x02, "MButton": 0x04,
            "XButton1": 0x05, "XButton2": 0x06,
        }
        if key_str in mouse_vks:
            return GestureAction(kind=ActionKind.MOUSE_CLICK,
                                 vk=mouse_vks[key_str], modifiers=mods)

        vk = GestureAction._resolve_vk(key_str)
        return GestureAction(kind=ActionKind.KEY_PRESS, vk=vk, modifiers=mods)

    @staticmethod
    def _resolve_vk(key_str: str) -> int:
        """キー名文字列をVKコードに解決する。"""
        if key_str in GestureAction._SPECIAL_KEYS:
            vk = GestureAction._SPECIAL_KEYS[key_str]
            if vk is None:
                raise ValueError(f"ホイールキーは押しっぱなし記法に使用できません: {key_str!r}")
            return vk
        if len(key_str) == 1:
            c = key_str.upper()
            if 'A' <= c <= 'Z':
                return ord(c)
            if '0' <= c <= '9':
                return ord(c)
            return ord(key_str)
        raise ValueError(f"解釈できないキー名: {key_str!r}")


# ---------------------------------------------------------------------------
# ジェスチャデータ  [SPEC-ACTION-THREE-WAY]
# ---------------------------------------------------------------------------

@dataclass
class GestureData:
    """
    ジェスチャキーと3種類の動作・リピート開始時間のセット。

    down_action   : ダウン発行条件が成立した時点で発火 [SPEC-ACTION-THREE-WAY]
    up_action     : ジェスチャキーが離された/トリガ変更時に発火（ダウン発行済みが条件）
                    [SPEC-ACTION-UP-TRIGGER][SPEC-ACTION-UP-SUPPRESS]
    repeat_action : リピート開始時間経過後にリピート間隔ごとに発火 [SPEC-REPEAT-TARGET]
    repeat_start  : 0=最速（リピート動作Noneなら無効）[SPEC-REPEAT-DISABLED]
    """
    gesture_key:   GestureKey
    down_action:   Optional[GestureAction] = None
    up_action:     Optional[GestureAction] = None
    repeat_action: Optional[GestureAction] = None
    repeat_start:  float = 0.0


# ---------------------------------------------------------------------------
# ジェスチャレコード
# ---------------------------------------------------------------------------

@dataclass
class GestureRecord:
    """
    トリガと複数のジェスチャデータの組み合わせ。
    threshold=None のときシステムデフォルトを使用 [SPEC-MOVE-THRESHOLD]
    move_cooldown=None または 0.0 のときクールダウン無効 [SPEC-MOVE-COOLDOWN]
    """
    trigger: frozenset
    gesture_data: list[GestureData] = field(default_factory=list)
    threshold: Optional[float] = None
    move_cooldown: Optional[float] = None

    def trigger_action(self) -> Optional[GestureData]:
        """空欄ジェスチャキー（トリガ自体への動作）を返す。[SPEC-TRIGGER-ACTION-ASSIGN]"""
        for gd in self.gesture_data:
            if gd.gesture_key.kind == GestureKeyKind.TRIGGER:
                return gd
        return None
