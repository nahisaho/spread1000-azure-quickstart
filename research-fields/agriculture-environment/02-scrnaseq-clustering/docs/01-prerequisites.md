# 01 — 前提条件

- Python 3.10+ (3.12 推奨)
- CPU (3 分程度)
- 初回のみ PBMC 3k データ (~5MB) を自動ダウンロード

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

依存関係:
- `scanpy==1.10.3` — single-cell 解析標準
- `leidenalg==0.10.2` + `igraph==0.11.6` — Leiden クラスタリング
