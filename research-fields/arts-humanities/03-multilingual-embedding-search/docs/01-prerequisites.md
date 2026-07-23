# 01 — 前提条件

- Python 3.10+
- Azure サブスクリプション + Azure OpenAI 利用申請承認済み
- Bash 環境

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

依存: `openai>=2.0`, `faiss-cpu`, `numpy`, `python-dotenv`
