# input_driver_debug.py v1.2
# input_driver.py の動作確認用デバッグスクリプト
# 30秒後に自動停止するフェールセーフ付き
#
# 実行方法: プロジェクトルートから python -m debug.input_driver_debug

import time
import threading
import os
from drivers.input_driver import InputDriver

FAILSAFE_SECONDS = 30


def on_key(vk, pressed):
    print(f"[KEY] vk=0x{vk:02X} {'押下' if pressed else '離上'}")
    return True  # 伝播


def on_mouse_button(vk, pressed):
    names = {
        0x01: '左',
        0x02: '右',
        0x04: '中',
        0x05: 'X1',
        0x06: 'X2',
        0x10: 'ボタン6',
        0x11: 'ボタン7',
    }
    name = names.get(vk, f'不明(0x{vk:02X})')
    print(f"[MOUSE BTN] {name}ボタン {'押下' if pressed else '離上'}")
    return True  # 伝播


def on_mouse_scroll(delta, horizontal):
    if horizontal:
        direction = '右' if delta > 0 else '左'
        print(f"[SCROLL] 水平 delta={delta} ({direction})")
    else:
        direction = '上' if delta > 0 else '下'
        print(f"[SCROLL] 垂直 delta={delta} ({direction})")
    return True  # 伝播


def on_mouse_move(dx, dy):
    print(f"[MOUSE MOVE] dx={dx}, dy={dy}")


def on_mouse_move_filter(x, y):
    print(f"[MOUSE MOVE FILTER] x={x}, y={y}")
    return True  # 伝播


driver = InputDriver(
    on_key=on_key,
    on_mouse_button=on_mouse_button,
    on_mouse_scroll=on_mouse_scroll,
    on_mouse_move=on_mouse_move,
    on_mouse_move_filter=on_mouse_move_filter,
)
driver.start()

print(f"input_driver デバッグ起動中。{FAILSAFE_SECONDS}秒後に自動停止します。")


def failsafe():
    time.sleep(FAILSAFE_SECONDS)
    print("[FAILSAFE] 自動停止します。")
    driver.stop()
    os._exit(0)


fs_thread = threading.Thread(target=failsafe, daemon=True)
fs_thread.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    driver.stop()
