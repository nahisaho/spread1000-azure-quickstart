# 01 — 前提条件

## 環境

- Python 3.10 以上 (3.12 推奨)
- Windows / macOS / Linux
- CPU のみで OK (数分〜10 分)

## インストール

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```

## 動作確認

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

`2.7.1+cpu False` と出れば OK。
