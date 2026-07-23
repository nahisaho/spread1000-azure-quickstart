# 06 — 片付け

```bash
az group delete -n rg-multiling-demo --yes --no-wait
rm -rf .venv/ data/index.faiss data/index_meta.json outputs/*
```

Azure OpenAI デプロイメントは RG 削除で消えます。**Global Standard デプロイメントは分単位課金** (使わなければコストほぼゼロ) ですが、明示的削除が安心。
