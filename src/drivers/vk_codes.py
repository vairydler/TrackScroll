# vk_codes.py v1.0
# Windows 仮想キーコード (VK_*) およびスキャンコード (SC_*) 定数定義
# 参考: https://learn.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes
#
# 使用例:
#   from vk_codes import VK, SC
#   od.key_press(VK.A)
#   od.key_press_scan(SC.A)

class VK:
    """仮想キーコード定数。"""

    # ------------------------------------------------------------------
    # マウスボタン (output_driver.py / input_driver.py と共通)
    # ------------------------------------------------------------------
    LBUTTON  = 0x01
    RBUTTON  = 0x02
    MBUTTON  = 0x04
    XBUTTON1 = 0x05
    XBUTTON2 = 0x06

    # ------------------------------------------------------------------
    # 制御キー
    # ------------------------------------------------------------------
    BACK      = 0x08   # Backspace
    TAB       = 0x09
    RETURN    = 0x0D   # Enter
    SHIFT     = 0x10
    CONTROL   = 0x11   # Ctrl
    MENU      = 0x12   # Alt
    PAUSE     = 0x13
    CAPITAL   = 0x14   # Caps Lock
    ESCAPE    = 0x1B
    SPACE     = 0x20
    PRIOR     = 0x21   # Page Up
    NEXT      = 0x22   # Page Down
    END       = 0x23
    HOME      = 0x24
    LEFT      = 0x25
    UP        = 0x26
    RIGHT     = 0x27
    DOWN      = 0x28
    SNAPSHOT  = 0x2C   # Print Screen
    INSERT    = 0x2D
    DELETE    = 0x2E

    # ------------------------------------------------------------------
    # 数字キー (メインキーボード)
    # ------------------------------------------------------------------
    N0 = 0x30
    N1 = 0x31
    N2 = 0x32
    N3 = 0x33
    N4 = 0x34
    N5 = 0x35
    N6 = 0x36
    N7 = 0x37
    N8 = 0x38
    N9 = 0x39

    # ------------------------------------------------------------------
    # アルファベットキー
    # ------------------------------------------------------------------
    A = 0x41
    B = 0x42
    C = 0x43
    D = 0x44
    E = 0x45
    F = 0x46
    G = 0x47
    H = 0x48
    I = 0x49
    J = 0x4A
    K = 0x4B
    L = 0x4C
    M = 0x4D
    N = 0x4E
    O = 0x4F
    P = 0x50
    Q = 0x51
    R = 0x52
    S = 0x53
    T = 0x54
    U = 0x55
    V = 0x56
    W = 0x57
    X = 0x58
    Y = 0x59
    Z = 0x5A

    # ------------------------------------------------------------------
    # Windows キー・アプリケーションキー
    # ------------------------------------------------------------------
    LWIN = 0x5B
    RWIN = 0x5C
    APPS = 0x5D   # アプリケーションキー（右クリックメニュー）

    # ------------------------------------------------------------------
    # テンキー
    # ------------------------------------------------------------------
    NUMPAD0   = 0x60
    NUMPAD1   = 0x61
    NUMPAD2   = 0x62
    NUMPAD3   = 0x63
    NUMPAD4   = 0x64
    NUMPAD5   = 0x65
    NUMPAD6   = 0x66
    NUMPAD7   = 0x67
    NUMPAD8   = 0x68
    NUMPAD9   = 0x69
    MULTIPLY  = 0x6A   # テンキー *
    ADD       = 0x6B   # テンキー +
    SUBTRACT  = 0x6D   # テンキー -
    DECIMAL   = 0x6E   # テンキー .
    DIVIDE    = 0x6F   # テンキー /
    NUMLOCK   = 0x90
    SEPARATOR = 0x6C   # テンキー Enter (一部キーボード)

    # ------------------------------------------------------------------
    # ファンクションキー
    # ------------------------------------------------------------------
    F1  = 0x70
    F2  = 0x71
    F3  = 0x72
    F4  = 0x73
    F5  = 0x74
    F6  = 0x75
    F7  = 0x76
    F8  = 0x77
    F9  = 0x78
    F10 = 0x79
    F11 = 0x7A
    F12 = 0x7B
    F13 = 0x7C
    F14 = 0x7D
    F15 = 0x7E
    F16 = 0x7F
    F17 = 0x80
    F18 = 0x81
    F19 = 0x82
    F20 = 0x83
    F21 = 0x84
    F22 = 0x85
    F23 = 0x86
    F24 = 0x87

    # ------------------------------------------------------------------
    # ロックキー
    # ------------------------------------------------------------------
    SCROLL = 0x91   # Scroll Lock

    # ------------------------------------------------------------------
    # 修飾キー（左右区別あり）
    # ------------------------------------------------------------------
    LSHIFT   = 0xA0
    RSHIFT   = 0xA1
    LCONTROL = 0xA2
    RCONTROL = 0xA3
    LMENU    = 0xA4   # 左 Alt
    RMENU    = 0xA5   # 右 Alt (AltGr)

    # ------------------------------------------------------------------
    # ブラウザ・メディア・アプリ系
    # ------------------------------------------------------------------
    BROWSER_BACK      = 0xA6
    BROWSER_FORWARD   = 0xA7
    BROWSER_REFRESH   = 0xA8
    BROWSER_STOP      = 0xA9
    BROWSER_SEARCH    = 0xAA
    BROWSER_FAVORITES = 0xAB
    BROWSER_HOME      = 0xAC
    VOLUME_MUTE       = 0xAD
    VOLUME_DOWN       = 0xAE
    VOLUME_UP         = 0xAF
    MEDIA_NEXT_TRACK  = 0xB0
    MEDIA_PREV_TRACK  = 0xB1
    MEDIA_STOP        = 0xB2
    MEDIA_PLAY_PAUSE  = 0xB3
    LAUNCH_MAIL       = 0xB4
    LAUNCH_MEDIA      = 0xB5
    LAUNCH_APP1       = 0xB6
    LAUNCH_APP2       = 0xB7

    # ------------------------------------------------------------------
    # 記号キー（日本語 109 キーボード基準）
    # ※ キーボードレイアウトにより実際の文字は異なる場合がある
    # ------------------------------------------------------------------
    OEM_1          = 0xBA   # ; :（US: ; :  / JP: ; +）
    OEM_PLUS       = 0xBB   # =（US: = +  / JP: ^ ~）
    OEM_COMMA      = 0xBC   # , <
    OEM_MINUS      = 0xBD   # - _（US: - _  / JP: - =）
    OEM_PERIOD     = 0xBE   # . >
    OEM_2          = 0xBF   # / ?（US: / ?  / JP: / ?）
    OEM_3          = 0xC0   # `（US: ` ~  / JP: @ `）
    OEM_4          = 0xDB   # [（US: [ {  / JP: [ {）
    OEM_5          = 0xDC   # \（US: \ |  / JP: \ |）
    OEM_6          = 0xDD   # ]（US: ] }  / JP: ] }）
    OEM_7          = 0xDE   # '（US: ' "  / JP: ^ ~）
    OEM_8          = 0xDF   # (メーカー依存)
    OEM_102        = 0xE2   # 追加キー (JP: \ _  / 欧州: < >)

    # ------------------------------------------------------------------
    # 日本語キーボード固有
    # ------------------------------------------------------------------
    KANA         = 0x15   # カナ
    KANJI        = 0x19   # 漢字
    CONVERT      = 0x1C   # 変換
    NONCONVERT   = 0x1D   # 無変換
    DBE_ALPHANUMERIC = 0xF0   # 英数（半角/全角と同等）
    OEM_AUTO     = 0xF3   # 自動変換
    OEM_COPY     = 0xF2   # コピー (JP専用)
    OEM_ENLW     = 0xF4   # 全角英数
    OEM_BACKTAB  = 0xF5   # Shift+Tab 相当 (JP)

    # ------------------------------------------------------------------
    # その他
    # ------------------------------------------------------------------
    SLEEP      = 0x5F
    CANCEL     = 0x03   # Ctrl+Break
    CLEAR      = 0x0C   # テンキー 5 (NumLock OFF 時)
    SELECT     = 0x29
    PRINT      = 0x2A
    EXECUTE    = 0x2B
    HELP       = 0x2F
    ATTN       = 0xF6
    CRSEL      = 0xF7
    EXSEL      = 0xF8
    EREOF      = 0xF9
    PLAY       = 0xFA
    ZOOM       = 0xFB
    NONAME     = 0xFC
    PA1        = 0xFD
    OEM_CLEAR  = 0xFE

    # ------------------------------------------------------------------
    # よく使うエイリアス
    # ------------------------------------------------------------------
    ENTER     = RETURN
    CTRL      = CONTROL
    ALT       = MENU
    LCTRL     = LCONTROL
    RCTRL     = RCONTROL
    LALT      = LMENU
    RALT      = RMENU
    BACKSPACE = BACK
    CAPS_LOCK = CAPITAL
    PAGE_UP   = PRIOR
    PAGE_DOWN = NEXT
    PRTSC     = SNAPSHOT


class SC:
    """
    スキャンコード定数（Set 1 / Make コード）。
    key_press_scan / key_down_scan / key_up_scan に渡す。

    拡張キー（テンキー以外の方向キー、Insert、Delete 等）は
    0xE0 プレフィックス付きの 2 バイトコードが必要な場合があるが、
    output_driver.py の KEYEVENTF_SCANCODE では wScan に
    下位バイトのみ渡し、KEYEVENTF_EXTENDEDKEY を組み合わせるのが一般的。
    ここでは wScan に渡す値（下位バイト）を定義する。

    VK ベースの操作で十分な場合は SC より VK の使用を推奨。
    """

    # ------------------------------------------------------------------
    # ESC・ファンクションキー
    # ------------------------------------------------------------------
    ESCAPE = 0x01
    F1     = 0x3B
    F2     = 0x3C
    F3     = 0x3D
    F4     = 0x3E
    F5     = 0x3F
    F6     = 0x40
    F7     = 0x41
    F8     = 0x42
    F9     = 0x43
    F10    = 0x44
    F11    = 0x57
    F12    = 0x58

    # ------------------------------------------------------------------
    # 数字・記号行（US/JP 共通の物理位置）
    # ------------------------------------------------------------------
    N1           = 0x02   # 1 !
    N2           = 0x03   # 2 @
    N3           = 0x04   # 3 #
    N4           = 0x05   # 4 $
    N5           = 0x06   # 5 %
    N6           = 0x07   # 6 ^
    N7           = 0x08   # 7 &
    N8           = 0x09   # 8 *
    N9           = 0x0A   # 9 (
    N0           = 0x0B   # 0 )
    MINUS        = 0x0C   # - _ (US) / - = (JP)
    EQUALS       = 0x0D   # = + (US) / ^ ~ (JP)
    BACKSPACE    = 0x0E

    # ------------------------------------------------------------------
    # QWERTY 行
    # ------------------------------------------------------------------
    TAB     = 0x0F
    Q       = 0x10
    W       = 0x11
    E       = 0x12
    R       = 0x13
    T       = 0x14
    Y       = 0x15
    U       = 0x16
    I       = 0x17
    O       = 0x18
    P       = 0x19
    LBRACKET = 0x1A   # [ { (US/JP)
    RBRACKET = 0x1B   # ] } (US/JP)
    RETURN  = 0x1C    # Enter (メインキーボード)
    ENTER   = 0x1C    # エイリアス

    # ------------------------------------------------------------------
    # ASDF 行
    # ------------------------------------------------------------------
    LCONTROL = 0x1D
    A        = 0x1E
    S        = 0x1F
    D        = 0x20
    F        = 0x21
    G        = 0x22
    H        = 0x23
    J        = 0x24
    K        = 0x25
    L        = 0x26
    SEMICOLON = 0x27   # ; : (US) / ; + (JP)
    QUOTE    = 0x28    # ' " (US) / : * (JP)
    BACKQUOTE = 0x29   # ` ~ (US) / 半角/全角 (JP)
    LSHIFT   = 0x2A
    BACKSLASH = 0x2B   # \ | (US) / ] } (JP)

    # ------------------------------------------------------------------
    # ZXCV 行
    # ------------------------------------------------------------------
    Z       = 0x2C
    X       = 0x2D
    C       = 0x2E
    V       = 0x2F
    B       = 0x30
    N       = 0x31
    M       = 0x32
    COMMA   = 0x33   # , <
    PERIOD  = 0x34   # . >
    SLASH   = 0x35   # / ?
    RSHIFT  = 0x36
    NUMPAD_MULTIPLY = 0x37   # テンキー *
    LMENU   = 0x38   # 左 Alt
    SPACE   = 0x39
    CAPITAL = 0x3A   # Caps Lock

    # ------------------------------------------------------------------
    # テンキー
    # ------------------------------------------------------------------
    NUMPAD7   = 0x47
    NUMPAD8   = 0x48
    NUMPAD9   = 0x49
    NUMPAD_SUBTRACT = 0x4A
    NUMPAD4   = 0x4B
    NUMPAD5   = 0x4C
    NUMPAD6   = 0x4D
    NUMPAD_ADD = 0x4E
    NUMPAD1   = 0x4F
    NUMPAD2   = 0x50
    NUMPAD3   = 0x51
    NUMPAD0   = 0x52
    NUMPAD_DECIMAL = 0x53
    NUMPAD_ENTER   = 0x1C   # 拡張 (E0 プレフィックス)
    NUMPAD_DIVIDE  = 0x35   # 拡張 (E0 プレフィックス)
    NUMLOCK   = 0x45
    SCROLL    = 0x46   # Scroll Lock

    # ------------------------------------------------------------------
    # ナビゲーション・編集キー（拡張、E0 プレフィックス付き）
    # ※ KEYEVENTF_EXTENDEDKEY が自動付与される VK 経由を推奨
    # ------------------------------------------------------------------
    INSERT    = 0x52   # 拡張
    DELETE    = 0x53   # 拡張
    HOME      = 0x47   # 拡張
    END       = 0x4F   # 拡張
    PAGE_UP   = 0x49   # 拡張
    PAGE_DOWN = 0x51   # 拡張
    UP        = 0x48   # 拡張
    DOWN      = 0x50   # 拡張
    LEFT      = 0x4B   # 拡張
    RIGHT     = 0x4D   # 拡張
    SNAPSHOT  = 0x37   # Print Screen (拡張)

    # ------------------------------------------------------------------
    # Windows キー・その他
    # ------------------------------------------------------------------
    LWIN    = 0x5B   # 拡張
    RWIN    = 0x5C   # 拡張
    APPS    = 0x5D   # 拡張（アプリケーションキー）
    RMENU   = 0x38   # 右 Alt (拡張, E0 プレフィックス)
    RCONTROL = 0x1D  # 右 Ctrl (拡張, E0 プレフィックス)

    # ------------------------------------------------------------------
    # 日本語キーボード固有
    # ------------------------------------------------------------------
    MUHENKAN   = 0x7B   # 無変換
    HENKAN     = 0x79   # 変換
    HIRAGANA   = 0x70   # ひらがな/カタカナ
    YEN        = 0x7D   # ¥ | (JP 右下)
    UNDERSCORE = 0x73   # _ (JP)

    # ------------------------------------------------------------------
    # エイリアス
    # ------------------------------------------------------------------
    CTRL      = LCONTROL
    ALT       = LMENU
    CAPS_LOCK = CAPITAL
    PRTSC     = SNAPSHOT
