# input_driver.py v2.5
"""
デバイス入力をフックしてコールバックで通知するドライバ。

v2.4 → v2.5 変更:
  - _RdpState の restore_x/y を Raw Input 単位（生値）で保持するよう変更。
    scale 変換は SetCursorPos 呼び出し時のみ行う。
    これにより int 変換による端数誤差の累積を防ぐ。
  - _RdpState に restoring フラグを追加。
    SetCursorPos 直後の WM_MOUSEMOVE を _ms_proc 内で1回だけスキップし、
    WH_MOUSE_LL 側のループバックを防ぐ。
    restoring フラグは _ms_proc スレッド内のみで読み書きされるため
    スレッド競合の懸念はない。

v2.3 → v2.4 変更:
  - カーソル強制復元ロジックを InputDriver 内で完結させる。
    on_mouse_move_filter が False を返す条件（block_cursor=True かつ絶対座標モード）で
    SetCursorPos(restore_x, restore_y) を呼び last_x/y をその場で restore 座標に更新する。

v2.2 → v2.3 変更:
  - RDP関連の状態変数を _RdpState クラスにまとめた。
  - set_block_cursor(value) を追加。

v2.1 → v2.2 変更:
  - RDP等の絶対座標モード（MOUSE_MOVE_ABSOLUTE）対応。

v2.0 → v2.1 変更:
  - パッケージ構成対応。
    `from output_driver` → `from drivers.output_driver`

v1.0 → v2.0 変更:
  - [SPEC-SELF-EVENT-FILTER] 対応。
"""

import ctypes
from ctypes import wintypes
import threading

from drivers.output_driver import GESTURE_EXTRA_INFO

HC_ACTION       = 0
WH_KEYBOARD_LL  = 13
WH_MOUSE_LL     = 14
WM_KEYDOWN      = 0x0100
WM_KEYUP        = 0x0101
WM_SYSKEYDOWN   = 0x0104
WM_SYSKEYUP     = 0x0105
WM_MOUSEMOVE    = 0x0200
WM_LBUTTONDOWN  = 0x0201
WM_LBUTTONUP    = 0x0202
WM_RBUTTONDOWN  = 0x0204
WM_RBUTTONUP    = 0x0205
WM_MBUTTONDOWN  = 0x0207
WM_MBUTTONUP    = 0x0208
WM_MOUSEWHEEL   = 0x020A
WM_XBUTTONDOWN  = 0x020B
WM_XBUTTONUP    = 0x020C
WM_MOUSEHWHEEL  = 0x020E
WM_INPUT        = 0x00FF
HWND_MESSAGE    = wintypes.HWND(-3)
RIM_TYPEMOUSE   = 0
RIDEV_INPUTSINK = 0x00000100

# Raw Input マウスフラグ
MOUSE_MOVE_ABSOLUTE = 0x0001  # 絶対座標モード（RDP等）

# 仮想デスクトップサイズ取得用
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

VK_LBUTTON  = 0x01
VK_RBUTTON  = 0x02
VK_MBUTTON  = 0x04
VK_XBUTTON1 = 0x05
VK_XBUTTON2 = 0x06

RI_MOUSE_BUTTON_1_DOWN = 0x0001
RI_MOUSE_BUTTON_1_UP   = 0x0002
RI_MOUSE_BUTTON_2_DOWN = 0x0004
RI_MOUSE_BUTTON_2_UP   = 0x0008
RI_MOUSE_BUTTON_3_DOWN = 0x0010
RI_MOUSE_BUTTON_3_UP   = 0x0020
RI_MOUSE_BUTTON_4_DOWN = 0x0040
RI_MOUSE_BUTTON_4_UP   = 0x0080
RI_MOUSE_BUTTON_5_DOWN = 0x0100
RI_MOUSE_BUTTON_5_UP   = 0x0200
RI_MOUSE_WHEEL         = 0x0400
RI_MOUSE_HWHEEL        = 0x0800

user32 = ctypes.windll.user32

HOOKPROC = ctypes.WINFUNCTYPE(
    ctypes.c_longlong,
    ctypes.c_int,
    ctypes.c_ulonglong,
    ctypes.c_longlong,
)

WNDPROCTYPE = ctypes.WINFUNCTYPE(
    ctypes.c_longlong,
    ctypes.c_void_p,
    ctypes.c_uint,
    ctypes.c_ulonglong,
    ctypes.c_longlong,
)

user32.DefWindowProcW.argtypes = [
    ctypes.c_void_p,
    ctypes.c_uint,
    ctypes.c_ulonglong,
    ctypes.c_longlong,
]
user32.DefWindowProcW.restype = ctypes.c_longlong

user32.CallNextHookEx.argtypes = [
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_ulonglong,
    ctypes.c_longlong,
]
user32.CallNextHookEx.restype = ctypes.c_longlong


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode",      ctypes.c_ulong),
        ("scanCode",    ctypes.c_ulong),
        ("flags",       ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]

class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt",          wintypes.POINT),
        ("mouseData",   ctypes.c_ulong),
        ("flags",       ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]

class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ("usUsagePage", ctypes.c_ushort),
        ("usUsage",     ctypes.c_ushort),
        ("dwFlags",     ctypes.c_ulong),
        ("hwndTarget",  ctypes.c_void_p),
    ]

class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ("dwType",  ctypes.c_ulong),
        ("dwSize",  ctypes.c_ulong),
        ("hDevice", ctypes.c_void_p),
        ("wParam",  ctypes.c_ulonglong),
    ]

class RAWMOUSE(ctypes.Structure):
    _fields_ = [
        ("usFlags",            ctypes.c_ushort),
        ("usButtonFlags",      ctypes.c_ushort),
        ("usButtonData",       ctypes.c_short),
        ("ulRawButtons",       ctypes.c_ulong),
        ("lLastX",             ctypes.c_long),
        ("lLastY",             ctypes.c_long),
        ("ulExtraInformation", ctypes.c_ulong),
    ]

class RAWINPUT(ctypes.Structure):
    _fields_ = [
        ("header", RAWINPUTHEADER),
        ("mouse",  RAWMOUSE),
    ]


def _call(callback, *args):
    """
    コールバックを呼び出し、戻り値を返す。
    コールバックが None または戻り値が None の場合は True（伝播）とみなす。
    """
    if callback is None:
        return True
    result = callback(*args)
    return result if result is not None else True


# ===========================================================================
# RDP環境用状態オブジェクト
# ===========================================================================

class _RdpState:
    """
    RDP環境（絶対座標モード）に関する状態をまとめたオブジェクト。

    is_abs       : 絶対座標モードかどうか。初回 Raw Input イベントで確定する。
                   起動時点では不明のため None で初期化。
    scale_x/y    : 0〜65535 レンジを実ピクセルに換算するスケール係数。
                   起動時に仮想デスクトップサイズから計算する。
                   SetCursorPos 呼び出し時にのみ使用する。
    last_x/y     : 前回の絶対座標（Raw Input 単位・生値）。-1 = 未初期化。
    restore_x/y  : カーソルを戻す先の絶対座標（Raw Input 単位・生値）。
                   非ブロック中のみ現在位置に更新する。
                   ブロック中は据え置き（SetCursorPos の戻り先として保持）。
    block_cursor : カーソル移動ブロック中かどうか。
                   GestureEventHandler から set_block_cursor() 経由で更新される。
    restoring    : SetCursorPos 直後のフラグ。
                   True のとき _ms_proc は次の WM_MOUSEMOVE を1回だけスキップする。
                   _ms_proc スレッド内のみで読み書きされるためロック不要。
    """

    def __init__(self):
        self.is_abs:       bool | None = None   # 初回イベントで確定
        self.scale_x:      float       = 1.0
        self.scale_y:      float       = 1.0
        self.last_x:       int         = -1     # -1 = 未初期化（生値）
        self.last_y:       int         = -1
        self.restore_x:    int         = 0      # 生値
        self.restore_y:    int         = 0      # 生値
        self.block_cursor: bool        = False
        self.restoring:    bool        = False  # SetCursorPos 直後スキップ用

    def init_scale(self) -> None:
        """起動時に一度だけ呼ぶ。仮想デスクトップサイズからスケール係数を計算する。"""
        vw = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN) or 1
        vh = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN) or 1
        self.scale_x = vw / 65535.0
        self.scale_y = vh / 65535.0


# ===========================================================================
# InputDriver
# ===========================================================================

class InputDriver:
    """
    デバイス入力をフックしてコールバックで通知するドライバ。

    [SPEC-SELF-EVENT-FILTER]
    フックコールバックで dwExtraInfo を照合し、
    自己送出イベント（output_driver.py が送出したもの）を無視する。
    識別子のデフォルトは output_driver.GESTURE_EXTRA_INFO と同値。
    set_extra_info() で変更可能（output_driver.OutputDriver と同じ値を設定すること）。

    RDP環境（絶対座標モード）対応:
    Raw Input の usFlags に MOUSE_MOVE_ABSOLUTE が立っている場合、
    前回座標との差分を計算し、スケール係数で実ピクセル相当量に換算して
    on_mouse_move に渡す。

    カーソル移動ブロック（RDP対応）:
    on_mouse_move_filter が False を返した際、絶対座標モード確定済みであれば
    _ms_proc 内で SetCursorPos(restore_x * scale, restore_y * scale) を呼び
    カーソルを強制復元する。restore_x/y・last_x/y はいずれも Raw Input 単位の
    生値で保持し、scale 変換は SetCursorPos 呼び出し時にのみ行う。
    SetCursorPos 直後の WM_MOUSEMOVE は restoring フラグで1回だけスキップする。

    RDP関連の状態は _RdpState オブジェクト（self._rdp）にまとめられている。

    コールバック一覧（戻り値: True=伝播, False=伝播停止, None=伝播）:
        on_key(vk: int, pressed: bool) -> bool | None
        on_mouse_button(vk: int, pressed: bool) -> bool | None
        on_mouse_scroll(delta: int, horizontal: bool) -> bool | None
        on_mouse_move(dx: int, dy: int)
            ※移動は伝播制御なし（Raw Input由来・実ピクセル相当の相対移動量）
        on_mouse_move_filter(x: int, y: int) -> bool | None
            ※移動の伝播制御専用（WH_MOUSE_LL由来・絶対座標）
    """

    def __init__(self,
                 on_key=None,
                 on_mouse_button=None,
                 on_mouse_scroll=None,
                 on_mouse_move=None,
                 on_mouse_move_filter=None):
        self.on_key               = on_key
        self.on_mouse_button      = on_mouse_button
        self.on_mouse_scroll      = on_mouse_scroll
        self.on_mouse_move        = on_mouse_move
        self.on_mouse_move_filter = on_mouse_move_filter
        self._kb_hook             = None
        self._ms_hook             = None
        self._extra_info: int     = GESTURE_EXTRA_INFO  # [SPEC-SELF-EVENT-FILTER]

        # RDP環境用状態オブジェクト
        self._rdp = _RdpState()
        self._rdp.init_scale()

    def set_extra_info(self, value: int) -> None:
        """[SPEC-SELF-EVENT-FILTER] 自己送出識別子を変更する。"""
        self._extra_info = value

    def set_block_cursor(self, value: bool) -> None:
        """
        カーソル移動ブロック状態を更新する。
        GestureEventHandler の update() から呼ばれる。
        RDP環境では SetCursorPos によるカーソル強制復元の ON/OFF を制御する。
        """
        self._rdp.block_cursor = value

    def start(self):
        hook_thread = threading.Thread(target=self._run_hooks,    daemon=True)
        ri_thread   = threading.Thread(target=self._run_rawinput, daemon=True)
        hook_thread.start()
        ri_thread.start()

    def stop(self):
        if self._kb_hook:
            user32.UnhookWindowsHookEx(self._kb_hook)
            self._kb_hook = None
        if self._ms_hook:
            user32.UnhookWindowsHookEx(self._ms_hook)
            self._ms_hook = None

    def _run_hooks(self):
        kb_cb = HOOKPROC(self._kb_proc)
        ms_cb = HOOKPROC(self._ms_proc)
        self._kb_cb = kb_cb  # GC防止
        self._ms_cb = ms_cb

        self._kb_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, kb_cb, None, 0)
        self._ms_hook = user32.SetWindowsHookExW(WH_MOUSE_LL,    ms_cb, None, 0)

        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def _run_rawinput(self):
        wnd_proc_cb = WNDPROCTYPE(self._wnd_proc)
        self._wnd_proc_cb = wnd_proc_cb  # GC防止

        class WNDCLASSEX(ctypes.Structure):
            _fields_ = [
                ("cbSize",        ctypes.c_uint),
                ("style",         ctypes.c_uint),
                ("lpfnWndProc",   WNDPROCTYPE),
                ("cbClsExtra",    ctypes.c_int),
                ("cbWndExtra",    ctypes.c_int),
                ("hInstance",     ctypes.c_void_p),
                ("hIcon",         ctypes.c_void_p),
                ("hCursor",       ctypes.c_void_p),
                ("hbrBackground", ctypes.c_void_p),
                ("lpszMenuName",  ctypes.c_wchar_p),
                ("lpszClassName", ctypes.c_wchar_p),
                ("hIconSm",       ctypes.c_void_p),
            ]

        hinstance  = ctypes.windll.kernel32.GetModuleHandleW(None)
        class_name = "InputDriverWindow"
        wndclass   = WNDCLASSEX()
        wndclass.cbSize        = ctypes.sizeof(WNDCLASSEX)
        wndclass.lpfnWndProc   = wnd_proc_cb
        wndclass.lpszClassName = class_name
        wndclass.hInstance     = hinstance
        user32.RegisterClassExW(ctypes.byref(wndclass))

        hwnd = user32.CreateWindowExW(
            0, class_name, "InputDriver",
            0, 0, 0, 0, 0,
            HWND_MESSAGE, None, hinstance, None
        )

        rid = RAWINPUTDEVICE()
        rid.usUsagePage = 0x01
        rid.usUsage     = 0x02
        rid.dwFlags     = RIDEV_INPUTSINK
        rid.hwndTarget  = hwnd
        user32.RegisterRawInputDevices(
            ctypes.byref(rid), 1, ctypes.sizeof(RAWINPUTDEVICE)
        )

        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def _kb_proc(self, nCode, wParam, lParam):
        propagate = True
        if nCode == HC_ACTION:
            kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            # [SPEC-SELF-EVENT-FILTER] 自己送出イベントは無視して伝播
            if kb.dwExtraInfo == self._extra_info:
                return user32.CallNextHookEx(None, nCode, wParam, lParam)
            if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                propagate = _call(self.on_key, kb.vkCode, True)
            elif wParam in (WM_KEYUP, WM_SYSKEYUP):
                propagate = _call(self.on_key, kb.vkCode, False)
        if not propagate:
            return 1
        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    def _ms_proc(self, nCode, wParam, lParam):
        propagate = True
        if nCode == HC_ACTION:
            ms = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            # [SPEC-SELF-EVENT-FILTER] 自己送出イベントは無視して伝播
            if ms.dwExtraInfo == self._extra_info:
                return user32.CallNextHookEx(None, nCode, wParam, lParam)

            hi_word = (ms.mouseData >> 16) & 0xFFFF

            if wParam == WM_MOUSEMOVE:
                rdp = self._rdp
                # SetCursorPos 直後の1回はスキップしてループバックを防ぐ
                if rdp.restoring:
                    rdp.restoring = False
                    return 1  # 伝播停止（カーソルは既に復元済み）

                propagate = _call(self.on_mouse_move_filter, ms.pt.x, ms.pt.y)

                # 伝播停止 かつ 絶対座標モード確定済み → カーソル強制復元
                if not propagate and rdp.is_abs:
                    user32.SetCursorPos(
                        int(rdp.restore_x * rdp.scale_x),
                        int(rdp.restore_y * rdp.scale_y),
                    )
                    rdp.restoring = True

            elif wParam == WM_LBUTTONDOWN:
                propagate = _call(self.on_mouse_button, VK_LBUTTON, True)
            elif wParam == WM_LBUTTONUP:
                propagate = _call(self.on_mouse_button, VK_LBUTTON, False)
            elif wParam == WM_RBUTTONDOWN:
                propagate = _call(self.on_mouse_button, VK_RBUTTON, True)
            elif wParam == WM_RBUTTONUP:
                propagate = _call(self.on_mouse_button, VK_RBUTTON, False)
            elif wParam == WM_MBUTTONDOWN:
                propagate = _call(self.on_mouse_button, VK_MBUTTON, True)
            elif wParam == WM_MBUTTONUP:
                propagate = _call(self.on_mouse_button, VK_MBUTTON, False)
            elif wParam == WM_XBUTTONDOWN:
                vk = VK_XBUTTON1 if hi_word == 1 else VK_XBUTTON2
                propagate = _call(self.on_mouse_button, vk, True)
            elif wParam == WM_XBUTTONUP:
                vk = VK_XBUTTON1 if hi_word == 1 else VK_XBUTTON2
                propagate = _call(self.on_mouse_button, vk, False)
            elif wParam == WM_MOUSEWHEEL:
                delta = ctypes.c_short(hi_word).value
                propagate = _call(self.on_mouse_scroll, delta, False)
            elif wParam == WM_MOUSEHWHEEL:
                delta = ctypes.c_short(hi_word).value
                propagate = _call(self.on_mouse_scroll, delta, True)

        if not propagate:
            return 1
        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_INPUT and self.on_mouse_move:
            size = ctypes.c_uint(0)
            user32.GetRawInputData(
                lparam, 0x10000003, None,
                ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER)
            )
            buf = (ctypes.c_byte * size.value)()
            user32.GetRawInputData(
                lparam, 0x10000003, buf,
                ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER)
            )
            ri = ctypes.cast(buf, ctypes.POINTER(RAWINPUT)).contents
            if ri.header.dwType == RIM_TYPEMOUSE:
                self._handle_extra_buttons(ri.mouse.usButtonFlags)
                if ri.mouse.lLastX != 0 or ri.mouse.lLastY != 0:
                    self._handle_mouse_move(ri.mouse.usFlags,
                                            ri.mouse.lLastX,
                                            ri.mouse.lLastY)
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _handle_mouse_move(self, flags: int, x: int, y: int) -> None:
        """
        Raw Input の移動イベントを処理する。
        絶対座標モード（RDP等）と相対座標モードを usFlags で切り替える。
        is_abs は初回イベント時に確定し、以降は変化しない前提で扱う。

        絶対座標モード:
          - 初回イベント（last_x == -1）は差分計算をスキップして大ジャンプを防ぐ。
          - last_x/y・restore_x/y はいずれも Raw Input 単位の生値で保持する。
          - 差分をスケール係数で実ピクセル相当量に換算して on_mouse_move に渡す。
          - dx=dy=0 の場合は on_mouse_move を呼ばない。
          - 非ブロック中のみ restore_x/y を現在位置に更新する。
            ブロック中は restore_x/y を据え置き（SetCursorPos の戻り先として保持）。

        相対座標モード（通常）:
          - x / y をそのまま dx / dy として on_mouse_move に渡す。
        """
        rdp = self._rdp

        # 初回イベントで絶対/相対モードを確定
        if rdp.is_abs is None:
            rdp.is_abs = bool(flags & MOUSE_MOVE_ABSOLUTE)

        if rdp.is_abs:
            # 絶対座標モード（RDP等）
            if rdp.last_x == -1:
                # 初回: 前回値を記録するだけでコールバックはスキップ
                rdp.last_x    = x
                rdp.last_y    = y
                rdp.restore_x = x
                rdp.restore_y = y
                return

            dx = int((x - rdp.last_x) * rdp.scale_x)
            dy = int((y - rdp.last_y) * rdp.scale_y)
            rdp.last_x = x
            rdp.last_y = y

            if not rdp.block_cursor:
                # 非ブロック中: 現在位置を restore 座標として更新（生値のまま）
                rdp.restore_x = x
                rdp.restore_y = y

            if dx != 0 or dy != 0:
                self.on_mouse_move(dx, dy)
        else:
            # 相対座標モード（通常）
            self.on_mouse_move(x, y)

    def _handle_extra_buttons(self, flags):
        """Raw Input でボタン6・7を検知（メーカー依存）"""
        extra_map = [
            (0x1000, 0x10, True),
            (0x2000, 0x10, False),
            (0x4000, 0x11, True),
            (0x8000, 0x11, False),
        ]
        for flag_bit, vk, pressed in extra_map:
            if flags & flag_bit:
                _call(self.on_mouse_button, vk, pressed)
