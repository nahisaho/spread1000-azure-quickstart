# 01 — 前提条件

- Python 3.10+ (3.12 推奨)
- CPU (2 分)
- 追加データダウンロード不要 (`src/dataset.py` が合成)

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```
