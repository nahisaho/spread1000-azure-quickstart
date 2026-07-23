# 01 — 前提条件

- Python 3.10+
- Azure サブスクリプション
- インターネット接続
- Bash 環境 (WSL2 / macOS / Linux / Cloud Shell)

## Python 環境

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## OS 別の追加パッケージ

Azure Speech SDK は OpenSSL の共有ライブラリに依存します。

- **Ubuntu/Debian**: `sudo apt install -y libssl-dev libasound2t64` (Ubuntu 24.04) または `libasound2` (22.04)
- **macOS**: 追加不要
- **Windows**: PowerShell では `pip install azure-cognitiveservices-speech` で OK
