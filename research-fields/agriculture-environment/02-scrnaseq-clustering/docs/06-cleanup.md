# 06 — 片付け

Azure リソースなし、CPU ローカルのみ。

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/agriculture-environment/02-scrnaseq-clustering"
cd "$SCENARIO_DIR"
test -f src/analyze.py || { echo "wrong dir — aborting"; exit 1; }
rm -rf -- "$SCENARIO_DIR/data/pbmc3k_raw.h5ad" "$SCENARIO_DIR/outputs"
deactivate 2>/dev/null; rm -rf "$SCENARIO_DIR/.venv"
```
