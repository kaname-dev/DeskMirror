# DeskMirror

PC の画面を Wi-Fi 経由で Nintendo 3DS の上画面にリアルタイム表示するホームブリュー（CIA）です。  
カスタムファームウェア（Luma3DS 等）上で FBI からインストールして HOME メニューから起動できます。

## Windows で 3DS を「モニター」として使う

3DS を USB/HDMI モニターとして直接認識させることはできません。代わりに **仮想ディスプレイ** を Windows に追加し、その画面を 3DS へ配信します（拡張デスクトップと同じ使い方）。

### セットアップ（初回）

```powershell
.\scripts\setup-virtual-monitor.ps1
```

1. **Virtual Display Driver** をインストール（スクリプト内の winget または [GitHub Releases](https://github.com/VirtualDrivers/Virtual-Display-Driver/releases)）
2. `.\scripts\apply-vdd-resolution.ps1` で **800×480** を登録（下記「解像度について」参照）
3. Windows **設定 → システム → ディスプレイ** で「画面を拡張する」
4. 仮想モニターをメインの横に配置し、ウィンドウをドラッグして使う

### 解像度について（重要）

| 画面 | 解像度 |
|------|--------|
| **3DS 上画面**（実機） | **400×240**（固定） |
| **Windows 仮想モニター**（VDD） | **800×480** を選ぶ（推奨） |

Virtual Display Driver は **400×240 を出せません**（ドライバの最小が **640×480**）。  
**800×480** は 3DS と同じ **5:3** の比率なので、PC 側で歪まず **400×240** に縮小して 3DS へ送ります。

```powershell
.\scripts\apply-vdd-resolution.ps1
```

実行後、VDD Control でドライバを再起動し、表示設定で **800 × 480** を選択してください。

### 配信（仮想モニター → 3DS）

`cast.bat` / `cast-config.json`（`vdd: true`）使用時、**キャスト中だけ**仮想ディスプレイを有効化します（終了時に自動で無効化）。初回は **管理者 (UAC)** の承認が必要です。消えないときは `scripts\vdd-off.bat` を実行してください。手動で常時表示したい場合は `vdd_auto: false` を設定してください。

```powershell
copy cast-config.json.example cast-config.json
cast.bat
```

または IP 指定:

```powershell
start-cast-vdd.bat <3DSのIP>
```

## 使い方（基本）

### 1. 3DS 側

1. PC と 3DS を**同じ Wi-Fi** に接続
2. **DeskMirror** を起動
3. 下画面に表示される **3DS の IP アドレス** をメモ（例: `192.168.1.42`）
4. 「Waiting for PC...」のまま待機

### 2. PC 側

初回のみ Python 依存関係をインストール:

```powershell
pip install -r scripts/requirements-cast.txt
```

送信を開始（`<3DS IP>` は手順1の IP）:

```powershell
# バッチ（ダブルクリック可）
start-cast.bat 192.168.1.42

# または直接
python scripts/pc-cast.py --host 192.168.1.42
```

| オプション | 説明 |
|------------|------|
| `--fps 25` | 送信フレームレート（既定 25、`0` で上限なし） |
| （既定） | **拡張ディスプレイ**（非プライマリ）を自動選択 |
| `--vdd` | **仮想モニター**をキャプチャ（Windows に 3DS 用デスクトップ） |
| `--vdd-auto` / `--no-vdd-auto` | キャスト中のみ VDD を有効化（既定: 有効） |
| `--primary` | メイン画面をキャプチャ（複製モード向け） |
| `--monitor 2` | mss のモニター番号を指定 |
| `--list-monitors` | 接続中のモニター一覧を表示 |
| `--port 7878` | TCP ポート（3DS 側と一致） |

接続が成功すると上画面に PC 画面が表示され、下画面に FPS が表示されます。

### 操作（3DS）

| ボタン | 機能 |
|--------|------|
| **START** | 終了 |

待機中の上画面は **3DS MONITOR** の立体スプラッシュです。**3Dスライダーを上げると**立体表示されます（配信中の PC 画面は 2D）。HOME の CIA バナーは安定のため **2D**（`banner.png`）を使用しています。

## 技術仕様

| 項目 | 値 |
|------|-----|
| 解像度 | 400×240（上画面） |
| 形式 | RGB565 |
| プロトコル | TCP、ポート **7878** |
| フレームヘッダ | magic `3PCS` + width + height |

### フレームレートと画質

- **画質**: 常に 400×240・RGB565（圧縮なし）。下げずに FPS だけ調整可能
- **目安**: 同一 Wi-Fi で **20〜30 FPS** 程度（3DS の描画・Wi-Fi が上限）
- **上げ方**: `python scripts/pc-cast.py --fps 30` または `--fps 0`（上限なし）
- **コツ**: 仮想モニターを **800×480** にすると縮小が1回で済む（5:3 維持）

## 構成

| 項目 | 内容 |
|------|------|
| 3DS | libctru（ソケット・描画） |
| PC | Python 3 + mss + Pillow |
| ビルド | devkitARM / GNU Make |

## 初回セットアップ（Windows）

```powershell
.\scripts\setup-devkitpro.ps1
```

## ビルド

```powershell
.\scripts\build.ps1 -Target cia
```

成果物: `output/DeskMirror.cia`

アイコン生成（任意・ビルド前）:

```powershell
python scripts/generate_assets.py
```

## 実機へのインストール

### FBI 遠隔インストール

```powershell
.\scripts\fbi-serve.ps1 -WebUi -Build
```

または `build-and-start.bat` / `start-server.bat` を使用。

### SD カード

`output/DeskMirror.cia` を FBI でインストール。

## カスタマイズ

`resources/AppInfo` でタイトル・製品コード・タイトル ID を変更します。

```
APP_TITLE = DeskMirror
APP_PRODUCT_CODE = CTR-DMIR
APP_UNIQUE_ID = 0xDMIR3D
```

**重要:** [3dsdb](https://www.3dsdb.com/) 等で未使用の `APP_UNIQUE_ID` / `APP_PRODUCT_CODE` を使ってください。

バナー・アイコン: `python scripts/generate_assets.py` で再生成

- **バナー** (`resources/banner.png`): HOME メニュー・起動時（2D、安定）
- **3D バナー** (`banner.cgfx`): 実験的。一部の本体でフリーズするため既定では無効（`BANNER_3D=1 make cia`）
- **アイコン** (`resources/icon.png`): HOME 下画面の 48×48

## トラブルシューティング

| 症状 | 対処 |
|------|------|
| PC が接続できない | 同一 Wi-Fi / 3DS アプリ起動中 / ファイアウォールで **7878** を許可 |
| 画面が止まる | `--fps` を下げる（例: `--fps 15`） |
| もっと滑らかにしたい | `--fps 30` または `--fps 0`（画質は常に 400×240） |
| 真っ暗 | 3DS IP が正しいか確認 |
| `pip install` エラー | Python 3 を PATH に追加 |

## ディレクトリ構成

```
DeskMirror/
├── source/main.cpp      # 3DS 受信・表示
├── scripts/pc-cast.py   # PC 送信
├── cast.bat             # cast-config.json で PC 送信（推奨）
├── start-cast.bat       # IP 指定で PC 送信
├── resources/           # AppInfo, アイコン, RSF
└── output/              # ビルド成果物
```
