# 06 — 片付け

ローカル CPU のみ。Azure リソースなし。

```bash
cd research-fields/math-physics-earth/02-symbolic-regression
test -f src/train.py || { echo "wrong dir — aborting cleanup"; exit 1; }
rm -rf data/*.npz outputs/*
deactivate && rm -rf .venv
```
