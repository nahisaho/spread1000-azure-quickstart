# 01 — 前提条件

- Python 3.10+
- CPU (3-10 分、パラメータ次第)
- 初回のみ MedMNIST PathMNIST 自動 DL (~205MB)

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```
