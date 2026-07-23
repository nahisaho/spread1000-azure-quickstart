# 06 — 片付け

```bash
az group delete -n rg-kobunsho-demo --yes --no-wait
rm -rf .venv/ outputs/*
```

**Azure OpenAI デプロイメント**は RG 削除で一緒に消えます (デプロイメントだけ削除する場合は Azure OpenAI Studio で個別に)。
