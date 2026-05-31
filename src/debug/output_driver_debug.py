# output_driver_debug.py v1.1
# output_driver.py の動作確認用デバッグスクリプト
#
# 【前提】
#   - Windows 上で実行すること
#   - テキストエディタ（メモ帳等）を開いてフォーカスを当てた状態で
#     スクリプトを起動し、Enter キーを押して各テストを進める
#   - 各テストの前に READY_DELAY 秒の待機があるので、
#     その間にテスト対象ウィンドウへフォーカスを移すこと
#   - 実行方法: プロジェクトルートから python -m debug.output_driver_debug
#
# 【テスト内容】
#   Step 01 : key_down / key_up           ('A' キー 押下・離上を個別送出)
#   Step 02 : key_press                   ('B' キー 押下→離上を一括送出)
#   Step 03 : key_press (拡張キー)        (Home キー)
#   Step 04 : key_down_scan / key_up_scan (スキャンコード 'C')
#   Step 05 : key_press_scan              (スキャンコード 'D')
#   Step 06 : type_char                   (Unicode 文字 'あ')
#   Step 07 : type_text                   (文字列 "Hello, World!")
#   Step 08 : モディファイヤ付きキー      (Ctrl+A → 全選択)
#   Step 09 : mouse_button                (左ボタン 押下・離上を個別送出)
#   Step 10 : mouse_click (左)            (左クリック)
#   Step 11 : mouse_click (右)            (右クリック)
#   Step 12 : mouse_click (中)            (中クリック)
#   Step 13 : mouse_click (X1/X2)         (サイドボタン)
#   Step 14 : mouse_double_click          (左ダブルクリック)
#   Step 15 : mouse_scroll (垂直)         (上3ノッチ → 下3ノッチ)
#   Step 16 : mouse_scroll (水平)         (右3ノッチ → 左3ノッチ)
#   Step 17 : mouse_move_rel              (四角を描いて元位置に戻る)
#   Step 18 : mouse_move_abs              (プライマリ画面中央へ絶対移動)

import time
import ctypes
from drivers.output_driver import (
    OutputDriver,
    VK_LBUTTON, VK_RBUTTON, VK_MBUTTON, VK_XBUTTON1, VK_XBUTTON2,
    WHEEL_DELTA,
)

try:
    from drivers.vk_codes import VK, SC
    HAS_VK_CODES = True
except ImportError:
    HAS_VK_CODES = False
    print("[WARNING] vk_codes.py が見つかりません。SC テストはスキップします。")

READY_DELAY = 3   # 各テスト前の待機秒数

od = OutputDriver()
u32 = ctypes.windll.user32


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def step(num: int, desc: str):
    print(f"\n[Step {num:02d}] {desc}")
    print(f"  {READY_DELAY} 秒後に実行します。テスト対象ウィンドウへフォーカスを移してください...")
    time.sleep(READY_DELAY)


def result(ok: bool, label: str = ""):
    tag = "OK" if ok else "NG"
    print(f"  [{tag}] {label}" if label else f"  [{tag}]")
    if not ok:
        print("       ↑ 戻り値 False（SendInput が 0 を返した可能性）")
        print("         管理者権限の不足 / UAC による制限を確認してください")


def wait_enter(prompt: str = "次のステップへ進むには Enter を押してください..."):
    try:
        input(f"  >>> {prompt}")
    except EOFError:
        pass


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def main():
    section("output_driver.py 動作確認スクリプト v1.0")
    print("  テキストエディタ（メモ帳等）を開いてフォーカスを当て、")
    print("  準備ができたら Enter を押してテストを開始してください。")
    wait_enter("開始するには Enter を押してください...")

    # ------------------------------------------------------------------
    # Step 01: key_down / key_up
    # ------------------------------------------------------------------
    step(1, "key_down / key_up — 'A' キーを押下・離上（個別）")
    vk_a = VK.A if HAS_VK_CODES else 0x41
    ok1 = od.key_down(vk_a)
    time.sleep(0.1)
    ok2 = od.key_up(vk_a)
    result(ok1 and ok2, "エディタに 'a' が入力されるはず")
    wait_enter()

    # ------------------------------------------------------------------
    # Step 02: key_press
    # ------------------------------------------------------------------
    step(2, "key_press — 'B' キーを押下→離上（一括）")
    vk_b = VK.B if HAS_VK_CODES else 0x42
    ok = od.key_press(vk_b)
    result(ok, "エディタに 'b' が入力されるはず")
    wait_enter()

    # ------------------------------------------------------------------
    # Step 03: key_press (拡張キー)
    # ------------------------------------------------------------------
    step(3, "key_press (拡張キー) — Home キー")
    vk_home = VK.HOME if HAS_VK_CODES else 0x24
    ok = od.key_press(vk_home)
    result(ok, "カーソルが行頭へ移動するはず")
    wait_enter()

    # ------------------------------------------------------------------
    # Step 04: key_down_scan / key_up_scan
    # ------------------------------------------------------------------
    if HAS_VK_CODES:
        step(4, "key_down_scan / key_up_scan — スキャンコードで 'C' キー")
        ok1 = od.key_down_scan(SC.C)
        time.sleep(0.1)
        ok2 = od.key_up_scan(SC.C)
        result(ok1 and ok2, "エディタに 'c' が入力されるはず")
    else:
        print("\n[Step 04] SKIP（vk_codes.py なし）")
    wait_enter()

    # ------------------------------------------------------------------
    # Step 05: key_press_scan
    # ------------------------------------------------------------------
    if HAS_VK_CODES:
        step(5, "key_press_scan — スキャンコードで 'D' キー")
        ok = od.key_press_scan(SC.D)
        result(ok, "エディタに 'd' が入力されるはず")
    else:
        print("\n[Step 05] SKIP（vk_codes.py なし）")
    wait_enter()

    # ------------------------------------------------------------------
    # Step 06: type_char
    # ------------------------------------------------------------------
    step(6, "type_char — Unicode 文字 'あ' を送出")
    ok = od.type_char('あ')
    result(ok, "'あ' が入力されるはず（IME / レイアウト非依存）")
    wait_enter()

    # ------------------------------------------------------------------
    # Step 07: type_text
    # ------------------------------------------------------------------
    step(7, "type_text — 文字列 'Hello, World!' を送出")
    ok = od.type_text("Hello, World!")
    result(ok, "'Hello, World!' がそのまま入力されるはず")
    wait_enter()

    # ------------------------------------------------------------------
    # Step 08: モディファイヤ付きキー（Ctrl+A）
    # ------------------------------------------------------------------
    step(8, "モディファイヤ付きキー — Ctrl+A（全選択）")
    vk_ctrl = VK.CTRL if HAS_VK_CODES else 0x11
    vk_a    = VK.A    if HAS_VK_CODES else 0x41
    od.key_down(vk_ctrl)
    time.sleep(0.05)
    od.key_press(vk_a)
    time.sleep(0.05)
    ok = od.key_up(vk_ctrl)
    result(ok, "テキストが全選択されるはず")
    wait_enter()

    # ------------------------------------------------------------------
    # Step 09: mouse_button (個別)
    # ------------------------------------------------------------------
    step(9, "mouse_button — 左ボタン 押下・離上（個別）")
    ok1 = od.mouse_button(VK_LBUTTON, True)
    time.sleep(0.1)
    ok2 = od.mouse_button(VK_LBUTTON, False)
    result(ok1 and ok2, "左クリックと同等の動作")
    wait_enter()

    # ------------------------------------------------------------------
    # Step 10: mouse_click (左)
    # ------------------------------------------------------------------
    step(10, "mouse_click — 左クリック")
    ok = od.mouse_click(VK_LBUTTON)
    result(ok, "左クリック")
    wait_enter()

    # ------------------------------------------------------------------
    # Step 11: mouse_click (右)
    # ------------------------------------------------------------------
    step(11, "mouse_click — 右クリック（コンテキストメニューが出るはず）")
    ok = od.mouse_click(VK_RBUTTON)
    result(ok, "右クリック")
    print("  ※ コンテキストメニューが出た場合は Esc で閉じてください")
    wait_enter()

    # ------------------------------------------------------------------
    # Step 12: mouse_click (中)
    # ------------------------------------------------------------------
    step(12, "mouse_click — 中クリック")
    ok = od.mouse_click(VK_MBUTTON)
    result(ok, "中クリック（ブラウザではスクロールモードになることが多い）")
    wait_enter()

    # ------------------------------------------------------------------
    # Step 13: mouse_click (X1 / X2)
    # ------------------------------------------------------------------
    step(13, "mouse_click — X1 / X2 ボタン（サイドボタン）")
    ok1 = od.mouse_click(VK_XBUTTON1)
    time.sleep(0.3)
    ok2 = od.mouse_click(VK_XBUTTON2)
    result(ok1 and ok2, "X1（戻る相当）→ X2（進む相当）の順にクリック")
    wait_enter()

    # ------------------------------------------------------------------
    # Step 14: mouse_double_click
    # ------------------------------------------------------------------
    step(14, "mouse_double_click — 左ダブルクリック")
    ok = od.mouse_double_click(VK_LBUTTON)
    result(ok, "ダブルクリック（エディタでは単語選択になるはず）")
    wait_enter()

    # ------------------------------------------------------------------
    # Step 15: mouse_scroll (垂直)
    # ------------------------------------------------------------------
    step(15, "mouse_scroll — 垂直スクロール（上3ノッチ → 下3ノッチ）")
    print("  スクロール可能なウィンドウ上にカーソルを置いてください")
    time.sleep(1)
    for _ in range(3):
        od.mouse_scroll(WHEEL_DELTA)
        time.sleep(0.15)
    time.sleep(0.5)
    for _ in range(3):
        od.mouse_scroll(-WHEEL_DELTA)
        time.sleep(0.15)
    result(True, "上3ノッチ後、下3ノッチ（目視確認）")
    wait_enter()

    # ------------------------------------------------------------------
    # Step 16: mouse_scroll (水平)
    # ------------------------------------------------------------------
    step(16, "mouse_scroll — 水平スクロール（右3ノッチ → 左3ノッチ）")
    print("  水平スクロール可能なウィンドウ上にカーソルを置いてください")
    time.sleep(1)
    for _ in range(3):
        od.mouse_scroll(WHEEL_DELTA, horizontal=True)
        time.sleep(0.15)
    time.sleep(0.5)
    for _ in range(3):
        od.mouse_scroll(-WHEEL_DELTA, horizontal=True)
        time.sleep(0.15)
    result(True, "右3ノッチ後、左3ノッチ（目視確認）")
    wait_enter()

    # ------------------------------------------------------------------
    # Step 17: mouse_move_rel
    # ------------------------------------------------------------------
    step(17, "mouse_move_rel — 相対移動（右200→下200→左200→上200）")
    moves = [(200, 0), (0, 200), (-200, 0), (0, -200)]
    ok = True
    for dx, dy in moves:
        ok &= od.mouse_move_rel(dx, dy)
        time.sleep(0.3)
    result(ok, "カーソルが四角を描いて元の位置に戻るはず")
    wait_enter()

    # ------------------------------------------------------------------
    # Step 18: mouse_move_abs
    # ------------------------------------------------------------------
    step(18, "mouse_move_abs — プライマリ画面中央へ絶対移動")
    cx = u32.GetSystemMetrics(0) // 2
    cy = u32.GetSystemMetrics(1) // 2
    ok = od.mouse_move_abs(cx, cy)
    result(ok, f"mouse_move_abs({cx}, {cy}) → 画面中央へ移動")
    print("  ※ virtual_desk=True のテストはマルチモニタ環境で手動確認してください")
    wait_enter()

    # ------------------------------------------------------------------
    # 完了
    # ------------------------------------------------------------------
    section("全テスト完了")
    print("  各ステップの [OK] / [NG] を確認してください。")
    print("  [NG] の場合は SendInput の戻り値が 0 です。")
    print("  管理者権限の不足 / UAC による制限が原因の可能性があります。")


if __name__ == "__main__":
    main()
