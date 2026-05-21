# File Sorter

ファイル名のキーワード・パターンに応じて、ファイルを自動的にフォルダへ振り分けるシンプルな GUI ツールです。
Python 標準ライブラリ (Tkinter) のみで動作し、Windows 用の単体 EXE としても配布できます。

![Platform](https://img.shields.io/badge/platform-Windows-blue)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Version](https://img.shields.io/badge/version-1.0-brightgreen)

---

## 主な機能

- **3 種類のマッチ方式**
  - キーワード部分一致 — ファイル名に指定文字列を含むものを振り分け
  - 先頭 N 文字 — 拡張子を除いたファイル名の先頭 N 文字でサブフォルダを自動生成
  - 末尾 N 文字除外 — 拡張子を除いた末尾 N 文字を取り除いた部分でサブフォルダを自動生成
- **移動 / コピー** の切り替え
- **プレビュー機能** — 実行前にどのファイルがどこに振り分けられるか確認
- **大文字・小文字の区別** をルールごとに切り替え可能
- **ダークテーマ UI** — Tkinter ベースの落ち着いた色合い
- **ルール永続化** — `rules.json` に自動保存（次回起動時に復元）

---

## ダウンロード（Windows 用 EXE）

ビルド済み EXE は本リポジトリに同梱されています。

- [`releases/v1.0/FileSorter_v1.0.exe`](releases/v1.0/FileSorter_v1.0.exe) (約 9.9 MB)
- ビルド情報・SHA256 ハッシュ: [`releases/v1.0/BUILD_INFO.txt`](releases/v1.0/BUILD_INFO.txt)

ダウンロードしたら任意のフォルダに置いてダブルクリックで起動できます。
インストール不要・Python 不要です。設定ファイル `rules.json` は EXE と同じフォルダに自動作成されます。

---

## ソースから実行する場合

### 必要環境

- Windows / macOS / Linux
- Python 3.9 以上（Tkinter 同梱）

### 起動

```bash
git clone https://github.com/Bunpo2025/File-sorter.git
cd File-sorter
python main.py
```

外部ライブラリは不要です。`requirements.txt` も空（標準ライブラリのみ使用）です。

---

## 使い方

1. **対象フォルダ** に、振り分けたいファイルが入っているフォルダを指定します
2. **振り分け先** に、ファイルを移動／コピーする先のルートフォルダを指定します
3. **振り分けルール** パネルで「＋ ルール追加」をクリックし、マッチ方式を選択
4. **プレビュー** パネルで、どのファイルがどこに振り分けられるかを確認
5. 問題なければ右下の「**実行**」ボタンで一括処理

### マッチ方式の使い分け例

| 方式 | 用途例 |
|---|---|
| **キーワード部分一致** | `invoice` を含むファイルを `invoices/` へ |
| **先頭 N 文字** | `ABC123_xxx.jpg`, `ABC123_yyy.jpg` を `ABC123/` フォルダに自動分類 |
| **末尾 N 文字除外** | `document_001.pdf`, `document_002.pdf` を `document/` フォルダにまとめる |

---

## 自分でビルドする

PyInstaller を使って単体 EXE を生成できます。

```bash
build.bat
```

`build.bat` は以下を自動で行います。

1. `py` ランチャー → `python` → 既定インストール先の順で Python を自動検出
2. PyInstaller が未インストールなら `pip install pyinstaller` を実行
3. `--onefile --windowed` で `dist/FileSorter.exe` を生成

別 PC でも Python さえあれば、そのまま動きます。

---

## プロジェクト構成

```
File-sorter/
├── main.py                    # アプリ本体（Tkinter GUI + 振り分けロジック）
├── build.bat                  # Python 自動検出付きビルドスクリプト
├── FileSorter.spec            # PyInstaller 設定（自動生成）
├── requirements.txt           # （標準ライブラリのみ／空）
├── .gitignore
├── README.md
└── releases/
    └── v1.0/
        ├── FileSorter_v1.0.exe
        └── BUILD_INFO.txt
```

`rules.json` はアプリ起動時に作成・更新されるユーザー設定のため、リポジトリには含まれません。

---

## バージョン

現在: **v1.0**

リリース履歴は [Tags](https://github.com/Bunpo2025/File-sorter/tags) を参照してください。
