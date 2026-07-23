# 01 — 前提条件

## 環境

- Python 3.10+ (3.12 推奨)
- Windows / macOS / Linux, CPU のみで OK

## インストール

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

python -m pip install --upgrade pip
python -m pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```

## 動作確認

```bash
python -c "import torch, numpy, sklearn, scipy; print(torch.__version__)"
```
