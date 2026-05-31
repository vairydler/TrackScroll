# マウスジェスチャドライバ リファクタリング作業工程資料

**作成日:** 2025-05-18  
**更新日:** 2025-05-23 (Rev.4)  
**対象バージョン:** gesture_core.py v2.3.0 / main.py v2.0 ほか現行一式

---

## 目的

現行のジェスチャドライバをタスクトレイ常駐アプリとして再構成する。
具体的には以下の3点を達成する。

1. **ジェスチャ機能のカプセル化** — ジェスチャ処理をGUI非依存の単体モジュールとして独立させる
2. **アプリ内メッセージキューの導入** — コンポーネント間通信を統一されたフォーマットで行う
3. **タスクトレイGUIの追加** — システムトレイアイコン・メニューによる常駐アプリ化

---

## 成果物ファイル一覧（完成形）

| ファイル | 役割 | 新規/既存 |
|---|---|---|
| `app_messages.py` | メッセージ定義（コマンド・型） | 新規 |
| `app_core.py` | AppTask 基底クラス・AppCore（メインスレッド・ルーティング・タスク管理） | 新規 |
| `gesture_service.py` | ジェスチャ機能の外部向けファサード | 新規 |
| `console_app.py` | コンソール版タスク（ログ出力） | 新規 |
| `tray_app.py` | タスクトレイGUI | 新規 |
| `main.py` | エントリポイント（タスク生成・登録・引数で版切り替え） | 改修 |
| `gesture_core.py` | ジェスチャコアエンジン（on_warning コールバック追加） | 改修 |
| `gesture_event.py` | イベント定義（変更なし） | 既存 |
| `gesture_action.py` | アクション定義（変更なし） | 既存 |
| `gesture_builder.py` | テーブルビルダー（変更なし） | 既存 |
| `gesture_config.py` | 設定ファイル（変更なし） | 既存 |
| `input_driver.py` | 入力ドライバ（変更なし） | 既存 |
| `output_driver.py` | 出力ドライバ（変更なし） | 既存 |
| `vk_codes.py` | キーコード定数（変更なし） | 既存 |
| `spec_overall.md` | 全体仕様書 | 新規 |
| `spec_gesture.md` | ジェスチャ仕様書（現行 gesture_spec_v2_6.md を改訂） | 改訂 |
| `spec_gui.md` | GUI仕様書 | 新規 |

---

## アーキテクチャ概要

```
main.py  (--console / --gui で切り替え)
  └── AppCore（メインスレッド）
        ├── メインメッセージキュー（(sender, AppMessage) の Queue）
        ├── GestureService（ジェスチャタスク）
        │     ├── GestureCore
        │     ├── GestureEventHandler
        │     ├── InputDriver
        │     └── OutputDriver
        └── ConsoleApp  ← --console 時
            または
            TrayApp     ← --gui 時
              └── pystray（タスクトレイ）
```

### メッセージフロー

```
各タスク
  └─[_post_to_core(msg)]→ AppCore のメインメッセージキュー（sender が自動付与される）
                              └─[broadcast]→ 送信元を除く全タスクの post_message(msg)
                                              └─ 各タスクが不要なコマンドを読み捨て
```

`AppMessage` の構造：

```python
@dataclass
class AppMessage:
    command: Command    # コマンド（enum）
    params: Any         # パラメータ（任意のオブジェクト、省略可）
```

**sender の管理方針：**
- `AppCore.add_task(task, name)` でタスクを登録する際に name を一元管理する
- `functools.partial` で sender 名をバインドした `_post_to_core` 関数を各タスクに渡す
- 各タスクは `self._post_to_core(msg)` を呼ぶだけでよく、自分の名前を意識しない
- ブロードキャスト時に送信元（sender）を除外することで自己ループを防止する

**ブロードキャスト方式の採用理由：**
タスク数が少なく（3〜5本）、タスクとコマンドが実質1対1対応のため、
宛先フィールドによるルーティングは冗長と判断した。
将来タスクが増えた場合は `AppCore._broadcast()` を購読方式に差し替えることで対応できる。
その際 `AppMessage`・`Command`・各タスクの `post_message` シグネチャは変更不要。

---

## 工程一覧

| # | 工程名 | 主な作業内容 | 依存工程 |
|---|---|---|---|
| 1 | メッセージ定義 | `app_messages.py` の作成 | なし |
| 2 | タスク共通インターフェース設計 | `AppTask` 基底クラスの定義（`app_core.py` 内） | 工程1 |
| 3 | GestureService 作成 | ジェスチャ機能のカプセル化・エラー通知をメッセージに変換 | 工程2 |
| 4 | ConsoleApp 作成 | コンソール版タスク実装 | 工程2 |
| 5 | AppCore 作成 | メインスレッド・ルーティング実装 | 工程3・4 |
| 6 | main.py 改修 | タスク生成・登録・引数処理のみに簡略化 | 工程5 |
| 7 | コンソール版 動作確認 | GUIなしで全ジェスチャ動作・メッセージルーティングを確認 | 工程6 |
| 8 | 仕様書作成（フェーズ1） | 全体・ジェスチャ仕様書の執筆・GUI仕様書の骨格 | 工程7 |
| 9 | TrayApp 作成 | タスクトレイGUI実装（pystray使用） | 工程8 |
| 10 | GUI版 動作確認 | GUI込みで全確認項目を再検証 | 工程9 |
| 11 | 仕様書追記（フェーズ2） | spec_gui.md 完成・spec_overall.md 更新 | 工程10 |

---

## 各工程の詳細

---

### 工程1：メッセージ定義（`app_messages.py`）

**目的**  
全コンポーネントが参照する宛先・コマンドの定義を一元化する。

**作成内容**

- `Command` enum — コマンド種別（下表参照）
- `GestureStatus` enum / `StatusParams` dataclass — `UI_UPDATE_STATUS` のパラメータ型
- `AppMessage` dataclass — `{command, params}` の2フィールド（宛先なし・ブロードキャスト方式）
- ファクトリ関数 — よく使うメッセージの簡易生成（`msg_gesture_start()` など）

**コマンド一覧**

| コマンド | 主な送受信者 | 説明 |
|---|---|---|
| `GESTURE_START` | → GestureService | ジェスチャ開始 |
| `GESTURE_STOP` | → GestureService | ジェスチャ停止 |
| `GESTURE_RELOAD_CONFIG` | → GestureService | 設定再読み込み |
| `GESTURE_ERROR` | GestureService → | エラー通知（paramsにメッセージ） |
| `GESTURE_CONFLICT_WARNING` | GestureService → | 競合警告 |
| `GESTURE_INVALID_UP_WARNING` | GestureService → | 不正アップ動作警告 |
| `UI_SHOW_WARNING` | → UIタスク | 警告表示（バルーン or コンソール） |
| `UI_UPDATE_STATUS` | → UIタスク | 状態更新（アイコン or コンソールログ） |
| `UI_NOTIFY` | → UIタスク | 通知（バルーン or コンソールログ） |
| `APP_QUIT` | 任意 → AppCore | アプリ終了要求 |
| `APP_ERROR` | 任意 → AppCore | アプリレベルエラー |

ブロードキャスト方式のため「方向」は設計上の慣習であり、強制されない。
各タスクが不要なコマンドを読み捨てることで実質的な宛先制御を行う。

**注意点**
- このファイルは全工程で参照されるため、最初に確定させる
- UI系コマンドは `ConsoleApp` と `TrayApp` が同一コマンドを受け取り、
  それぞれの方法で表現する（コンソールへの出力 / バルーン通知）
- コマンドの追加は後工程でも可能だが、既存コマンドの変更は影響範囲が広い

---

### 工程2：タスク共通インターフェース設計

**目的**  
AppCore がルーティング先として扱う各タスクの共通契約を定義する。

**作成内容（`app_core.py` の冒頭に定義）**

```python
class AppTask(ABC):
    """全タスクが実装する共通インターフェース。"""

    def __init__(self):
        self._post_to_core: Callable[[AppMessage], None] | None = None

    def set_post_to_core(self, fn: Callable[[AppMessage], None]) -> None:
        """AppCore.add_task() から sender バインド済みの post 関数を受け取る。"""
        self._post_to_core = fn

    @abstractmethod
    def post_message(self, msg: AppMessage) -> None:
        """AppCore からメッセージを受け取る唯一の入口。非ブロッキング。"""
        ...

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...
```

**設計方針**
- `post_message` は非ブロッキングとする（タスク内部キューに積んで即返却）
- タスク内部の処理スレッドは各タスクが管理する
- `set_post_to_core` は具象メソッドとして基底クラスに実装し、各タスクでの実装は不要
- `AppCore` は `post_message` を呼ぶだけで、タスクの実装詳細を知らない

---

### 工程3：GestureService 作成（`gesture_service.py`）

**目的**  
現行の `GestureApp`（main.py 内）を独立したタスクとして再構成し、
ジェスチャ処理とGUIを完全分離する。

**現行 main.py からの移管対象**
- `ConfigProvider` クラス
- `OutputDriver`, `InputDriver`, `GestureCore`, `GestureEventHandler` の生成と接続
- `[SPEC-SELF-EVENT-FILTER]` の識別子同期処理
- ジェスチャテーブルロード

**GestureService の責務**
- `AppTask` インターフェースの実装
- `GESTURE_START` / `GESTURE_STOP` / `GESTURE_RELOAD_CONFIG` の受け付け
- 警告検出結果を `GESTURE_CONFLICT_WARNING` / `GESTURE_INVALID_UP_WARNING` としてポスト
- ジェスチャコア内部の `queue.Queue`（イベントキュー）はそのまま維持

**gesture_core.py の変更**
- `_show_popup()` と `import tkinter` を削除
- `GestureCore.load()` に `on_warning` コールバック引数を追加
  - シグネチャ: `(kind: str, messages: list[str]) -> None`
  - `kind` は `"conflict"` または `"invalid_up"`
  - 省略時（None）は警告を無視する

**コンストラクタ**
- `__init__` に引数なし。`set_post_to_core()` 経由で `_post_to_core` を受け取る

---

### 工程4：ConsoleApp 作成（`console_app.py`）

**目的**  
GUIなしで動作確認できるコンソール版UIタスクを実装する。
TrayApp と同一の `AppTask` インターフェースを実装することで、
AppCore からは差し替え可能な存在とする。

**ConsoleApp の責務**
- `AppTask` インターフェースの実装
- `UI_SHOW_WARNING` → 標準出力に警告テキストを出力
- `UI_UPDATE_STATUS` → 標準出力に状態テキストを出力
- `UI_NOTIFY` → 標準出力に通知テキストを出力

**設計方針**
- ロジックは最小限。標準出力への print で十分
- `__init__` に引数なし。`set_post_to_core()` 経由で `_post_to_core` を受け取る
- `APP_QUIT` は AppCore が処理するため、ConsoleApp での処理は不要（読み捨て）
- Ctrl+C（SIGINT）ハンドラはコンソール版専用として `main.py` が設定する
  （TrayApp では コンソールウィンドウが存在しないため SIGINT が届かない）

---

### 工程5：AppCore 作成（`app_core.py`）

**目的**  
メインスレッドでメインメッセージキューを読み出し、
タスクへブロードキャストするルーターを実装する。

**AppCore の責務**
- `add_task(task, name)` によるタスク登録と名前の一元管理
- メインメッセージキュー（`Queue[(sender, AppMessage)]`）の読み出しループ
- 受信した `AppMessage` を送信元を除く全タスクにブロードキャスト
- `APP_QUIT` の受信でタスクを登録逆順に `stop()` して終了
- `APP_ERROR` のログ出力
- ループ検出フェールセーフ（同一 command が連続 N 回でFATAL終了）

**add_task の設計**

```python
def add_task(self, task: AppTask, name: str) -> None:
    # 名前の競合チェック
    if any(n == name for n, _ in self._tasks):
        raise ValueError(f"タスク名が競合しています: {name!r}")
    self._tasks.append((name, task))
    # sender をバインドした post 関数を渡す
    task.set_post_to_core(partial(self._post, sender=name))
```

**ブロードキャスト実装**

```python
def _broadcast(self, sender: str, msg: AppMessage) -> None:
    # 送信元を除く全タスクにブロードキャスト（自己ループ防止）
    # NOTE: 購読方式へ移行するときはこのメソッドのみ差し替える
    for name, task in self._tasks:
        if name == sender:
            continue
        task.post_message(msg)
```

**run() の設計**

```python
def run(self) -> None:
    # 登録順に start()
    for _, task in self._tasks:
        task.start()
    # メッセージループ
    try:
        self._message_loop()
    finally:
        # 登録逆順に stop()
        self._shutdown()
```

**タスクのインスタンス生成は main.py の責務**  
AppCore はタスクの型を知らない。`add_task()` でタスクを受け取るだけ。

---

### 工程6：main.py 改修

**目的**  
`main.py` をエントリポイントとしての最小限の記述に絞る。

**起動引数**

```
python main.py [--console | --gui]
  --console  : コンソール版で起動（デフォルト）
  --gui      : タスクトレイGUI版で起動
```

**改修後の main.py の責務**
- `argparse` による起動引数処理
- タスクインスタンスの生成
- `AppCore.add_task()` によるタスク登録
- コンソール版のみ `signal.SIGINT` ハンドラを設定（GUI版はトレイメニューから終了）
- `AppCore.run()` の呼び出し（ブロッキング）

**main.py のイメージ**

```python
def main():
    args = parse_args()

    app_core = AppCore()
    gesture_service = GestureService()
    app_core.add_task(gesture_service, "GestureService")

    if args.mode == "console":
        signal.signal(signal.SIGINT, lambda s, f: gesture_service._post_to_core(msg_app_quit()))
        ui_task = ConsoleApp()
        app_core.add_task(ui_task, "ConsoleApp")
    else:
        ui_task = TrayApp()
        app_core.add_task(ui_task, "TrayApp")

    app_core.run()  # 内部で登録順に start() → メッセージループ → 逆順に stop()
```

**現行 main.py から削除する処理**
- `ConfigProvider` クラス → `gesture_service.py` へ移管済み
- `GestureApp` クラス → `gesture_service.py` へ移管済み
- `signal` ハンドラの `app.stop()` 直呼び → `AppCore` 経由に変更

---

### 工程7：コンソール版 動作確認

**目的**  
GUIを介さずに、ジェスチャ機能・メッセージルーティングが
正しく動作することを確認する。

**確認項目**

| # | 確認内容 |
|---|---|
| 1 | `python main.py --console` で起動できる |
| 2 | ジェスチャ動作が現行と同等に機能する（既存デバッグスクリプトで確認） |
| 3 | 競合警告・不正アップ警告がコンソールに出力される |
| 4 | Ctrl+C で正常終了する |
| 5 | ダウン発行済みキーのアップが終了時に発行される（SPEC-STOP-CLEANUP） |
| 6 | `GESTURE_RELOAD_CONFIG` を手動ポストして設定再読み込みが動作する |

---

### 工程8：仕様書作成（フェーズ1）

**目的**  
コンソール版完成時点のアーキテクチャを正として仕様書を整備する。
GUI仕様書はこの時点では骨格のみ作成し、工程11で完成させる。

#### spec_overall.md（全体仕様書）

| 節 | 内容 |
|---|---|
| 1. アーキテクチャ概要 | コンポーネント図・依存関係 |
| 2. メッセージキュー仕様 | `AppMessage` 構造・ルーティング規則・sender管理方針 |
| 3. タスク共通インターフェース | `AppTask` の契約 |
| 4. 起動・終了シーケンス | 正常系・異常系・起動引数 |
| 5. エラー通知フロー | GESTURE_ERROR → CORE → UI の経路 |
| 6. 実装上の制約・注意事項 | スレッドモデル・GIL考慮点など |

#### spec_gesture.md（ジェスチャ仕様書）

現行 `gesture_spec_v2_6.md` を基に以下を更新：

- エラー通知手段の変更（tkinter → メッセージポスト）を反映
- `GestureService` としての外部インターフェースを追記
- バージョンを 2.7 に更新

#### spec_gui.md（GUI仕様書・骨格のみ）

| 節 | 内容 |
|---|---|
| 1. 概要 | GUI版の位置づけ・ConsoleApp との関係 |
| 2〜以降 | TBD（工程11で記述） |

---

### 工程9：TrayApp 作成（`tray_app.py`）

**目的**  
pystray を用いたタスクトレイ常駐GUIを実装する。
`ConsoleApp` と同一の `AppTask` インターフェースを実装し、
AppCore からは差し替えのみで動作する。

**依存ライブラリ**
- `pystray` — タスクトレイアイコン管理
- `Pillow` — トレイアイコン画像生成

**TrayApp の責務**
- `AppTask` インターフェースの実装
- トレイアイコン表示・右クリックメニュー
- `UI_UPDATE_STATUS` によるアイコン・ツールチップ変更
- `UI_NOTIFY` / `UI_SHOW_WARNING` によるバルーン通知
- メニュー操作（有効/無効切替・終了など）から `APP_QUIT` 等をメインメッセージキューにポスト

**初期メニュー構成（案）**
```
[アイコン右クリック]
  ├── ジェスチャ: 有効  ← トグル
  ├── ─────────────
  └── 終了
```

**設計方針**
- pystray のイベントループはバックグラウンドスレッドで実行
- GUIへのコマンドはすべて `post_message` 経由で受け取る（スレッドセーフ）
- `__init__` に引数なし。`set_post_to_core()` 経由で `_post_to_core` を受け取る
- 終了手段はトレイメニューの「終了」のみ。SIGINT は届かないため対応しない

---

### 工程10：GUI版 動作確認

**目的**  
TrayApp を追加した状態で全項目を再検証する。

**確認項目**

| # | 確認内容 |
|---|---|
| 1 | `python main.py --gui` で起動し、タスクトレイにアイコンが表示される |
| 2 | ジェスチャ動作が `--console` 版と同等に機能する |
| 3 | 競合警告・不正アップ警告がバルーン通知として表示される |
| 4 | トレイメニューから終了が正常に完了する |
| 5 | ダウン発行済みキーのアップが終了時に発行される（SPEC-STOP-CLEANUP） |
| 6 | `--console` に戻しても引き続き正常動作する（TrayApp 追加による副作用がない） |

---

### 工程11：仕様書追記（フェーズ2）

**目的**  
GUI版完成後に spec_gui.md を完成させ、spec_overall.md を最新化する。

#### spec_gui.md（完成版）

| 節 | 内容 |
|---|---|
| 1. 概要 | GUI版の位置づけ・ConsoleApp との関係 |
| 2. タスクトレイアイコン | アイコン仕様・状態別表示 |
| 3. 右クリックメニュー | 項目・動作定義 |
| 4. バルーン通知 | 通知種別・表示条件 |
| 5. 受信コマンド一覧 | `UI_*` コマンドの動作定義 |
| 6. 送信メッセージ一覧 | GUI操作から発行されるコマンド |

---

## 各工程でクロードに渡す共通入力

各工程の会話で、以下のファイルをプロジェクトの共通入力として設定する。

### 全工程共通

| ファイル | 目的 |
|---|---|
| `app_messages.py` | コマンド定義の参照（工程1完了後） |
| `gesture_spec_v2_6.md` | ジェスチャ仕様の参照 |
| `refactoring_plan.md` | 本資料 |

### 工程別追加ファイル

| 工程 | 追加ファイル |
|---|---|
| 工程3 | `gesture_core.py`, `gesture_event.py`, `gesture_action.py`, `gesture_builder.py`, `gesture_config.py`, `input_driver.py`, `output_driver.py`, `main.py` |
| 工程4 | （追加なし） |
| 工程5 | `gesture_service.py`（工程3成果物）, `console_app.py`（工程4成果物） |
| 工程6 | `app_core.py`（工程5成果物）, `main.py` |
| 工程7 | 全成果物（コンソール版） |
| 工程8 | 全成果物（コンソール版） |
| 工程9 | `app_core.py`, `app_messages.py`, `console_app.py`（差し替え参考） |
| 工程10 | 全成果物（GUI版含む） |
| 工程11 | 全成果物 |

---

## バージョン管理方針

新規ファイルは `v1.0` から開始する。  
既存ファイルを改修する場合はマイナーバージョンを上げる（例: `main.py v2.0` → `v2.1`）。  
工程ごとの成果物はファイル先頭コメントにバージョンを明記する。

---

## 依存ライブラリ追加分

```
pystray   # 工程9から必要
Pillow    # 工程9から必要
```

いずれも pip でインストール可能。Windows 環境で動作確認済みのライブラリを選択している。

---

*以上*
