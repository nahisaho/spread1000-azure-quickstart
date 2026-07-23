# 01 — 前提条件

- Python 3.10+ (3.12 推奨)
- CPU (数分〜10 分)
- 初回のみ Fashion-MNIST 30MB を自動ダウンロード

## インストール

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```

## 確認

```bash
python -c "import torch, torchvision; print(torch.__version__, torchvision.__version__)"
```
