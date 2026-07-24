# 06 — 片付け

Azure リソースなし、CPU ローカルのみ。

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/agriculture-environment/03-hyperspectral-1dcnn"
cd "$SCENARIO_DIR"
test -f src/train.py || { echo "abort: wrong directory"; exit 1; }

# 生成ファイルのみ削除 (data/README.md や LICENSE は保持)
rm -f data/*.mat data/*.npy
rm -f outputs/*.pt outputs/*.png outputs/*.csv outputs/*.json
deactivate 2>/dev/null || true
rm -rf .venv
```
