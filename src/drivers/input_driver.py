# input_driver.py v2.1
"""
デバイス入力をフックしてコールバックで通知するドライバ。

v2.0 → v2.1 変更:
  - パッケージ構成対応。
    `from output_driver` → `from drivers.output_driver`

v2.2 → v2.0 変更:
  - [SPEC-SELF-EVENT-FILTER] 対応。
    フックコールバック (_kb_proc / _ms_proc) で dwExtraInfo を照合し、
    自己送出イベントを無視（CallNextHookEx に渡さずスキップ）する。
    識別子は output_driver.GESTURE_EXTRA_INFO と同値をデフォルトとし、
    InputDriver.set_extra_info() で変更可能。
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


class InputDriver:
    """
    デバイス入力をフックしてコールバックで通知するドライバ。

    [SPEC-SELF-EVENT-FILTER]
    フックコールバックで dwExtraInfo を照合し、
    自己送出イベント（output_driver.py が送出したもの）を無視する。
    識別子のデフォルトは output_driver.GESTURE_EXTRA_INFO と同値。
    set_extra_info() で変更可能（output_driver.OutputDriver と同じ値を設定すること）。

    コールバック一覧（戻り値: True=伝播, False=伝播停止, None=伝播）:
        on_key(vk: int, pressed: bool) -> bool | None
        on_mouse_button(vk: int, pressed: bool) -> bool | None
        on_mouse_scroll(delta: int, horizontal: bool) -> bool | None
        on_mouse_move(dx: int, dy: int)
            ※移動は伝播制御なし（Raw Input由来・相対移動量）
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

    def set_extra_info(self, value: int) -> None:
        """[SPEC-SELF-EVENT-FILTER] 自己送出識別子を変更する。"""
        self._extra_info = value

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
                propagate = _call(self.on_mouse_move_filter, ms.pt.x, ms.pt.y)
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
                    self.on_mouse_move(ri.mouse.lLastX, ri.mouse.lLastY)
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

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
