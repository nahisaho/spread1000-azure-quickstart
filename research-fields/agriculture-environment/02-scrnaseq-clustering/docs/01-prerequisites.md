# 01 — 前提条件

- Python 3.10+ (3.12 推奨)
- CPU (3 分程度)
- 初回のみ PBMC 3k データ (~5MB) を自動ダウンロード

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/agriculture-environment/02-scrnaseq-clustering"
cd "$SCENARIO_DIR"
test -f src/analyze.py || { echo "wrong dir — aborting"; exit 1; }
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.in
```

依存関係 (`requirements.in`):
- `scanpy==1.10.3` — single-cell 解析標準
- `igraph==0.11.6` + `python-igraph==0.11.6` — Leiden クラスタリング (`flavor="igraph"`)
- `umap-learn==0.5.6`, `numpy==1.26.4`, `pandas==2.2.2`, `matplotlib==3.9.2`, `seaborn==0.13.2`

> **注意**: `leidenalg` は不要です。本シナリオは `flavor="igraph"` を使用しています。
