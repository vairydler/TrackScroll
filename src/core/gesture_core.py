# gesture_core.py v2.5.4
"""
ジェスチャコアエンジン。

v2.5.3 → v2.5.4 変更:
  - パッケージ構成対応。
    `from gesture_action` → `from core.gesture_action`
    `from gesture_event`  → `from core.gesture_event`
    `from output_driver`  → `from drivers.output_driver`

v2.5.2 → v2.5.3 変更:
  - _notify_handler() から toggle_hotkey_vks の渡しを削除。
    gesture_event.py v2.3 の変更に伴う追従。

v2.5.1 → v2.5.2 変更:
  ホットキーVKの伝播制御を GestureEventHandler 側に移譲。

  - _notify_handler() でホットキーVKを trigger_vks に合成するロジックを廃止。
    代わりに enabled と toggle_hotkey_vks を update() に渡すだけにした。
  - _check_toggle_hotkey() の _notify_handler() 呼び出しはそのまま維持。
    enabled 変化を handler に即時反映するために必要。

v2.5.0 → v2.5.1 変更:
  ホットキーVKの伝播停止を enabled 状態に連動させる修正。

  - enabled=True 時: ホットキーVKを trigger_vks に追加し伝播停止。
  - enabled=False 時: ホットキーVKを trigger_vks に含めず伝播させる。
    ジェスチャ無効中はホットキーキーが透過し、ユーザーに違和感を与えない。
  - _check_toggle_hotkey() で ON/OFF 両方向のトグル後に _notify_handler() を呼ぶよう修正。
    v2.5.0 では OFF→ON（有効化）時に _notify_handler() が呼ばれておらず、
    有効化後も trigger_vks にホットキーが含まれないままになるバグがあった。

v2.4.1 → v2.5.0 変更:
  ホットキーによるジェスチャ有効/無効トグル機能を追加。

  - GestureCore.__init__ に _enabled フラグ・_toggle_hotkey・_on_toggle コールバックを追加。
  - GestureCore.load() で config.get_toggle_hotkey() を読み込み _toggle_hotkey に格納。
    ホットキーのVKは _notify_handler() 経由で GestureEventHandler の trigger_vks に追加され、
    [SPEC-HOOK-BLOCK-TRIGGER-KEY] と同様に常時伝播停止される。
  - _on_key / _on_mouse_button でホットキー完成を判定。
    「ホットキーを構成する最後の1キーが押された瞬間」にトグル発火。
    複数キー同時押しに対応（frozenset[int] 形式で設定）。
  - 無効状態（_enabled=False）では _update_trigger をスキップし、
    アクティブセッションがあれば強制終了してフック解除保証を維持。
  - _on_toggle コールバック: load() に引数を追加し、トグル時に呼ばれる。
    シグネチャ: (enabled: bool) -> None。省略時（None）は何もしない。

v2.4.0 → v2.4.1 変更:
  - HookSession に repeat_interval 引数を追加。
  - _start_repeat に immediate 引数を追加。
    repeat_last_t を now - repeat_interval に変更し、
    repeat_start 条件成立の瞬間に初回リピートが即発火するよう修正。
  - _check_trigger_repeat で _start_repeat(immediate=True) を使用。
    トリガ自体のダウン発行後、リピート開始までに repeat_interval 分の
    余分な遅延が発生していたバグを修正。

v2.3.0 → v2.4.0 変更:
  - _show_popup() を削除し、import tkinter を除去。
    警告通知の責務を GestureService へ移管。
  - GestureCore.load() に on_warning コールバック引数を追加。
    シグネチャ: (kind: str, messages: list[str]) -> None
    kind は "conflict" または "invalid_up"。
    省略時（None）は警告を無視する。

v2.2.0 → v2.3.0 変更:
  [SPEC-HOOK-BLOCK-CURSOR] 仕様書v2.6対応。
    カーソル移動禁止条件を「フック中かつ移動方向ジェスチャキーが1つ以上登録されている
    場合のみ」に変更。
    HookSession.__init__ で _block_cursor を bool として事前計算し、
    block_cursor() メソッドで返す。
    GestureCore._notify_handler() で hooked=True の代わりに
    block_cursor=session.block_cursor() を渡すように変更。
    GestureEventHandler.update() の引数名を hooked → block_cursor に変更（v2.1対応）。

  [最適化] block_scroll_v / block_scroll_h も同様に HookSession.__init__ で
    bool として事前計算するよう変更。呼び出し側からは引き続きメソッド経由でアクセス。
    これにより _notify_handler() からのコールバック毎の any() 走査を排除。

v2.1.0 → v2.2.0 変更:
  [SPEC-MOVE-COOLDOWN] 実装。
    HookSession に移動クールダウン状態（最終確定方向・時刻）を追加。
    on_move で同一方向かつクールダウン時間内の場合にダウン動作をスキップ。
    別方向確定時はタイマーをリセットして通常実行。
    クールダウン中でもリピートは継続する。
  [SPEC-TIMEOUT-RESET] 廃止（仕様書 v2.4）。
    Shift等の押し増し時にOSが他キーのリピートを止める挙動により、
    キーリピートの途絶による検出アプローチは誤作動を招くため削除。
    関連コード（_kb_trigger_vks / _last_kb_event_t / _check_kb_timeout）を全削除。

v2.0（旧 gesture_core.py v2.0）→ v2.0（仕様書2.2対応）変更:
  仕様書2.2の全仕様に対応。主な変更点:

  [SPEC-ACTION-THREE-WAY]
    HookSession がダウン/アップ/リピートの3動作を管理する。

  [SPEC-ACTION-DOWN-UP-PAIR] [SPEC-ACTION-DOWN-KEY-TRACKING]
    ダウン発行済みジェスチャキーをスタックで管理し、
    セッション破棄時に逆順でアップを発行する。
    トリガ自体（TRIGGER）も同スタックで管理。

  [SPEC-ACTION-UP-TRIGGER] [SPEC-ACTION-UP-SUPPRESS]
    ダウン発行済みであることがアップ発行の唯一の条件。
    ジェスチャキーを離したとき・トリガ変更時に発火。

  [SPEC-TRIGGER-ACTION-DELAY]
    トリガ自体のダウン動作は「フリック」または「リピート開始」のみで発行。
    猶予時間以内に他のジェスチャが実行された場合は抑制（猶予カウント停止）。

  [SPEC-TRIGGER-ACTION-PUSHONLY]
    押し増し（新規アクティブ）時のみトリガ自体のダウン発行対象。
    押し減らし復帰は対象外。

  [SPEC-REPEAT-TARGET]
    リピート対象はリピート動作のみ。ダウン動作はリピートしない。

  [SPEC-REPEAT-KIND]
    ジェスチャキーの種別によりリピートタイマ管理を分離。
    KEY / MOUSE_BTN: 押下中のみリピート継続。
    MOVE / SCROLL: 最後のイベントからカウント。

  [SPEC-REPEAT-STOP]
    リピート中のキーが離されたときアップ動作を発行してから停止。

  [SPEC-STOP-CLEANUP]
    stop() 呼び出し時にダウン発行済み全ジェスチャキーのアップを逆順発行。

  [SPEC-SELF-EVENT-FILTER]
    output_driver / input_driver の dwExtraInfo 識別子を一致させる。

  [SPEC-INVALID-UP-DETECT]
    移動・スクロール系ジェスチャキーへのアップ動作登録をロード時に検出・警告。

仕様トレース（継続）:
  [SPEC-TRIGGER-ALWAYS-WATCH]       常時トリガ監視
  [SPEC-TRIGGER-CHANGE]             トリガ変更の検出
  [SPEC-TRIGGER-CHANGE-SWITCH]      旧フック終了・新フック開始
  [SPEC-TRIGGER-CHANGE-NO-ROLLBACK] 実行済み動作はロールバックしない
  [SPEC-TRIGGER-COUNT-RESET]        トリガ変更時にカウントリセット
  [SPEC-HOOK-BLOCK-CURSOR]          移動方向ジェスチャキーがある場合のみ WM_MOUSEMOVE を停止
  [SPEC-HOOK-BLOCK-GESTURE-KEY]     フック中ジェスチャキー入力伝播停止
  [SPEC-HOOK-BLOCK-TRIGGER-KEY]     トリガ構成VKは常時伝播停止
  [SPEC-HOOK-NO-MATCH-PASSTHROUGH]  ジェスチャキー不一致時は伝播
  [SPEC-HOOK-OUT-PASSTHROUGH]       フック外は入力を一切妨げない
  [SPEC-HOOK-RELEASE-GUARANTEE]     何も押していない状態でフック継続しない
  [SPEC-MOVE-THRESHOLD]             累積移動量→方向確定
  [SPEC-MOVE-RESET]                 動作実行後に累積移動量リセット
  [SPEC-REPEAT-START]               リピートタイマ開始タイミング
  [SPEC-REPEAT-CLEAR-ON-MOVE]       手ブレ補正しきい値超えでリピートリセット
  [SPEC-REPEAT-CLEAR-ON-NEW-GESTURE]別ジェスチャキーでリピートリセット
  [SPEC-REPEAT-INTERVAL]            リピート発火間隔（メインループ内判定）
  [SPEC-REPEAT-SINGLE]              リピートは常に1つ
  [SPEC-REPEAT-DISABLED]            repeat_action=None でリピート無効
  [SPEC-CONFLICT-DETECT]            競合チェック（ロード時）
  [SPEC-CONFLICT-PRIORITY]          競合時トリガ優先
  [SPEC-GKEY-SIMULTANEOUS]          同時押し先着順処理
"""

from __future__ import annotations

import math
import queue
import threading
import time
from typing import Callable, Optional

from core.gesture_action import (
    ActionKind, GestureAction, GestureData, GestureKey,
    GestureKeyKind, GestureRecord,
)
from core.gesture_event import (
    GestureEventHandler,
    KeyEvent, MouseButtonEvent, ScrollEvent, MoveEvent,
)
from drivers.output_driver import OutputDriver, WHEEL_DELTA


# ===========================================================================
# 競合チェック / 不正アップ検出
# ===========================================================================

def check_conflicts(table: list[GestureRecord]) -> list[str]:
    """[SPEC-CONFLICT-DETECT][SPEC-CONFLICT-PRIORITY]"""
    conflicts: list[str] = []
    trigger_set = {rec.trigger for rec in table}
    for rec in table:
        for gd in rec.gesture_data:
            gk = gd.gesture_key
            if gk.kind not in (GestureKeyKind.MOUSE_BTN, GestureKeyKind.KEY):
                continue
            candidate = rec.trigger | frozenset({gk.vk})
            if candidate in trigger_set and candidate != rec.trigger:
                conflicts.append(
                    f"競合: トリガ {_fmt_trigger(rec.trigger)} の"
                    f"ジェスチャキー vk=0x{gk.vk:02X} が、"
                    f"トリガ {_fmt_trigger(candidate)} と重複しています。"
                    f"（トリガを優先して動作します [SPEC-CONFLICT-PRIORITY]）"
                )
    return conflicts


def check_invalid_up(table: list[GestureRecord]) -> list[str]:
    """
    [SPEC-INVALID-UP-DETECT]
    移動方向・スクロール系のジェスチャキーにアップ動作が登録されている場合に検出する。
    """
    warnings: list[str] = []
    for rec in table:
        for gd in rec.gesture_data:
            if gd.gesture_key.kind in GestureKeyKind.NO_UP_KINDS:
                if gd.up_action is not None:
                    warnings.append(
                        f"不正なアップ動作: トリガ {_fmt_trigger(rec.trigger)} の"
                        f"ジェスチャキー {gd.gesture_key.kind!r} に"
                        f"アップ動作が登録されています。"
                        f"このジェスチャキーはアップ動作を持ちません。"
                    )
    return warnings


def _fmt_trigger(t: frozenset) -> str:
    return "+".join(f"0x{v:02X}" for v in sorted(t))


# ===========================================================================
# 動作送出
# ===========================================================================

def _execute_action(action: GestureAction, od: OutputDriver) -> None:
    """GestureAction を OutputDriver 経由で送出する。"""
    k = action.kind
    if k == ActionKind.KEY_PRESS:
        for m in action.modifiers:
            od.key_down(m)
        od.key_press(action.vk)
        for m in reversed(action.modifiers):
            od.key_up(m)
    elif k == ActionKind.KEY_DOWN:
        od.key_down(action.vk)
    elif k == ActionKind.KEY_UP:
        od.key_up(action.vk)
    elif k == ActionKind.KEY_SEQUENCE:
        # ↓+Ctrl 等: vk_list 順に down / 逆順に up [SPEC-ACTION-STRING-NOTATION]
        if action.is_down:
            for vk in action.vk_list:
                od.key_down(vk)
        else:
            for vk in reversed(action.vk_list):
                od.key_up(vk)
    elif k == ActionKind.MOUSE_CLICK:
        # [SPEC-ACTION-STRING-NOTATION] モディファイヤあり: mod down → click → mod up（逆順）
        for m in action.modifiers:
            od.key_down(m)
        od.mouse_click(action.vk)
        for m in reversed(action.modifiers):
            od.key_up(m)
    elif k == ActionKind.MOUSE_DOWN:
        # [SPEC-ACTION-STRING-NOTATION] ↓^LButton: mod down → button down
        for m in action.modifiers:
            od.key_down(m)
        od.mouse_button(action.vk, True)
    elif k == ActionKind.MOUSE_UP:
        # [SPEC-ACTION-STRING-NOTATION] ↑^LButton: button up → mod up（逆順）
        od.mouse_button(action.vk, False)
        for m in reversed(action.modifiers):
            od.key_up(m)
    elif k == ActionKind.SCROLL:
        # [SPEC-ACTION-STRING-NOTATION] モディファイヤあり: mod down → scroll → mod up（逆順）
        for m in action.modifiers:
            od.key_down(m)
        od.mouse_scroll(action.delta, action.horizontal)
        for m in reversed(action.modifiers):
            od.key_up(m)
    elif k == ActionKind.FUNCTION:
        if action.func:
            action.func()


# ===========================================================================
# フックセッション
# ===========================================================================

class HookSession:
    """
    単一トリガレコードのフックセッション。
    トリガ変更でインスタンスを破棄し新しいインスタンスを生成する。
    メインループスレッドからのみアクセスされるためロック不要。

    [SPEC-TRIGGER-CHANGE-SWITCH][SPEC-TRIGGER-COUNT-RESET]
    [SPEC-ACTION-DOWN-KEY-TRACKING] ダウン発行済みスタック管理
    [SPEC-TRIGGER-ACTION-PUSHONLY] is_pushon フラグで押し増し判定
    [SPEC-MOVE-COOLDOWN] 移動方向クールダウン（最終確定方向・時刻の2値で管理）
    [SPEC-HOOK-BLOCK-CURSOR] _block_cursor を __init__ で事前計算（bool）
    """

    def __init__(self, record: GestureRecord, od: OutputDriver,
                 default_threshold: float, delay_time: float,
                 jitter_threshold: float, repeat_interval: float,
                 is_pushon: bool):
        """
        Parameters
        ----------
        repeat_interval : リピート発火間隔（秒）。_start_repeat の初回遅延除去に使用。
        is_pushon       : True=押し増しによる新規アクティブ, False=押し減らし復帰
                          [SPEC-TRIGGER-ACTION-PUSHONLY]
        """
        self._rec              = record
        self._od               = od
        self._repeat_interval  = repeat_interval
        self._threshold        = record.threshold if record.threshold is not None \
                                 else default_threshold
        self._delay_time       = delay_time
        self._jitter_threshold = jitter_threshold
        self._is_pushon        = is_pushon  # [SPEC-TRIGGER-ACTION-PUSHONLY]

        # 移動クールダウン [SPEC-MOVE-COOLDOWN]
        _cd = record.move_cooldown
        self._move_cooldown: float = _cd if (_cd is not None and _cd > 0.0) else 0.0
        self._cd_last_direction: Optional[str] = None   # 最後に確定した方向
        self._cd_last_time: float = 0.0                 # その時刻

        # 累積移動量 [SPEC-MOVE-THRESHOLD]
        self._accum_x = 0.0
        self._accum_y = 0.0

        # 猶予時間管理 [SPEC-TRIGGER-ACTION-DELAY]
        self._session_start   = time.monotonic()
        self._delay_active    = True   # True=まだ猶予カウント有効
        self._trigger_down_issued = False  # トリガ自体のダウン発行済み

        # ダウン発行済みスタック [SPEC-ACTION-DOWN-KEY-TRACKING]
        # 要素: GestureData（ダウン発行条件を満たしたもの）
        self._down_stack: list[GestureData] = []

        # 押下中のジェスチャキー → GestureData の辞書
        # （KEY / MOUSE_BTN のアップ管理用）[SPEC-ACTION-UP-TRIGGER]
        self._pressed_gkeys: dict[GestureKey, GestureData] = {}

        # ジェスチャキー→GestureData の辞書（トリガ以外）
        self._key_map: dict[GestureKey, GestureData] = {
            gd.gesture_key: gd
            for gd in record.gesture_data
            if gd.gesture_key.kind != GestureKeyKind.TRIGGER
        }

        # ブロック判定フラグを事前計算（セッション生成時に1度だけ）
        # [SPEC-HOOK-BLOCK-CURSOR] 移動方向ジェスチャキーが1つ以上ある場合のみ True
        _move_kinds = frozenset({
            GestureKeyKind.MOVE_UP, GestureKeyKind.MOVE_DOWN,
            GestureKeyKind.MOVE_LEFT, GestureKeyKind.MOVE_RIGHT,
        })
        self._block_cursor:   bool = any(gk.kind in _move_kinds
                                         for gk in self._key_map)
        self._block_scroll_v: bool = any(
            gk.kind in (GestureKeyKind.SCROLL_UP, GestureKeyKind.SCROLL_DOWN)
            for gk in self._key_map
        )
        self._block_scroll_h: bool = any(
            gk.kind in (GestureKeyKind.SCROLL_LEFT, GestureKeyKind.SCROLL_RIGHT)
            for gk in self._key_map
        )

        # リピート状態 [SPEC-REPEAT-START][SPEC-REPEAT-SINGLE]
        self.repeat_gd:      Optional[GestureData] = None
        self.repeat_start_t: float = 0.0
        self.repeat_last_t:  float = 0.0

        # トリガがアクティブになった時点でリピートタイマ開始 [SPEC-REPEAT-START]
        # ただし repeat_action=None なら無効 [SPEC-REPEAT-DISABLED]
        trigger_gd = record.trigger_action()
        if trigger_gd is not None and trigger_gd.repeat_action is not None:
            self._start_repeat(trigger_gd)

    # ------------------------------------------------------------------ #
    # ブロック判定情報（GestureEventHandler に渡す）
    # ------------------------------------------------------------------ #

    def block_cursor(self) -> bool:
        """[SPEC-HOOK-BLOCK-CURSOR] 事前計算済みフラグを返す。"""
        return self._block_cursor

    def block_keys(self) -> frozenset:
        """[SPEC-HOOK-BLOCK-GESTURE-KEY]"""
        return frozenset(
            gk.vk for gk in self._key_map
            if gk.kind in (GestureKeyKind.MOUSE_BTN, GestureKeyKind.KEY)
        )

    def block_scroll_v(self) -> bool:
        """事前計算済みフラグを返す。"""
        return self._block_scroll_v

    def block_scroll_h(self) -> bool:
        """事前計算済みフラグを返す。"""
        return self._block_scroll_h

    # ------------------------------------------------------------------ #
    # マウス移動 [SPEC-MOVE-THRESHOLD]
    # ------------------------------------------------------------------ #

    def on_move(self, dx: int, dy: int) -> None:
        """[SPEC-MOVE-THRESHOLD][SPEC-REPEAT-CLEAR-ON-MOVE][SPEC-MOVE-COOLDOWN]"""
        dist = math.hypot(dx, dy)
        if dist >= self._jitter_threshold:
            self._reset_repeat_timer()  # [SPEC-REPEAT-CLEAR-ON-MOVE]

        self._accum_x += dx
        self._accum_y += dy
        if math.hypot(self._accum_x, self._accum_y) < self._threshold:
            return

        angle = math.degrees(math.atan2(self._accum_y, self._accum_x))
        if   -45 <= angle <  45:           direction = "right"
        elif  45 <= angle < 135:           direction = "down"
        elif angle >= 135 or angle < -135: direction = "left"
        else:                              direction = "up"

        self._accum_x = 0.0  # [SPEC-MOVE-RESET]
        self._accum_y = 0.0

        # [SPEC-MOVE-COOLDOWN] クールダウン判定
        if self._move_cooldown > 0.0:
            now = time.monotonic()
            if direction == self._cd_last_direction:
                if now - self._cd_last_time < self._move_cooldown:
                    # 同一方向かつクールダウン中 → ダウン動作をスキップ
                    # （累積はリセット済み。リピートは継続するため何もしない）
                    return
            # 別方向 or クールダウン終了: タイマーを更新して通常実行
            self._cd_last_direction = direction
            self._cd_last_time = now

        gk = GestureKey.move(direction)
        gd = self._key_map.get(gk)
        if gd is not None:
            self._fire_gesture_down(gd)

    # ------------------------------------------------------------------ #
    # ジェスチャキー入力
    # ------------------------------------------------------------------ #

    def on_mouse_button(self, vk: int, pressed: bool) -> None:
        gk = GestureKey.mouse_button(vk)
        gd = self._key_map.get(gk)
        if gd is None:
            return
        if pressed:
            self._fire_gesture_down(gd)
            self._pressed_gkeys[gk] = gd   # [SPEC-ACTION-UP-TRIGGER]
        else:
            self._fire_gesture_up_for_key(gk)  # [SPEC-ACTION-UP-TRIGGER]

    def on_scroll(self, delta: int, horizontal: bool) -> None:
        direction = ("right" if delta > 0 else "left") if horizontal \
                    else ("up" if delta > 0 else "down")
        gk = GestureKey.scroll(direction)
        gd = self._key_map.get(gk)
        if gd is not None:
            self._fire_gesture_down(gd)

    def on_key(self, vk: int, pressed: bool) -> None:
        gk = GestureKey.key(vk)
        gd = self._key_map.get(gk)
        if gd is None:
            return
        if pressed:
            self._fire_gesture_down(gd)
            self._pressed_gkeys[gk] = gd   # [SPEC-ACTION-UP-TRIGGER]
        else:
            self._fire_gesture_up_for_key(gk)  # [SPEC-ACTION-UP-TRIGGER]

    # ------------------------------------------------------------------ #
    # 猶予時間チェック [SPEC-TRIGGER-ACTION-DELAY]
    # ------------------------------------------------------------------ #

    def check_delay_and_repeat(self, now: float, repeat_interval: float) -> None:
        """
        メインループから定期的に呼ばれる。
        1. 猶予時間経過 かつ リピート開始時間経過 → トリガ自体のダウン発行・リピート開始
        2. リピート発火判定
        [SPEC-TRIGGER-ACTION-DELAY][SPEC-REPEAT-START][SPEC-REPEAT-INTERVAL]
        """
        # トリガ自体のリピート開始判定
        self._check_trigger_repeat(now)
        # 通常リピート発火
        self._check_repeat_fire(now, repeat_interval)

    def _check_trigger_repeat(self, now: float) -> None:
        """
        [SPEC-TRIGGER-ACTION-DELAY] リピート開始条件:
          猶予時間経過 かつ リピート開始時間経過 → ダウン発行・リピート開始
        [SPEC-TRIGGER-ACTION-PUSHONLY] 押し増しのみ対象。
        """
        if self._trigger_down_issued:
            return
        if not self._delay_active:
            return
        if not self._is_pushon:
            return  # [SPEC-TRIGGER-ACTION-PUSHONLY] 押し減らし復帰は対象外

        trigger_gd = self._rec.trigger_action()
        if trigger_gd is None:
            return
        if trigger_gd.repeat_action is None:
            return  # [SPEC-REPEAT-DISABLED]

        elapsed = now - self._session_start
        # 猶予時間経過 かつ リピート開始時間経過
        if elapsed >= self._delay_time and elapsed >= trigger_gd.repeat_start:
            self._issue_trigger_down(trigger_gd)
            self._start_repeat(trigger_gd, immediate=True)

    def _check_repeat_fire(self, now: float, repeat_interval: float) -> None:
        """[SPEC-REPEAT-INTERVAL] リピート発火判定。"""
        if self.repeat_gd is None:
            return
        gd = self.repeat_gd
        if gd.repeat_action is None:
            return  # [SPEC-REPEAT-DISABLED]

        # トリガ自体のリピートはダウン発行済みが条件 [SPEC-REPEAT-START]
        if gd.gesture_key.kind == GestureKeyKind.TRIGGER:
            if not self._trigger_down_issued:
                return

        if now - self.repeat_start_t >= gd.repeat_start:
            if now - self.repeat_last_t >= repeat_interval:
                _execute_action(gd.repeat_action, self._od)
                self.repeat_last_t = now

    # ------------------------------------------------------------------ #
    # トリガ自体への動作 [SPEC-TRIGGER-ACTION-DELAY][SPEC-TRIGGER-ACTION-ON-FLICK]
    # ------------------------------------------------------------------ #

    def on_trigger_release(self, suppress_flick: bool = False) -> None:
        """
        フック終了時（トリガ離上・トリガ変更）に呼ばれる。

        フリック判定: 猶予時間以内かつダウン未発行 → ダウン発行→即アップ発行
        [SPEC-TRIGGER-ACTION-DELAY][SPEC-TRIGGER-ACTION-PUSHONLY]
        [SPEC-ACTION-DOWN-UP-PAIR]

        suppress_flick : True のとき（押し増しによるトリガ変更）はフリック発行を抑制する。
                         A→A+B 変更時に A のフリックが誤発行されるのを防ぐ。
                         [SPEC-TRIGGER-ACTION-DELAY] 連打シナリオ参照。
        """
        # ダウン発行済みジェスチャキーを逆順でアップ発行 [SPEC-ACTION-DOWN-KEY-TRACKING]
        self._flush_down_stack()

        # フリック判定 [SPEC-TRIGGER-ACTION-DELAY]
        # 押し増しによるトリガ変更時はフリック発行しない（suppress_flick=True）
        if not suppress_flick \
                and not self._trigger_down_issued \
                and self._delay_active \
                and self._is_pushon:
            trigger_gd = self._rec.trigger_action()
            if trigger_gd is not None:
                elapsed = time.monotonic() - self._session_start
                if elapsed <= self._delay_time:
                    # フリック: ダウン→アップ
                    self._issue_trigger_down(trigger_gd)
                    if trigger_gd.up_action is not None:
                        _execute_action(trigger_gd.up_action, self._od)
                    return

        # トリガ自体のアップ（ダウン発行済みの場合）[SPEC-ACTION-DOWN-UP-PAIR]
        if self._trigger_down_issued:
            trigger_gd = self._rec.trigger_action()
            if trigger_gd is not None and trigger_gd.up_action is not None:
                _execute_action(trigger_gd.up_action, self._od)

    # ------------------------------------------------------------------ #
    # 内部: ジェスチャダウン発行
    # ------------------------------------------------------------------ #

    def _fire_gesture_down(self, gd: GestureData) -> None:
        """
        ジェスチャキーのダウン発行条件成立。
        - 猶予カウントを停止 [SPEC-TRIGGER-ACTION-DELAY]
        - ダウン動作を発行（None でも「発行済み」として扱う）[SPEC-ACTION-UP-SUPPRESS]
        - スタックに積む [SPEC-ACTION-DOWN-KEY-TRACKING]
        - リピートタイマをリセット・切り替え [SPEC-REPEAT-CLEAR-ON-NEW-GESTURE]
        """
        # 猶予カウント停止 [SPEC-TRIGGER-ACTION-DELAY]
        self._delay_active = False

        # ダウン動作発行
        if gd.down_action is not None:
            _execute_action(gd.down_action, self._od)

        # ダウン発行済みスタックに積む [SPEC-ACTION-DOWN-KEY-TRACKING]
        self._down_stack.append(gd)

        # リピートタイマ切り替え [SPEC-REPEAT-CLEAR-ON-NEW-GESTURE][SPEC-REPEAT-DISABLED]
        if gd.repeat_action is not None:
            self._start_repeat(gd)
        else:
            # repeat_action=None なのでリピート対象をクリア [SPEC-REPEAT-DISABLED]
            self.repeat_gd = None

    def _fire_gesture_up_for_key(self, gk: GestureKey) -> None:
        """
        KEY / MOUSE_BTN のジェスチャキーが離されたときアップ動作を発行する。
        [SPEC-ACTION-UP-TRIGGER][SPEC-ACTION-UP-SUPPRESS]
        [SPEC-REPEAT-STOP]
        """
        gd = self._pressed_gkeys.pop(gk, None)
        if gd is None:
            return

        # リピート停止 [SPEC-REPEAT-STOP]
        if self.repeat_gd is gd:
            self.repeat_gd = None

        # ダウン発行済みであることが条件 [SPEC-ACTION-UP-SUPPRESS]
        if gd in self._down_stack:
            self._down_stack.remove(gd)
            if gd.up_action is not None:
                _execute_action(gd.up_action, self._od)

    def _issue_trigger_down(self, trigger_gd: GestureData) -> None:
        """トリガ自体のダウン動作を発行し、発行済みフラグを立てる。"""
        self._trigger_down_issued = True
        if trigger_gd.down_action is not None:
            _execute_action(trigger_gd.down_action, self._od)

    def _flush_down_stack(self) -> None:
        """
        ダウン発行済みスタックを逆順に走査してアップ動作を発行する。
        [SPEC-ACTION-DOWN-KEY-TRACKING][SPEC-ACTION-DOWN-UP-PAIR]
        TRIGGERキーはここでは処理しない（on_trigger_release で別途処理）。
        """
        for gd in reversed(self._down_stack):
            if gd.gesture_key.kind == GestureKeyKind.TRIGGER:
                continue  # トリガ自体は on_trigger_release で処理
            if gd.up_action is not None:
                _execute_action(gd.up_action, self._od)
        self._down_stack.clear()
        self._pressed_gkeys.clear()

    # ------------------------------------------------------------------ #
    # 内部: リピートタイマ
    # ------------------------------------------------------------------ #

    def _start_repeat(self, gd: GestureData, immediate: bool = False) -> None:
        """[SPEC-REPEAT-START][SPEC-REPEAT-SINGLE]
        immediate : True のとき repeat_start はすでに満たされているとみなす。
                    トリガ自体のダウン発行後（_check_trigger_repeat）で使用。
        repeat_last_t を now - repeat_interval に設定することで、
        repeat_start 条件が成立した瞬間に初回リピートが即発火できるようにする。
        """
        self.repeat_gd      = gd
        now = time.monotonic()
        self.repeat_start_t = now - (gd.repeat_start if immediate else 0)
        self.repeat_last_t  = now - self._repeat_interval

    def _reset_repeat_timer(self) -> None:
        """[SPEC-REPEAT-CLEAR-ON-MOVE]"""
        if self.repeat_gd is not None:
            now = time.monotonic()
            self.repeat_start_t = now
            self.repeat_last_t  = now


# ===========================================================================
# GestureCore
# ===========================================================================

class GestureCore:
    """
    ジェスチャコアエンジン。

    メインループスレッド1本でキューからイベントを取り出し、
    トリガ判定・セッション管理・動作送出・リピート時間判定を行う。
    状態変更はメインループスレッドのみが行うためロック不要。

    """

    def __init__(self, config, od: OutputDriver,
                 handler: GestureEventHandler,
                 event_queue: queue.Queue):
        self._config  = config
        self._od      = od
        self._handler = handler
        self._queue   = event_queue

        self._table:             list[GestureRecord] = []
        self._trigger_map:       dict[frozenset, GestureRecord] = {}
        self._all_trigger_vks:   frozenset = frozenset()
        self._default_threshold: float = 30.0
        self._jitter_threshold:  float = 5.0
        self._repeat_interval:   float = 0.08
        self._delay_time:        float = 0.3

        self._pressed:        set[int] = set()
        self._active_trigger: Optional[frozenset] = None
        self._session:        Optional[HookSession] = None

        # ホットキー（有効/無効トグル）
        self._enabled:        bool = True
        self._toggle_hotkey:  Optional[frozenset] = None   # None=無効
        self._on_toggle:      Optional[Callable[[bool], None]] = None

        self._loop_thread: Optional[threading.Thread] = None
        self._running = False

    # ------------------------------------------------------------------ #
    # ロード
    # ------------------------------------------------------------------ #

    def load(self, on_warning: Callable[[str, list[str]], None] | None = None,
             on_toggle: Callable[[bool], None] | None = None) -> None:
        """
        [SPEC-CONFIG-FILE][SPEC-CONFLICT-DETECT][SPEC-INVALID-UP-DETECT]

        on_warning : 警告発生時に呼ばれるコールバック。
                     シグネチャ: (kind: str, messages: list[str]) -> None
                     kind は "conflict" または "invalid_up"。
                     省略時（None）は警告を無視する。
        on_toggle  : ホットキーでトグルされた際に呼ばれるコールバック。
                     シグネチャ: (enabled: bool) -> None
                     省略時（None）は通知しない。
        """
        self._on_toggle         = on_toggle
        self._table             = self._config.get_gesture_table()
        self._default_threshold = self._config.get_default_move_threshold()
        self._jitter_threshold  = self._config.get_jitter_threshold()
        self._repeat_interval   = self._config.get_repeat_interval()
        self._delay_time        = self._config.get_delay_time()
        self._trigger_map       = {rec.trigger: rec for rec in self._table}
        self._all_trigger_vks   = frozenset(
            vk for rec in self._table for vk in rec.trigger
        )

        # ホットキー読み込み
        raw_hotkey = self._config.get_toggle_hotkey() \
            if hasattr(self._config, "get_toggle_hotkey") else None
        self._toggle_hotkey = raw_hotkey if raw_hotkey else None

        # 競合チェック [SPEC-CONFLICT-DETECT]
        conflicts = check_conflicts(self._table)
        if conflicts and on_warning is not None:
            on_warning("conflict", conflicts)

        # 不正アップ動作チェック [SPEC-INVALID-UP-DETECT]
        invalid_ups = check_invalid_up(self._table)
        if invalid_ups and on_warning is not None:
            on_warning("invalid_up", invalid_ups)

        self._notify_handler()

        self._running = True
        self._loop_thread = threading.Thread(
            target=self._main_loop, daemon=True)
        self._loop_thread.start()

    def stop(self) -> None:
        """
        停止。
        [SPEC-STOP-CLEANUP] ダウン発行済み全ジェスチャキーのアップを逆順発行。
        """
        self._running = False

        if self._session is not None:
            self._session.on_trigger_release()
            self._session = None

        # 押下中トリガVKの離上イベントを送出 [SPEC-HOOK-RELEASE-GUARANTEE]
        for vk in list(self._pressed):
            if vk in {0x01, 0x02, 0x04, 0x05, 0x06}:
                self._od.mouse_button(vk, False)
            else:
                self._od.key_up(vk)
        self._pressed.clear()
        self._active_trigger = None
        self._notify_handler()

    # ------------------------------------------------------------------ #
    # メインループ
    # ------------------------------------------------------------------ #

    def _main_loop(self) -> None:
        """
        キューからイベントを取り出して処理し、リピートを時間判定する。
        スレッドは1本のみ。状態変更はすべてここで行う。
        [SPEC-REPEAT-INTERVAL]
        """
        tick = 0.005  # 5ms ポーリング

        while self._running:
            now = time.monotonic()

            # フック解除保証 [SPEC-HOOK-RELEASE-GUARANTEE]
            if self._session is not None and not self._pressed:
                self._session.on_trigger_release()
                self._end_session()

            # 猶予時間・リピート時間判定 [SPEC-TRIGGER-ACTION-DELAY][SPEC-REPEAT-INTERVAL]
            if self._session is not None:
                self._session.check_delay_and_repeat(now, self._repeat_interval)

            # キューからイベントを処理
            try:
                while True:
                    event = self._queue.get_nowait()
                    self._process_event(event)
            except queue.Empty:
                pass

            time.sleep(tick)

    # ------------------------------------------------------------------ #
    # イベント処理
    # ------------------------------------------------------------------ #

    def _process_event(self, event) -> None:
        if isinstance(event, KeyEvent):
            self._on_key(event.vk, event.pressed)
        elif isinstance(event, MouseButtonEvent):
            self._on_mouse_button(event.vk, event.pressed)
        elif isinstance(event, ScrollEvent):
            self._on_scroll(event.delta, event.horizontal)
        elif isinstance(event, MoveEvent):
            self._on_move(event.dx, event.dy)

    def _on_key(self, vk: int, pressed: bool) -> None:
        """[SPEC-TRIGGER-ALWAYS-WATCH]"""
        if pressed:
            self._pressed.add(vk)
        else:
            self._pressed.discard(vk)

        # ホットキー判定（pressed 更新後に行う）
        if pressed and self._check_toggle_hotkey():
            return  # トグル発火後はトリガ更新しない

        # 無効状態ではトリガ更新をスキップ
        if not self._enabled:
            return

        self._update_trigger()
        if self._session is not None:
            self._session.on_key(vk, pressed)

    def _on_mouse_button(self, vk: int, pressed: bool) -> None:
        """[SPEC-TRIGGER-ALWAYS-WATCH]"""
        if pressed:
            self._pressed.add(vk)
        else:
            self._pressed.discard(vk)

        # ホットキー判定（pressed 更新後に行う）
        if pressed and self._check_toggle_hotkey():
            return  # トグル発火後はトリガ更新しない

        # 無効状態ではトリガ更新をスキップ
        if not self._enabled:
            return

        self._update_trigger()
        if self._session is not None:
            self._session.on_mouse_button(vk, pressed)

    def _on_scroll(self, delta: int, horizontal: bool) -> None:
        if self._session is not None:
            self._session.on_scroll(delta, horizontal)

    def _on_move(self, dx: int, dy: int) -> None:
        if self._session is not None:
            self._session.on_move(dx, dy)

    # ------------------------------------------------------------------ #
    # トリガ変更 [SPEC-TRIGGER-CHANGE]
    # ------------------------------------------------------------------ #

    def _update_trigger(self) -> None:
        """[SPEC-TRIGGER-CHANGE][SPEC-TRIGGER-CHANGE-SWITCH][SPEC-TRIGGER-COUNT-RESET]"""
        new_trigger = self._best_trigger(self._pressed)
        if new_trigger == self._active_trigger:
            return

        # 押し増しかどうか判定 [SPEC-TRIGGER-ACTION-PUSHONLY]
        # 旧トリガ ⊂ 新トリガ（新規VKが追加された）→ 押し増し
        old_trigger = self._active_trigger
        if new_trigger is not None and old_trigger is not None:
            is_pushon = old_trigger < new_trigger  # 真部分集合なら押し増し
        elif new_trigger is not None and old_trigger is None:
            is_pushon = True   # トリガなし → 新トリガ: フック開始＝押し増し
        else:
            is_pushon = False  # 押し減らしまたはフック終了

        # 旧セッション終了 [SPEC-TRIGGER-CHANGE-SWITCH]
        # 押し増し変更時はフリック抑制 [SPEC-TRIGGER-ACTION-DELAY]
        if self._session is not None:
            self._session.on_trigger_release(suppress_flick=is_pushon)
            self._end_session()

        self._active_trigger = new_trigger

        if new_trigger is None:
            return

        rec = self._trigger_map.get(new_trigger)
        if rec is None:
            self._active_trigger = None
            return

        # 新セッション開始 [SPEC-TRIGGER-CHANGE-SWITCH][SPEC-TRIGGER-COUNT-RESET]
        self._session = HookSession(
            record=rec,
            od=self._od,
            default_threshold=self._default_threshold,
            delay_time=self._delay_time,
            jitter_threshold=self._jitter_threshold,
            repeat_interval=self._repeat_interval,
            is_pushon=is_pushon,
        )
        self._notify_handler()

    def _end_session(self) -> None:
        self._session = None
        self._notify_handler()

    def _check_toggle_hotkey(self) -> bool:
        """
        ホットキーが完成した（最後の1キーが揃った）かを判定し、
        完成していればトグルを発火して True を返す。

        「最後の1キーが押された瞬間」とは、
        _toggle_hotkey が _pressed の部分集合になった状態を指す。
        複数キーの同時押しに対応。

        伝播停止の方針:
          - enabled=True 時: ホットキーVKは trigger_vks に含まれ伝播停止される。
          - enabled=False 時: ホットキーVKは trigger_vks に含まれず伝播される。
            ユーザーから見てジェスチャ無効中はホットキーが透過して見える。
        """
        if self._toggle_hotkey is None:
            return False
        if not self._toggle_hotkey.issubset(self._pressed):
            return False

        # トグル発火
        self._enabled = not self._enabled

        if not self._enabled:
            # 無効化: アクティブセッションを強制終了 [SPEC-HOOK-RELEASE-GUARANTEE]
            if self._session is not None:
                self._session.on_trigger_release()
                self._session = None
            self._active_trigger = None

        # enabled 変化に伴い trigger_vks を更新（ON/OFF 両方で呼ぶ）
        self._notify_handler()

        if self._on_toggle is not None:
            self._on_toggle(self._enabled)

        return True

    def _best_trigger(self, pressed: set[int]) -> Optional[frozenset]:
        """最長マッチ。[SPEC-CONFLICT-PRIORITY]"""
        best: Optional[frozenset] = None
        best_len = 0
        for trigger in self._trigger_map:
            if trigger.issubset(pressed) and len(trigger) > best_len:
                best = trigger
                best_len = len(trigger)
        return best

    # ------------------------------------------------------------------ #
    # ハンドラへの通知
    # ------------------------------------------------------------------ #

    def _notify_handler(self) -> None:
        """セッション変化時に GestureEventHandler へ最新状態を通知する。"""
        if self._session is not None:
            self._handler.update(
                block_cursor   = self._session.block_cursor(),
                trigger_vks    = self._all_trigger_vks,
                block_keys     = self._session.block_keys(),
                block_scroll_v = self._session.block_scroll_v(),
                block_scroll_h = self._session.block_scroll_h(),
                enabled        = self._enabled,
            )
        else:
            self._handler.update(
                block_cursor   = False,
                trigger_vks    = self._all_trigger_vks,
                block_keys     = frozenset(),
                block_scroll_v = False,
                block_scroll_h = False,
                enabled        = self._enabled,
            )
