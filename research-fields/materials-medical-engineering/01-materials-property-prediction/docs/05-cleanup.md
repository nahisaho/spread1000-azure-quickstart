# 05. クリーンアップ

## ローカル / WSL2 / macOS

本教材は Azure リソースを一切作成しません。ローカルの生成物のみ削除:

```bash
rm -rf data/mp-bandgap.parquet data/features.parquet \
       data/predictions.parquet data/metrics.json \
       data/model_xgboost.ubj data/split_ids.json \
       data/parity.png data/*.manifest.json .venv
```

## AML Compute Instance を自分で用意した場合

本教材はワークスペースやリソースグループを作らないため、ここで扱うのは**自分で作成した Compute Instance の停止・削除**のみです。

```bash
# Compute Instance を停止 (課金停止)
az ml compute stop --name <ci-name> \
  --resource-group <your-existing-rg> --workspace-name <your-existing-ws>

# 完全に削除
az ml compute delete --name <ci-name> \
  --resource-group <your-existing-rg> --workspace-name <your-existing-ws> --yes
```

> [!DANGER]
> **`az group delete` を安易に使わないでください**。本教材は資源グループを作成しないため、既存の RG を丸ごと削除すると本教材と無関係な資産まで消える可能性があります。同 RG に本教材専用の Compute Instance を作った場合でも、必ず名前指定で個別に削除してください。

## Materials Project API キー

API キー自体はダッシュボードから revoke できます: https://next-gen.materialsproject.org/dashboard

漏洩の疑いがある場合は再生成してください。

## コスト確認 (AML Compute Instance を使った場合のみ)

```bash
az consumption usage list --include-meter-details \
  --start-date $(date -u -d '7 days ago' +%Y-%m-%d) \
  --end-date $(date -u +%Y-%m-%d) \
  --query "[?contains(instanceName || '', '<ci-name>')].[usageStart, meterDetails.meterName, pretaxCost, currency]" \
  -o table
```

想定コストは**ローカル実行なら $0**、AML Compute Instance E2s_v3 を idle shutdown ありで 30 分利用した場合 **$0.10 前後**です (Storage / Log Analytics / 通信料は別途)。それ以上の課金が計上されている場合は idle shutdown 未設定・別途起動した VM / GPU リソースが残っていないか確認してください。
