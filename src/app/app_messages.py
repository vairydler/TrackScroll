# app_messages.py v1.2
"""
アプリ内メッセージ定義。

全コンポーネントが参照するコマンド（Command）・
メッセージ本体（AppMessage）を一元定義する。

v1.0 → v1.1 変更:
  - Destination enum を削除。
    配信方式をブロードキャストとしたため宛先フィールド不要。
  - AppMessage から dest フィールドを削除。
  - ファクトリ関数から dest 引数を削除。
  - 購読方式への移行ポイントを NOTE に明記。

v1.1 → v1.2 変更:
  - GESTURE_TOGGLED コマンドを追加。
    ホットキーによる有効/無効トグル時に GestureCore から送出される。
    params: bool  True=有効化, False=無効化

メッセージフロー（ブロードキャスト方式）:
    各タスク
      └─[post]→ AppCore のメインメッセージキュー（Queue[AppMessage]）
                    └─[broadcast]→ 全登録タスクの post_message(msg)
                                    └─ 各タスクが不要なコマンドを読み捨て

購読方式への移行ポイント:
    AppCore._broadcast(msg) の実装を差し替えるだけで移行できる。
    各タスクに subscribe(commands) を追加し、
    AppCore が登録コマンドと一致するタスクにのみ配信する形にする。
    AppMessage・Command・各タスクの post_message シグネチャは変更不要。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


# ---------------------------------------------------------------------------
# コマンド
# ---------------------------------------------------------------------------

class Command(Enum):
    """
    コマンド種別。

    命名規則:
        GESTURE_* : GestureService が関与するコマンド
        UI_*      : UIタスク（ConsoleApp / TrayApp）が関与するコマンド
        APP_*     : アプリ全体に関わるコマンド

    各タスクは自分が処理するコマンドのみハンドルし、残りは読み捨てる。
    """

    # ------------------------------------------------------------------
    # GESTURE 系
    # ------------------------------------------------------------------

    GESTURE_START = auto()
    """GestureService を起動する。params: None"""

    GESTURE_STOP = auto()
    """GestureService を停止する。params: None"""

    GESTURE_RELOAD_CONFIG = auto()
    """ジェスチャ設定を再読み込みする。params: None"""

    GESTURE_ERROR = auto()
    """
    GestureService 内で回復不能なエラーが発生した。
    params: str  エラーメッセージ
    """

    GESTURE_CONFLICT_WARNING = auto()
    """
    ジェスチャテーブルに競合が検出された。[SPEC-CONFLICT-DETECT]
    params: list[str]  競合の説明文リスト
    """

    GESTURE_INVALID_UP_WARNING = auto()
    """
    移動/スクロール系ジェスチャキーに不正なアップ動作が登録されている。[SPEC-INVALID-UP-DETECT]
    params: list[str]  警告の説明文リスト
    """

    GESTURE_TOGGLED = auto()
    """
    ホットキーによってジェスチャの有効/無効が切り替わった。
    GestureCore → GestureService → UIタスクへ通知される。
    params: bool  True=有効化, False=無効化
    """

    # ------------------------------------------------------------------
    # UI 系
    # ------------------------------------------------------------------

    UI_SHOW_WARNING = auto()
    """
    警告を表示する。
    ConsoleApp: 標準出力に出力。TrayApp: バルーン通知。
    params: str  警告メッセージ
    """

    UI_UPDATE_STATUS = auto()
    """
    状態を更新する。
    ConsoleApp: 標準出力にログ。TrayApp: アイコン・ツールチップ変更。
    params: StatusParams
    """

    UI_NOTIFY = auto()
    """
    通知を表示する。
    ConsoleApp: 標準出力に出力。TrayApp: バルーン通知。
    params: str  通知メッセージ
    """

    # ------------------------------------------------------------------
    # APP 系
    # ------------------------------------------------------------------

    APP_QUIT = auto()
    """アプリ終了を要求する。params: None"""

    APP_ERROR = auto()
    """アプリレベルのエラーを通知する。params: str  エラーメッセージ"""


# ---------------------------------------------------------------------------
# パラメータ型
# ---------------------------------------------------------------------------

class GestureStatus(Enum):
    """GestureService の動作状態。UI_UPDATE_STATUS の params に含まれる。"""
    RUNNING  = auto()   # ジェスチャ有効
    STOPPED  = auto()   # ジェスチャ停止中
    ERROR    = auto()   # エラー状態


@dataclass
class StatusParams:
    """
    UI_UPDATE_STATUS コマンドのパラメータ。
    TrayApp ではアイコンやツールチップの更新に使用する。
    ConsoleApp では status と message をログ出力に使用する。
    """
    status:  GestureStatus
    message: str = ""


# ---------------------------------------------------------------------------
# メッセージ本体
# ---------------------------------------------------------------------------

@dataclass
class AppMessage:
    """
    アプリ内メッセージ。
    各タスクは AppCore.post(msg) を通じてこの形式でポストする。

    Fields
    ------
    command : 実行するコマンド。
    params  : コマンドに付随するパラメータ。省略時は None。
              型は Command ごとのドキュメントを参照。
    """
    command: Command
    params:  Any = field(default=None)


# ---------------------------------------------------------------------------
# ファクトリ関数（よく使うメッセージの簡易生成）
# ---------------------------------------------------------------------------

def msg_gesture_start() -> AppMessage:
    return AppMessage(Command.GESTURE_START)

def msg_gesture_stop() -> AppMessage:
    return AppMessage(Command.GESTURE_STOP)

def msg_gesture_reload() -> AppMessage:
    return AppMessage(Command.GESTURE_RELOAD_CONFIG)

def msg_app_quit() -> AppMessage:
    return AppMessage(Command.APP_QUIT)

def msg_app_error(message: str) -> AppMessage:
    return AppMessage(Command.APP_ERROR, message)

def msg_ui_notify(message: str) -> AppMessage:
    return AppMessage(Command.UI_NOTIFY, message)

def msg_ui_warning(message: str) -> AppMessage:
    return AppMessage(Command.UI_SHOW_WARNING, message)

def msg_ui_status(status: GestureStatus, message: str = "") -> AppMessage:
    return AppMessage(Command.UI_UPDATE_STATUS,
                      StatusParams(status=status, message=message))

def msg_gesture_toggled(enabled: bool) -> AppMessage:
    return AppMessage(Command.GESTURE_TOGGLED, enabled)
