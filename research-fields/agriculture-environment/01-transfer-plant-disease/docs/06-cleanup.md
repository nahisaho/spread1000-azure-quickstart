# 06 — 片付け

ローカル CPU のみ、Azure リソースなし。

```bash
# 作業ディレクトリを絶対パスで固定してから実行 (BLOCKING 2)
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/agriculture-environment/01-transfer-plant-disease"
cd "$SCENARIO_DIR"
test -f src/train.py || { echo "wrong dir; abort"; exit 1; }
rm -rf -- "$SCENARIO_DIR/data/flowers-102" "$SCENARIO_DIR/outputs"
deactivate 2>/dev/null; rm -rf .venv
```

Flowers102 は初回 330MB DL 済み。再学習しないなら `data/flowers-102/` は消して OK。
