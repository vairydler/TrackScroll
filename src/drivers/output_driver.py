# output_driver.py v2.1
"""
キー・マウス入力を SendInput で送出するドライバ。

v1.1 → v2.0 変更:
  - [SPEC-SELF-EVENT-FILTER] 対応。
    送出する全イベントの dwExtraInfo に識別子を付与する。
    識別子はモジュールレベル定数 GESTURE_EXTRA_INFO をデフォルト値とし、
    OutputDriver.set_extra_info() で変更可能。
  - MOUSEINPUT / KEYBDINPUT の dwExtraInfo フィールドを
    POINTER(c_ulong) → c_ulonglong に変更。
    ULONG_PTR は64bit環境で8バイトのため c_ulonglong が正しいサイズ。

v2.0 → v2.1 変更:
  - dwExtraInfo を c_ulong（4バイト）から c_ulonglong（8バイト）に修正。
    c_ulong では構造体サイズが Windows の期待値と一致せず SendInput が失敗していた。
"""

import ctypes
from ctypes import wintypes

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

INPUT_MOUSE    = 0
INPUT_KEYBOARD = 1

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP       = 0x0002
KEYEVENTF_SCANCODE    = 0x0008
KEYEVENTF_UNICODE     = 0x0004

MOUSEEVENTF_MOVE        = 0x0001
MOUSEEVENTF_LEFTDOWN    = 0x0002
MOUSEEVENTF_LEFTUP      = 0x0004
MOUSEEVENTF_RIGHTDOWN   = 0x0008
MOUSEEVENTF_RIGHTUP     = 0x0010
MOUSEEVENTF_MIDDLEDOWN  = 0x0020
MOUSEEVENTF_MIDDLEUP    = 0x0040
MOUSEEVENTF_XDOWN       = 0x0080
MOUSEEVENTF_XUP         = 0x0100
MOUSEEVENTF_WHEEL       = 0x0800
MOUSEEVENTF_HWHEEL      = 0x1000
MOUSEEVENTF_ABSOLUTE    = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000

XBUTTON1 = 0x0001
XBUTTON2 = 0x0002

VK_LBUTTON  = 0x01
VK_RBUTTON  = 0x02
VK_MBUTTON  = 0x04
VK_XBUTTON1 = 0x05
VK_XBUTTON2 = 0x06

WHEEL_DELTA = 120

# [SPEC-SELF-EVENT-FILTER] 自己送出イベント識別子のデフォルト値
# input_driver.py と同じ値を参照することで自己送出を判定する。
GESTURE_EXTRA_INFO: int = 0x47455354  # "GEST"

# ---------------------------------------------------------------------------
# 構造体
# ---------------------------------------------------------------------------

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",          ctypes.c_long),
        ("dy",          ctypes.c_long),
        ("mouseData",   ctypes.c_ulong),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_ulonglong),  # ULONG_PTR: 64bit環境で8バイト
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk",         ctypes.c_ushort),
        ("wScan",       ctypes.c_ushort),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_ulonglong),  # ULONG_PTR: 64bit環境で8バイト
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type",   ctypes.c_ulong),
        ("_input", _INPUT_UNION),
    ]

# ---------------------------------------------------------------------------
# user32 セットアップ
# ---------------------------------------------------------------------------

user32 = ctypes.windll.user32

user32.SendInput.argtypes = [
    ctypes.c_uint,
    ctypes.POINTER(INPUT),
    ctypes.c_int,
]
user32.SendInput.restype = ctypes.c_uint

user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype  = ctypes.c_int

SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

# ---------------------------------------------------------------------------
# 内部ヘルパー
# ---------------------------------------------------------------------------

def _send(*inputs: INPUT) -> int:
    """INPUT 構造体の列を SendInput に渡す。送信成功数を返す。"""
    arr = (INPUT * len(inputs))(*inputs)
    return user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))


def _mouse_input(flags: int,
                 dx: int = 0,
                 dy: int = 0,
                 mouse_data: int = 0,
                 extra_info: int = 0) -> INPUT:
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp._input.mi.dx          = dx
    inp._input.mi.dy          = dy
    # mouseData は c_ulong フィールドだが、スクロール値は符号付き32bitとして
    # Windows に渡す必要があるため & 0xFFFFFFFF で2の補数表現に変換して代入する。
    inp._input.mi.mouseData   = mouse_data & 0xFFFFFFFF
    inp._input.mi.dwFlags     = flags
    inp._input.mi.time        = 0
    inp._input.mi.dwExtraInfo = extra_info  # [SPEC-SELF-EVENT-FILTER]
    return inp


def _key_input(vk: int, flags: int, scan: int = 0,
               extra_info: int = 0) -> INPUT:
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp._input.ki.wVk         = vk
    inp._input.ki.wScan       = scan
    inp._input.ki.dwFlags     = flags
    inp._input.ki.time        = 0
    inp._input.ki.dwExtraInfo = extra_info  # [SPEC-SELF-EVENT-FILTER]
    return inp


# 拡張キー（右側・テンキー以外の方向キー等）の VK 一覧
_EXTENDED_KEYS = {
    0x21,  # VK_PRIOR  (Page Up)
    0x22,  # VK_NEXT   (Page Down)
    0x23,  # VK_END
    0x24,  # VK_HOME
    0x25,  # VK_LEFT
    0x26,  # VK_UP
    0x27,  # VK_RIGHT
    0x28,  # VK_DOWN
    0x2D,  # VK_INSERT
    0x2E,  # VK_DELETE
    0x5B,  # VK_LWIN
    0x5C,  # VK_RWIN
    0x5D,  # VK_APPS
    0x6F,  # VK_DIVIDE (テンキー /)
    0x90,  # VK_NUMLOCK
    0xA1,  # VK_RSHIFT
    0xA3,  # VK_RCONTROL
    0xA5,  # VK_RMENU
}

# ---------------------------------------------------------------------------
# OutputDriver
# ---------------------------------------------------------------------------

class OutputDriver:
    """
    キー・マウス入力を SendInput で送出するドライバ。

    [SPEC-SELF-EVENT-FILTER]
    全送出イベントの dwExtraInfo に _extra_info を付与する。
    デフォルトは GESTURE_EXTRA_INFO。set_extra_info() で変更可能。
    """

    def __init__(self):
        self._extra_info: int = GESTURE_EXTRA_INFO  # [SPEC-SELF-EVENT-FILTER]

    def set_extra_info(self, value: int) -> None:
        """[SPEC-SELF-EVENT-FILTER] 自己送出識別子を変更する。"""
        self._extra_info = value

    # ------------------------------------------------------------------
    # キーボード
    # ------------------------------------------------------------------

    def key_down(self, vk: int) -> bool:
        """仮想キー vk を押下する。戻り値: True=送信成功"""
        flags = KEYEVENTF_EXTENDEDKEY if vk in _EXTENDED_KEYS else 0
        return _send(_key_input(vk, flags,
                                extra_info=self._extra_info)) == 1

    def key_up(self, vk: int) -> bool:
        """仮想キー vk を離す。戻り値: True=送信成功"""
        flags = KEYEVENTF_KEYUP
        if vk in _EXTENDED_KEYS:
            flags |= KEYEVENTF_EXTENDEDKEY
        return _send(_key_input(vk, flags,
                                extra_info=self._extra_info)) == 1

    def key_press(self, vk: int) -> bool:
        """仮想キー vk を押下→離上（1回打鍵）。戻り値: True=両イベント送信成功"""
        flags_dn = KEYEVENTF_EXTENDEDKEY if vk in _EXTENDED_KEYS else 0
        flags_up = flags_dn | KEYEVENTF_KEYUP
        return _send(
            _key_input(vk, flags_dn, extra_info=self._extra_info),
            _key_input(vk, flags_up, extra_info=self._extra_info),
        ) == 2

    def key_down_scan(self, scan: int) -> bool:
        """スキャンコード指定で押下。"""
        return _send(_key_input(0, KEYEVENTF_SCANCODE, scan,
                                extra_info=self._extra_info)) == 1

    def key_up_scan(self, scan: int) -> bool:
        """スキャンコード指定で離上。"""
        return _send(_key_input(0, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, scan,
                                extra_info=self._extra_info)) == 1

    def key_press_scan(self, scan: int) -> bool:
        """スキャンコード指定で押下→離上。"""
        return _send(
            _key_input(0, KEYEVENTF_SCANCODE, scan,
                       extra_info=self._extra_info),
            _key_input(0, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, scan,
                       extra_info=self._extra_info),
        ) == 2

    def type_char(self, char: str) -> bool:
        """Unicode 文字を1文字送出（IME・レイアウト非依存）。"""
        code = ord(char[0])
        return _send(
            _key_input(0, KEYEVENTF_UNICODE, code,
                       extra_info=self._extra_info),
            _key_input(0, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, code,
                       extra_info=self._extra_info),
        ) == 2

    def type_text(self, text: str) -> bool:
        """文字列を Unicode イベントで送出。"""
        inputs = []
        for ch in text:
            code = ord(ch)
            inputs.append(_key_input(0, KEYEVENTF_UNICODE, code,
                                     extra_info=self._extra_info))
            inputs.append(_key_input(0, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, code,
                                     extra_info=self._extra_info))
        return _send(*inputs) == len(inputs)

    # ------------------------------------------------------------------
    # マウス ボタン
    # ------------------------------------------------------------------

    _BUTTON_MAP = {
        VK_LBUTTON:  (MOUSEEVENTF_LEFTDOWN,   MOUSEEVENTF_LEFTUP,   0),
        VK_RBUTTON:  (MOUSEEVENTF_RIGHTDOWN,  MOUSEEVENTF_RIGHTUP,  0),
        VK_MBUTTON:  (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP, 0),
        VK_XBUTTON1: (MOUSEEVENTF_XDOWN,      MOUSEEVENTF_XUP,      XBUTTON1 << 16),
        VK_XBUTTON2: (MOUSEEVENTF_XDOWN,      MOUSEEVENTF_XUP,      XBUTTON2 << 16),
    }

    def mouse_button(self, vk: int, pressed: bool) -> bool:
        """マウスボタンを押下 (pressed=True) または離上 (pressed=False)。"""
        entry = self._BUTTON_MAP.get(vk)
        if entry is None:
            raise ValueError(f"未対応のマウスボタン VK: 0x{vk:02X}")
        dn_flag, up_flag, mdata = entry
        flag = dn_flag if pressed else up_flag
        return _send(_mouse_input(flag, mouse_data=mdata,
                                  extra_info=self._extra_info)) == 1

    def mouse_click(self, vk: int = VK_LBUTTON) -> bool:
        """マウスボタンを押下→離上（クリック）。"""
        entry = self._BUTTON_MAP.get(vk)
        if entry is None:
            raise ValueError(f"未対応のマウスボタン VK: 0x{vk:02X}")
        dn_flag, up_flag, mdata = entry
        return _send(
            _mouse_input(dn_flag, mouse_data=mdata, extra_info=self._extra_info),
            _mouse_input(up_flag, mouse_data=mdata, extra_info=self._extra_info),
        ) == 2

    def mouse_double_click(self, vk: int = VK_LBUTTON) -> bool:
        """ダブルクリック（クリック×2）。"""
        entry = self._BUTTON_MAP.get(vk)
        if entry is None:
            raise ValueError(f"未対応のマウスボタン VK: 0x{vk:02X}")
        dn_flag, up_flag, mdata = entry
        return _send(
            _mouse_input(dn_flag, mouse_data=mdata, extra_info=self._extra_info),
            _mouse_input(up_flag, mouse_data=mdata, extra_info=self._extra_info),
            _mouse_input(dn_flag, mouse_data=mdata, extra_info=self._extra_info),
            _mouse_input(up_flag, mouse_data=mdata, extra_info=self._extra_info),
        ) == 4

    # ------------------------------------------------------------------
    # マウス スクロール
    # ------------------------------------------------------------------

    def mouse_scroll(self, delta: int, horizontal: bool = False) -> bool:
        """
        スクロールを送出。
        delta: 正=上/右, 負=下/左。1ノッチ = WHEEL_DELTA(120) が標準。
        horizontal: False=垂直（デフォルト）, True=水平
        """
        flag = MOUSEEVENTF_HWHEEL if horizontal else MOUSEEVENTF_WHEEL
        return _send(_mouse_input(flag, mouse_data=delta,
                                  extra_info=self._extra_info)) == 1

    # ------------------------------------------------------------------
    # マウス 移動
    # ------------------------------------------------------------------

    def mouse_move_rel(self, dx: int, dy: int) -> bool:
        """相対座標でマウスを移動。"""
        return _send(_mouse_input(MOUSEEVENTF_MOVE, dx=dx, dy=dy,
                                  extra_info=self._extra_info)) == 1

    def mouse_move_abs(self, x: int, y: int, virtual_desk: bool = False) -> bool:
        """絶対座標 (ピクセル) でマウスを移動。"""
        if virtual_desk:
            sw = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN) or 1
            sh = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN) or 1
            nx = (x * 65535) // (sw - 1)
            ny = (y * 65535) // (sh - 1)
            flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
        else:
            sw = user32.GetSystemMetrics(0) or 1
            sh = user32.GetSystemMetrics(1) or 1
            nx = (x * 65535) // (sw - 1)
            ny = (y * 65535) // (sh - 1)
            flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
        return _send(_mouse_input(flags, dx=nx, dy=ny,
                                  extra_info=self._extra_info)) == 1
