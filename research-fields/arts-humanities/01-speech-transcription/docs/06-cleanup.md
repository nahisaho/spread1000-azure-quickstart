# 06 — 片付け

## リソース削除 (課金停止)

```bash
az group delete -n rg-speech-demo --yes --no-wait
```

または Portal → リソースグループ → Delete。

## ローカルクリーンアップ

```bash
rm -rf .venv/ data/*.wav outputs/*
```

## 課金停止の確認

- Portal → Cost Management + Billing → Cost analysis → タグ / RG でフィルタ
- Speech リソースは削除後 30 日は「削除済み」表示、その間 recover 可能
