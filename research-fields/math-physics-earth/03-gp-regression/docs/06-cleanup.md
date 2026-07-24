# 06 — 片付け

ローカル CPU のみ。Azure リソースなし。

```bash
cd "$(git rev-parse --show-toplevel)/research-fields/math-physics-earth/03-gp-regression"
rm -rf outputs/*
test -f src/train.py && deactivate && rm -rf .venv
```
