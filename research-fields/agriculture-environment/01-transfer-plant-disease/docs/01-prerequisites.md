# 01 — 前提条件

- Python 3.10+ (3.12 推奨)
- CPU (5-10 分)
- 初回のみ Flowers102 ~330MB + ResNet18 重み ~44MB のダウンロード

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```

```bash
python -c "import torch, torchvision; print(torch.__version__, torchvision.__version__)"
```
