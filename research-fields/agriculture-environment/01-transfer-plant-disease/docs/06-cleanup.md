# 06 — 片付け

ローカル CPU のみ、Azure リソースなし。

```bash
rm -rf data/ outputs/*
deactivate && rm -rf .venv
```

Flowers102 は初回 330MB DL 済み。再学習しないなら `data/flowers-102/` は消して OK。
