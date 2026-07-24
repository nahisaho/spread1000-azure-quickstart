# 01 — 前提条件

- Python 3.11+ (3.12 推奨)
- Windows / macOS / Linux, CPU のみ

```bash
cd research-fields/math-physics-earth/02-symbolic-regression
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import gplearn; print(gplearn.__version__)"
```
