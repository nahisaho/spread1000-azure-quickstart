# 05. クリーンアップ

## ローカル / WSL2

Azure リソースは作成していないため、削除するものはありません。ローカルファイルの削除:

```bash
rm -rf data/mp-bandgap.parquet data/features.parquet \
       data/predictions.parquet data/metrics.json \
       data/*.manifest.json .venv
```

## AML Compute Instance を作成した場合

```bash
az group delete -n rg-spread-materials-01 --yes --no-wait
```

完了確認:

```bash
az group exists -n rg-spread-materials-01
```

## Materials Project API キー

API キー自体はダッシュボードから revoke できます: https://next-gen.materialsproject.org/dashboard

漏洩の疑いがある場合は再生成してください。

## コスト確認

```bash
az consumption usage list \
  --start-date $(date -u -d '7 days ago' +%Y-%m-%d) \
  --end-date $(date -u +%Y-%m-%d) \
  --query "[?contains(instanceName, 'materials-01')].[usageStart, meterDetails.meterName, pretaxCost, currency]" \
  -o table
```

想定コストは**ローカル実行なら $0**、AML Compute Instance 30 分でも **$0.10 未満**です。それ以上の課金が計上されている場合は削除忘れのリソースを確認してください。
