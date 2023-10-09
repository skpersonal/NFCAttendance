# NFCAttendance

## 動作確認デバイス

- PaSoRi RC-S380

## 使い方

**最初に環境変数でSYSTEM_CODEとSERVICE_CODEを指定してください。**

`check4.py`を実行するとGUIが立ち上がります。

出席or退席を選択してから学生証をタッチしてください。

ログはメインウィンドウ下部に表示されます。

"出席チェック"ボタンで過去の出席状況を見ることができます。

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
