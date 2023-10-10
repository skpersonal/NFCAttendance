# NFCAttendance

## 機能

- 読み取った学籍番号をタイムスタンプと共にcsvに記録する
- 読み取った学籍番号を画面に表示する
- 出席状況を確認する（GUI版のみ、rosterはCanvasLMS形式を想定）

## 動作確認デバイス

- PaSoRi RC-S380
- nfcpyが使用できるデバイスであれば動くと思います

## 使い方

**最初に環境変数でSYSTEM_CODEとSERVICE_CODEを指定してください。**

### GUI

`check4.py`を実行するとGUIが立ち上がります。

出席or退席を選択してから学生証をタッチしてください。

ログはメインウィンドウ下部に表示されます。

"出席チェック"ボタンで過去の出席状況を見ることができます。

### CUI

`check4_headless.py`を実行するとCUIでの操作ができます

GUI版より使える機能が少なく、タッチした時にコンソールに表示する機能と、履歴をcsvに保存する機能しかありません

## 環境構築

### 前提準備(Mac)

[Homebrew](https://brew.sh/)をインストールする

- tcl-tk,libusbのインストール

```bash
brew update
brew install tcl-tk libusb
```

### 本体

```bash
git clone https://github.com/skpersonal/NFCAttendance.git
cd NFCAttendance
pip3 install -r requirements.txt
```
